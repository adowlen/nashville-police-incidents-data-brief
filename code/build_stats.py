#!/usr/bin/env python3
"""Builder: MNPD Incidents cleaned layer + stats.json.

Reads the 2026-11-04 raw snapshot of the Metro Nashville Police
Department Incidents layer and, for the fusion comparisons, the
deposited Nashville stack layers mnpd_calls_2025_clean (calls ledger,
2025) and traffic_accidents_clean (crash ledger, 2019-2026), plus the
official Police Precinct Boundaries polygons archived in this package
(data/precinct_boundaries.geojson, pulled by code/pull_boundaries.py).
Writes:
  stack/nashville/layers/mnpd_incidents_clean.parquet
  <package>/stats.json and the package data panels (CSV) into data/.
Definitions (agency metadata v2.0, 2023-06-13, archived at
data/source-metadata.pdf): an incident is one or more crimes committed
by an individual or group acting in concert at the same time and
place; the layer's grain, verified against the data, is one row per
offense-victim record within an incident (Primary_Key concatenates
Incident_Number, Offense_Number and Victim_Number). All trend figures
are offense records; distinct incidents are counted separately where
stated. Time is Incident_Occurred read in America/Chicago.
Code classes follow the metadata's own Appendix D structure:
  - "NIBRS criminal offense codes": the FBI NIBRS list (09A-90Z).
  - "MNPD local incident-type codes": the 610-850 series the metadata
    appends after the NIBRS list (matter of record, found/lost and
    recovered property, non-criminal deaths, overdoses, transports).
    Six codes inside that series name criminal conduct (64A, 64B,
    700, 710, 730, 850); they are counted and the split is re-run
    with them reclassified as a sensitivity check.
Cleaning never deletes rows: sentinel/invalid values are mapped to
unknown and flagged. Section 10.1 assertions run inline before stats
are written; a failed assertion aborts the build.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

HERE = Path(__file__).resolve()
PKG = HERE.parents[1]
STACK = HERE.parents[2] / "stack" / "nashville"
RAW = STACK / "snapshots" / "2026-11-04" / "mnpd_incidents_raw.parquet"
CLEAN = STACK / "layers" / "mnpd_incidents_clean.parquet"
CALLS = STACK / "layers" / "mnpd_calls_2025_clean.parquet"
ACC = STACK / "layers" / "traffic_accidents_clean.parquet"

df = pd.read_parquet(RAW)
N = len(df)
assert N > 900000, N
assert df["OBJECTID"].is_unique

out = df.copy()
occ = pd.to_datetime(df["Incident_Occurred"], unit="ms", utc=True).dt.tz_convert("America/Chicago")
rep = pd.to_datetime(df["Incident_Reported"], unit="ms", utc=True).dt.tz_convert("America/Chicago")
out["occurred_local"] = occ
out["reported_local"] = rep
out["year"] = occ.dt.year
out["month"] = occ.dt.strftime("%Y-%m")
assert occ.min() >= pd.Timestamp("2019-01-01", tz="America/Chicago")
assert occ.max() <= pd.Timestamp("2026-11-04 23:59", tz="America/Chicago")

# --- Code classes (Appendix D structure) ---
codes = df["Offense_NIBRS"].astype("string").str.strip()
out["nibrs_code"] = codes

def code_num(c):
    if c is None or (isinstance(c, float) and np.isnan(c)) or pd.isna(c):
        return -1
    d = ""
    for ch in str(c):
        if ch.isdigit():
            d += ch
        else:
            break
    return int(d) if d else -1

num = codes.map(code_num)
LOCAL_BLOCK_CRIMINAL = {"64A", "64B", "700", "710", "730", "850"}
code_class = np.where(codes.isna(), "unknown",
              np.where(num.between(600, 899), "mnpd_local", "nibrs_criminal"))
out["code_class"] = code_class
n_unknown_code = int((code_class == "unknown").sum())
n_local = int((code_class == "mnpd_local").sum())
n_crim = int((code_class == "nibrs_criminal").sum())
assert n_unknown_code + n_local + n_crim == N
local_block_criminal_rows = int(codes.isin(LOCAL_BLOCK_CRIMINAL).sum())

# 10.1.4 categorical exhaustiveness: full Counter of the code field.
code_counter_all = codes.value_counts(dropna=False)
assert int(code_counter_all.sum()) == N
code_counts = {("null" if pd.isna(k) else str(k)): int(v) for k, v in code_counter_all.items()}

APPENDIX_D = set("""09A 09B 09C 100 11A 11B 11C 11D 120 13A 13B 13C 13D 200 210 220
23A 23B 23C 23D 23E 23F 23G 23H 240 250 26A 26B 26C 26D 26E 26F 26G 270 280 290
35A 35B 36A 36B 370 39A 39B 39C 39D 40A 40B 40C 510 520 610 620 630 640 64A 64B
650 660 680 685 690 695 700 710 715 720 730 735 740 750 760 770 780 790 800 810
820 850 90A 90B 90C 90D 90E 90F 90G 90H 90I 90J 90Z""".split())
observed_codes = {str(k) for k in code_counter_all.index if not pd.isna(k)}
codes_not_in_appendix = sorted(observed_codes - APPENDIX_D)

# --- Traps and cleaning flags ---
midnight = (occ.dt.hour == 0) & (occ.dt.minute == 0) & (occ.dt.second == 0)
out["midnight_suspect_flag"] = midnight
n_midnight = int(midnight.sum())
lag_days = (rep - occ).dt.total_seconds() / 86400.0
out["report_lag_days"] = lag_days
n_reported_before = int((lag_days < 0).sum())
prefix_year = (df["Incident_Number"] // 10 ** 7)
n_prefix_mismatch = int((prefix_year != out["year"]).sum())
pk_counts = df["Primary_Key"].value_counts()
pk_collision_keys = int((pk_counts > 1).sum())
pk_collision_rows = int(pk_counts[pk_counts > 1].sum())
n_incidents = int(df["Incident_Number"].nunique())

# Victim type: Appendix G codes only; anything else is keying junk.
VICTIM_OK = {"B", "F", "G", "I", "O", "P", "R", "S", "U"}
vt = df["Victim_Type"].astype("string")
out["victim_type_clean"] = vt.where(vt.isin(VICTIM_OK))
out["victim_type_unknown_flag"] = out["victim_type_clean"].isna()
n_victim_junk = int((vt.notna() & ~vt.isin(VICTIM_OK)).sum())

# ZIP: served as float-strings ('37207.0') on known rows; normalize.
zip_raw = df["ZIP_Code"].astype("string").str.strip()
zip_clean = zip_raw.str.replace(r"\.0$", "", regex=True)
zip_clean = zip_clean.where(zip_clean.str.fullmatch(r"\d{5}").fillna(False))
out["zip_clean"] = zip_clean
out["zip_unknown_flag"] = zip_clean.isna()

# Coordinates: null or 0,0 = unknown; all known values are 3-decimal
# rounded per the metadata (privacy rounding).
lat, lon = df["Latitude"], df["Longitude"]
coords_unknown = lat.isna() | lon.isna() | ((lat == 0) & (lon == 0))
out["coords_unknown_flag"] = coords_unknown
n_coords_outside = int((~coords_unknown & (~lat.between(35.9, 36.5) | ~lon.between(-87.1, -86.4))).sum())

# Patrol geography completeness break (Zone and RPA are jointly
# populated; both end after 2021).
zone_known_by_year = {int(y): round(float(v), 4) for y, v in
                      df["Zone"].notna().groupby(out["year"]).mean().items()}

# --- Spatial precinct assignment (validated below) ---
geo = json.loads((PKG / "data" / "precinct_boundaries.geojson").read_text())
NAME = {"EAST": "East", "MADISON": "Madison", "NORTH": "North", "WEST": "West",
        "SOUTHEAST": "Southeast", "MIDTOWN HILLS": "Midtown Hills", "SOUTH": "South",
        "HERMITAGE": "Hermitage", "CENTRAL": "Central"}
polys, pnames = [], []
for f in geo["features"]:
    polys.append(shape(f["geometry"]))
    pnames.append(NAME[f["properties"]["PrecinctName"]])
tree = STRtree(polys)

def assign(lat_v, lon_v):
    if lat_v is None or lon_v is None or pd.isna(lat_v) or pd.isna(lon_v) or (lat_v == 0 and lon_v == 0):
        return None
    p = Point(float(lon_v), float(lat_v))
    idx = tree.query(p, predicate="within")
    if len(idx) == 0:
        idx = tree.query(p, predicate="intersects")
    return pnames[int(idx[0])] if len(idx) else None

out["precinct_spatial"] = [assign(a, b) for a, b in zip(lat, lon)]
out["precinct_unknown_flag"] = out["precinct_spatial"].isna()
ZONE2PREC = {1: "West", 2: "East", 3: "South", 4: "Central", 5: "Hermitage",
             6: "North", 7: "Madison", 8: "Midtown Hills", 9: "Southeast"}
out["precinct_zone_derived"] = (df["Zone"] // 100).map(
    lambda v: ZONE2PREC.get(int(v)) if pd.notna(v) else None)

# Control 10.2: zone-derived vs spatial on rows where both exist.
ctrl = out[out["precinct_zone_derived"].notna() & out["precinct_spatial"].notna()]
ctrl_agree = float((ctrl["precinct_zone_derived"] == ctrl["precinct_spatial"]).mean())
ctrl_n = int(len(ctrl))
top_disagree = (ctrl[ctrl["precinct_zone_derived"] != ctrl["precinct_spatial"]]
                .groupby(["precinct_zone_derived", "precinct_spatial"]).size()
                .sort_values(ascending=False).head(3))
ctrl_top_disagreements = [{"zone_precinct": a, "spatial_precinct": b, "rows": int(v)}
                          for (a, b), v in top_disagree.items()]

out.to_parquet(CLEAN, index=False)

# --- Status (incident-level in the source: verified 0 incidents with
# more than one status across their rows) ---
status = df["Incident_Status_Description"]
status_consistency = int(df.groupby("Incident_Number")["Incident_Status_Description"].nunique().gt(1).sum())
assert status_consistency == 0
STATUS_GROUPS = ["OPEN", "UNFOUNDED", "CLEARED BY ARREST", "REFUSED TO COOPERATE", "OTHER"]

def status_block(frame_status):
    n = len(frame_status)
    vc = frame_status.value_counts(dropna=False)
    rows = {}
    for s in ["OPEN", "UNFOUNDED", "CLEARED BY ARREST", "REFUSED TO COOPERATE",
              "PROSECUTION DECLINED", "JUVENILE, NO CUSTODY", "DEATH OF OFFENDER",
              "EXTRADITION DECLINED", "INACTIVE"]:
        rows[s] = int(vc.get(s, 0))
    rows["null"] = int(frame_status.isna().sum())
    other = rows["PROSECUTION DECLINED"] + rows["JUVENILE, NO CUSTODY"] + rows["DEATH OF OFFENDER"] \
        + rows["EXTRADITION DECLINED"] + rows["INACTIVE"] + rows["null"]
    return {"n": int(n),
            "open": rows["OPEN"], "open_share": round(rows["OPEN"] / n, 4),
            "unfounded": rows["UNFOUNDED"], "unfounded_share": round(rows["UNFOUNDED"] / n, 4),
            "cleared_by_arrest": rows["CLEARED BY ARREST"],
            "cleared_share": round(rows["CLEARED BY ARREST"] / n, 4),
            "refused_to_cooperate": rows["REFUSED TO COOPERATE"],
            "other_and_null": int(other)}

status_all = status_block(status)
status_crim = status_block(status[code_class == "nibrs_criminal"])
status_local = status_block(status[code_class == "mnpd_local"])
unf = status == "UNFOUNDED"
unf_local_share = float((unf & (code_class == "mnpd_local")).sum() / unf.sum())

def unfounded_share_by_year(mask):
    return {int(y): round(float(v), 4) for y, v in unf[mask].groupby(out.loc[mask, "year"]).mean().items()}

# --- Year tables ---
def year_table(mask_all=True):
    rows = {}
    for y in range(2019, 2027):
        m = out["year"] == y
        rows[str(y)] = {
            "records": int(m.sum()),
            "nibrs_criminal": int((m & (code_class == "nibrs_criminal")).sum()),
            "mnpd_local": int((m & (code_class == "mnpd_local")).sum()),
            "unknown_code": int((m & (code_class == "unknown")).sum()),
            "code_740": int((m & (codes == "740")).sum()),
            "local_share": round(float((m & (code_class == "mnpd_local")).sum() / m.sum()), 4),
            "distinct_incidents": int(df.loc[m, "Incident_Number"].nunique()),
            "complete_year": bool(y <= 2025),
        }
    return rows

full_years = year_table()
jan_oct_mask = occ.dt.month <= 10
jan_oct = {}
for y in range(2019, 2027):
    m = jan_oct_mask & (out["year"] == y)
    jan_oct[str(y)] = {
        "records": int(m.sum()),
        "nibrs_criminal": int((m & (code_class == "nibrs_criminal")).sum()),
        "mnpd_local": int((m & (code_class == "mnpd_local")).sum()),
        "unknown_code": int((m & (code_class == "unknown")).sum()),
        "code_740": int((m & (codes == "740")).sum()),
        "distinct_incidents": int(df.loc[m, "Incident_Number"].nunique()),
    }

def jo(y, field="nibrs_criminal"):
    return jan_oct[str(y)][field]

def pct(new, old):
    return round((new - old) / old * 100, 1)

trend = {
    "criminal_jan_oct_2023": jo(2023), "criminal_jan_oct_2025": jo(2025), "criminal_jan_oct_2026": jo(2026),
    "criminal_change_2023_to_2025_jan_oct_pct": pct(jo(2025), jo(2023)),
    "criminal_change_2025_to_2026_jan_oct_pct": pct(jo(2026), jo(2025)),
    "criminal_change_2024_to_2025_jan_oct_pct": pct(jo(2025), jo(2024)),
    "criminal_full_2023": full_years["2023"]["nibrs_criminal"],
    "criminal_full_2025": full_years["2025"]["nibrs_criminal"],
    "criminal_change_full_2023_to_2025_pct": pct(full_years["2025"]["nibrs_criminal"], full_years["2023"]["nibrs_criminal"]),
    "criminal_change_full_2019_to_2025_pct": pct(full_years["2025"]["nibrs_criminal"], full_years["2019"]["nibrs_criminal"]),
    "local_full_2019": full_years["2019"]["mnpd_local"], "local_full_2025": full_years["2025"]["mnpd_local"],
    "local_change_full_2019_to_2025_pct": pct(full_years["2025"]["mnpd_local"], full_years["2019"]["mnpd_local"]),
    "total_full_2023": full_years["2023"]["records"], "total_full_2025": full_years["2025"]["records"],
    "total_change_full_2023_to_2025_pct": pct(full_years["2025"]["records"], full_years["2023"]["records"]),
}

# Sensitivity: reclassify the six criminal codes inside the local series.
crim_alt = (code_class == "nibrs_criminal") | codes.isin(LOCAL_BLOCK_CRIMINAL)
jo_alt = {y: int((jan_oct_mask & (out["year"] == y) & crim_alt).sum()) for y in (2023, 2025, 2026)}
sensitivity = {"local_block_criminal_codes": sorted(LOCAL_BLOCK_CRIMINAL),
               "local_block_criminal_rows": local_block_criminal_rows,
               "criminal_jan_oct_reclassified": {str(k): v for k, v in jo_alt.items()},
               "change_2025_to_2026_jan_oct_pct_reclassified": pct(jo_alt[2026], jo_alt[2025])}

# --- Category detail ---
FOCUS = ["240", "23F", "23G", "120", "13A", "13B", "13C", "290", "220", "23C",
         "23H", "23D", "35A", "35B", "520", "26A", "26B", "90J", "90C", "200"]
NIBRS_LABEL = {"240": "Motor Vehicle Theft", "23F": "Theft From Motor Vehicle",
               "23G": "Theft of Motor Vehicle Parts or Accessories", "120": "Robbery",
               "13A": "Aggravated Assault", "13B": "Simple Assault", "13C": "Intimidation",
               "290": "Destruction/Damage/Vandalism of Property", "220": "Burglary/Breaking & Entering",
               "23C": "Shoplifting", "23H": "All Other Larceny", "23D": "Theft From Building",
               "35A": "Drug/Narcotic Violations", "35B": "Drug Equipment Violations",
               "520": "Weapon Law Violations", "26A": "False Pretenses/Swindle/Confidence Game",
               "26B": "Credit Card/ATM Fraud", "90J": "Trespass of Real Property",
               "90C": "Disorderly Conduct", "200": "Arson", "740": "Matter of Record (MNPD local code)",
               "715": "Found Property (MNPD local code)", "810": "Lost Property (MNPD local code)",
               "780": "Recovered Property (MNPD local code)", "90Z": "All Other Offenses",
               "90F": "Family Offenses, Nonviolent"}
cat_rows = []
for c in FOCUS + ["740", "715", "810", "780"]:
    m = codes == c
    fy = {str(y): int((m & (out["year"] == y)).sum()) for y in range(2019, 2026)}
    jow = {str(y): int((m & jan_oct_mask & (out["year"] == y)).sum()) for y in range(2019, 2027)}
    cat_rows.append({"code": c, "label": NIBRS_LABEL[c], "total": int(m.sum()),
                     "full_years": fy, "jan_oct": jow,
                     "change_jan_oct_2019_to_2026_pct": pct(jow["2026"], jow["2019"]),
                     "change_jan_oct_2023_to_2026_pct": pct(jow["2026"], jow["2023"])})
vehicle_codes = codes.isin(["240", "23F", "23G"])
veh_jo = {str(y): int((vehicle_codes & jan_oct_mask & (out["year"] == y)).sum()) for y in range(2019, 2027)}
vehicle_cluster = {"codes": ["240", "23F", "23G"], "jan_oct": veh_jo,
                   "change_2023_to_2026_pct": pct(veh_jo["2026"], veh_jo["2023"]),
                   "change_2019_to_2026_pct": pct(veh_jo["2026"], veh_jo["2019"])}

# January 2025 code-23F anomaly: monthly counts + report-lag profile.
m23 = codes == "23F"
jan25 = m23 & (out["year"] == 2025) & (occ.dt.month == 1)
anomaly = {"code": "23F", "jan_2025_rows": int(jan25.sum()),
           "jan_other_years": {str(y): int((m23 & (out["year"] == y) & (occ.dt.month == 1)).sum())
                               for y in (2019, 2020, 2021, 2022, 2023, 2024, 2026)},
           "jan_2025_share_reported_after_30_days": round(float((lag_days[jan25] > 30).mean()), 4),
           "all_23f_share_reported_after_30_days": round(float((lag_days[m23] > 30).mean()), 4),
           "excess_over_typical_january": int(jan25.sum() - 800),
           "jan_oct_2025_23f_as_served": int((m23 & jan_oct_mask & (out["year"] == 2025)).sum()),
           "jan_oct_2025_23f_excluding_january": int((m23 & jan_oct_mask & (out["year"] == 2025) & (occ.dt.month > 1)).sum())}

# Tail completeness (Denver method): Oct 1-19 daily rate vs Sep 14-30.
def tail_ratio(y):
    o = ((out["year"] == y) & (occ.dt.month == 10) & (occ.dt.day <= 19)).sum() / 19
    s = ((out["year"] == y) & (occ.dt.month == 9) & (occ.dt.day >= 14)).sum() / 17
    return round(float(o / s), 3)
tail = {"oct1_19_vs_sep14_30_daily_rate_ratio": {str(y): tail_ratio(y) for y in (2023, 2024, 2025, 2026)},
        "reading": "2026 ratio below the 0.985-1.018 range of 2023-2025 implies roughly 400 records (about 0.5 percent of the Jan-Oct 2026 window) occurred in the last 19 days but are not yet reported in the layer; Jan-Oct 2026 figures are understated by about that amount"}

# --- Report types (codes with metadata Appendix A labels; the served
# description field disagrees - see traps) ---
RT_LABEL = {"D": "DISPATCHED", "S": "SELF-INITIATED (metadata Appendix A)",
            "T": "TELESERVE", "W": "WALK-IN", "O": "OTHER", "CIR": "CIR (not in Appendix A)"}
rt = df["Report_Type"].value_counts(dropna=False)
report_types = {("null" if pd.isna(k) else str(k)): {"rows": int(v), "label": RT_LABEL.get(str(k), str(k))}
                for k, v in rt.items()}
teleserve_by_year = {int(y): round(float(v), 4) for y, v in
                     (df["Report_Type"] == "T").groupby(out["year"]).mean().items()}

# --- Domestic ---
dom_yes = df["Domestic_Related"] == "Yes"
domestic = {"yes_rows": int(dom_yes.sum()), "yes_share_all": round(float(dom_yes.mean()), 4),
            "yes_share_within_assaults_13A_13B": round(float(dom_yes[codes.isin(["13A", "13B"])].mean()), 4),
            "by_year": {int(y): round(float(v), 4) for y, v in dom_yes.groupby(out["year"]).mean().items()}}

# --- Fusion 1: precinct geography, incidents vs crashes ---
acc = pd.read_parquet(ACC)
acc_known = acc[acc["precinct_full"].notna()]
acc_spatial = [assign(a, b) for a, b in zip(acc["Lat"], acc["Long"])]
acc = acc.assign(precinct_spatial_fusion=acc_spatial)
acc_ctrl = acc[acc["precinct_full"].notna() & acc["precinct_spatial_fusion"].notna()]
acc_agree = float((acc_ctrl["precinct_full"] == acc_ctrl["precinct_spatial_fusion"]).mean())

def precinct_shares(series):
    vc = series.value_counts(dropna=True)
    n = int(vc.sum())
    return {k: {"records": int(v), "share_of_known": round(float(v) / n, 4)}
            for k, v in vc.items()}, n

PRECINCTS = ["Central", "East", "Hermitage", "Madison", "Midtown Hills", "North", "South", "Southeast", "West"]
inc_pool = out[(out["year"] >= 2019) & (out["year"] <= 2025) & (code_class == "nibrs_criminal")]
inc_sh, inc_n = precinct_shares(inc_pool["precinct_spatial"])
acc_pool = acc[(acc["year_local"] >= 2019) & (acc["year_local"] <= 2025)]
acc_rec_sh, acc_rec_n = precinct_shares(acc_pool["precinct_full"])
acc_sp_sh, _ = precinct_shares(acc_pool["precinct_spatial_fusion"])
fusion_precinct = []
for p in PRECINCTS:
    fusion_precinct.append({
        "precinct": p,
        "incidents_criminal_records_2019_2025": inc_sh.get(p, {}).get("records", 0),
        "incidents_share": inc_sh.get(p, {}).get("share_of_known"),
        "crashes_recorded_2019_2025": acc_rec_sh.get(p, {}).get("records", 0),
        "crashes_share_recorded": acc_rec_sh.get(p, {}).get("share_of_known"),
        "crashes_share_spatial_check": acc_sp_sh.get(p, {}).get("share_of_known"),
        "share_gap_points": round(inc_sh.get(p, {}).get("share_of_known", 0) - acc_rec_sh.get(p, {}).get("share_of_known", 0), 4)})

def spearman(a, b):
    ra = pd.Series(a).rank().to_numpy(dtype=float)
    rb = pd.Series(b).rank().to_numpy(dtype=float)
    return round(float(np.corrcoef(ra, rb)[0, 1]), 3)

sp_inc_acc = spearman([inc_sh[p]["share_of_known"] for p in PRECINCTS],
                      [acc_rec_sh[p]["share_of_known"] for p in PRECINCTS])

# --- Fusion 2: the 2025 triad (calls / incidents / crashes) ---
calls = pd.read_parquet(CALLS)
call_sh, call_n = precinct_shares(calls["precinct"])
inc25 = out[out["year"] == 2025]
inc25_sh, inc25_n = precinct_shares(inc25["precinct_spatial"])
inc25c_sh, inc25c_n = precinct_shares(inc25.loc[code_class[out["year"] == 2025] == "nibrs_criminal", "precinct_spatial"])
acc25 = acc[acc["year_local"] == 2025]
acc25_sh, acc25_n = precinct_shares(acc25["precinct_full"])
triad = []
for p in PRECINCTS:
    triad.append({"precinct": p,
                  "calls_share_2025": call_sh.get(p, {}).get("share_of_known"),
                  "incidents_share_2025_all_records": inc25_sh.get(p, {}).get("share_of_known"),
                  "incidents_share_2025_criminal_only": inc25c_sh.get(p, {}).get("share_of_known"),
                  "crashes_share_2025": acc25_sh.get(p, {}).get("share_of_known")})
triad_block = {
    "calls": {"known_precinct_records": call_n, "unknown_records": int(calls["precinct"].isna().sum()),
              "unknown_share": round(float(calls["precinct"].isna().mean()), 4)},
    "incidents_all_records": {"known_precinct_records": inc25_n, "total_records_2025": int(len(inc25)),
                              "unknown_share": round(1 - inc25_n / len(inc25), 4)},
    "incidents_criminal_only": {"known_precinct_records": inc25c_n},
    "crashes": {"known_precinct_records": acc25_n, "total_records_2025": int(len(acc25)),
                "unknown_share": round(1 - acc25_n / len(acc25), 4)},
    "by_precinct": triad,
    "spearman_calls_vs_incidents_all": spearman([call_sh[p]["share_of_known"] for p in PRECINCTS],
                                                [inc25_sh[p]["share_of_known"] for p in PRECINCTS]),
    "spearman_incidents_vs_crashes": spearman([inc25_sh[p]["share_of_known"] for p in PRECINCTS],
                                              [acc25_sh[p]["share_of_known"] for p in PRECINCTS]),
}

# --- Fusion 3: calls -> incidents linkage, 2025 ---
call_nums = calls.loc[calls["Complaint_Number"].notna(), "Complaint_Number"].astype(str)
call_num_set = set(call_nums.unique())
inc_num_str = df["Incident_Number"].astype("int64").astype(str)
inc_num_set = set(inc_num_str.unique())
matched = call_num_set & inc_num_set
inc2025_ids = set(inc_num_str[out["year"] == 2025].unique())
matched_2025 = call_num_set & inc2025_ids
calls_join = {
    "calls_2025_rows": int(len(calls)),
    "calls_with_complaint_number_rows": int(calls["Complaint_Number"].notna().sum()),
    "distinct_complaint_numbers": int(len(call_num_set)),
    "distinct_numbers_matched_in_incidents_layer": int(len(matched)),
    "match_rate_of_distinct_numbers": round(len(matched) / len(call_num_set), 4),
    "distinct_numbers_matched_to_2025_occurred_incident": int(len(matched_2025)),
    "distinct_incidents_occurred_2025": int(len(inc2025_ids)),
    "share_of_2025_incidents_with_a_linked_call": round(len(matched_2025) / len(inc2025_ids), 4),
}

# --- ZIP table (descriptive, known-ZIP rows only) ---
zip_known = out[~out["zip_unknown_flag"]]
zip_top = (zip_known.groupby("zip_clean").size().sort_values(ascending=False).head(10))
zip_rows = [{"zip": str(k), "records": int(v)} for k, v in zip_top.items()]

stats = {
  "dataset": "Metro Nashville Police Department Incidents (Metro_Nashville_Police_Department_Incidents_view layer 0)",
  "snapshot_date": "2026-11-04",
  "rows": N,
  "unit": "one row = one offense-victim record within an incident (Primary_Key = Incident_Number + Offense_Number + Victim_Number, verified against the data); distinct incidents are counted separately where stated. Counts are records of reported incidents in MNPD's RMS export, not a count of crimes committed; the metadata warns the export is not an official MNPD incident report and records are subject to change during investigation",
  "distinct_incidents": n_incidents,
  "rows_per_incident_mean": round(N / n_incidents, 3),
  "coverage": {
    "occurred_min": str(occ.min()), "occurred_max": str(occ.max()),
    "window_note": "metadata describes a 7-year rolling extract, daily updates; the served extent is 2019-01-01 to 2026-11-03 (America/Chicago). 2026 is a partial year (through Nov 3); every cross-year comparison uses full years 2019-2025 or matched Jan-Oct windows",
    "complete_years": [2019, 2020, 2021, 2022, 2023, 2024, 2025]
  },
  "code_classes": {
    "definition": "NIBRS criminal offense codes = the FBI NIBRS list in the metadata's Appendix D (09A-90Z); MNPD local incident-type codes = the 610-850 series Appendix D appends after the NIBRS list (matter of record, found/lost/recovered property, non-criminal deaths, overdoses, transports and similar). Six codes in the local series name criminal conduct (64A, 64B, 700, 710, 730, 850) and are handled by a printed sensitivity check",
    "nibrs_criminal_rows": n_crim, "nibrs_criminal_share": round(n_crim / N, 4),
    "mnpd_local_rows": n_local, "mnpd_local_share": round(n_local / N, 4),
    "unknown_code_rows": n_unknown_code,
    "code_740_rows": int((codes == "740").sum()), "code_740_share": round(float((codes == "740").mean()), 4),
    "code_740_descriptions": {"POLICE INQUIRY": int(((codes == "740") & (df["Offense_Description"] == "POLICE INQUIRY")).sum()),
                              "TRANSPORT": int(((codes == "740") & (df["Offense_Description"] == "TRANSPORT")).sum())}
  },
  "sensitivity_reclassification": sensitivity,
  "full_years": full_years,
  "jan_oct_windows": jan_oct,
  "trend": trend,
  "tail_completeness": tail,
  "categories": cat_rows,
  "vehicle_cluster": vehicle_cluster,
  "january_2025_23f_anomaly": anomaly,
  "status": {"all_records": status_all, "nibrs_criminal": status_crim, "mnpd_local": status_local,
             "unfounded_records": int(unf.sum()), "unfounded_share_all": round(float(unf.mean()), 4),
             "share_of_unfounded_that_is_local_code": round(unf_local_share, 4),
             "unfounded_share_by_year_criminal": unfounded_share_by_year(code_class == "nibrs_criminal"),
             "unfounded_share_by_year_local": unfounded_share_by_year(code_class == "mnpd_local"),
             "status_is_incident_level": "verified: 0 of 783,832 incidents carry more than one status across their rows"},
  "report_types": report_types,
  "teleserve_share_by_year": teleserve_by_year,
  "domestic_related": domestic,
  "geography": {
    "zone_rpa_known_share_by_year": zone_known_by_year,
    "zone_rpa_note": "Zone and RPA are jointly populated: known on 96.5 percent of 2019 rows, 90.2 percent of 2021 rows, 17.7 percent of 2022 rows, and under 0.1 percent from 2023 on. Patrol geography therefore cannot carry a full-period comparison; precinct geography is spatial, from coordinates, validated against the zone codes where they exist",
    "coords_unknown_rows": int(coords_unknown.sum()), "coords_outside_davidson_bbox_rows": n_coords_outside,
    "spatial_control_incidents": {"rows_with_zone_and_spatial": ctrl_n,
                                  "agreement_zone_derived_vs_spatial": round(ctrl_agree, 4),
                                  "top_disagreements": ctrl_top_disagreements},
    "spatial_control_crashes": {"rows_with_recorded_and_spatial": int(len(acc_ctrl)),
                                "agreement_recorded_vs_spatial": round(acc_agree, 4),
                                "reading": "crash precinct shares are printed on the recorded precinct (the published crash brief's basis); the spatial re-assignment of the same crashes moves no precinct's 2019-2025 share by more than the gap printed in fusion_precinct_2019_2025"},
    "zip": {"known_rows": int((~out["zip_unknown_flag"]).sum()),
            "unknown_share": round(float(out["zip_unknown_flag"].mean()), 4),
            "format_note": "ZIP is served as float-strings (for example '37207.0') and is missing on about 46 percent of records in every year, unlike the crash layer's 99.6 percent ZIP completeness; ZIP is used descriptively only",
            "top10_by_records": zip_rows}
  },
  "fusion_precinct_2019_2025": {"incidents_population": "NIBRS criminal offense records with a spatial precinct, occurred 2019-2025",
                                "incidents_known_records": inc_n,
                                "crashes_population": "reported crashes with a recorded precinct, occurred 2019-2025 (deposited crash layer, 2026-11-01 snapshot)",
                                "crashes_known_records": acc_rec_n,
                                "spearman_incidents_vs_crashes": sp_inc_acc,
                                "by_precinct": fusion_precinct},
  "fusion_triad_2025": triad_block,
  "calls_incident_join_2025": calls_join,
  "code_counts_all_rows": code_counts,
  "traps": {
    "primary_key_not_unique": {"collision_keys": pk_collision_keys, "rows_on_collision_keys": pk_collision_rows,
                               "note": "the metadata calls Primary_Key a unique identifier for each record; 114 keys are shared by 263 rows carrying different offense or victim combinations (the key concatenates offense and victim numbers without a separator, so combinations collide). OBJECTID is the unique row key"},
    "midnight_placeholder_rows": n_midnight, "midnight_share": round(n_midnight / N, 4),
    "reported_before_occurred_rows": n_reported_before,
    "report_lag_days_median": round(float(lag_days.median()), 3),
    "incident_number_prefix_year_mismatch_rows": n_prefix_mismatch,
    "victim_type_junk_rows": n_victim_junk,
    "codes_not_in_metadata_appendix_d": codes_not_in_appendix,
    "report_type_description_defect": "the served Report_Type_Description matches the metadata Appendix A key only for D (DISPATCHED) and W-count rows carry 'WITNESS' where Appendix A says WALK-IN; code S is served as 'SUSPECT' where Appendix A says SELF-INITIATED, and codes T, O and CIR (68,660 rows) carry no description at all. This brief uses codes with Appendix A labels throughout",
    "weapon_field_defect": "Weapon_Description mixes two vocabularies (NONE / PERSONAL (HANDS) / HANDGUN alongside Unarmed / CLUB) and is null on 50,754 rows; no weapon figure is published in this brief",
    "offense_description_defect": "Offense_Description is the RMS/Tennessee label set, not the NIBRS label: 44 of 72 codes carry more than one description, and code 23F (NIBRS: Theft From Motor Vehicle) is described as 'BURGLARY- MOTOR VEHICLE' on 71,995 rows. All grouping in this brief is by NIBRS code with Appendix D labels"
  },
  "censoring_note": "Incident status is a snapshot at pull time: recent incidents have had less time to be cleared, and the OPEN share of recent years is right-censored. The 2026 Jan-Oct window is additionally understated by roughly 0.5 percent (about 400 records) of late-October incidents not yet reported into the layer at pull time (see tail_completeness)."
}

# Data panels (CSV) for the package
DATA = PKG / "data"; DATA.mkdir(parents=True, exist_ok=True)
pd.DataFrame([{"year": y, **v} for y, v in full_years.items()]).to_csv(DATA / "year_table_panel.csv", index=False)
pd.DataFrame([{"year": y, **v} for y, v in jan_oct.items()]).to_csv(DATA / "jan_oct_panel.csv", index=False)
pd.DataFrame(cat_rows).assign(full_years=lambda d: d["full_years"].astype(str),
                              jan_oct=lambda d: d["jan_oct"].astype(str)).to_csv(DATA / "category_panel.csv", index=False)
cat_long = []
for r in cat_rows:
    for y, v in r["jan_oct"].items():
        cat_long.append({"code": r["code"], "label": r["label"], "year": int(y), "jan_oct_records": v})
pd.DataFrame(cat_long).to_csv(DATA / "category_jan_oct_panel.csv", index=False)
pd.DataFrame(fusion_precinct).to_csv(DATA / "fusion_precinct_panel.csv", index=False)
pd.DataFrame(triad).to_csv(DATA / "triad_2025_panel.csv", index=False)
pd.DataFrame([{"status": k, "all_records": status_all[k] if k in status_all else None} for k in []]).to_csv(DATA / "status_panel.csv", index=False)
status_panel = pd.DataFrame([
    {"population": "all records", **{k: status_all[k] for k in ["n", "open", "open_share", "unfounded", "unfounded_share", "cleared_by_arrest", "cleared_share", "refused_to_cooperate", "other_and_null"]}},
    {"population": "NIBRS criminal codes", **{k: status_crim[k] for k in ["n", "open", "open_share", "unfounded", "unfounded_share", "cleared_by_arrest", "cleared_share", "refused_to_cooperate", "other_and_null"]}},
    {"population": "MNPD local codes", **{k: status_local[k] for k in ["n", "open", "open_share", "unfounded", "unfounded_share", "cleared_by_arrest", "cleared_share", "refused_to_cooperate", "other_and_null"]}},
])
status_panel.to_csv(DATA / "status_panel.csv", index=False)
pd.DataFrame(zip_rows).to_csv(DATA / "zip_top10_panel.csv", index=False)

(PKG / "stats.json").write_text(json.dumps(stats, indent=2))
print(f"clean layer: {CLEAN} rows={len(out)}")
print(f"rows {N}; incidents {n_incidents}; criminal {n_crim} ({n_crim/N:.2%}); local {n_local} ({n_local/N:.2%}); 740 {(codes=='740').sum()}")
print(f"trend: criminal Jan-Oct 2023 {jo(2023)} -> 2025 {jo(2025)} -> 2026 {jo(2026)} ({trend['criminal_change_2025_to_2026_jan_oct_pct']}%)")
print(f"spatial control agreement: {ctrl_agree:.4f} on {ctrl_n:,}; crashes control: {acc_agree:.4f}")
print(f"calls join: {len(matched)}/{len(call_num_set)} = {len(matched)/len(call_num_set):.3%}")
print("BUILD OK")
