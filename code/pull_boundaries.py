#!/usr/bin/env python3
"""Snapshot pull: MNPD Police Precinct Boundaries (brief pull, 2026-11-04).

Fetches the 9 precinct polygons as GeoJSON from the official
Police_Precinct_Boundaries_view service and archives them in this
package's data/ folder. The incidents layer's own patrol geography
(Zone / RPA) is populated only through 2021, so precinct assignment
for 2022-2026 is spatial, from the incident coordinates (rounded to
3 decimals by MNPD for privacy). The assignment is validated in
build_stats.py against the layer's own zone codes on the 352,229
rows where both exist (agreement recorded in stats.json).
Output: data/precinct_boundaries.geojson plus data/boundaries_log.json.
"""
import hashlib, json
from pathlib import Path
import requests

BASE = "https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Police_Precinct_Boundaries_view/FeatureServer/0"
PKG = Path(__file__).resolve().parents[1]

def main():
    meta = requests.get(BASE, params={"f": "json"}, timeout=60).json()
    g = requests.get(BASE + "/query", params={"where": "1=1", "outFields": "*",
                                              "returnGeometry": "true", "f": "geojson"}, timeout=120).json()
    names = sorted(f["properties"]["PrecinctName"] for f in g["features"])
    assert len(g["features"]) == 9, names
    out = PKG / "data" / "precinct_boundaries.geojson"
    out.write_text(json.dumps(g))
    log = {"dataset": "MNPD Police Precinct Boundaries (Police_Precinct_Boundaries_view, layer 0)",
           "endpoint": BASE, "snapshot_date": "2026-11-04",
           "features": len(g["features"]), "precincts": names,
           "service_last_edit_ms": meta.get("editingInfo", {}).get("dataLastEditDate"),
           "file": str(out), "size_bytes": out.stat().st_size,
           "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
    (PKG / "data" / "boundaries_log.json").write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))

if __name__ == "__main__":
    main()
