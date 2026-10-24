"""Renderer for the first-level IDEF0 (plain and traced) and the Metafunction trace."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle
import textwrap
import mdata as M

plt.rcParams["font.family"] = "Arial"

RED, BLUE, GRAY, BLACK = "#c62828", "#1558b0", "#a9a9a9", "#222222"
BOXFC, BOXEC = "#dce9f7", "#4d78a8"

# ------------------------------------------------------------------ geometry
FW, FH = 11.95, 8.2
X0, DX, W = 1.85, 1.12, 0.80
Y0, DY, HB = 6.75, 0.84, 0.60          # top of box 0, row pitch, box height
TOPY = FH - 0.30                         # control labels


def bx(i):
    return X0 + i * DX


def by(i):
    return Y0 - i * DY                   # top edge


def spread(n, lo, hi):
    if n == 1:
        return [(lo + hi) / 2]
    return [hi - k * (hi - lo) / (n - 1) for k in range(n)]


# External label text (line-broken) and side
EXT_LABEL = {
    "IO.1": "Commuter Entries\nand Requests", "IO.2": "Commuter Consent\nand Settings",
    "IO.3": "Commute Result\nand Advice", "IO.4": "Weather\nRequest",
    "IO.5": "Weather\nForecast Data", "IO.6": "Reviewed Emission\nFactors",
    "IO.7": "Aggregate Summary\nRequest", "IO.8": "Approved Aggregate\nSummary",
    "IO.9": "Pilot Program\nRules", "IO.10": "Release\nConfiguration",
    "IO.11": "Hosting Service\nStatus",
}


class Fig:
    def __init__(self):
        self.fig = plt.figure(figsize=(FW, FH))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, FW)
        self.ax.set_ylim(0, FH)
        self.ax.axis("off")
        self.branch = {}          # (io, dest) -> polyline
        self.labelpos = {}

    # drawing primitives
    def line(self, pts, color=BLACK, lw=1.1, arrow=True, z=2, ls="-"):
        xs, ys = zip(*pts)
        self.ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="butt", zorder=z, ls=ls)
        if arrow:
            (x1, y1), (x2, y2) = pts[-2], pts[-1]
            self.ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                             arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=7,
                                             shrinkA=0, shrinkB=0), zorder=z + 1)

    def label(self, x, y, s, color=BLACK, fs=6.8, ha="center", va="center", rot=0, bg=True, z=6, weight="normal"):
        t = self.ax.text(x, y, s, fontsize=fs, ha=ha, va=va, rotation=rot, color=color, zorder=z,
                         linespacing=0.95, fontweight=weight,
                         bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.92) if bg else None)
        return t

    def badge(self, x, y, s, color):
        r = 0.095 if len(s) < 3 else 0.115
        w = 0.13 + 0.07 * (len(s) - 1)
        self.ax.add_patch(FancyBboxPatch((x - w / 2, y - 0.085), w, 0.17, boxstyle="round,pad=0,rounding_size=0.08",
                                         fc=color, ec="white", lw=0.8, zorder=9))
        self.ax.text(x, y - 0.004, s, fontsize=7.2, color="white", ha="center", va="center", fontweight="bold", zorder=10)

    def box(self, i, idn, name):
        x, yt = bx(i), by(i)
        self.ax.add_patch(FancyBboxPatch((x, yt - HB), W, HB, boxstyle="round,pad=0,rounding_size=0.04",
                                         fc=BOXFC, ec=BOXEC, lw=1.1, zorder=4))
        self.ax.text(x + 0.04, yt - 0.03, idn, fontsize=6.6, color="#1a2a6c", fontweight="bold", va="top", ha="left", zorder=5)
        nm = "\n".join(textwrap.wrap(name, 14))
        self.ax.text(x + W / 2, yt - HB / 2 - 0.06, nm, fontsize=7.0, ha="center", va="center", zorder=5, linespacing=0.95)


def first_level(path, trace=None, title=None):
    """trace: dict io -> dict(color, badges=[(number, branchkey|'ext'|'trunk', frac)])  or None for plain."""
    F = Fig()
    n = len(M.L1)
    idx = {f: i for i, (f, _) in enumerate(M.L1)}
    # boxes
    for i, (f, nm) in enumerate(M.L1):
        F.box(i, f, nm)

    # ---- slot assignment
    ins = {i: [] for i in range(n)}      # left-edge input slots (io, kind)
    ctl = {i: [] for i in range(n)}      # top-edge control slots
    outs = {i: [] for i in range(n)}     # right-edge output slots
    for io, (srcs, dests) in M.L1FLOW.items():
        for d, role in dests:
            if d == "ENV":
                continue
            (ins if role == "I" else ctl)[idx[d]].append(io)
        for s in srcs:
            if s != "ENV":
                outs[idx[s]].append(io)

    def far(io, i):
        return max([idx[d] for d, _ in M.L1FLOW[io][1] if d != "ENV"] or [99])

    # outputs: external first (top), then nearest-first top -> farthest bottom
    out_slot, chan = {}, {}
    for i in range(n):
        lst = sorted(outs[i], key=lambda io: (0 if "ENV" in [d for d, _ in M.L1FLOW[io][1]] else 1, far(io, i)))
        ys = spread(len(lst), by(i) - HB + 0.10, by(i) - 0.14) if len(lst) > 1 else [by(i) - HB / 2 - 0.04]
        internal = [io for io in lst if far(io, i) != 99]
        for io, y in zip(lst, ys):
            out_slot[(io, i)] = y
        # channels: nearest destination -> outermost (right); farthest -> innermost (left)
        k = len(internal)
        for r, io in enumerate(internal):
            chan[(io, i)] = bx(i) + W + 0.10 + (k - 1 - r) * 0.11 if k > 1 else bx(i) + W + 0.16
    in_slot = {}
    for i in range(n):
        lst = sorted(ins[i], key=lambda io: (0 if "ENV" in M.L1FLOW[io][0] else 1, io))
        ys = spread(len(lst), by(i) - HB + 0.10, by(i) - 0.14) if len(lst) > 1 else [by(i) - HB / 2 - 0.04]
        for io, y in zip(lst, ys):
            in_slot[(io, i)] = y
    ctl_slot = {}
    for i in range(n):
        lst = sorted(ctl[i], key=lambda io: (0 if "ENV" not in M.L1FLOW[io][0] else 1, io))
        xs = spread(len(lst), bx(i) + 0.18, bx(i) + W - 0.12) if len(lst) > 1 else [bx(i) + W * 0.62]
        for io, x in zip(lst, xs):
            ctl_slot[(io, i)] = x

    # control routing levels: top margin levels for external controls
    top_level = {"IO.9": Y0 + 0.34, "IO.2": Y0 + 0.62, "IO.6": Y0 + 0.90}
    # bands above destination boxes for internal controls
    band = {}
    for i in range(n):
        for k, io in enumerate(sorted(ctl[i], key=lambda io: io)):
            band[(io, i)] = by(i) + 0.13 + 0.05 * k

    polys = {}

    def color_of(io):
        if trace is None:
            return BLACK
        return trace.get(io, {}).get("color", GRAY)

    def lw_of(io):
        if trace is None:
            return 1.1
        return 1.9 if io in trace else 0.8

    for io, (srcs, dests) in M.L1FLOW.items():
        col, lw = color_of(io), lw_of(io)
        # ---- external inputs
        if "ENV" in srcs:
            for d, role in dests:
                i = idx[d]
                if role == "I":
                    y = in_slot[(io, i)]
                    if io not in polys:
                        pts = [(1.60, y), (bx(i), y)]
                        F.line(pts, col, lw)
                        polys[(io, d)] = pts
                        F.ax.text(1.52, y, EXT_LABEL[io], fontsize=7.0, ha="right", va="center", color=col if trace else BLACK,
                                  linespacing=0.95, zorder=6)
                else:  # external control from the top
                    xs = ctl_slot[(io, i)]
                    lvl = top_level[io]
                    first_i = min(idx[x[0]] for x in dests)
                    x_first = ctl_slot[(io, first_i)]
                    if i == first_i:
                        pts = [(xs, lvl), (xs, by(i))]
                        F.line(pts, col, lw)
                        F.ax.text(xs, lvl + 0.06, EXT_LABEL[io], fontsize=7.0, ha="center", va="bottom",
                                  color=col if trace else BLACK, linespacing=0.95, zorder=6)
                    else:
                        pts = [(x_first, lvl), (xs, lvl), (xs, by(i))]
                        F.line(pts, col, lw)
                        F.ax.plot([x_first], [lvl], marker="o", ms=2.2, color=col, zorder=5)
                    polys[(io, d)] = pts
            continue
        # ---- internal / external outputs
        for s in srcs:
            i = idx[s]
            ys = out_slot[(io, i)]
            xs_ = bx(i) + W
            if any(d == "ENV" for d, _ in dests):
                xe = 10.75
                pts = [(xs_, ys), (xe, ys)]
                F.line(pts, col, lw)
                polys[(io, s)] = pts
                F.ax.text(xe + 0.07, ys, EXT_LABEL[io], fontsize=7.0, ha="left", va="center",
                          color=col if trace else BLACK, linespacing=0.95, zorder=6)
                continue
            xc = chan[(io, i)]
            dl = sorted(dests, key=lambda t: idx[t[0]])
            lowest = min(
                [in_slot[(io, idx[d])] if role == "I" else band[(io, idx[d])] for d, role in dl])
            # trunk
            F.line([(xs_, ys), (xc, ys)], col, lw, arrow=False)
            F.line([(xc, ys), (xc, lowest)], col, lw, arrow=False)
            for d, role in dl:
                j = idx[d]
                if role == "I":
                    y = in_slot[(io, j)]
                    pts = [(xc, y), (bx(j), y)]
                else:
                    yb = band[(io, j)]
                    xt = ctl_slot[(io, j)]
                    pts = [(xc, yb), (xt, yb), (xt, by(j))]
                F.line(pts, col, lw, arrow=True)
                if len(dl) > 1 or True:
                    F.ax.plot([xc], [pts[0][1]], marker="o", ms=2.0, color=col, zorder=5) if len(dl) > 1 else None
                polys[(io, d)] = [(xs_, ys), (xc, ys)] + pts
            polys[(io, "trunk")] = [(xc, ys), (xc, lowest)]
            chan[(io, "x")] = xc

    # ---- tags on internal lines, legend, badges
    def pt_at(poly, frac):
        import math
        segs=[(poly[k],poly[k+1]) for k in range(len(poly)-1)]
        L=[math.dist(p,q) for p,q in segs]; tot=sum(L); t=frac*tot
        for (p,q),l in zip(segs,L):
            if t<=l or (p,q)==segs[-1]:
                r=0 if l==0 else min(t/l,1); return (p[0]+(q[0]-p[0])*r, p[1]+(q[1]-p[1])*r), (q[0]-p[0],q[1]-p[1])
            t-=l
    TAGF = {"IO.12":.30,"IO.13":.40,"IO.15":.40,"IO.16":.35,"IO.18":.25,"IO.19":.62,"IO.20":.25,"IO.22":.50}
    BAND = {"IO.14","IO.17","IO.21"}
    for io in M.INTERNAL:
        srcs, dests = M.L1FLOW[io]
        i = idx[srcs[0]]
        col = (GRAY if (trace is not None and io not in trace) else BLACK) if trace is not None else BLACK
        if io in BAND:
            d = dests[0][0]; poly = polys[(io, d)]
            (x, y), _ = pt_at(poly[2:] if len(poly) > 3 else poly, 0.30)
            F.label(x, y, io, color=col, fs=5.8, rot=0)
        else:
            tr = polys[(io, "trunk")]
            (x, y), _ = pt_at(tr, TAGF[io])
            F.label(x, y, io, color=col, fs=5.8, rot=90)
    if trace is not None:
        for io, spec in trace.items():
            for num, key, frac in spec["badges"]:
                poly = polys[(io, key)]
                (x, y), _ = pt_at(poly, frac)
                F.badge(x, y, num, spec["color"])
    # legend of flow names (lower-left)
    names = sorted(M.IO, key=lambda k: int(k.split(".")[1]))
    yy = 4.55
    F.ax.text(0.25, yy + 0.2, "Input/output key", fontsize=7.2, fontweight="bold", ha="left", va="center")
    for k in names:
        if k in M.INTERNAL or True:
            c = BLACK
            if trace is not None and k not in trace:
                c = GRAY
            F.ax.text(0.25, yy - 0.0, k, fontsize=5.7, ha="left", va="center", color=c, fontweight="bold")
            F.ax.text(0.72, yy - 0.0, M.IO[k], fontsize=5.7, ha="left", va="center", color=c)
            yy -= 0.112
    return F, polys, chan, in_slot, out_slot, ctl_slot, idx


def finish(F, path, legend=None):
    if legend:
        y = 0.35
        x = 1.6
        for txt, col, lw in legend:
            F.ax.plot([x, x + 0.45], [y, y], color=col, lw=lw)
            F.ax.text(x + 0.52, y, txt, fontsize=7.0, va="center", color=BLACK)
            x += 0.52 + 0.075 * len(txt) + 0.35
    F.fig.savefig(path, dpi=220)
    plt.close(F.fig)


if __name__ == "__main__":
    F, *_ = first_level("x")
    finish(F, "../diagrams/_test_first_level.png")
