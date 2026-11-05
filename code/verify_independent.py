#!/usr/bin/env python3
"""Independent verifier (Section 11 method diversity).
Three implementations sharing no code with the builder:
 (1) server-side ArcGIS queries against the live service;
 (2) a pyarrow recount of the raw snapshot (no pandas), with all
     windows computed by raw epoch arithmetic against fixed UTC
     boundary instants;
 (3) a matplotlib.path point-in-polygon re-assignment of precincts
     (the builder used shapely STRtree), recomputing the zone-era
     control agreement and the 2025 incident precinct shares.
Compares all against stats.json. Prints PASS/FAIL per check.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pyarrow.parquet as pq
import requests
from matplotlib.path import Path as MplPath

HERE = Path(__file__).resolve()
PKG = HERE.parents[1]
STACK = HERE.parents[2] / "stack" / "nashville"
BASE = "https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Metro_Nashville_Police_Department_Incidents_view/FeatureServer/0"
stats = json.loads((PKG / "stats.json").read_text())
checks = []
CT = ZoneInfo("America/Chicago")

def check(name, ok, detail=""):
    checks.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")

def ms(y, m, d):
    return int(datetime(y, m, d, tzinfo=CT).astimezone(timezone.utc).timestamp() * 1000)

def q(params):
    params = dict(params)
    if "outStatistics" in params:
        params["outStatistics"] = json.dumps(params["outStatistics"])
    r = requests.get(BASE + "/query", params=params, timeout=180)
    r.raise_for_status()
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"])
    return d

# --- (1) server-side ---
live = q({"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
check("server count (live service updates daily; drift-tolerant)",
      abs(live - stats["rows"]) <= 3000, f"live now {live} vs snapshot {stats['rows']}")

def tslit(y, m, d):
    dt = datetime(y, m, d, tzinfo=CT).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

for y in (2019, 2025):
    c = q({"where": f"Incident_Occurred >= timestamp '{tslit(y,1,1)}' AND Incident_Occurred < timestamp '{tslit(y+1,1,1)}'",
           "returnCountOnly": "true", "f": "json"})["count"]
    snap = stats["full_years"][str(y)]["records"]
    check(f"server full-year {y} record count (drift-tolerant)",
          abs(c - snap) / snap <= 0.015, f"server {c} vs snapshot {snap}")

d = q({"where": "1=1", "groupByFieldsForStatistics": "Offense_NIBRS",
       "outStatistics": [{"statisticType": "count", "onStatisticField": "OBJECTID", "outStatisticFieldName": "n"}],
       "f": "json"})
server_codes = {f["attributes"]["Offense_NIBRS"]: f["attributes"]["n"] for f in d["features"]}
ok_codes = 0
for code in ("740", "13B", "23F", "240", "120", "290"):
    snap = stats["code_counts_all_rows"][code]
    if abs(server_codes.get(code, 0) - snap) / snap <= 0.02:
        ok_codes += 1
check("server groupBy code counts within 2 percent for 6 headline codes",
      ok_codes == 6, f"{ok_codes}/6 within tolerance (740 server {server_codes.get('740')} vs snapshot {stats['code_counts_all_rows']['740']})")

zn = q({"where": "Zone IS NOT NULL", "returnCountOnly": "true", "f": "json"})["count"]
check("server Zone-known count (geography break is in the source, not the pull)",
      abs(zn - 353882) / 353882 <= 0.01, f"server {zn} vs snapshot 353,882")

# --- (2) pyarrow recount, raw epoch arithmetic ---
t = pq.read_table(STACK / "snapshots" / "2026-11-04" / "mnpd_incidents_raw.parquet")
check("pyarrow row count", t.num_rows == stats["rows"], f"{t.num_rows}")
inc = t.column("Incident_Number").to_pylist()
check("pyarrow distinct incidents", len(set(inc)) == stats["distinct_incidents"],
      f"{len(set(inc)):,}")
occ = np.array(t.column("Incident_Occurred").to_pylist(), dtype="int64")
codes = [c.strip() if isinstance(c, str) else "" for c in t.column("Offense_NIBRS").to_pylist()]

def cnum(c):
    dd = ""
    for ch in c:
        if ch.isdigit():
            dd += ch
        else:
            break
    return int(dd) if dd else -1

nums = np.array([cnum(c) for c in codes])
is_local = (nums >= 600) & (nums <= 899)
is_crim = (nums >= 0) & ~is_local
check("pyarrow class totals", int(is_crim.sum()) == stats["code_classes"]["nibrs_criminal_rows"]
      and int(is_local.sum()) == stats["code_classes"]["mnpd_local_rows"],
      f"criminal {int(is_crim.sum())}, local {int(is_local.sum())}")
for y, expect in ((2023, stats["trend"]["criminal_jan_oct_2023"]),
                  (2025, stats["trend"]["criminal_jan_oct_2025"]),
                  (2026, stats["trend"]["criminal_jan_oct_2026"])):
    m = (occ >= ms(y, 1, 1)) & (occ < ms(y, 11, 1)) & is_crim
    check(f"pyarrow Jan-Oct {y} criminal records (epoch window)", int(m.sum()) == expect,
          f"{int(m.sum())} vs {expect}")
st = t.column("Incident_Status_Description").to_pylist()
unf = sum(1 for v in st if v == "UNFOUNDED")
check("pyarrow UNFOUNDED total", unf == stats["status"]["all_records"]["unfounded"], f"{unf:,}")
unf_local = sum(1 for v, l in zip(st, is_local) if v == "UNFOUNDED" and l)
check("pyarrow UNFOUNDED within local codes", unf_local == stats["status"]["mnpd_local"]["unfounded"],
      f"{unf_local:,}")
pk = t.column("Primary_Key").to_pylist()
from collections import Counter
pkc = Counter(pk)
coll = sum(1 for v in pkc.values() if v > 1)
check("pyarrow Primary_Key collision keys", coll == stats["traps"]["primary_key_not_unique"]["collision_keys"],
      f"{coll} keys")

# --- (3) matplotlib.path spatial re-assignment ---
geo = json.loads((PKG / "data" / "precinct_boundaries.geojson").read_text())
NAME = {"EAST": "East", "MADISON": "Madison", "NORTH": "North", "WEST": "West",
        "SOUTHEAST": "Southeast", "MIDTOWN HILLS": "Midtown Hills", "SOUTH": "South",
        "HERMITAGE": "Hermitage", "CENTRAL": "Central"}
paths = []
for f in geo["features"]:
    geom = f["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        paths.append((NAME[f["properties"]["PrecinctName"]], MplPath(np.array(poly[0]))))

lat = np.array(t.column("Latitude").to_pylist(), dtype="float64")
lon = np.array(t.column("Longitude").to_pylist(), dtype="float64")
zone = np.array(t.column("Zone").to_pylist(), dtype="float64")
Z2P = {1: "West", 2: "East", 3: "South", 4: "Central", 5: "Hermitage",
       6: "North", 7: "Madison", 8: "Midtown Hills", 9: "Southeast"}

def mpl_assign(idx):
    pts = np.column_stack([lon[idx], lat[idx]])
    res = np.full(len(idx), None, dtype=object)
    for name, path in paths:
        hit = path.contains_points(pts)
        res[hit & (res == None)] = name
    return res

ctrl_idx = np.where(~np.isnan(zone) & ~np.isnan(lat) & (lat != 0))[0]
ctrl_idx = ctrl_idx[::7]  # deterministic every-7th sample of the control population
sp = mpl_assign(ctrl_idx)
zp = np.array([Z2P[int(zone[i] // 100)] for i in ctrl_idx])
both = sp != None
agree = float((sp[both] == zp[both]).mean())
builder_agree = stats["geography"]["spatial_control_incidents"]["agreement_zone_derived_vs_spatial"]
check("mpl-path zone-era control agreement (sampled, independent polygon code)",
      abs(agree - builder_agree) <= 0.01,
      f"sample agreement {agree:.4f} on {int(both.sum()):,} sampled rows vs builder {builder_agree}")

idx25 = np.where((occ >= ms(2025, 1, 1)) & (occ < ms(2026, 1, 1)) & ~np.isnan(lat) & (lat != 0))[0]
sp25 = mpl_assign(idx25)
known25 = sp25 != None
from collections import Counter as C2
c25 = C2(sp25[known25])
tot25 = sum(c25.values())
max_dev = 0.0
for r in stats["fusion_triad_2025"]["by_precinct"]:
    share = c25[r["precinct"]] / tot25
    max_dev = max(max_dev, abs(share - r["incidents_share_2025_all_records"]))
check("mpl-path 2025 incident precinct shares vs builder (max deviation)",
      max_dev <= 0.005, f"max deviation {max_dev:.4f} across 9 precincts")

fails = [c for c in checks if not c[1]]
print(f"\n{len(checks) - len(fails)}/{len(checks)} checks pass")
out = {"checks": [{"name": n, "pass": ok, "detail": d} for n, ok, d in checks],
       "passed": len(checks) - len(fails), "total": len(checks)}
(PKG / "data" / "verify_independent_output.json").write_text(json.dumps(out, indent=2))
if fails:
    raise SystemExit(1)
