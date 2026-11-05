# Sources - Nashville Police Incidents brief (2026-11-05)

## Primary source (pulled for this brief)

- Metro Nashville Police Department Incidents, ArcGIS FeatureServer view, layer 0
  - Service: https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Metro_Nashville_Police_Department_Incidents_view/FeatureServer/0
  - ArcGIS item: d747436243e9439e968fce056545016a (Metro Government of Nashville and Davidson County)
  - Snapshot: 2026-11-04 full pull, 473 paged queries of 2,000 records (OBJECTID order), 945,811 records
  - Raw snapshot (stack): stack/nashville/snapshots/2026-11-04/mnpd_incidents_raw.parquet, 39,293,160 bytes, SHA-256 c8a2c697cebb39217a1b40451a4bda00c74582d1532461eee580f0a48937ab0e
  - Cleaned layer (stack): stack/nashville/layers/mnpd_incidents_clean.parquet, 945,811 rows
  - Coverage: Incident_Occurred 2019-01-01 to 2026-11-03 20:45 (America/Chicago); the service updates daily and the metadata describes a 7-year rolling extract
  - Pull log: data/pull_log.json

## Agency documentation (read before analysis)

- MNPD Open Data metadata PDF, version 2.0, last updated 2023-06-13, ArcGIS item ef33d8a39a5a43169645c36039588e2e
  - Archived at data/source-metadata.pdf; retrieval URL recorded in data/pull_log.json
  - Basis for: the row definition (one offense-victim record within an incident), the Appendix A report-type key, the Appendix D code list used for the criminal / local class split and all category labels, the Appendix G victim-type key, the privacy rounding of coordinates, and the notice that the export is not an official MNPD incident report

## Boundaries (pulled for this brief)

- Nashville and Davidson County Police Precinct Boundaries, ArcGIS FeatureServer view, layer 0
  - Service: https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Police_Precinct_Boundaries_view/FeatureServer/0
  - ArcGIS item: 8dbdfea945ab43ebb2d1f02babedfb18; 9 precinct polygons (CENTRAL, EAST, HERMITAGE, MADISON, MIDTOWN HILLS, NORTH, SOUTH, SOUTHEAST, WEST)
  - Archived at data/precinct_boundaries.geojson; log at data/boundaries_log.json

## Deposited layers fused against (no re-pull)

- MNPD Calls for Service 2025 - Nashville stack layer mnpd_calls_2025 (cleaned), 486,611 calls, deposit 2026-10-16 (internal study). Complaint_Number present on 73,763 rows / 72,041 distinct; precinct not determined on 112,371 rows (23.1 percent).
- Nashville Traffic Accidents - Nashville stack layer traffic_accidents (cleaned), 222,903 crashes 2019-2026, snapshot 2026-11-01; the layer behind the published Nashville traffic accidents brief (2026-11-02). Recorded precinct (precinct_full) is the published basis; RPA jointly null with precinct on 21,216 rows.

## Reference packages

- Nashville building permit applications brief (2026-11-04 package) - structural template for this package.
- Denver crime brief (adowlen/denver-crime-data-brief) - analysis-form mirror in the first locality: decomposition findings, matched partial-year windows, grouping sensitivity printed.
