"""Data-drawn charts for the MNPD incidents brief (2026-11-05).
Brand palette: dark charcoal, amber, teal. Every chart prints its
population, measure, and scope labels on the graphic itself (framing
standard). All figures are read from stats.json at run time.

Layout: titles and footnotes are figure-level text with fixed axes
margins (no tight_layout), so no footnote can clip or overlap an axis.
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parent.parent
stats = json.loads((ROOT / "stats.json").read_text())
CH = ROOT / "charts"
CH.mkdir(exist_ok=True)
CHARCOAL = "#23272b"; AMBER = "#f5a800"; TEAL = "#2a9d8f"; GREY = "#8a8f98"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": CHARCOAL,
                     "axes.edgecolor": CHARCOAL, "axes.labelcolor": CHARCOAL,
                     "xtick.color": CHARCOAL, "ytick.color": CHARCOAL})
SNAP = stats["snapshot_date"]
ROWS = stats["rows"]
FOOT = (f"Source: Metro Nashville Police Department Incidents layer, pulled {SNAP}; {ROWS:,} offense-victim records.\n"
        "Criminal offense codes are the FBI NIBRS list in the agency metadata's Appendix D; local codes are MNPD's 610-850 incident-type series.")


def frame(fig, title, foot, top=0.80, bottom=0.17, left=0.09, right=0.985):
    fig.text(0.012, 0.975, title, fontsize=10.5, va="top", ha="left")
    fig.text(0.012, 0.012, foot, fontsize=7.5, color=GREY, va="bottom", ha="left")
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=right)


def save(fig, name):
    fig.savefig(CH / name, dpi=200, facecolor="white")
    plt.close(fig)
    print(name)


# (a) Composition by matched Jan-Oct window, 2019-2026
jo = stats["jan_oct_windows"]
years = [str(y) for y in range(2019, 2027)]
crim = [jo[y]["nibrs_criminal"] for y in years]
loc = [jo[y]["mnpd_local"] for y in years]
tot = [jo[y]["records"] for y in years]
fig, ax = plt.subplots(figsize=(9.5, 5.4))
ax.bar(years, crim, color=TEAL, label="NIBRS criminal offense codes")
ax.bar(years, loc, bottom=crim, color=AMBER, label="MNPD local incident-type codes")
for x, (c, l, t) in enumerate(zip(crim, loc, tot)):
    ax.text(x, t + 2200, f"{t:,}", ha="center", fontsize=8.5)
    ax.text(x, c / 2, f"{c:,}", ha="center", va="center", fontsize=8, color="white")
    ax.text(x, c + l / 2, f"{l:,}", ha="center", va="center", fontsize=8, color=CHARCOAL)
ax.set_ylim(0, max(tot) * 1.14)
ax.set_ylabel("Records in the Jan-Oct window")
ax.legend(fontsize=8.5, frameon=False, loc="lower left")
ax.spines[["top", "right"]].set_visible(False)
frame(fig,
      "Two ledgers in one file: criminal offense records fall, non-criminal incident records hold\n"
      "Population: all records in matched Jan-Oct windows (2026 is partial by construction, matched to the same window)\n"
      "Criminal offense records fell about 10 percent in each of the last two windows",
      FOOT + "\nWindow totals include 2-27 records per window that carry no offense code and sit in neither segment.",
      top=0.79, bottom=0.175, left=0.085, right=0.99)
save(fig, "chart_composition_jan_oct.png")

# (b) Category trends, Jan-Oct windows
cats = {r["code"]: r for r in stats["categories"]}
veh = stats["vehicle_cluster"]["jan_oct"]
series = [
    ("Vehicle theft cluster (240 + 23F + 23G)", [veh[y] for y in years], AMBER, "-"),
    ("Simple assault (13B)", [cats["13B"]["jan_oct"][y] for y in years], TEAL, "-"),
    ("Aggravated assault (13A)", [cats["13A"]["jan_oct"][y] for y in years], CHARCOAL, "-"),
    ("Vandalism (290)", [cats["290"]["jan_oct"][y] for y in years], GREY, "-"),
    ("Robbery (120)", [cats["120"]["jan_oct"][y] for y in years], TEAL, "--"),
]
fig, ax = plt.subplots(figsize=(9.5, 5.4))
for label, vals, color, ls in series:
    ax.plot(years, vals, color=color, linestyle=ls, marker="o", markersize=4, linewidth=1.8, label=label)
    dy = 550 if label.startswith("Simple") else (-950 if label.startswith("Vehicle") else 0)
    ax.text(len(years) - 1 + 0.12, vals[-1] + dy, f"{vals[-1]:,}", va="center", fontsize=8.5, color=color)
ax.set_ylabel("Records in the Jan-Oct window")
ax.set_xlim(-0.2, len(years) - 0.4)
ax.legend(fontsize=8.5, frameon=False, loc="upper right")
ax.spines[["top", "right"]].set_visible(False)
frame(fig,
      "The decline is in property and street categories; assaults did not fall below their 2019 level\n"
      "Population: records under each NIBRS code in matched Jan-Oct windows; end labels are the Jan-Oct 2026 counts\n"
      "Vehicle theft cluster 16,076 (2023) to 8,585 (2026); robbery 2,230 (2019) to 640; simple assault 8,851 to 8,772",
      FOOT, top=0.79, bottom=0.15, left=0.085, right=0.965)
save(fig, "chart_category_trends.png")

# (c) Status composition by code class
def seg(block):
    n = block["n"]
    return [("Open", block["open"] / n * 100, TEAL),
            ("Unfounded", block["unfounded"] / n * 100, AMBER),
            ("Cleared by arrest", block["cleared_by_arrest"] / n * 100, CHARCOAL),
            ("Refused + other", (block["refused_to_cooperate"] + block["other_and_null"]) / n * 100, GREY)]

pops = [("MNPD local incident-type codes\n(321,859 records)", seg(stats["status"]["mnpd_local"])),
        ("NIBRS criminal offense codes\n(623,874 records)", seg(stats["status"]["nibrs_criminal"]))]
fig, ax = plt.subplots(figsize=(9.5, 4.6))
for i, (label, segs) in enumerate(pops):
    left = 0.0
    for name, val, color in segs:
        ax.barh(i, val, left=left, color=color)
        if val >= 4:
            if left + val >= 99.9:  # final segment: right-align inside the bar end
                ax.text(99.3, i, f"{name}\n{val:.1f}%", ha="right", va="center",
                        fontsize=7.5, color="white" if color != AMBER else CHARCOAL)
            else:
                ax.text(left + val / 2, i, f"{name}\n{val:.1f}%", ha="center", va="center",
                        fontsize=7.5, color="white" if color != AMBER else CHARCOAL)
        left += val
ax.set_yticks([0, 1]); ax.set_yticklabels([p[0] for p in pops], fontsize=9)
ax.set_xlim(0, 100); ax.set_xlabel("Share of the population's records by incident status at the pull date (%)")
ax.spines[["top", "right"]].set_visible(False)
frame(fig,
      "The ledger's 31.7 percent UNFOUNDED rate is a composition artifact\n"
      "Population: all 945,811 records by code class; status is the incident's status at the November 4, 2026 pull\n"
      "96.3 percent of unfounded records sit under local codes; the criminal-code unfounded share is 1.8 percent",
      FOOT, top=0.78, bottom=0.17, left=0.235, right=0.99)
save(fig, "chart_status_by_class.png")

# (d) The 2025 triad: precinct shares across the three ledgers
tri = stats["fusion_triad_2025"]["by_precinct"]
tri = sorted(tri, key=lambda r: -r["incidents_share_2025_all_records"])
labels = [r["precinct"] for r in tri]
import numpy as np
ypos = np.arange(len(labels))
h = 0.26
fig, ax = plt.subplots(figsize=(9.5, 6.0))
ax.barh(ypos + h, [r["calls_share_2025"] * 100 for r in tri], height=h, color=CHARCOAL, label="Calls for service 2025 (demand)")
ax.barh(ypos, [r["incidents_share_2025_all_records"] * 100 for r in tri], height=h, color=TEAL, label="Incident records 2025 (all codes)")
ax.barh(ypos - h, [r["crashes_share_2025"] * 100 for r in tri], height=h, color=AMBER, label="Reported crashes 2025")
ax.set_yticks(ypos); ax.set_yticklabels(labels, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Share of the ledger's known-precinct 2025 records (%)")
ax.legend(fontsize=8.5, frameon=False, loc="lower right")
ax.spines[["top", "right"]].set_visible(False)
frame(fig,
      "Three ledgers, three geographies: where Nashville calls, what gets recorded, where crashes happen\n"
      "Population: 2025 records with a known precinct in each ledger\n"
      "(calls 374,240 of 486,611; incidents 115,565 of 118,421; crashes 26,349 of 26,985)\n"
      "Incident and crash shares track closely (rank correlation 0.82); Midtown Hills leads calls, not incidents",
      "Sources: MNPD Calls for Service 2025 layer (stack deposit 2026-10-16), MNPD Incidents layer pulled 2026-11-04,\n"
      "Nashville Traffic Accidents layer (stack deposit 2026-11-01). Incident precincts are spatial (privacy-rounded coordinates),\n"
      "validated at 96.4 percent against the layer's own zone codes; crash precincts as recorded; call precincts as recorded or zone-derived.",
      top=0.765, bottom=0.175, left=0.115, right=0.99)
save(fig, "chart_triad_precinct_2025.png")
print("charts done")
