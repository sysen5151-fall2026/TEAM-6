"""Figures for the Chapter 8 + 9 report, drawn from pdata (same source as the model patch)."""
import os
import textwrap
from collections import OrderedDict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import mdata as M
import pdata as P
import idef0m as I

plt.rcParams["font.family"] = "Arial"
HERE = os.path.dirname(os.path.abspath(__file__))
DIA = os.path.join(HERE, "..", "diagrams")
BOXFC, BOXEC, NAVY = "#dce9f7", "#4d78a8", "#1a2a6c"
EXTFC, EXTEC = "#efe6d2", "#8a7a55"
RED, BLUE, BLACK, GRAY = "#c62828", "#1558b0", "#222222", "#a9a9a9"


def out(name):
    return os.path.join(DIA, name)


def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def node(ax, cx, cy, w, h, idn, name, fc=BOXFC, ec=BOXEC, fs=8.5, wrap=14):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.05", fc=fc, ec=ec, lw=1.2, zorder=4))
    ax.text(cx - w / 2 + 0.05, cy + h / 2 - 0.04, idn, fontsize=fs - 1.2, color=NAVY, fontweight="bold", va="top", ha="left", zorder=5)
    ax.text(cx, cy - 0.06, "\n".join(textwrap.wrap(name, wrap)), fontsize=fs, ha="center", va="center", zorder=5, linespacing=1.0)


def tree(ax, parent, kids, ypar, ykid):
    """parent/kids: (cx, w, h) tuples; draws elbow connectors."""
    px, pw, ph = parent
    ymid = (ypar - ph / 2 + ykid + kids[0][2] / 2) / 2
    ax.plot([px, px], [ypar - ph / 2, ymid], color=BLACK, lw=1.2, zorder=2)
    xs = [k[0] for k in kids]
    ax.plot([min(xs + [px]), max(xs + [px])], [ymid, ymid], color=BLACK, lw=1.2, zorder=2)
    for kx, kw, kh in kids:
        ax.annotate("", xy=(kx, ykid + kh / 2), xytext=(kx, ymid), arrowprops=dict(arrowstyle="-|>", color=BLACK, lw=1.2, mutation_scale=9, shrinkA=0, shrinkB=0), zorder=3)


# ------------------------------------------------------------------------------ hierarchy diagrams
def hierarchy_overall():
    fig, ax = canvas(15.5, 7.2)
    bw, bh = 1.45, 0.78
    node(ax, 7.75, 6.6, 1.6, bh, "0", "Universe")
    allx = OrderedDict(list(P.EXTERNAL.items()) + list(P.EXTRA_EXTERNAL.items()))
    xs = {"C.0": 1.6}
    for k, x in enumerate(allx):
        xs[x] = 4.0 + 1.6 * k
    y1 = 5.1
    node(ax, xs["C.0"], y1, bw, bh, "C.0", "EcoCommute")
    for x, n in allx.items():
        node(ax, xs[x], y1, bw, bh, x, n, fc=EXTFC if x not in P.EXTRA_EXTERNAL else "#f3e3d3", ec=EXTEC, wrap=13)
    tree(ax, (7.75, 1.6, bh), [(xs[k], bw, bh) for k in xs], 6.6, y1)
    y2 = 3.4
    cx = [0.95 + 1.78 * i for i in range(8)]
    for a, x in zip(P.A1, cx):
        node(ax, x, y2, 1.62, 0.9, a, P.ASSET_NAME[a], fs=7.8, wrap=15)
    tree(ax, (xs["C.0"], bw, bh), [(x, 1.62, 0.9) for x in cx], y1, y2)
    y3 = 1.35
    kx = [cx[2] - 2.55 + 1.75 * j for j in range(4)]
    kx = [3.0 + 1.75 * j for j in range(4)]
    for a, x in zip(P.A2, kx):
        node(ax, x, y3, 1.6, 0.9, a, P.ASSET_NAME[a], fs=7.6, wrap=12, fc="#e4f0e0", ec="#5f8f55")
    tree(ax, (cx[2], 1.62, 0.9), [(x, 1.6, 0.9) for x in kx], y2, y3)
    ax.text(0.15, 6.9, "Level 0\nLevel 1\nLevel 2\nLevel 3", fontsize=1, alpha=0)
    for y, t in [(6.6, "Universe"), (5.1, "System of interest and external assets"), (3.4, "First-level subsystems (one per first-level function)"), (1.35, "Second-level modules of C.0.2")]:
        ax.text(15.35, y + 0.55, t, fontsize=7.5, ha="right", color="#555555", style="italic")
    fig.savefig(out("fig_hier_overall.png"), dpi=200)
    plt.close(fig)


def hierarchy_context():
    fig, ax = canvas(13, 3.6)
    node(ax, 6.5, 3.0, 1.7, 0.8, "0", "Universe")
    xs = [1.4, 3.3, 5.2, 7.1, 9.0, 10.0]
    items = [("C.0", "EcoCommute", BOXFC, BOXEC)] + [(k, v, EXTFC, EXTEC) for k, v in P.EXTERNAL.items()] + [(k, v, "#f3e3d3", EXTEC) for k, v in P.EXTRA_EXTERNAL.items()]
    xs = [1.0 + 1.55 * i for i in range(8)]
    for x, (i, n, fc, ec) in zip(xs, items):
        node(ax, x, 1.2, 1.4, 0.85, i, n, fc=fc, ec=ec, fs=8.0, wrap=13)
    tree(ax, (6.5, 1.7, 0.8), [(x, 1.4, 0.85) for x in xs], 3.0, 1.2)
    fig.savefig(out("fig_hier_context.png"), dpi=200)
    plt.close(fig)


def hierarchy_c0():
    fig, ax = canvas(15.0, 4.7)
    node(ax, 7.5, 4.0, 2.4, 0.8, "C.0", "EcoCommute", fs=9)
    cx = [0.95 + 1.8 * i for i in range(8)]
    for (f, v), x in zip(P.ASSET1.items(), cx):
        node(ax, x, 1.7, 1.66, 1.0, v[0], v[1], fs=8.2, wrap=15)
        ax.text(x, 0.82, f"performs {f}\n{M.L1NAME[f]}", fontsize=6.6, ha="center", va="top", color="#7a1f1f", linespacing=1.0)
    tree(ax, (7.5, 2.4, 0.8), [(x, 1.66, 1.0) for x in cx], 4.0, 1.7)
    fig.savefig(out("fig_hier_c0.png"), dpi=200)
    plt.close(fig)


def hierarchy_c02():
    fig, ax = canvas(10.5, 4.6)
    node(ax, 5.25, 3.9, 2.6, 0.85, "C.0.2", "Reference Data Subsystem", fs=9, wrap=26)
    kx = [1.3 + 2.6 * j for j in range(4)]
    for (f, v), x in zip(P.FUNC2.items(), kx):
        node(ax, x, 1.7, 2.2, 1.0, v[1], v[2], fs=8.5, wrap=18, fc="#e4f0e0", ec="#5f8f55")
        ax.text(x, 0.95, f"performs {f}\n{v[0]}", fontsize=7.2, ha="center", va="top", color="#7a1f1f", linespacing=1.0)
    tree(ax, (5.25, 2.6, 0.85), [(x, 2.2, 1.0) for x in kx], 3.9, 1.7)
    fig.savefig(out("fig_hier_c02.png"), dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------------------ IDEF0
def idef0_first():
    I.MECH.clear()
    I.MECH.update({f: (v[0], v[1]) for f, v in P.ASSET1.items()})
    F, *_ = I.first_level("x")
    F.ax.text(0.25, 0.55, "Mechanism of F.2: C.0 EcoCommute (decomposed by C.0.0 to C.0.7)", fontsize=7.4, color="#7a1f1f", fontweight="bold")
    I.finish(F, out("fig_idef0_first_mech.png"))


def idef0_second():
    W, H = 12.4, 7.4
    fig, ax = canvas(W, H)
    bw, bh = 1.75, 0.95
    pos = {"F.2.2.1": (4.4, 6.0), "F.2.2.2": (6.2, 4.55), "F.2.2.3": (8.0, 3.1), "F.2.2.4": (9.8, 1.65)}  # centre
    for f, (x, y) in pos.items():
        name, aid, an, _ = P.FUNC2[f]
        ax.add_patch(FancyBboxPatch((x - bw / 2, y - bh / 2), bw, bh, boxstyle="round,pad=0,rounding_size=0.05", fc=BOXFC, ec=BOXEC, lw=1.3, zorder=4))
        ax.text(x - bw / 2 + 0.06, y + bh / 2 - 0.05, f, fontsize=8, color=NAVY, fontweight="bold", va="top", zorder=5)
        ax.text(x, y - 0.06, "\n".join(textwrap.wrap(name, 16)), fontsize=9.2, ha="center", va="center", zorder=5)
        ax.annotate("", xy=(x, y - bh / 2), xytext=(x, y - bh / 2 - 0.36), arrowprops=dict(arrowstyle="-|>", color=BLACK, lw=1.2, mutation_scale=9, shrinkA=0, shrinkB=0))
        ax.text(x, y - bh / 2 - 0.40, aid + "\n" + an, fontsize=7.6, ha="center", va="top", color="#7a1f1f", fontweight="bold", linespacing=1.0,
                bbox=dict(fc="white", ec="none", pad=0.8), zorder=7)

    def line(pts, arrow=True, dot=False):
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=BLACK, lw=1.3, zorder=3)
        if arrow:
            (x1, y1), (x2, y2) = pts[-2], pts[-1]
            ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color=BLACK, lw=1.3, mutation_scale=9, shrinkA=0, shrinkB=0), zorder=4)
        if dot:
            ax.plot([pts[0][0]], [pts[0][1]], "o", ms=3, color=BLACK, zorder=5)

    def lab(x, y, s, ha="center", va="center", fs=7.8, bold=False):
        ax.text(x, y, s, fontsize=fs, ha=ha, va=va, zorder=6, linespacing=1.0, fontweight="bold" if bold else "normal",
                bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.95))

    L = lambda f: pos[f][0] - bw / 2
    R_ = lambda f: pos[f][0] + bw / 2
    T = lambda f: pos[f][1] + bh / 2
    # inputs from environment (left)
    x_in = 0.2
    y22, y23 = pos["F.2.2.2"][1] + 0.12, pos["F.2.2.3"][1] + 0.12
    line([(x_in + 1.65, y22), (L("F.2.2.2"), y22)])
    line([(2.55, y22), (2.55, y23), (L("F.2.2.3"), y23)], dot=False)
    ax.plot([2.55], [y22], "o", ms=3, color=BLACK, zorder=5)
    lab(x_in + 0.8, y22 + 0.02, "Validated\nCommute Entry\n(IO.12)", fs=7.8)
    y24 = pos["F.2.2.4"][1] + 0.12
    line([(x_in + 1.65, y24), (L("F.2.2.4"), y24)])
    lab(x_in + 0.8, y24 + 0.02, "Weather\nForecast Data\n(IO.5)", fs=7.8)
    # control from top: IO.6 -> F.2.2.1
    line([(pos["F.2.2.1"][0], 7.05), (pos["F.2.2.1"][0], T("F.2.2.1"))])
    lab(pos["F.2.2.1"][0] + 1.35, 7.0, "Reviewed Emission Factors (IO.6)", fs=7.8)
    # IO.23: F.2.2.1 -> F.2.2.2 control
    y1 = pos["F.2.2.1"][1] + 0.1
    xc2 = pos["F.2.2.2"][0] + 0.2
    line([(R_("F.2.2.1"), y1), (xc2, y1), (xc2, T("F.2.2.2"))])
    lab(xc2 + 0.05, y1 - 0.0, "Versioned Factor Set (IO.23)", ha="left", fs=7.6)
    # IO.14: F.2.2.2 -> env right
    xo = 11.4
    y2o = pos["F.2.2.2"][1] + 0.12
    line([(R_("F.2.2.2"), y2o), (xo, y2o)])
    lab(xo + 0.05, y2o, "Emission Factor\nRecord (IO.14)", ha="left")
    # IO.4: F.2.2.3 -> env right (upper) ; IO.24 lower -> F.2.2.4 control
    y3a, y3b = pos["F.2.2.3"][1] + 0.2, pos["F.2.2.3"][1] - 0.08
    line([(R_("F.2.2.3"), y3a), (xo, y3a)])
    lab(xo + 0.05, y3a, "Weather\nRequest (IO.4)", ha="left")
    xc4 = pos["F.2.2.4"][0] + 0.25
    line([(R_("F.2.2.3"), y3b), (xc4, y3b), (xc4, T("F.2.2.4"))])
    lab(xc4 + 0.05, y3b - 0.0, "Forecast Query Context (IO.24)", ha="left", fs=7.6)
    y4o = pos["F.2.2.4"][1] + 0.12
    line([(R_("F.2.2.4"), y4o), (xo, y4o)])
    lab(xo + 0.05, y4o, "Trip Weather\nForecast (IO.15)", ha="left")
    ax.text(0.25, 0.35, "Mechanism of F.2.2: C.0.2 Reference Data Subsystem (decomposed by C.0.2.1 to C.0.2.4).   Control IO.6, inputs IO.5 and IO.12, outputs IO.4, IO.14 and IO.15 are carried down from the first-level IDEF0.",
            fontsize=7.4, color="#7a1f1f", fontweight="bold")
    fig.savefig(out("fig_idef0_second_mech.png"), dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------------------ asset (conduit) diagrams
def _conduit_label(ax, x, y, cid, ios, fs=6.8, color=BLUE):
    ax.text(x, y, f"{cid}\n{' '.join(i.replace('IO.', '') for i in ios)}", fontsize=fs, ha="center", va="center", color=color, zorder=8,
            linespacing=0.95, bbox=dict(fc="white", ec=color, lw=0.6, pad=1.2, boxstyle="round,pad=0.15"))


def asset_context():
    fig, ax = canvas(11.5, 6.4)
    node(ax, 5.75, 3.2, 2.3, 1.2, "C.0", "EcoCommute", fs=11)
    spots = {"X.1": (1.5, 5.3), "X.2": (1.5, 1.1), "X.3": (5.75, 5.7), "X.4": (10.0, 5.3), "X.5": (10.0, 1.1)}
    spots.update({"X.6": (10.3, 3.2), "X.7": (5.75, 0.7)})
    allx = dict(P.EXTERNAL)
    allx.update(P.EXTRA_EXTERNAL)
    for x, (cx, cy) in spots.items():
        node(ax, cx, cy, 1.9, 0.9, x, allx[x], fc=EXTFC if x in P.EXTERNAL else "#f3e3d3", ec=EXTEC, fs=9)
    ctx = [  # name, external, ios, offset of label along line
        ("Trip details", "X.1", ["IO.1", "IO.2"], (-0.28, 0.0)), ("Result and advice", "X.1", ["IO.3"], (0.28, 0.0)),
        ("Weather query", "X.3", ["IO.4"], (-0.3, 0)), ("Forecast", "X.3", ["IO.5"], (0.3, 0)),
        ("Reviewed factors", "X.4", ["IO.6"], (0, 0)), ("Summary request", "X.2", ["IO.7", "IO.9"], (-0.3, 0)),
        ("Approved aggregates", "X.2", ["IO.8"], (0.3, 0)), ("Hosting service", "X.5", ["IO.10", "IO.11"], (0, 0)),
    ]
    import numpy as np
    ctx += [(n, x, io_, (-0.3 if n == "Route request" else 0.3 if n == "Route response" else 0, 0)) for n, x, io_ in P.CTX_EXTRA]
    for name, x, ios, (dx, _) in ctx:
        extra = x in P.EXTRA_EXTERNAL
        cx, cy = spots[x]
        p0 = np.array([5.75, 3.2])
        p1 = np.array([cx, cy])
        v = p1 - p0
        nrm = np.array([-v[1], v[0]]) / np.linalg.norm(v)
        off = nrm * dx * 1.3
        a = p0 + v * 0.22 + off
        b = p1 - v * 0.17 + off
        ax.plot([a[0], b[0]], [a[1], b[1]], color=BLACK, lw=1.2, zorder=2, ls="--" if extra else "-")
        m = (a + b) / 2
        ax.text(m[0], m[1], f"{name}\n{', '.join(ios)}", fontsize=6.9, ha="center", va="center", color=BLUE, zorder=8, linespacing=0.95,
                bbox=dict(fc="white", ec="none", pad=1.2))
    ax.text(0.15, 0.12, "Dashed: conduits and assets added in model 11.0 for use cases UC.3 and UC.4; they have no top-level function yet.", fontsize=7.2, color="#555555")
    fig.savefig(out("fig_asset_context.png"), dpi=200)
    plt.close(fig)


POS1 = {  # first-level asset diagram layout
    "C.0.1": (4.2, 7.6), "C.0.2": (7.2, 8.4), "C.0.3": (10.2, 7.6), "C.0.5": (7.4, 6.2), "C.0.6": (12.0, 4.6),
    "C.0.4": (4.4, 3.0), "C.0.7": (8.4, 2.6), "C.0.0": (3.0, 1.5),
    "X.1": (1.2, 5.6), "X.3": (11.8, 9.2), "X.4": (4.2, 9.4), "X.2": (12.4, 1.6), "X.5": (0.9, 0.5),
}


def asset_first():
    import numpy as np
    fig, ax = canvas(14.2, 10.2)
    ax.add_patch(Rectangle((2.2, 0.95), 11.0, 8.1, fc="#f8fafd", ec="#9bb1cc", lw=1.2, ls="--", zorder=0))
    ax.text(2.35, 8.85, "C.0 EcoCommute", fontsize=10, fontweight="bold", color=NAVY, va="top")
    for a, (x, y) in POS1.items():
        if a.startswith("X"):
            node(ax, x, y, 1.7, 0.85, a, P.EXTERNAL[a], fc=EXTFC, ec=EXTEC, fs=8.4, wrap=13)
        else:
            node(ax, x, y, 1.85, 0.95, a, P.ASSET_NAME[a], fs=8.4, wrap=15)
    for cid, name, a, b, ios, med in P.CONDUITS1:
        pa, pb = np.array(POS1[a]), np.array(POS1[b])
        v = pb - pa
        L = np.linalg.norm(v)
        u = v / L
        # trim to box edges
        def trim(p, u, bw=0.9, bh=0.48):
            t = min(bw / abs(u[0]) if u[0] else 1e9, bh / abs(u[1]) if u[1] else 1e9)
            return p + u * t
        s, e = trim(pa, u), trim(pb, -u)
        e = pb - u * (np.linalg.norm(trim(pb, -u) - pb))
        # separate paired conduits slightly
        nrm = np.array([-u[1], u[0]])
        pair = [c for c in P.CONDUITS1 if {c[2], c[3]} == {a, b}]
        k = pair.index(next(c for c in pair if c[0] == cid)) - (len(pair) - 1) / 2
        s, e = s + nrm * 0.16 * k, e + nrm * 0.16 * k
        ext = a.startswith("X") or b.startswith("X")
        ax.plot([s[0], e[0]], [s[1], e[1]], color="#555555" if not ext else "#8a6d2f", lw=1.3, zorder=2)
        frac = 0.5 + 0.0
        m = s + (e - s) * frac
        _conduit_label(ax, m[0], m[1], cid, ios, color=BLUE if not ext else "#8a4b00")
    ax.text(2.4, 0.15, "Conduit tags: conduit id above, transferred input/output numbers below (e.g. 12 = IO.12). Brown = interface to an external asset; blue = internal interface. Names and media: Table 11.",
            fontsize=7.6, color="#444444")
    fig.savefig(out("fig_asset_first.png"), dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------------------ N2 / I2
def _matrix(path, ids, names, cells, top, right, cw, ch, title_fs=7.6, cell_fs=6.2, idkind="F"):
    n = len(ids)
    W, H = (n + 2) * cw, (n + 1) * ch + 0.2
    fig, ax = canvas(W, H)
    # grid origin: top-left of the matrix at (0, H-ch-0.1)
    def cell(i, j):  # row i, col j
        return (j * cw, H - 0.1 - ch - (i + 1) * ch + ch)  # bottom-left y
    ax.add_patch(Rectangle((0, 0), 0.001, 0.001))
    for i in range(n):
        for j in range(n):
            x = j * cw
            y = H - 0.1 - ch - (i) * ch - ch
            fc = "white"
            ax.add_patch(Rectangle((x, y), cw, ch, fc=fc, ec="#555555", lw=0.9))
            if i == j:
                ax.add_patch(Rectangle((x, y), cw, ch, fc=BOXFC, ec="#555555", lw=0.9))
                ax.text(x + 0.06, y + ch - 0.06, ids[i], fontsize=title_fs, color=NAVY, fontweight="bold", va="top")
                ax.text(x + cw / 2, y + ch / 2 - 0.05, "\n".join(textwrap.wrap(names[i], 16)), fontsize=title_fs + 0.6, ha="center", va="center")
            elif (i, j) in cells:
                ax.text(x + 0.05, y + ch - 0.05, cells[(i, j)], fontsize=cell_fs, va="top", ha="left", linespacing=1.05, color="#1c1c1c")
    # top row (from outside) and right column (to outside)
    for j in range(n):
        x = j * cw
        y = H - 0.1 - ch
        ax.add_patch(Rectangle((x, y), cw, ch, fc="#fbf7ee", ec="#555555", lw=0.9))
        if j in top:
            ax.text(x + 0.05, y + ch - 0.05, top[j], fontsize=cell_fs, va="top", ha="left", linespacing=1.05)
    for i in range(n):
        x = n * cw
        y = H - 0.1 - ch - i * ch - ch
        ax.add_patch(Rectangle((x, y), cw, ch, fc="#fbf7ee", ec="#555555", lw=0.9))
        if i in right:
            ax.text(x + 0.05, y + ch - 0.05, right[i], fontsize=cell_fs, va="top", ha="left", linespacing=1.05)
    # the grid above uses y offset so that top row sits above row 0
    ax.set_ylim(0, H)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _fix_matrix(path, ids, names, cells, top, right, cw, ch, title_fs=8.6, cell_fs=7.4):
    n = len(ids)
    W, H = (n + 1) * cw + 0.1, (n + 1) * ch + 0.1
    fig, ax = canvas(W, H)
    ytop = H - 0.05
    ax.text(0.05, ytop + 0.0, "", fontsize=1)
    for j in range(n):          # top row
        x = 0.05 + j * cw
        y = ytop - ch
        ax.add_patch(Rectangle((x, y), cw, ch, fc="#fbf7ee", ec="#555555", lw=0.9))
        if j in top:
            ax.text(x + 0.05, y + ch - 0.05, top[j], fontsize=cell_fs, va="top", ha="left", linespacing=1.05)
    for i in range(n):
        for j in range(n + 1):
            x = 0.05 + j * cw
            y = ytop - ch - (i + 1) * ch
            if j == n:
                ax.add_patch(Rectangle((x, y), cw, ch, fc="#fbf7ee", ec="#555555", lw=0.9))
                if i in right:
                    ax.text(x + 0.05, y + ch - 0.05, right[i], fontsize=cell_fs, va="top", ha="left", linespacing=1.05)
                continue
            if i == j:
                ax.add_patch(Rectangle((x, y), cw, ch, fc=BOXFC, ec="#555555", lw=0.9))
                ax.text(x + 0.06, y + ch - 0.06, ids[i], fontsize=title_fs - 0.6, color=NAVY, fontweight="bold", va="top")
                ax.text(x + cw / 2, y + ch / 2 - 0.07, "\n".join(textwrap.wrap(names[i], 15)), fontsize=title_fs, ha="center", va="center")
            else:
                ax.add_patch(Rectangle((x, y), cw, ch, fc="white", ec="#555555", lw=0.9))
                if (i, j) in cells:
                    ax.text(x + 0.05, y + ch - 0.05, cells[(i, j)], fontsize=cell_fs, va="top", ha="left", linespacing=1.05)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def i2_first():
    ids = P.A1
    idx = {a: i for i, a in enumerate(ids)}
    cells, top, right = {}, {}, {}
    for cid, name, a, b, ios, med in P.CONDUITS1:
        txt = f"{cid} {name}\n{', '.join(ios)}"
        if a in idx and b in idx:
            # information direction: IO produced by a's function flows to b
            cells[(idx[a], idx[b])] = (cells.get((idx[a], idx[b]), "") + ("\n" if (idx[a], idx[b]) in cells else "") + txt)
        elif b in idx:   # external -> asset (top row), also bidirectional trip details handled
            fl = [io for io in ios]
            top[idx[b]] = (top.get(idx[b], "") + ("\n" if idx[b] in top else "") + f"{a} > {cid} {name}\n{', '.join(fl)}")
        elif a in idx:
            right[idx[a]] = (right.get(idx[a], "") + ("\n" if idx[a] in right else "") + f"{cid} {name} > {b}\n{', '.join(ios)}")
    # trip details also carries IO.3 back to the Commuter; hosting service carries IO.11 in
    right[1] = right.get(1, "") + "\nK.1 Trip details > X.1\nIO.3 (entry form)"
    top[0] = top.get(0, "") + "\nX.5 > K.11 Hosting service\nIO.11"
    names = [P.ASSET_NAME[a] for a in ids]
    _fix_matrix(out("fig_i2_first.png"), ids, names, cells, top, right, 1.5, 0.84)


def i2_second():
    ids = P.A2
    idx = {a: i for i, a in enumerate(ids)}
    cells = {(0, 1): "K.2.1 Factor set access\nIO.23", (2, 3): "K.2.2 Query context\nIO.24"}
    top = {0: "X.4 > K.7 Reviewed factors\nIO.6", 1: "C.0.1 > K.12 Entry to\nreference data\nIO.12", 2: "C.0.1 > K.12 Entry to\nreference data\nIO.12",
           3: "X.3 > K.6 Forecast\nIO.5"}
    right = {1: "K.16 Factor record\n> C.0.3\nIO.14", 2: "K.5 Weather query\n> X.3\nIO.4", 3: "K.17 Trip forecast\n> C.0.5\nIO.15"}
    _fix_matrix(out("fig_i2_second.png"), ids, [P.ASSET_NAME[a] for a in ids], cells, top, right, 1.85, 1.25)


def n2_second():
    ids = P.L2ORDER
    cells = {(0, 1): "IO.23 Versioned\nFactor Set", (2, 3): "IO.24 Forecast\nQuery Context"}
    top = {0: "IO.6 Reviewed\nEmission Factors", 1: "IO.12 Validated\nCommute Entry", 2: "IO.12 Validated\nCommute Entry", 3: "IO.5 Weather\nForecast Data"}
    right = {1: "IO.14 Emission\nFactor Record", 2: "IO.4 Weather\nRequest", 3: "IO.15 Trip Weather\nForecast"}
    _fix_matrix(out("fig_n2_second.png"), ids, [P.FUNC2[f][0] for f in ids], cells, top, right, 1.85, 1.25)


# ------------------------------------------------------------------------------ sequence diagrams
def sequence(path, lanes, steps, title_left, w=11.5, row=0.62, legend=True):
    n = len(lanes)
    H = 1.9 + row * len(steps)
    fig, ax = canvas(w, H)
    x0, dx = 1.1, (w - 1.2) / n
    cx = {l[0]: x0 + dx * (i + 0.5) for i, l in enumerate(lanes)}
    for lid, name, kind in lanes:
        fc, ec = (EXTFC, EXTEC) if kind == "ext" else (BOXFC, BOXEC)
        ax.add_patch(FancyBboxPatch((cx[lid] - dx * 0.44, H - 1.25), dx * 0.88, 0.95, boxstyle="round,pad=0,rounding_size=0.05", fc=fc, ec=ec, lw=1.3, zorder=3))
        ax.text(cx[lid], H - 0.52, lid, fontsize=9, ha="center", va="center", fontweight="bold", color=NAVY, zorder=4)
        ax.text(cx[lid], H - 0.85, "\n".join(textwrap.wrap(name, 14)), fontsize=8.4, ha="center", va="center", zorder=4, linespacing=0.95)
        ax.plot([cx[lid]] * 2, [H - 1.25, 0.55], color="#8aa09a", ls="--", lw=0.9, zorder=1)
    ax.text(0.1, H - 0.8, title_left, fontsize=7.6, color="#555555")
    for k, (num, name, snd, rcv, io, uc, kind) in enumerate(steps):
        y = H - 1.25 - row * (k + 0.75)
        col = RED if kind == "ext" else BLUE
        ax.text(0.1, y, uc.replace(", ", ",\n"), fontsize=7, va="center", color="#555555", linespacing=0.95)
        tgt = rcv if isinstance(rcv, list) else [rcv]
        xs_ = cx[snd]
        far = max(tgt, key=lambda t: abs(cx[t] - xs_))
        ax.plot([xs_, cx[far]], [y, y], color=col, lw=1.9, zorder=3, ls="--" if uc == "precondition" else "-")
        ax.plot([xs_], [y], "o", ms=3.5, color=col, zorder=5)
        for t in tgt:
            d = 1 if cx[t] > xs_ else -1
            ax.annotate("", xy=(cx[t], y), xytext=(cx[t] - d * 0.2, y), arrowprops=dict(arrowstyle="-|>", color=col, lw=1.9, mutation_scale=9, shrinkA=0, shrinkB=0), zorder=5)
        mid = (xs_ + cx[far]) / 2
        ax.text(mid, y + 0.1, f"{name} ({io})", fontsize=8.8, ha="center", va="bottom", color=col, zorder=6)
        bx = xs_ + (0.3 if cx[far] > xs_ else -0.3)
        ax.add_patch(FancyBboxPatch((bx - 0.17, y - 0.1), 0.34, 0.2, boxstyle="round,pad=0,rounding_size=0.09", fc=col, ec="white", lw=0.8, zorder=7))
        ax.text(bx, y - 0.005, num, fontsize=7, color="white", ha="center", va="center", fontweight="bold", zorder=8)
    if legend:
        ax.text(w - 0.1, 0.2, "Red = interaction with an external asset (n)   Blue = internal interaction (n.m)   Dashed = precondition", fontsize=7.4, ha="right", color="#333333")
    fig.savefig(path, dpi=200)
    plt.close(fig)


def seq_first():
    lanes = [("X.1", "Commuter", "ext")] + [(a, P.ASSET_NAME[a], "int") for a in ["C.0.1", "C.0.2", "C.0.3", "C.0.4", "C.0.5", "C.0.6"]] + [("X.3", "Open-Meteo", "ext"), ("X.4", "Emission Factor Publisher", "ext")]
    sequence(out("fig_seq_first.png"), lanes, P.SEQ1, "UC.1\naction", w=12.2)


def seq_second():
    lanes = [("X.4", "Emission Factor Publisher", "ext"), ("C.0.1", "Entry Subsystem", "int")] + [(a, P.ASSET_NAME[a], "int") for a in P.A2] + [("C.0.3", "Estimation Subsystem", "int"), ("C.0.5", "Recommendation Subsystem", "int"), ("X.3", "Open-Meteo", "ext")]
    sequence(out("fig_seq_second.png"), lanes, P.SEQ2, "UC.1\naction", w=12.2, row=0.72)


# ------------------------------------------------------------------------------ spider (traceability)
def spider():
    import reqdata as Q
    fig, ax = canvas(13.0, 9.4)
    cx, cy = 6.5, 4.7
    node(ax, cx, cy, 2.4, 0.95, "C.0.2", "Reference Data Subsystem", fs=9.5, wrap=18)

    def box(x, y, t, fc, w=0.95, h=0.36, fs=7.2):
        ax.plot([cx, x], [cy, y], color="#9aa3ad", lw=0.8, zorder=1)
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.06", fc=fc, ec="#666666", lw=0.8, zorder=3))
        ax.text(x, y, t, fontsize=fs, ha="center", va="center", zorder=4, linespacing=1.0)

    def head(x, y, t, fc, ha="center"):
        ax.text(x, y, t, fontsize=8, fontweight="bold", ha=ha, va="center", color="#333333", bbox=dict(fc=fc, ec="none", pad=2.5), zorder=5)
    sysr = ["3.3.1.2", "3.1.1.3", "3.1.1.4", "3.1.2.2", "3.2.3", "3.2.4", "3.2.5", "3.4.1.1", "3.4.1.2", "3.4.2.1", "3.4.3.1", "3.4.3.2", "3.4.5.2", "3.4.6.1"]
    head(cx, 9.05, "system requirements it is traced from (via the component requirements)", "#f6dede")
    for k, t in enumerate(sysr):
        box(1.45 + (k % 7) * 1.7, 8.45 if k < 7 else 7.8, t, "#f6dede", w=1.1)
    head(1.15, 6.55, "functions performed", "#dce9f7")
    for k, t in enumerate(["F.2.2"] + list(P.FUNC2)):
        box(1.15, 6.0 - k * 0.55, t, "#dce9f7", w=1.1)
    head(11.7, 6.55, "component requirements (satisfied by)", "#ead9f3")
    groups = [("5.1 Input", "5.1.1 to 5.1.3"), ("5.2 Output", "5.2.1 to 5.2.3"), ("5.3 Interface", "5.3.1 to 5.3.6"), ("5.4 Functional", "5.4.1 to 5.4.4"), ("5.5 System-wide", "5.5.1 to 5.5.7")]
    for k, (a_, b_) in enumerate(groups):
        box(11.7, 6.0 - k * 0.62, a_ + chr(10) + b_, "#ead9f3", w=1.7, h=0.5)
    head(2.6, 2.75, "modules (decomposed by)", "#e4f0e0")
    for k, t in enumerate(P.ASSET2):
        box(1.0 + k * 1.3, 2.15, t, "#e4f0e0", w=1.15)
    head(9.0, 2.75, "conduits (transfer input/outputs)", "#fff0cf")
    ks = ["K.5", "K.6", "K.7", "K.12", "K.16", "K.17", "K.2.1", "K.2.2"]
    for k, t in enumerate(ks):
        box(7.2 + (k % 4) * 1.35, 2.15 if k < 4 else 1.5, t, "#fff0cf", w=1.1)
    fig.savefig(out("fig_spider.png"), dpi=200)
    plt.close(fig)


def alt_chart():
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    names, vals = [], []
    for k, (n, d, sc) in P.ALTS.items():
        names.append(f"{k}  {n}")
        vals.append(sum(w * s for (_, w, _), s in zip(P.CRITERIA, sc)) / 100)
    cols = ["#1558b0", "#a9a9a9", "#a9a9a9"]
    b = ax.barh(names[::-1], vals[::-1], color=cols[::-1])
    for r, v in zip(b, vals[::-1]):
        ax.text(v + 0.05, r.get_y() + r.get_height() / 2, f"{v:.2f}", va="center", fontsize=9)
    ax.set_xlim(0, 5)
    ax.set_xlabel("Weighted score (1 to 5)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out("fig_alt_scores.png"), dpi=200)
    plt.close(fig)


def all_figs():
    hierarchy_overall(); hierarchy_context(); hierarchy_c0(); hierarchy_c02()
    idef0_first(); idef0_second()
    asset_context(); asset_first()
    i2_first(); i2_second(); n2_second()
    seq_first(); seq_second()
    spider(); alt_chart()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for f in sys.argv[1:]:
            globals()[f]()
    else:
        all_figs()
