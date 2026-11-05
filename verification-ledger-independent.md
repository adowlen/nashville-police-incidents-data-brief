# Independent verification ledger - Nashville Police Incidents brief (2026-11-05)

Verifier: code/verify_independent.py, run 2026-11-04 after the build and the Section 10 audit. Method diversity per standards section 11: three routes that share no code with the builder (code/build_stats.py).

## Method 1 - server-side aggregates (the live ArcGIS service answers)

The service itself computes the counts (returnCountOnly and groupBy statistics), so the pull, the parquet round-trip and the local arithmetic are all bypassed. Tolerances absorb the service's daily updates.

```
PASS  server count (live service updates daily; drift-tolerant)  live now 945811 vs snapshot 945811
PASS  server full-year 2019 record count (drift-tolerant)  server 119745 vs snapshot 119745
PASS  server full-year 2025 record count (drift-tolerant)  server 118421 vs snapshot 118421
PASS  server groupBy code counts within 2 percent for 6 headline codes  6/6 within tolerance (740 server 205180 vs snapshot 205180)
PASS  server Zone-known count (geography break is in the source, not the pull)  server 353882 vs snapshot 353,882
```

Result detail: at verification time the live service held the identical state - every server figure equaled the snapshot exactly, zero drift. The six groupBy codes were 740, 13B, 23F, 240, 120, 290. The Zone-known count (353,882) independently confirms the patrol-geography break is a property of the source data, not of the pull.

## Method 2 - pyarrow recount of the raw snapshot (epoch arithmetic)

The raw snapshot parquet is re-read with pyarrow compute only (no pandas, no builder code); Jan-Oct windows are rebuilt from raw epoch milliseconds (America/Chicago = UTC-5 across each Jan-Oct span, which contains no offset change).

```
PASS  pyarrow row count  945811
PASS  pyarrow distinct incidents  783,832
PASS  pyarrow class totals  criminal 623874, local 321859
PASS  pyarrow Jan-Oct 2023 criminal records (epoch window)  71454 vs 71454
PASS  pyarrow Jan-Oct 2025 criminal records (epoch window)  63634 vs 63634
PASS  pyarrow Jan-Oct 2026 criminal records (epoch window)  57222 vs 57222
PASS  pyarrow UNFOUNDED total  299,992
PASS  pyarrow UNFOUNDED within local codes  289,016
PASS  pyarrow Primary_Key collision keys  114 keys
```

Result detail: every recount is exact, including the trend figures the headline rests on and the Primary_Key collision count behind trap 2.

## Method 3 - independent polygon implementation (matplotlib.path)

Point-in-polygon is recomputed with matplotlib.path, a different implementation from the builder's shapely STRtree, over the same archived precinct polygons.

```
PASS  mpl-path zone-era control agreement (sampled, independent polygon code)  sample agreement 0.9633 on 50,327 sampled rows vs builder 0.9635
PASS  mpl-path 2025 incident precinct shares vs builder (max deviation)  max deviation 0.0000 across 9 precincts
```

Result detail: the control agreement reproduces within sampling noise (every 7th control row), and the 2025 precinct shares behind the triad chart reproduce exactly.

## Verdict

16/16 checks pass. Process note: the verifier's first run failed on an ArcGIS query-format error of the verifier's own making (raw epoch values in a date where-clause, HTTP 400); the year queries were rewritten with timestamp literals and the full suite then passed. No figure in stats.json changed at any point. Machine-readable output: data/verify_independent_output.json; console capture: data/verify_independent_output.txt.
