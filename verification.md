# Verification - Nashville Police Incidents brief (2026-11-05)

## Source verification (standards 9.4)

- The agency's own metadata document (MNPD Open Data metadata v2.0, 2023-06-13, ArcGIS item ef33d8a39a5a43169645c36039588e2e) was downloaded and read in full BEFORE any analysis; it is archived at data/source-metadata.pdf. The row definition, the Appendix A report-type key, the Appendix D code list (the basis of the criminal / local split and of every category label), the Appendix G victim-type key, the coordinate privacy rounding, and the "not an official incident report" notice all come from that document, not from the field names.
- The primary layer was verified live before the pull: service metadata read, record count 945,811 at pull time (944,929 when first profiled on 2026-11-02; the service updates daily). Full paged pull: 473 queries of 2,000 by OBJECTID; snapshot 39,293,160 bytes, SHA-256 c8a2c697cebb39217a1b40451a4bda00c74582d1532461eee580f0a48937ab0e per data/pull_log.json, re-verified against the file on disk during this build (a wrong hash carried in the build's working notes was caught by that check and corrected in sources.md and here before publication; the verifier's pyarrow recount reads the file itself, so no figure was ever affected).
- The two fused layers were NOT re-pulled: the calls layer is the 2025 deposit from the 2026-10-16 internal study and the crash layer is the 2026-11-01 deposit behind the published traffic accidents brief; both are cited with their snapshot dates in sources.md and in the triad chart's footnotes. What was joined: crashes by precinct share comparison (no record-level join exists or is claimed); calls by the shared complaint number (record-level, F6) and by precinct shares. What was not joined: incidents to crashes at record level (no shared key exists), and calls to incidents for the 84.8 percent of calls that carry no complaint number - the brief prints that limit inside F6 itself.

## Headline figures (all in stats.json)

- 945,811 records; 783,832 distinct incidents; 1.207 records per incident; coverage 2019-01-01 to 2026-11-03 20:45 local.
- Criminal offense codes 623,874 (65.96 percent); MNPD local incident-type codes 321,859 (34.03 percent); no code 78. Code 740: 205,180 (21.69 percent) = POLICE INQUIRY 185,355 + TRANSPORT 19,825.
- Trend (criminal codes): full years 85,651 (2023) to 75,641 (2025), -11.7 percent; -7.3 percent against 2019. Jan-Oct: 71,454 (2023) to 63,634 (2025) to 57,222 (2026); -9.9 percent (2024 to 2025), -10.1 percent (2025 to 2026), -10.9 percent (2023 to 2025). All-records full years: 129,728 to 118,421, -8.7 percent. Local full years: 38,098 (2019) to 42,775 (2025), +12.3 percent. Sensitivity: reclassifying the six criminal-conduct codes inside the local series (3,553 records) moves the 2025 to 2026 Jan-Oct criminal change to -10.0 percent.
- Status: OPEN 438,727 (46.39 percent), UNFOUNDED 299,992 (31.72 percent), CLEARED BY ARREST 141,450 (14.96 percent), REFUSED TO COOPERATE 58,062, other and null 7,580. 96.34 percent of unfounded records are local codes. Criminal codes: unfounded 1.76 percent, open 66.93 percent, cleared by arrest 21.05 percent. Local codes: unfounded 89.80 percent, open 6.57 percent. Status verified incident-level: 0 of 783,832 incidents carry more than one status.
- Fusion 2019-2025: incidents criminal records known-precinct 563,734; crashes known-precinct 178,685; Spearman 0.80; largest share gap North +2.31 points. Triad 2025: calls vs incidents Spearman 0.317; incidents vs crashes 0.817. Calls join 2025: 68,373 of 72,041 distinct complaint numbers matched (94.91 percent); 66,470 matched to a 2025-occurred incident; 67.19 percent of 2025's 98,930 incidents have a linked call.

## Methods checklist (standards section 6)

- [x] Unit stated wherever the numbers' meaning depends on it: records (offense-victim rows) everywhere; incidents named explicitly in the status verification and the calls join.
- [x] Ranking basis stated: precinct figures are shares of each ledger's known-precinct records; denominators printed in stats.json, in F6, and on the triad chart.
- [x] Coverage period stated on the brief, the README, and every chart.
- [x] Definitions fixed before results: code classes follow Appendix D's structure (read before analysis); the six-code ambiguity is handled by a printed sensitivity, not a silent choice.
- [x] Grouping sensitivity printed: the class split (F1/F2 sensitivity) and the crash recorded-vs-spatial basis (F5 control) both carry their alternatives in the text.
- [x] Windows matched for partial years; tail completeness measured (ratio test) and printed with its size (~400 records, ~0.5 percent of the Jan-Oct 2026 window).
- [x] No rate, risk, or per-capita figure published: precinct comparisons are record shares only; no exposure denominator exists in these layers and none was imported.
- [x] Every chart titles its population and measure on the graphic; all four charts and the hero were viewed after rendering.
- [x] Interpretation confined to the labeled "What this might mean" section, each reading paired with its strongest alternative.
- [x] "Who can act" names lever owners (MNPD command and the Metro Council public safety committee; MNPD Open Data / RMS export owners; MNPD and Metro ITS; Metro Council and NDOT), the concrete action, the cost class, and the outcome measure with its dataset.

## Pre-flight audit (Section 10 - HARD BLOCKING GATE)

Run: code/audit_section10.py against the cleaned layer and stats.json, after the build and again after the stats rebuild that added the unknown-code fields. Output (data/audit_output.txt):

```
rows in cleaned layer: 945811
[definition] OBJECTID unique on all 945811 rows; distinct incidents 783,832; row unit is the offense-victim record (Primary_Key grain verified in build) PASS
[10.1.1] null NIBRS code rows 78 held as their own class and excluded from both class populations; ZIP normalized (no float-string survives; unknown 440,556); coords unknown 11,947 (nulls + 0,0); midnight-exact timestamps 27,832 flagged and unused; victim-type junk 109 rows mapped unknown PASS
[10.1.2] window polarity: matched sample inside window ends 2026-10-31 (['2021-10-31', '2021-10-31', '2021-10-31']), excluded sample starts 2026-11 (['2026-11-01', '2026-11-01', '2026-11-01']); report-lag sign: 1,739 rows are reported-before-occurred and are COUNTED in stats['traps'], not dropped or sign-flipped PASS
[10.1.3] status groups sum to 945811 records; unfounded share recomputed 0.3172 on the record denominator; calls join is distinct numbers over distinct numbers (68,373/72,041) PASS
[10.1.4] Offense_NIBRS Counter: 73 values (incl. null), counts sum to 945811, matches stats.json key for key; Incident_Status_Description Counter: 10 values, sums to 945811 PASS
[10.1.5] code classes sum to 945811; fusion pool: incidents criminal 2019-2025 known 563,734 + unknown 2,582 = 566,316; every precinct share set sums to 1.0 on its own known-records denominator, with unknown shares printed in stats (calls 23.09 percent not-determined, incidents 2.41 percent, crashes 2.36 percent for 2025) PASS
[10.2] controls: (a) incidents spatial-vs-zone precinct agreement 0.9635 on 352,229 control rows (boundary pairs South/Midtown Hills dominate the disagreements, as expected from 3-decimal privacy-rounded coordinates near precinct borders); (b) crashes: recorded-vs-spatial share gap max 1.38 points across the 9 precincts, so the recorded-basis comparison is not an artifact of the assignment method; (c) Zone/RPA known share falls 0.9654 (2019) to 0.1774 (2022) to 0.0000 (2025) - the patrol-geography break is in the data, which is why precinct is spatial PASS
[12.3] effective windows: full years 2019-2025 complete; 2026 is Jan 1-Nov 3 and is used only in matched Jan-Oct windows, themselves understated by ~0.5 percent at the late-October tail (ratio test in stats['tail_completeness']); status figures are as of the 2026-11-04 pull, so recent years' OPEN shares are right-censored and are never compared as clearance performance PASS
ALL SECTION 10 GATES PASS
```

Audit process note, recorded honestly: the audit's first run failed on a bug in the audit script itself (the ZIP check used a regular-expression match in which "." matched any character, flagging normalized ZIPs as float-strings). The check was corrected to a literal match and the audit re-ran clean; the underlying data was never wrong, and the gate result above is from the corrected script that ships in code/.

## Trap dispositions (standards 10.1 / section 12)

1. Zone and RPA jointly populated only through 2021 (96.5 / 94.8 / 90.2 percent known 2019-2021, 17.7 percent in 2022, ~0 percent 2023-2026). Disposition: precinct is spatial for the whole period; the break is reported in the brief's definitions and in F5's method control. No zone-based trend is published.
2. Primary_Key not unique (114 keys, 263 rows, 149 excess) despite the metadata's "unique identifier" claim; the concatenation has no separator. Disposition: OBJECTID is the row key; counts as served; disclosed in data notes.
3. Report_Type_Description disagrees with Appendix A: S served as SUSPECT (Appendix A: SELF-INITIATED), W as WITNESS (Appendix A: WALK-IN), and T / O / CIR carry no served description (68,660 rows). Disposition: the brief uses codes with Appendix A labels and names the defect in "Who can act" as a publisher repair. Same defect family as the calls layer's Tencode_Description.
4. Offense_Description is the RMS/Tennessee label set, not NIBRS: 44 of 72 codes carry more than one description; 23F is described as "BURGLARY- MOTOR VEHICLE" on 71,995 records. Disposition: all grouping and labels by NIBRS code with Appendix D labels; disclosed in definitions.
5. ZIP served as float-strings and missing on ~46.6 percent of records in every year (the crash layer is 99.6 percent complete - the two layers' ZIP fields are not comparable). Six malformed raw values ("0.0", "3701.0", "6706.0", "7253.0", "3108.0", "UNK") mapped to unknown. Disposition: ZIP used descriptively only (top ZIPs 37013, 37207, 37211, 37115, 37203), never as a fusion key.
6. January 2025 code-23F anomaly: 1,648 records against 669-1,155 in other Januaries, spread across the month, report lag normal (1.15 percent reported after 30 days vs 1.07 percent baseline) - not a backfill artifact by the lag test; cause unknown. Disposition: disclosed in F3 and the data notes with the excluding-January sensitivity (Jan-Oct 2025 23F = 7,207); no month-level 23F claim is published; a documentation request is in "Who can act".
7. Incident_Number year prefix mismatches the occurred year on 15,313 records (1.6 percent), including junk prefixes (201, 202, 1900, 2012-2018). Disposition: all time analysis on Incident_Occurred; disclosed in definitions.
8. Placeholder and junk timestamps: 27,832 exactly-midnight occurred times (2.94 percent) flagged, no time-of-day figure published; 1,739 reported-before-occurred records counted, not dropped; Incident_Reported has a junk tail to 1995; median lag 0.128 days.
9. Victim_Type keystroke garbage on 109 rows ("NNNNNN", "CHRIST", "`" and similar) mapped to unknown; no victim-type figure published.
10. Weapon_Description mixes two vocabularies and is null on 50,754 records; no weapon figure published.
11. Coordinates: null on 11,762, 0,0 on 185 (unknown 11,947, 1.26 percent); 21 known-coordinate records outside the Davidson County bounding box excluded from spatial assignment; all coordinates rounded to exactly three decimals per the metadata.
12. Status censoring: status is at pull time; partial-2026 criminal unfounded share (2.36 percent vs 1.6-1.9 percent in full years) is a censoring artifact and is labeled as such in F4; OPEN shares are never compared across years. Investigation_Status "Open" count equals the OPEN status count exactly (438,727) - the two fields are the same fact, not corroboration.
13. Code "13c" served lowercase on 21 records: counted in the criminal class; the 13C category line counts the 34,713 uppercase records (intimidation understated by 21, 0.06 percent). It is the only served code absent from Appendix D as printed.
14. Report type CIR (1,831 records) is absent from Appendix A; reported under its code only.

## Internal controls

- Incidents: spatial precinct vs precinct derived from the record's own Zone code on the 352,229 records where both exist: 96.35 percent agreement; top disagreement pairs are the adjacent South / Midtown Hills border (1,500 + 1,135 records), consistent with three-decimal privacy rounding near borders.
- Crashes: recorded vs spatial precinct agreement 89.78 percent on 201,515 records; share-level control (the basis F5 uses) moves no precinct share by more than 1.38 points.
- Calls: the join rate is computed on distinct complaint numbers on both sides (no record-count inflation); the triad's unknown-precinct shares are printed with the findings.

## Independent verifier (Section 11)

code/verify_independent.py - three methods independent of the builder: (1) live server-side ArcGIS aggregates (counts and groupBy statistics statistics, drift-tolerant because the service updates daily); (2) a pyarrow recount of the raw snapshot using raw epoch-millisecond window arithmetic; (3) matplotlib.path point-in-polygon, a different polygon implementation from the builder's shapely STRtree, for both the zone-era control and the 2025 precinct shares. Result: 16/16 checks pass; every snapshot-side figure matched exactly (the live service still held the identical state at verification time, zero drift), the sampled control agreement was 0.9633 against the builder's 0.9635, and the 2025 precinct shares matched with max deviation 0.0000. Full ledger: verification-ledger-independent.md; machine output: data/verify_independent_output.json and data/verify_independent_output.txt. Verifier process note: the first verifier run failed on an ArcGIS query-format error (raw epoch values in a date where-clause); the queries were rewritten with timestamp literals and the full suite then passed - a verifier-side fix, no data change.

## QA cross-checks

- Every number in brief-draft.md and README.md was traced to stats.json or to a data/ panel during drafting; the hero composite and all four charts read stats.json at render time, so no graphic can carry a figure the stats do not.
- The hero lists 34 percent (local share 34.03 percent), 945,811 records, and the -10.1 percent Jan-Oct 2026 criminal change - all three read from stats.json by code/hero_composite.py.
- Hero and all four charts were viewed after rendering; two chart defects found in review (title lines and a footnote overflowing the figure edge, and two colliding end labels on the category chart) were fixed and the charts re-rendered and re-viewed before this file was written.
- Package text was grepped for en and em dashes (none in outward text) and for truncation markers (none).

## Adversarial notes (standards section 12)

- 12.1 proxy-as-outcome: record counts are records of reporting and logging, not incidence; the brief says so in the interpretation alternatives and never calls a count "crime" without the code class attached. The vehicle-category decline's reporting-sensitivity is named as the strongest alternative reading.
- 12.5 figure consistency: the figures quoted in more than one document (945,811; 34.0 percent; 205,180; -9.9 / -10.1 percent; 31.7 / 96.3 / 1.8 percent; 0.80 / 0.82 / 0.32; 94.9 / 67.2 percent; 96.4 percent) were cross-checked across brief-draft.md, README.md, stats.json, the charts and the hero after drafting.
- Named-party check: MNPD is named as the agency and as a lever owner (export repairs, complaint-number population). Every statement about the department is a measured property of its published layer or a labeled interpretation; the "Who can act" repairs are addressed to roles (Open Data / RMS export owners), not individuals. No private individual is named anywhere in the package.
- No figure in this brief depends on a social-media rendering or a third-party summary; all figures derive from the pulled layer, the archived metadata, and the two deposited stack layers.

## Section 11.3 flags

- First publication use of this dataset by Machine Readable: no benchmark or prior brief exists for this layer; the Denver crime brief is the analysis-form mirror, not a benchmark. Nothing in this package is framed as confirming or contradicting a prior Machine Readable figure for Nashville incidents.
- Aggregation-window flag: none. The windows are calendar years and matched Jan-Oct windows, stated everywhere they are used; no rolling or offset window is quoted.
- Timely hook: the Metro Council special meeting on Thursday, November 5, 2026 is named in "Who can act" as timing context only. The brief makes no claim about the meeting's agenda or content.

## Sync gate (standards 10.3)

- Headline figures in the brief, README, hero and charts all derive from the single stats.json produced by code/build_stats.py from the deposited cleaned layer; the pull snapshot's SHA-256 is recorded in data/pull_log.json and in the stack manifest.
- The package was NOT published by this build. The 6:30 AM QA run owns publication. Nothing in this package requires a re-pull: the live service matched the snapshot exactly at verification time, and the verifier's server-side tolerances absorb normal daily drift.

## Stack deposit

- Layer mnpd_incidents added to stack/nashville/manifest.json (raw snapshot + cleaned layer + traps + refresh cadence: the source updates daily; re-snapshot before any brief that uses this layer). A deposit note was appended to stack/nashville/verification.md.
