# Reviewer notes - Nashville Police Incidents brief (2026-11-05)

Self-review written before publication, in the template's form: what the definitions are, where the framing can be pressed, and what is deliberately not claimed.

## The one definitional choice everything hangs on

The criminal / local split follows the structure of the agency metadata's Appendix D: the FBI NIBRS list first, then MNPD's appended 610-850 series. It is the publisher's own organization of its code list, which is why it is defensible - but it is still a choice, and the brief prints the sensitivity (the six criminal-conduct codes inside the local series, 3,553 records, move the headline change by 0.1 points). A reviewer should press here first: if a reader believes code 850 (a small set of criminal-conduct records) or 64A/64B belong on the criminal side, F1's 34.0 percent becomes 33.7 percent and nothing else in the brief changes materially. That robustness is the finding's strength, and the brief says so rather than hiding the seam.

## Where the framing is most attackable

- F2's "second straight drop of about 10 percent" rests on matched Jan-Oct windows and a tail-completeness estimate (~400 unreported records, ~0.5 percent). If the late-October reporting backlog is larger in 2026 than the ratio test suggests, the 2026 figure rises and the -10.1 percent softens. The ratio method is the same one the Denver brief used, and the prior-year ratios (0.985-1.018) bound the effect well below the size of the change; still, this is the figure most likely to move on a re-pull, and the brief prints the caveat in its definitions rather than a footnote.
- F3's vehicle-cluster story carries the January 2025 23F anomaly inside the 2025 window figure (8,855 as served; 7,207 excluding January). The direction of the 2023-to-2026 comparison does not depend on it (2026 is lower than either 2025 variant by a wide margin), but a careful reviewer should note the 2025 point on chart (b) is flattered for 23F by roughly 1,650 records, and the brief discloses the anomaly in F3 itself, not only in data notes.
- F6 is the finding with the thinnest ice, and the brief says so in its own text: the calls join describes the 15.2 percent of calls that carry a complaint number. If complaint-number carriage correlates with precinct or call type, the 0.32 rank correlation could shift. The triad chart prints the three unknown shares, and the interpretation section's alternative reading names this artifact explicitly. What survives any such correction: the join rate itself (94.9 percent of carried numbers match), which is a data-quality fact about the two systems, not a geographic claim.
- F5 mixes bases deliberately (incidents spatial, crashes recorded) because the recorded basis is the published crash brief's basis; the spatial-vs-recorded control (max share movement 1.38 points) is printed in the finding so the reader does not have to trust the choice.

## What is deliberately not claimed

- No crime-rate, per-capita or risk figure anywhere. Precinct shares are shares of records; the brief repeats this in F5 because precinct rankings are the figures most likely to be quoted out of context.
- No clearance-performance claim. Status is a pull-date snapshot with right-censoring; F4 exists to dismantle the one status figure (31.7 percent unfounded) most likely to be misquoted, and the brief refuses the year-over-year OPEN comparison entirely rather than caveating it.
- No time-of-day, weapon, victim-type or ZIP-level finding: each of those fields failed a documented quality check (placeholder midnights, dual vocabularies, keystroke garbage, ~46 percent missing), and the data notes say which check each failed. A follow-up brief on any of them needs a publisher-side repair first.
- No claim about the November 5, 2026 Metro Council special meeting beyond its date: it is named as the timely audience for the code-class reporting convention, with no representation about the meeting's agenda.

## Provenance notes for the next editor

- This is the first Machine Readable publication from this layer; the Denver crime brief (2026-10-17) is the form mirror, and the natural Friday LinkedIn synthesis pairs the two localities' decomposition findings.
- The layer is now a stack deposit (mnpd_incidents) with a daily-updating source; any future brief from it must re-snapshot first (manifest cadence note) - the figures here are a 2026-11-04 state, verified drift-free at build time but not a standing state.
- Two audit-process blemishes are recorded in verification.md rather than cleaned up in the telling: the audit script's own regex bug on its first run, and the verifier's ArcGIS date-format failure on its first run. Both were tooling defects, both fixed, both re-run clean; the record keeps them because the gate's credibility is the point of the gate.
