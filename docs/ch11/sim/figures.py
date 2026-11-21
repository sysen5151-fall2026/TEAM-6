"""Figures of the Chapter 11 and 12 report, drawn from docs/ch11/data/analysis.json and the measured files.

    python docs/ch11/sim/figures.py

Writes PNG files to docs/ch11/diagrams. The risk matrix and the alternatives diagram are drawn from the same data as the
Innoslate model 11.5; the Innoslate screenshots, when the team adds them to docs/ch11/innoslate, are used in the report instead.
"""
import csv
import json
import os
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
D11 = os.path.join(ROOT, "docs", "ch11", "data")
OUT = os.path.join(ROOT, "docs", "ch11", "diagrams")
os.makedirs(OUT, exist_ok=True)
A = json.load(open(os.path.join(D11, "analysis.json"), encoding="utf-8"))
NAVY, TEAL, ORANGE, GREY, RED, GREEN, YEL = "#1F3A5F", "#2A9D8F", "#E76F51", "#8D99AE", "#D64545", "#5FB760", "#F2C94C"
COL = {"A": GREY, "B": "#5B8DB8", "C": "#9B7EBD", "D": TEAL, "E": ORANGE}
NAMES = {"A": "A Sequential", "B": "B Concurrent", "C": "C Keep-alive", "D": "D Name cache", "E": "E Queued"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def rows(name):
    with open(os.path.join(D11, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fig_alternatives():
    """What each alternative does for one plan, drawn from the medians of the route and forecast times measured with 120 s between requests."""
    parts = A["measured"]["gap_parts"]
    med = {k: (statistics.median(r for r, _ in parts[k]), statistics.median(w for _, w in parts[k])) for k in parts}
    poll = A["measured"]["poll_interval_s"] / 2
    fig, ax = plt.subplots(figsize=(9.0, 3.9))
    rows = []   # (label, [(text, start, duration, colour)], end)
    r, w = med["A"]
    rows.append(("A Sequential", [("routes", 0, r, "#8D99AE"), ("forecast", r, w, "#B8C0CC")], r + w))
    r, w = med["B"]
    rows.append(("B Concurrent", [("routes", 0, r, "#5B8DB8"), ("forecast", 0, w, "#A7C4DD")], max(r, w)))
    r, w = med["C"]
    rows.append(("C Keep-alive", [("routes", 0, r, "#9B7EBD"), ("forecast", 0, w, "#C9B8DE")], max(r, w)))
    r, w = med["D"]
    rows.append(("D Name cache", [("routes", 0, r, TEAL), ("forecast", 0, w, "#9ED7CF")], max(r, w)))
    r, w = med["B"]
    rows.append(("E Queued", [("first response", 0, 0.003, ORANGE), ("worker: as B", 0.003, max(r, w), "#F2A895"), ("wait for poll", 0.003 + max(r, w), poll, "#F7CFC4")], 0.003 + max(r, w) + poll))
    two = {"B Concurrent", "C Keep-alive", "D Name cache"}
    for i, (name, bars, end) in enumerate(rows):
        y = len(rows) - i
        for k, (label, start, dur, color) in enumerate(bars):
            if name in two:
                ax.barh(y + (0.17 if k == 0 else -0.17), dur, left=start, height=0.3, color=color, edgecolor="white")
            else:
                ax.barh(y, dur, left=start, height=0.5, color=color, edgecolor="white")
        ax.text(end + 0.08, y, f"{end:.2f} s", va="center", fontsize=8, color="#333")
    ax.axvline(3.0, color=RED, lw=1.2, ls="--")
    ax.text(3.04, len(rows) + 0.6, "3 s limit (3.4.2.1)", color=RED, fontsize=8)
    ax.set_yticks([len(rows) - i for i in range(len(rows))])
    ax.set_yticklabels([x[0] for x in rows])
    ax.set_xlabel("seconds from submit to result (medians of the routing and forecast times measured with 120 s between requests; "
                  "darker bar: routes, lighter: forecast)", fontsize=8)
    ax.set_xlim(0, 5.0)
    ax.set_ylim(0.4, len(rows) + 0.9)
    ax.set_title("What each alternative does for one plan", loc="left", fontsize=10, color=NAVY)
    save(fig, "fig_alternatives.png")


def fig_phases():
    ph = rows("connection_phases.csv")
    hosts = sorted({r["host"] for r in ph})
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    labels = ["name lookup", "TCP connect", "TLS handshake", "first response"]
    cols = [ORANGE, "#5B8DB8", "#9B7EBD", TEAL]
    for i, h in enumerate(hosts):
        sub = [r for r in ph if r["host"] == h]
        vals = [statistics.mean(float(r[k]) for r in sub) for k in ("dns_ms", "tcp_ms", "tls_ms", "first_response_ms")]
        left = 0
        for v, c, lab in zip(vals, cols, labels):
            ax.barh(i, v, left=left, color=c, label=lab if i == 0 else None)
            if v > 150:
                ax.text(left + v / 2, i, f"{v:.0f}", ha="center", va="center", color="white", fontsize=8)
            left += v
        ax.text(left + 40, i, f"{left:.0f} ms", va="center", fontsize=8)
    ax.set_yticks(range(len(hosts)))
    ax.set_yticklabels([h.replace("api.", "") for h in hosts])
    ax.set_xlabel("mean milliseconds per new connection (12 trials each)")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=4, fontsize=8)
    ax.set_title("Where a new connection spends its time", loc="left", fontsize=10, color=NAVY)
    save(fig, "fig_phases.png")


def fig_response():
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    raw = A["measured"]["gap_runs"]
    order = [k for k in "ABCDE" if k in raw]
    for i, k in enumerate(order):
        xs = raw[k]
        ax.boxplot([xs], positions=[i], widths=0.5, showfliers=False, patch_artist=True,
                   boxprops=dict(facecolor=COL[k], alpha=0.35, edgecolor=COL[k]), medianprops=dict(color="black"))
        ax.scatter([i + (j % 5 - 2) * 0.05 for j in range(len(xs))], xs, color=COL[k], s=16, zorder=3)
    ax.axhline(3.0, color=RED, ls="--", lw=1.1)
    ax.text(len(order) - 0.55, 3.05, "3 s", color=RED, fontsize=8, ha="right")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([NAMES[k] for k in order], fontsize=8)
    ax.set_ylabel("plan response (s)")
    ax.set_title("Plan response with 60 s between requests (each dot is one run)", loc="left", fontsize=10, color=NAVY)
    save(fig, "fig_response.png")


def fig_scores():
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ids = [w["id"] for w in A["weights"]]
    colors = ["#1F3A5F", "#5B8DB8", TEAL, "#9B7EBD", ORANGE, YEL]
    alts = list(A["totals"])
    for i, k in enumerate(alts):
        left = 0
        for cid, c in zip(ids, colors):
            w = next(x for x in A["weights"] if x["id"] == cid)["weight"]
            v = A["totals"][k]["values"][cid] * w
            ax.barh(i, v, left=left, color=c, label=cid if i == 0 else None, edgecolor="white")
            left += v
        ax.text(left + 1, i, f"{left:.1f}", va="center", fontsize=9, fontweight="bold")
    ax.set_yticks(range(len(alts)))
    ax.set_yticklabels([NAMES[k] for k in alts])
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xlabel("weighted value score (0 to 100), by criterion")
    ax.legend(frameon=False, ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.18), fontsize=8)
    ax.set_title("Effectiveness score of each alternative", loc="left", fontsize=10, color=NAVY)
    save(fig, "fig_scores.png")


def fig_sensitivity():
    ids = [w["id"] for w in A["weights"]]
    fig, axes = plt.subplots(2, 3, figsize=(9.2, 4.8), sharey=True)
    for ax, cid in zip(axes.flat, ids):
        pts = A["sweep"][cid]
        xs = [p[0] for p in pts]
        for k in A["totals"]:
            ax.plot(xs, [p[2][k] for p in pts], color=COL[k], lw=1.6 if k == A["selected"] else 1.0, label=NAMES[k])
        ax.axvline(1.0, color="#999", lw=0.8, ls=":")
        ax.set_title(f"{cid} weight x factor", fontsize=8.5, loc="left", color=NAVY)
        ax.set_xlim(0, 3)
    axes[0][0].set_ylabel("score")
    axes[1][0].set_ylabel("score")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.03))
    fig.suptitle("Sensitivity: each criterion's weight scaled from 0 to 3 times, others re-normalised", x=0.01, ha="left", fontsize=10, color=NAVY)
    fig.tight_layout()
    save(fig, "fig_sensitivity.png")


def fig_cost():
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for k in A["totals"]:
        ax.scatter(A["lcc"][k]["total"], A["totals"][k]["score"], s=90, color=COL[k], zorder=3)
        ax.annotate(NAMES[k], (A["lcc"][k]["total"], A["totals"][k]["score"]), xytext=(6, 5), textcoords="offset points", fontsize=8)
    ax.set_xlabel("life cycle cost over 3 years (US dollars, labour only)")
    ax.set_ylabel("effectiveness score")
    ax.set_title("Effectiveness against life cycle cost", loc="left", fontsize=10, color=NAVY)
    ax.grid(alpha=0.25)
    save(fig, "fig_cost.png")


def fig_risk_matrix(name="fig_risk_matrix.png", ids=None, title="Risk matrix: likelihood against overall impact"):
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    for L in range(1, 6):
        for I in range(1, 6):
            lvl = L * I
            c = RED if lvl >= 12 else YEL if lvl >= 6 else GREEN
            ax.add_patch(Rectangle((I - 0.5, L - 0.5), 1, 1, facecolor=c, alpha=0.55, edgecolor="white", lw=2))
    cells = {}
    for r in (A["risks"] if ids is None else [x for x in A["register"] if x["id"] in ids]):
        cells.setdefault((r["overall_cell"], r["L"]), []).append(r["id"])
    for (I, L), items in cells.items():
        for j, rid in enumerate(items):
            ax.text(I, L + 0.22 - 0.22 * j, rid, ha="center", va="center", fontsize=9, fontweight="bold", color="black",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#333", lw=0.8))
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.set_xticklabels(["1\nMinor", "2\nModerate", "3\nSerious", "4\nSevere", "5\nCritical"])
    ax.set_yticklabels(["1 Rare", "2 Unlikely", "3 Possible", "4 Likely", "5 Almost certain"])
    ax.set_xlabel("Overall impact (0.5 technical + 0.25 schedule + 0.25 cost, rounded)")
    ax.set_ylabel("Likelihood")
    ax.set_title(title, loc="left", fontsize=10, color=NAVY)
    for s in ax.spines.values():
        s.set_visible(False)
    save(fig, name)


def fig_register_matrix():
    fig_risk_matrix("fig_register_matrix.png", ids=[r["id"] for r in A["register"]], title="Product risk register on the same matrix (15 risks)")


def fig_c4():
    d = json.load(open(os.path.join(D11, "spike_gpu.json"), encoding="utf-8"))
    v1 = json.load(open(os.path.join(D11, "spike_gpu_guard_v1.json"), encoding="utf-8"))
    cats = d["B"]["violation_categories"]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.1), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    names = ["Template\n(A)", "Model, first\nguard", "Model, final\nguard"]
    vals = [0.0, v1["B"]["raw_unsupported_rate"] * 100, d["B"]["raw_unsupported_rate"] * 100]
    ax.bar(names, vals, color=[GREY, ORANGE, RED], width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=9)
    ax.set_ylabel("outputs rejected (%)")
    ax.set_ylim(0, 65)
    ax.set_title("40 cases: raw model text that fails the check", fontsize=9, loc="left", color=NAVY)
    ax = axes[1]
    labels = list(cats)
    ax.barh(labels, [cats[k] for k in labels], color=ORANGE)
    ax.invert_yaxis()
    ax.set_xlabel("violations (an output can have several)")
    ax.set_title("Why the text was rejected", fontsize=9, loc="left", color=NAVY)
    fig.tight_layout()
    save(fig, "fig_c4.png")


if __name__ == "__main__":
    fig_alternatives()
    fig_phases()
    fig_response()
    fig_scores()
    fig_sensitivity()
    fig_cost()
    fig_risk_matrix()
    fig_register_matrix()
    fig_c4()
    print("figures written to", OUT)
