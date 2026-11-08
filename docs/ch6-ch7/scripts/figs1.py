"""First-level IDEF0 (plain + traced) and Metafunction trace."""
import idef0 as D
from idef0 import RED, BLUE, GRAY, BLACK, BOXFC, BOXEC, Fig
import mdata as M
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

OUT = "../diagrams/"

TRACE = {
    "IO.6": dict(color=RED, badges=[("1", "F.2.2", .55)]),
    "IO.1": dict(color=RED, badges=[("2", "F.2.1", .30), ("4", "F.2.1", .62)]),
    "IO.2": dict(color=RED, badges=[("4", "F.2.1", .55)]),
    "IO.3": dict(color=RED, badges=[("3", "F.2.1", .93), ("7", "F.2.6", .93)]),
    "IO.4": dict(color=RED, badges=[("5", "F.2.2", .93)]),
    "IO.5": dict(color=RED, badges=[("6", "F.2.2", .55)]),
    "IO.12": dict(color=BLUE, badges=[("4.1", "trunk", .45)]),
    "IO.14": dict(color=BLUE, badges=[("4.2", "F.2.3", .88)]),
    "IO.15": dict(color=BLUE, badges=[("6.1", "trunk", .72)]),
    "IO.16": dict(color=BLUE, badges=[("6.2", "trunk", .72)]),
    "IO.17": dict(color=BLUE, badges=[("6.3", "F.2.6", .85)]),
    "IO.18": dict(color=BLUE, badges=[("6.4", "trunk", .70)]),
    "IO.20": dict(color=BLUE, badges=[("6.5", "trunk", .72)]),
}


def legend_trace(F):
    y = 1.50
    F.ax.text(0.25, y + 0.2, "Trace legend", fontsize=7.2, fontweight="bold", va="center")
    for col, lw, txt in [(RED, 1.9, "Carried down from Metafunction (n)"),
                         (BLUE, 1.9, "Internal first-level flow (n.m)"),
                         (GRAY, 0.8, "Not used by UC.1 (idle)")]:
        F.ax.plot([0.25, 0.65], [y, y], color=col, lw=lw)
        F.ax.text(0.72, y, txt, fontsize=6.2, va="center")
        y -= 0.15


def plain():
    F, *_ = D.first_level(None)
    D.finish(F, OUT + "fig_first_level_idef0.png")


def traced():
    F, *_ = D.first_level(None, trace=TRACE)
    legend_trace(F)
    D.finish(F, OUT + "fig_first_level_trace.png")


# ---------------------------------------------------------------- Metafunction trace
def meta_trace():
    FW, FH = 11.0, 7.0
    F = Fig.__new__(Fig)
    F.fig = plt.figure(figsize=(FW, FH))
    F.ax = F.fig.add_axes([0, 0, 1, 1]); F.ax.set_xlim(0, FW); F.ax.set_ylim(0, FH); F.ax.axis("off")
    pos = {"F.1": (0.3, 3.0, 2.0, 1.1), "F.2": (4.2, 2.95, 3.2, 1.2), "F.3": (8.9, 3.0, 1.9, 1.1),
           "F.5": (5.0, 5.7, 1.6, 0.9), "F.4": (3.2, 0.55, 2.0, 0.95), "F.6": (6.0, 0.55, 2.0, 0.95)}
    for f, (x, y, w, h) in pos.items():
        F.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05", fc=BOXFC, ec=BOXEC, lw=1.2, zorder=4))
        F.ax.text(x + 0.06, y + h - 0.05, f, fontsize=8, fontweight="bold", color="#1a2a6c", va="top", zorder=5)
        import textwrap
        F.ax.text(x + w / 2, y + h / 2 - 0.04, "\n".join(textwrap.wrap(M.TOP[f], 20)), fontsize=8.3, ha="center", va="center", zorder=5)
        if f == "F.2":
            F.ax.text(x + w / 2, y + 0.1, "Mechanism: " + M.MECH[f], fontsize=6.4, ha="center", va="bottom", color="#444")
        else:
            F.ax.text(x + w / 2, y - 0.14, "Mechanism: " + M.MECH[f], fontsize=6.4, ha="center", va="top", color="#444")
    used = {"IO.1": RED, "IO.2": RED, "IO.3": RED, "IO.4": RED, "IO.5": RED, "IO.6": RED}
    badges = {"IO.1": ["2", "4"], "IO.2": ["4"], "IO.3": ["3", "7"], "IO.4": ["5"], "IO.5": ["6"], "IO.6": ["1"]}
    ctl = {"IO.2", "IO.6", "IO.9"}
    # (io, p1, p2) straight lines p1->p2
    lines = {
        "IO.1": ((2.3, 3.85), (4.2, 3.85)), "IO.2": ((2.3, 3.55), (4.2, 3.55)), "IO.3": ((4.2, 3.25), (2.3, 3.25)),
        "IO.7": ((8.9, 3.85), (7.4, 3.85)), "IO.9": ((8.9, 3.55), (7.4, 3.55)), "IO.8": ((7.4, 3.25), (8.9, 3.25)),
        "IO.6": ((5.8, 5.7), (5.8, 4.15)),
        "IO.4": ((3.9, 2.95), (3.9, 1.5)), "IO.5": ((4.7, 1.5), (4.7, 2.95)),
        "IO.10": ((6.5, 2.95), (6.5, 1.5)), "IO.11": ((7.1, 1.5), (7.1, 2.95)),
    }
    for io, (p, q) in lines.items():
        col = used.get(io, GRAY)
        lw = 1.9 if io in used else 0.9
        F.line([p, q], col, lw)
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        lab = f"{io} {M.IO[io]}" + (" (control)" if io in ctl else "")
        if p[0] == q[0] and io in ("IO.4","IO.5","IO.10","IO.11"):
            import textwrap as _t
            lab = io + chr(10) + chr(10).join(_t.wrap(M.IO[io], 13))
        if p[1] == q[1]:
            F.ax.text(mx, my + 0.07, lab, fontsize=6.4, ha="center", va="bottom", color=col if io in used else GRAY)
        else:
            F.ax.text(mx - 0.07 if io in ("IO.4", "IO.10") else mx + 0.07, my, lab, fontsize=6.4,
                      ha="right" if io in ("IO.4", "IO.10") else "left", va="center", rotation=0, color=col if io in used else GRAY)
        for k, num in enumerate(badges.get(io, [])):
            t = 0.28 + 0.4 * k if len(badges[io]) > 1 else 0.5
            if p[1] == q[1]:
                bx_, by_ = p[0] + (q[0] - p[0]) * (0.18 + 0.64 * t if False else (0.25 + 0.5 * k if len(badges[io]) > 1 else 0.5)), my - 0.0
                by_ = my - 0.0
            else:
                bx_, by_ = mx, my
            F.badge(bx_, by_, num, RED)
    # shift: put second badge for IO.1/IO.3 clear of the label
    F.ax.text(0.3, 6.6, "Metafunction F.0, laid out as a hub for tracing (same functions, flows and directions as Figure 2)", fontsize=7.2, color="#333")
    y = 0.28
    for col, lw, txt in [(RED, 1.9, "Flow used by UC.1 (numbered as in the sequence diagram)"), (GRAY, 0.9, "Flow not used by UC.1")]:
        F.ax.plot([7.9, 8.3], [y, y], color=col, lw=lw); F.ax.text(8.4, y, txt, fontsize=6.4, va="center"); y += 0.18
    F.fig.savefig(OUT + "fig_metafunction_trace.png", dpi=220)
    plt.close(F.fig)


if __name__ == "__main__":
    plain(); traced(); meta_trace()
