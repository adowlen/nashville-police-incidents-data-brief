#!/usr/bin/env python3
"""Snapshot pull: Metro Nashville Police Department Incidents (brief pull, 2026-11-04).

Pages the ArcGIS FeatureServer at maxRecordCount, ordered by OBJECTID.
Raw snapshot is immutable: refuses to write if the target file exists.
Output: stack/nashville/snapshots/2026-11-04/mnpd_incidents_raw.parquet
plus pull_log.json in this package's data/ folder.
Run with: ~/workspace/goals/daily-civic-data-brief/hidden_files/denver-crime-brief-2026-10-17/.venv/bin/python code/pull_data.py
"""
import hashlib, json, sys, time
from pathlib import Path
import pandas as pd
import requests

BASE = "https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Metro_Nashville_Police_Department_Incidents_view/FeatureServer/0"
HERE = Path(__file__).resolve()
STACK = HERE.parents[2] / "stack" / "nashville"
OUT = STACK / "snapshots" / "2026-11-04" / "mnpd_incidents_raw.parquet"
PKG = HERE.parents[1]

def get(params, tries=4):
    last = None
    for i in range(tries):
        try:
            r = requests.get(BASE + "/query", params=params, timeout=180)
            r.raise_for_status()
            d = r.json()
            if "error" in d:
                raise RuntimeError(d["error"])
            return d
        except Exception as e:
            last = e; time.sleep(2 * (i + 1))
    raise last

def main():
    if OUT.exists():
        print(f"REFUSING: snapshot already exists: {OUT}"); sys.exit(1)
    meta = requests.get(BASE, params={"f": "json"}, timeout=60).json()
    page = meta.get("maxRecordCount") or 2000
    live = get({"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    print(f"live count: {live}, page size: {page}")
    rows, offset = [], 0
    while True:
        d = get({"where": "1=1", "outFields": "*", "orderByFields": "OBJECTID ASC",
                 "resultOffset": offset, "resultRecordCount": page, "f": "json"})
        feats = d.get("features", [])
        rows.extend(f["attributes"] for f in feats)
        print(f"  page offset {offset}: {len(feats)} rows, total {len(rows)}")
        if len(feats) < page:
            break
        offset += page
    assert len(rows) == live, f"pulled {len(rows)} != live {live}"
    df = pd.DataFrame(rows)
    assert df["OBJECTID"].is_unique, "OBJECTID not unique"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
    log = {
        "dataset": "Metro Nashville Police Department Incidents (Metro_Nashville_Police_Department_Incidents_view, layer 0)",
        "endpoint": BASE,
        "snapshot_date": "2026-11-04",
        "live_count_at_pull": live,
        "pulled_rows": len(rows),
        "pages": (live + page - 1) // page,
        "page_size": page,
        "service_last_edit_ms": meta.get("editingInfo", {}).get("dataLastEditDate"),
        "fields": [f["name"] for f in meta.get("fields", [])],
        "file": str(OUT),
        "size_bytes": OUT.stat().st_size,
        "sha256": sha,
    }
    (PKG / "data").mkdir(parents=True, exist_ok=True)
    (PKG / "data" / "pull_log.json").write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))

if __name__ == "__main__":
    main()
