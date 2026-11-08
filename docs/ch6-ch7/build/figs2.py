"""Sequence diagram, action diagram, hierarchy, N2, traceability matrix."""
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import mdata as M
from idef0 import RED, BLUE, GRAY, BOXFC, BOXEC
plt.rcParams["font.family"] = "Arial"
OUT = "../diagrams/"


def badge(ax, x, y, s, color, fs=7):
    w = 0.13 + 0.07 * (len(s) - 1)
    ax.add_patch(FancyBboxPatch((x - w / 2, y - 0.085), w, 0.17, boxstyle="round,pad=0,rounding_size=0.08", fc=color, ec="white", lw=.8, zorder=9))
    ax.text(x, y - 0.004, s, fontsize=fs, color="white", ha="center", va="center", fontweight="bold", zorder=10)


def newfig(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


# ------------------------------------------------------------ sequence diagram
def sequence():
    lanes = [("F.1", "Commuter"), ("F.2.1", "Collect Commute Entries"), ("F.2.2", "Manage Reference Data"),
             ("F.2.3", "Estimate Commute Emissions"), ("F.2.4", "Manage Commute Records"),
             ("F.2.5", "Evaluate Feasible Alternatives"), ("F.2.6", "Present Commute Results"),
             ("F.4", "Open-Meteo"), ("F.5", "Emission Factor Publisher")]
    W, H = 11.0, 7.4
    fig, ax = newfig(W, H)
    x0, dx = 1.35, 1.14
    X = {f: x0 + i * dx for i, (f, _) in enumerate(lanes)}
    top = H - 0.3
    for f, n in lanes:
        ext = f in ("F.1", "F.4", "F.5")
        ax.add_patch(FancyBboxPatch((X[f] - 0.5, top - 0.62), 1.0, 0.62, boxstyle="round,pad=0,rounding_size=0.04",
                                    fc="#efe6d2" if ext else BOXFC, ec="#8a7a55" if ext else BOXEC, lw=1))
        ax.text(X[f], top - 0.12, f, fontsize=7.2, fontweight="bold", ha="center", va="center", color="#1a2a6c")
        ax.text(X[f], top - 0.38, "\n".join(textwrap.wrap(n, 15)), fontsize=6.4, ha="center", va="center", linespacing=.95)
        ax.plot([X[f], X[f]], [top - 0.62, 0.35], color="#9aa", lw=.8, ls=(0, (4, 3)), zorder=1)
    ax.text(0.12, top - 0.3, "UC.1\naction", fontsize=6.4, color="#555", va="center")
    y = top - 0.95
    dy = (y - 0.55) / (len(M.SEQ) - 1)
    for num, name, snd, rcv, io, uc, kind in M.SEQ:
        col = RED if kind == "ext" else BLUE
        xs = X[snd]
        xr = [X[r] for r in rcv]
        far = max(xr, key=lambda v: abs(v - xs))
        ls = (0, (5, 3)) if uc == "precondition" else "-"
        ax.plot([xs, far], [y, y], color=col, lw=1.5, ls=ls, zorder=3)
        ax.plot([xs], [y], marker="o", ms=3, color=col, zorder=4)
        for v in xr:
            d = 1 if v > xs else -1
            ax.annotate("", xy=(v, y), xytext=(v - d * 0.2, y),
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=1.5, mutation_scale=8, shrinkA=0, shrinkB=0), zorder=4)
        cx = (xs + far) / 2
        ax.text(cx, y + 0.07, f"{name}  ({io})", fontsize=6.6, ha="center", va="bottom", color=col, zorder=6,
                bbox=dict(fc="white", ec="none", pad=0.5, alpha=.9))
        bxp = min(xs, far) + 0.17 if abs(far - xs) > 0.5 else xs + (-0.17 if far < xs else 0.17)
        badge(ax, bxp, y, num, col)
        ax.text(0.12, y, uc.replace("precondition", "before UC.1"), fontsize=6.2, color="#555", va="center")
        y -= dy
    ax.text(W - 0.1, 0.12, "Red = external interaction (number n)   Blue = internal first-level interaction (n.m)   Dashed = precondition",
            fontsize=6.4, ha="right", color="#333")
    fig.savefig(OUT + "fig_sequence.png", dpi=220)
    plt.close(fig)


# ------------------------------------------------------------ action diagram (model)
def action():
    lanes = ["X.1 Commuter", "C.1 Web Front End", "C.2 Application Service", "C.3 Data Adapter", "C.4 Explanation Model", "X.3 Open-Meteo"]
    acts = [("UC.1.1", "Open Commute Entry", 0), ("UC.1.2", "Present Entry Fields", 1), ("UC.1.3", "Enter Trip Details", 0),
            ("UC.1.4", "Submit Commute", 0), ("UC.1.5", "Accept Entry and Retrieve Factor", 2), ("UC.1.6", "Request Weather", 3),
            ("UC.1.7", "Return Weather Forecast", 5), ("UC.1.8", "Estimate Emissions and Store Trip", 2),
            ("UC.1.9", "Update Trends and Compare Baseline", 2), ("UC.1.10", "Evaluate Feasible Alternatives", 2),
            ("UC.1.11", "Display Commute Result", 1), ("UC.1.12", "Review Result", 0)]
    flows = {0: ("2", "Entry Request"), 1: ("3", "Entry Form"), 3: ("4", "Commute Request"), 5: ("5", "Weather Query"),
             6: ("6", "Weather Forecast"), 10: ("7", "Commute Impact Result")}
    W, H = 11.0, 5.6
    fig, ax = newfig(W, H)
    lh, lx = 0.82, 1.45
    for i, l in enumerate(lanes):
        y = H - 0.4 - (i + 1) * lh
        ax.add_patch(Rectangle((0.1, y), W - 0.2, lh, fc="#f7f9fc" if i % 2 == 0 else "white", ec="#cfd6e0", lw=.8))
        ax.text(0.18, y + lh / 2, "\n".join(textwrap.wrap(l, 14)), fontsize=7, fontweight="bold", va="center", color="#1a2a6c")
    pitch, bw, bh = 0.78, 0.62, 0.56
    pos = []
    for k, (idn, nm, lane) in enumerate(acts):
        cx = lx + 0.38 + k * pitch
        cy = H - 0.4 - (lane + 1) * lh + lh / 2
        pos.append((cx, cy))
        ax.add_patch(FancyBboxPatch((cx - bw / 2, cy - bh / 2), bw, bh, boxstyle="round,pad=0,rounding_size=0.04", fc=BOXFC, ec=BOXEC, lw=1, zorder=4))
        ax.text(cx, cy + 0.2, idn, fontsize=5.8, fontweight="bold", ha="center", va="center", color="#1a2a6c", zorder=5)
        ax.text(cx, cy - 0.05, "\n".join(textwrap.wrap(nm, 12)), fontsize=5.3, ha="center", va="center", zorder=5, linespacing=.9)
    for k in range(len(acts) - 1):
        (x1, y1), (x2, y2) = pos[k], pos[k + 1]
        xa, xb = x1 + bw / 2, x2 - bw / 2
        xm = (xa + xb) / 2
        if k in flows:
            num, nm = flows[k]
            ax.plot([xa, xm, xm, xb], [y1, y1, y2, y2], color=RED, lw=1.4, zorder=3)
            ax.annotate("", xy=(xb, y2), xytext=(xb - .1, y2),
                        arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.4, mutation_scale=7, shrinkA=0, shrinkB=0), zorder=4)
            badge(ax, xm, (y1 + y2) / 2, num, RED)
        else:
            ax.plot([xa, xm, xm, xb], [y1, y1, y2, y2], color="#999", lw=1, ls=(0, (3, 2)), zorder=3)
            ax.text(xm, (y1 + y2) / 2 + (0.0 if y1 != y2 else 0.12), "no I/O", fontsize=5.0, color="#777", ha="center", va="center",
                    rotation=90 if y1 != y2 else 0, bbox=dict(fc="white", ec="none", pad=.3), zorder=6)
    ys = H - 0.25
    ax.text(0.12, ys, "Flow names and numbers:", fontsize=7, fontweight="bold")
    txt = "    ".join(f"{v[0]} {v[1]}" for k, v in flows.items())
    ax.text(2.3, ys, txt, fontsize=6.6, color=RED)
    ax.text(W - 0.1, 0.1, "UC.1.11 is performed by C.1 together with C.4. Dashed = no input/output modelled between the two actions.",
            fontsize=6.2, ha="right", color="#444")
    fig.savefig(OUT + "fig_action_diagram.png", dpi=220)
    plt.close(fig)


# ------------------------------------------------------------ hierarchy
DESC = {
    "F.2.0": "Deploy releases, monitor availability, run retirement",
    "F.2.1": "Present entry form, validate trip details, enforce consent, route deletions",
    "F.2.2": "Hold reviewed factors, select the factor, obtain the forecast",
    "F.2.3": "Estimate trip CO2e and compare with the always-drive baseline",
    "F.2.4": "Store trips, update trends, restrict access, delete on request",
    "F.2.5": "Apply distance, weather and settings rules to pick one alternative",
    "F.2.6": "Assemble and display result, baseline difference, alternative, explanation",
    "F.2.7": "Aggregate usage and CO2e under reporting rules and small-group suppression",
    "F.1": "Records commutes, states consent and settings, uses the advice",
    "F.3": "Sets reporting rules, requests and receives approved summaries",
    "F.4": "Returns a forecast for an approved coarse location and trip time",
    "F.5": "Releases reviewed factors with source, units, geography, version",
    "F.6": "Runs the service and reports hosting status",
}


def node(ax, cx, cy, w, h, idn, name, fc=BOXFC, ec=BOXEC, desc=None, fs=7):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.05", fc=fc, ec=ec, lw=1.1, zorder=4))
    ax.text(cx - w / 2 + 0.05, cy + h / 2 - 0.04, idn, fontsize=fs - .4, fontweight="bold", color="#1a2a6c", va="top", zorder=5)
    ax.text(cx, cy + (0.12 if desc else -0.02), "\n".join(textwrap.wrap(name, max(8, int(w * 12)))), fontsize=fs, ha="center", va="center",
            zorder=5, linespacing=.95, fontweight="bold" if desc else "normal")
    if desc:
        ax.text(cx, cy - h / 2 + 0.06, "\n".join(textwrap.wrap(desc, max(10, int(w * 15)))), fontsize=fs - 1.2, ha="center", va="bottom",
                zorder=5, color="#333", linespacing=.95)


def tree(ax, px, py, ph, kxs, ky, kh):
    ym = (py - ph / 2 + ky + kh / 2) / 2
    ax.plot([px, px], [py - ph / 2, ym], color="#555", lw=1, zorder=2)
    ax.plot([min(kxs + [px]), max(kxs + [px])], [ym, ym], color="#555", lw=1, zorder=2)
    for kx in kxs:
        ax.plot([kx, kx], [ym, ky + kh / 2], color="#555", lw=1, zorder=2)


def hier_overall():
    W, H = 11.0, 5.2
    fig, ax = newfig(W, H)
    for t, yy in [("Level 0", H - 0.5), ("Level 1", H - 1.95), ("Level 2", H - 3.75)]:
        ax.text(0.1, yy, t, fontsize=7, color="#666", va="center")
    rx, ry = W / 2, H - 0.5
    node(ax, rx, ry, 2.2, 0.6, "F.0", "Metafunction", fc="#fff3cf", ec="#b58a1b", fs=8)
    xs = [1.5 + i * 1.7 for i in range(6)]
    y1 = H - 1.95
    for (f, n), x in zip(M.TOP.items(), xs):
        node(ax, x, y1, 1.55, 0.78, f, n, fs=6.8)
    tree(ax, rx, ry, 0.6, xs, y1, 0.78)
    fx = xs[1]
    y2 = H - 3.75
    x2 = [1.15 + i * 1.28 for i in range(8)]
    for (f, n), x in zip(M.L1, x2):
        node(ax, x, y2, 1.18, 0.78, f, n, fs=6.5)
    tree(ax, fx, y1, 0.78, x2, y2, 0.78)
    ax.text(W / 2, 0.8, "F.1, F.3, F.4, F.5 and F.6 are performed by external assets and are not decomposed; F.2 is the function of the system of interest.",
            fontsize=7, ha="center", color="#333")
    ax.text(W / 2, 0.55, "Total: 1 + 6 + 8 = 15 functions on 3 levels.", fontsize=7, ha="center", color="#333")
    fig.savefig(OUT + "fig_hierarchy_overall.png", dpi=220)
    plt.close(fig)


def hier_part(name, kids, title):
    W, H = 7.4, 4.2
    fig, ax = newfig(W, H)
    node(ax, W / 2, H - 0.4, 2.0, 0.5, "F.0", "Metafunction", fc="#fff3cf", ec="#b58a1b", fs=7.5)
    node(ax, W / 2, H - 1.3, 2.8, 0.62, "F.2", M.TOP["F.2"], fs=7.2)
    ax.plot([W / 2, W / 2], [H - 0.65, H - 0.99], color="#555", lw=1)
    n = len(kids)
    pitch = (W - 0.3) / n
    xs = [0.15 + pitch / 2 + i * pitch for i in range(n)]
    y2 = H - 2.85
    for (f, nm), x in zip(kids, xs):
        node(ax, x, y2, pitch - 0.12, 1.5, f, nm, desc=DESC[f], fs=7.2)
    tree(ax, W / 2, H - 1.3, 0.62, xs, y2, 1.5)
    ax.text(W / 2, 0.15, title, fontsize=7, ha="center", color="#333")
    fig.savefig(OUT + name, dpi=220)
    plt.close(fig)


def hier_ext():
    W, H = 7.4, 3.4
    fig, ax = newfig(W, H)
    node(ax, W / 2, H - 0.4, 2.0, 0.5, "F.0", "Metafunction", fc="#fff3cf", ec="#b58a1b", fs=7.5)
    ex = [(f, M.TOP[f]) for f in ("F.1", "F.3", "F.4", "F.5", "F.6")]
    pitch = (W - 0.3) / 5
    xs = [0.15 + pitch / 2 + i * pitch for i in range(5)]
    y2 = H - 1.95
    for (f, nm), x in zip(ex, xs):
        node(ax, x, y2, pitch - 0.1, 1.45, f, nm, desc=DESC[f], fs=7)
        ax.text(x, y2 - 0.78, M.MECH[f], fontsize=5.6, ha="center", va="top", color="#555")
    tree(ax, W / 2, H - 0.4, 0.5, xs, y2, 1.45)
    ax.text(W / 2, 0.12, "Functions of the external assets (level 1 leaves)", fontsize=7, ha="center", color="#333")
    fig.savefig(OUT + "fig_hierarchy_external.png", dpi=220)
    plt.close(fig)


# ------------------------------------------------------------ N2
def n2():
    n = 8
    W, H = 11.2, 7.3
    fig, ax = newfig(W, H)
    x0, y0, cw, ch = 1.45, H - 1.0, 1.2, 0.72
    ids = M.L1ID
    cell = {}
    for io, (srcs, dests) in M.L1FLOW.items():
        for s in srcs:
            for d, role in dests:
                if s != "ENV" and d != "ENV":
                    cell.setdefault((s, d), []).append((io, role))
    traced = {"IO.12", "IO.14", "IO.15", "IO.16", "IO.17", "IO.18", "IO.20"}
    ax.text(x0 + n * cw / 2, H - 0.25, "To (destination function)", fontsize=8, fontweight="bold", ha="center")
    ax.text(0.1, y0 - n * ch / 2, "From\n(source\nfunction)", fontsize=8, fontweight="bold", ha="left", va="center")
    for j, f in enumerate(ids):
        ax.text(x0 + j * cw + cw / 2, y0 + 0.28, f, fontsize=7, fontweight="bold", ha="center", color="#1a2a6c")
        ax.text(x0 + j * cw + cw / 2, y0 + 0.08, M.L1NAME[f], fontsize=5.4, ha="center", va="center")
        ax.text(x0 - 0.06, y0 - j * ch - ch / 2 + 0.14, f, fontsize=7, fontweight="bold", ha="right", va="center", color="#1a2a6c")
        ax.text(x0 - 0.06, y0 - j * ch - ch / 2 - 0.06, "\n".join(textwrap.wrap(M.L1NAME[f], 14)), fontsize=5.2, ha="right", va="center", linespacing=.9)
    for i, s in enumerate(ids):
        for j, d in enumerate(ids):
            x, y = x0 + j * cw, y0 - (i + 1) * ch
            if i == j:
                ax.add_patch(Rectangle((x, y), cw, ch, fc=BOXFC, ec=BOXEC, lw=1))
                ax.text(x + cw / 2, y + ch / 2, f"{s}\n" + "\n".join(textwrap.wrap(M.L1NAME[s], 15)), fontsize=6, ha="center", va="center",
                        fontweight="bold", color="#1a2a6c", linespacing=.95)
                continue
            items = cell.get((s, d))
            if items:
                tr = any(io in traced for io, _ in items)
                ax.add_patch(Rectangle((x, y), cw, ch, fc="#d9e6fb" if tr else "#eef2f6", ec="#6b7f99", lw=.8))
                lines = []
                for io, role in items:
                    nm = M.IO[io] + (" (c)" if role == "C" else "")
                    lines.append(f"{io} " + "\n".join(textwrap.wrap(nm, 20)))
                ax.text(x + cw / 2, y + ch / 2, "\n".join(lines), fontsize=5.4, ha="center", va="center", linespacing=.95,
                        color=BLUE if tr else "#333")
            else:
                ax.add_patch(Rectangle((x, y), cw, ch, fc="white", ec="#c9d1db", lw=.6))
    ly = 0.3
    ax.add_patch(Rectangle((1.45, ly - .09), .3, .18, fc="#d9e6fb", ec="#6b7f99"))
    ax.text(1.83, ly, "flow used in the UC.1 trace", fontsize=6.4, va="center")
    ax.add_patch(Rectangle((3.75, ly - .09), .3, .18, fc="#eef2f6", ec="#6b7f99"))
    ax.text(4.13, ly, "other internal flow", fontsize=6.4, va="center")
    ax.text(5.8, ly, "(c) = the flow is a control of the destination function. Blank cell = no flow.", fontsize=6.4, va="center")
    fig.savefig(OUT + "fig_n2.png", dpi=220)
    plt.close(fig)


# ------------------------------------------------------------ traceability matrix
REQ = [  # id, short name, satisfied-by set, group
    ("3.1.1.1", "accept commuter entries and requests", {"F.2"}, "I/O"), ("3.1.1.2", "accept consent and settings", {"F.2"}, "I/O"),
    ("3.1.1.3", "accept weather forecast data", {"F.2"}, "I/O"), ("3.1.1.4", "accept reviewed emission factors", {"F.2"}, "I/O"),
    ("3.1.1.5", "accept aggregate summary requests", {"F.2"}, "I/O"), ("3.1.1.6", "accept pilot program rules", {"F.2"}, "I/O"),
    ("3.1.1.7", "accept hosting service status", {"F.2"}, "I/O"), ("3.1.2.1", "provide result and advice", {"F.2"}, "I/O"),
    ("3.1.2.2", "provide weather requests", {"F.2"}, "I/O"), ("3.1.2.3", "provide aggregate summaries", {"F.2"}, "I/O"),
    ("3.1.2.4", "provide release configuration", {"F.2"}, "I/O"),
    ("3.2.1", "web entry form", {"F.2", "F.1"}, "Interface"), ("3.2.2", "web result view", {"F.2", "F.1"}, "Interface"),
    ("3.2.3", "weather API request", {"F.2", "F.4"}, "Interface"), ("3.2.4", "weather API response", {"F.2", "F.4"}, "Interface"),
    ("3.2.5", "factor ingestion", {"F.2", "F.5"}, "Interface"), ("3.2.6", "admin dashboard", {"F.2", "F.3"}, "Interface"),
    ("3.2.7", "aggregate export", {"F.2", "F.3"}, "Interface"), ("3.2.8", "hosting interface", {"F.2", "F.6"}, "Interface"),
    ("3.3.1", "provide decision support", {"F.2"}, "Functional"), ("3.3.1.1", "collect commute entries", {"F.2.1"}, "Functional"),
    ("3.3.1.2", "manage reference data", {"F.2.2"}, "Functional"), ("3.3.1.3", "estimate commute emissions", {"F.2.3"}, "Functional"),
    ("3.3.1.4", "manage commute records", {"F.2.4"}, "Functional"), ("3.3.1.5", "evaluate feasible alternatives", {"F.2.5"}, "Functional"),
    ("3.3.1.6", "present commute results", {"F.2.6"}, "Functional"), ("3.3.1.7", "summarize pilot results", {"F.2.7"}, "Functional"),
    ("3.3.1.8", "operate service", {"F.2.0"}, "Functional"),
    ("3.4.1.1", "cost limit", {"F.2"}, "System-wide"), ("3.4.1.2", "report date", {"F.2"}, "System-wide"),
    ("3.4.2.1", "display time", {"F.2"}, "System-wide"), ("3.4.2.2", "entry time", {"F.2"}, "System-wide"),
    ("3.4.3.1", "availability", {"F.2"}, "System-wide"), ("3.4.3.2", "capacity", {"F.2"}, "System-wide"),
    ("3.4.4.1", "WCAG 2.2 AA", {"F.2"}, "System-wide"), ("3.4.5.1", "restrict trip records", {"F.2"}, "System-wide"),
    ("3.4.5.2", "coarse location only", {"F.2"}, "System-wide"), ("3.4.5.3", "small-group suppression", {"F.2"}, "System-wide"),
    ("3.4.6.1", "reproduce reference cases", {"F.2"}, "System-wide"),
]
IO_OF_REQ = {"3.1.1.1": "IO.1", "3.1.1.2": "IO.2", "3.1.1.3": "IO.5", "3.1.1.4": "IO.6", "3.1.1.5": "IO.7", "3.1.1.6": "IO.9",
             "3.1.1.7": "IO.11", "3.1.2.1": "IO.3", "3.1.2.2": "IO.4", "3.1.2.3": "IO.8", "3.1.2.4": "IO.10"}
ROWLIST = [("F.0", "Metafunction"), ("F.1", M.TOP["F.1"]), ("F.2", M.TOP["F.2"])] + [(f, M.L1NAME[f]) for f in M.L1ID] + \
          [("F.3", M.TOP["F.3"]), ("F.4", M.TOP["F.4"]), ("F.5", M.TOP["F.5"]), ("F.6", M.TOP["F.6"])]


def derived(fn, rid):
    io = IO_OF_REQ.get(rid)
    if not io or not fn.startswith("F.2."):
        return False
    srcs, dests = M.L1FLOW[io]
    return fn in srcs or fn in [d for d, _ in dests]


def matrix_data():
    out = {}
    for rid, nm, sat, g in REQ:
        for fn, _ in ROWLIST:
            if fn in sat:
                out[(fn, rid)] = "X"
            elif derived(fn, rid):
                out[(fn, rid)] = "o"
    return out


def matrix():
    data = matrix_data()
    nc, nr = len(REQ), len(ROWLIST)
    W, H = 11.7, 7.3
    fig, ax = newfig(W, H)
    x0, cw = 2.5, 0.215
    ytop, rh = H - 2.4, 0.3
    groups = {}
    for k, r in enumerate(REQ):
        groups.setdefault(r[3], []).append(k)
    cols = {"I/O": "#e8eefa", "Interface": "#eaf5ea", "Functional": "#fff3d9", "System-wide": "#f3e8f5"}
    for g, ks in groups.items():
        xa, xb = x0 + ks[0] * cw, x0 + (ks[-1] + 1) * cw
        ax.add_patch(Rectangle((xa, ytop), xb - xa, nr * -rh, fc=cols[g], ec="none", zorder=0))
        ax.text((xa + xb) / 2, H - 0.18, g + (" requirements" if g != "System-wide" else " req."), fontsize=7, ha="center", fontweight="bold")
        ax.plot([xa + .02, xb - .02], [H - 0.3, H - 0.3], color="#555", lw=1)
    for k, (rid, nm, sat, g) in enumerate(REQ):
        ax.text(x0 + k * cw + cw * 0.3, ytop + 0.04, f"{rid}  {nm}", fontsize=5.4, rotation=65, ha="left", va="bottom", rotation_mode="anchor")
    for i, (fn, nm) in enumerate(ROWLIST):
        y = ytop - (i + 1) * rh
        ax.text(x0 - 0.05, y + rh / 2, f"{fn} {nm}", fontsize=6.0, ha="right", va="center", fontweight="bold" if fn in ("F.0", "F.2") else "normal")
        ax.plot([0.1, x0 + nc * cw], [y, y], color="#c9d1db", lw=.5)
        for k, r in enumerate(REQ):
            v = data.get((fn, r[0]))
            if v == "X":
                ax.text(x0 + k * cw + cw / 2, y + rh / 2, "X", fontsize=7.5, ha="center", va="center", fontweight="bold", color="#111")
            elif v == "o":
                ax.text(x0 + k * cw + cw / 2, y + rh / 2, "o", fontsize=7.5, ha="center", va="center", color=BLUE)
    for k in range(nc + 1):
        ax.plot([x0 + k * cw] * 2, [ytop, ytop - nr * rh], color="#c9d1db", lw=.4)
    ax.plot([0.1, x0 + nc * cw], [ytop, ytop], color="#555", lw=.8)
    ax.text(0.1, 0.12, "X = requirement is satisfied by the function (satisfied by relationship in the model).   "
            "o = the function sends or receives the input/output that the requirement is satisfied by (from the first-level IDEF0).",
            fontsize=6.2, color="#333")
    fig.savefig(OUT + "fig_traceability_matrix.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    sequence()
    action()
    hier_overall()
    hier_part("fig_hierarchy_part1.png", M.L1[:4], "Partition 1 of 2: F.2.0 to F.2.3")
    hier_part("fig_hierarchy_part2.png", M.L1[4:], "Partition 2 of 2: F.2.4 to F.2.7")
    hier_ext()
    n2()
    matrix()
