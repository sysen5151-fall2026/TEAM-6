"""Portrait version of the sequence diagram (Figure: UC.1 over the first-level functions)."""
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import mdata as M
from idef0 import RED, BLUE, BOXFC, BOXEC
from figs2 import badge, newfig

plt.rcParams["font.family"] = "Arial"
OUT = "../diagrams/"


def sequence_portrait():
    lanes = [("F.1", "Commuter"), ("F.2.1", "Collect Commute Entries"), ("F.2.2", "Manage Reference Data"),
             ("F.2.3", "Estimate Commute Emissions"), ("F.2.4", "Manage Commute Records"),
             ("F.2.5", "Evaluate Feasible Alternatives"), ("F.2.6", "Present Commute Results"),
             ("F.4", "Open-Meteo"), ("F.5", "Emission Factor Publisher")]
    W, H = 7.7, 9.0
    fig, ax = newfig(W, H)
    x0, dx = 1.0, 0.76
    X = {f: x0 + i * dx for i, (f, _) in enumerate(lanes)}
    top = H - 0.2
    bw = 0.7
    for f, n in lanes:
        ext = f in ("F.1", "F.4", "F.5")
        ax.add_patch(FancyBboxPatch((X[f] - bw / 2, top - 0.8), bw, 0.8, boxstyle="round,pad=0,rounding_size=0.04",
                                    fc="#efe6d2" if ext else BOXFC, ec="#8a7a55" if ext else BOXEC, lw=1))
        ax.text(X[f], top - 0.13, f, fontsize=7.4, fontweight="bold", ha="center", va="center", color="#1a2a6c")
        ax.text(X[f], top - 0.46, "\n".join(textwrap.wrap(n, 13)), fontsize=6.2, ha="center", va="center", linespacing=.95)
        ax.plot([X[f], X[f]], [top - 0.8, 0.55], color="#9aa", lw=.8, ls=(0, (4, 3)), zorder=1)
    ax.text(0.08, top - 0.4, "UC.1\naction", fontsize=6.4, color="#555", va="center")
    y = top - 1.25
    dy = (y - 0.85) / (len(M.SEQ) - 1)
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
            ax.annotate("", xy=(v, y), xytext=(v - d * 0.16, y),
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=1.5, mutation_scale=8, shrinkA=0, shrinkB=0), zorder=4)
        cx = (xs + far) / 2
        label = f"{name} ({io})"
        if abs(far - xs) < 1.6:
            label = f"{name}\n({io})"
        ax.text(cx, y + 0.07, label, fontsize=6.4, ha="center", va="bottom", color=col, zorder=6, linespacing=.95,
                bbox=dict(fc="white", ec="none", pad=0.4, alpha=.92))
        bxp = min(xs, far) + 0.16 if abs(far - xs) > 0.5 else xs + (-0.16 if far < xs else 0.16)
        badge(ax, bxp, y, num, col)
        ax.text(0.08, y, uc.replace("precondition", "before UC.1").replace(", ", ",\n"), fontsize=5.8, color="#555", va="center")
        y -= dy
    ax.text(W - 0.1, 0.18, "Red = external interaction (n)   Blue = internal first-level interaction (n.m)   Dashed = precondition",
            fontsize=6, ha="right", color="#333")
    fig.savefig(OUT + "fig_sequence_portrait.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    sequence_portrait()
