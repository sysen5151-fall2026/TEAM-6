"""Draw the action diagrams and sequence diagrams of scenarios.py (Innoslate style: one branch per asset).

    python docs/ch10/sim/draw.py

Writes docs/ch10/diagrams/ad_sc<k>_p<j>.png (action diagram, three panels per scenario) and
sq_sc<k>.png (sequence diagram). Both are generated from the same data, so they agree by construction;
check_consistency() asserts it.
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

import scenarios as S

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "diagrams")
os.makedirs(OUT, exist_ok=True)
INT, EXT, EDGE, INK = "#DCE8F5", "#FBE3C8", "#33415C", "#1B1B1B"
PAR = "#8A5A00"


def layers(acts):
    """Longest-path layer of each action (inputs must come from an earlier layer)."""
    prod = {a["output"]: a for a in acts}
    depth = {}

    def d(a):
        if a["key"] in depth:
            return depth[a["key"]]
        v = 0
        for i in a["inputs"]:
            v = max(v, d(prod[i]) + 1)
        depth[a["key"]] = v
        return v

    for a in acts:
        d(a)
    return depth


def edges(acts):
    """(producer, consumer, io name) for every input of every action."""
    prod = {a["output"]: a for a in acts}
    return [(prod[i], a, i) for a in acts for i in a["inputs"]]


def check_consistency(sc):
    acts = S.actions(sc)
    assert len({a["output"] for a in acts}) == len(acts), "each action must generate its own output"
    prod = {a["output"] for a in acts}
    for a in acts:
        for i in a["inputs"]:
            assert i in prod, (a["num"], i)
    for a in acts:
        assert a["asset"] in S.ASSET_NAME


NPANELS = 3
COLW, BW, BH = 1.7, 1.3, 0.74
FS_NUM, FS_NAME, FS_DIST, FS_IO = 7.2, 6.6, 6.2, 6.2


def panel_ranges(nl, n=NPANELS):
    size = -(-nl // n)
    return [(i * size, min(nl, (i + 1) * size)) for i in range(n) if i * size < nl]


def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    return lines


def action_diagram(sc):
    acts = S.actions(sc)
    dep = layers(acts)
    nl = max(dep.values()) + 1
    panels = panel_ranges(nl)
    lanes = [a for a, _, _ in S.ASSETS]
    lane_name = {a: n for a, n, _ in S.ASSETS}
    sub = {}
    for a in acts:
        sub.setdefault((a["asset"], dep[a["key"]]), []).append(a)
    slot = {a["key"]: i for ks in sub.values() for i, a in enumerate(ks)}
    nsub = {ln: max([len(v) for (l, _), v in sub.items() if l == ln] or [1]) for ln in lanes}
    laneh = {ln: max(0.95, nsub[ln] * (BH + 0.1) + 0.2) for ln in lanes}
    ys, ytop = {}, 0.0
    for ln in lanes:
        ys[ln] = ytop
        ytop += laneh[ln]
    H = ytop
    figw = 11.0
    left = 1.9
    for pi, (lo, hi) in enumerate(panels, 1):
        ncol = hi - lo
        xoff = 0.0 if pi == 1 else 1.3
        right = 1.7 if pi < len(panels) else 0.35
        xmax = ncol * COLW + xoff + right
        ips = figw / (left + xmax)                   # inches per data unit (equal in x and y)
        figh = (H + 1.0) * ips + 0.15
        fig, ax = plt.subplots(figsize=(figw, figh))
        ax.set_xlim(-left, xmax)
        ax.set_ylim(H + 0.35, -0.7)
        ax.axis("off")
        cw = lambda fs: fs * 0.62 / 72 / ips          # character width in data units
        lh = lambda fs: fs * 1.28 / 72 / ips          # line height in data units
        ax.text(-left, -0.5, f"{S.SCENARIOS[sc]['id']} {S.SCENARIOS[sc]['title']} - action diagram, part {pi} of {len(panels)} (layers {lo + 1}-{hi} of {nl})",
                fontsize=10, fontweight="bold", color=INK, va="center")
        for ln in lanes:
            kind = next(k for a, _, k in S.ASSETS if a == ln)
            ax.add_patch(Rectangle((-left, ys[ln]), left + xmax, laneh[ln], fc="#FAFAFA" if lanes.index(ln) % 2 == 0 else "white", ec="#B8C0CC", lw=0.6, zorder=0))
            ax.add_patch(Rectangle((-left, ys[ln]), left - 0.12, laneh[ln], fc=EXT if kind == "ext" else INT, ec="#B8C0CC", lw=0.6, zorder=1))
            lab = wrap(lane_name[ln], 16)
            ax.text(-left + (left - 0.12) / 2, ys[ln] + laneh[ln] / 2, ln + "\n" + "\n".join(lab), ha="center", va="center", fontsize=7.4, color=INK, zorder=2, linespacing=1.1)
        pos, rects = {}, []
        for a in acts:
            L = dep[a["key"]]
            if lo <= L < hi:
                x = (L - lo) * COLW + 0.12 + xoff
                y = ys[a["asset"]] + 0.1 + slot[a["key"]] * (BH + 0.1)
                pos[a["key"]] = (x, y)
                rects.append((x, y, x + BW, y + BH))

        def free(r):
            return not any(r[0] < q[2] and r[2] > q[0] and r[1] < q[3] and r[3] > q[1] for q in rects)

        def put(lines, cands, fs, color, zorder=6):
            """Place a small multi-line label at the first candidate (cx, cy[, 'L'|'R']) where it hits no box or earlier label.
            'L': the label ends just left of cx; 'R': it starts just right of cx; otherwise it is centred on cx."""
            w = max(len(l) for l in lines) * cw(fs) + 0.1
            h = len(lines) * lh(fs) + 0.06
            def rect(c):
                cx, cy = c[0], c[1]
                mode = c[2] if len(c) > 2 else "C"
                x0 = cx - w / 2 if mode == "C" else (cx - 0.06 - w if mode == "L" else cx + 0.06)
                return (x0, cy - h / 2, x0 + w, cy + h / 2)
            chosen = next((c for c in cands if free(rect(c))), cands[0])
            r = rect(chosen)
            rects.append(r)
            ax.text((r[0] + r[2]) / 2, chosen[1], "\n".join(lines), fontsize=fs, color=color, ha="center", va="center", zorder=zorder, linespacing=1.1,
                    bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.95))

        # arrows below the boxes, labels afterwards
        done = set()
        in_idx = {}
        in_labeled = set()
        for p, c, io in edges(acts):
            pin, cin = p["key"] in pos, c["key"] in pos
            if not (pin or cin):
                continue
            if pin and cin:
                px, py = pos[p["key"]]
                cx, cy = pos[c["key"]]
                x0, y0, x1, y1 = px + BW, py + BH / 2, cx, cy + BH / 2
                same_adjacent = p["asset"] == c["asset"] and dep[c["key"]] - dep[p["key"]] == 1
                if same_adjacent:
                    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=EDGE, lw=0.8, shrinkA=0, shrinkB=0), zorder=2)
                    if (p["key"], io) not in done:
                        done.add((p["key"], io))
                        put(wrap(io, 8), [((x0 + x1) / 2, y0 - 0.2), ((x0 + x1) / 2, y0 + 0.2)], FS_IO, "#1F3A5F")
                    continue
                k_in = in_idx.get(c["key"], 0)
                in_idx[c["key"]] = k_in + 1
                xm = x1 - 0.1 - 0.17 * k_in
                ax.plot([x0, xm, xm], [y0, y0, y1], color=EDGE, lw=0.8, zorder=2, solid_capstyle="round")
                ax.annotate("", xy=(x1, y1), xytext=(xm, y1), arrowprops=dict(arrowstyle="-|>", color=EDGE, lw=0.8, shrinkA=0, shrinkB=0), zorder=2)
                if (p["key"], io) not in done:
                    done.add((p["key"], io))
                    span = y1 - y0
                    fr = (0.5, 0.35, 0.65, 0.2, 0.8, 0.1, 0.9)
                    cands = [(xm, y0 + span * f) for f in fr] + [(xm, y0 + span * f, "L") for f in fr] + [(xm, y0 + span * f, "R") for f in fr]
                    put(wrap(io, 11), cands, FS_IO, "#1F3A5F")
            elif pin and not cin:
                px, py = pos[p["key"]]
                x0, y0 = px + BW, py + BH / 2
                if (p["key"], io, "out") in done:
                    continue
                done.add((p["key"], io, "out"))
                xe = ncol * COLW + xoff + 0.25
                ax.annotate("", xy=(xe, y0), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=EDGE, lw=0.8, shrinkA=0, shrinkB=0), zorder=2)
                put(wrap(io, 14) + [f"to {c['num']} (part {pi + 1})"], [(xe + 0.1 + 0.5 * (max(len(l) for l in wrap(io, 14) + [f"to {c['num']} (part {pi + 1})"]) * cw(FS_IO) + 0.08), y0)], FS_IO, "#1F3A5F")
            else:
                cx, cy = pos[c["key"]]
                y1 = cy + BH / 2
                if (c["key"], io, "in") in done:
                    continue
                done.add((c["key"], io, "in"))
                ax.annotate("", xy=(cx, y1), xytext=(cx - 0.3, y1), arrowprops=dict(arrowstyle="-|>", color=EDGE, lw=0.8, shrinkA=0, shrinkB=0), zorder=2)
                if (p["key"], io) not in in_labeled:
                    in_labeled.add((p["key"], io))
                    tos = sorted({q["num"] for q2, q, i2 in edges(acts) if q2["key"] == p["key"] and i2 == io and q["key"] in pos})
                    put(wrap(io, 14) + [f"from {p['num']}"] + [], [(cx - 0.8, y1 - 0.3), (cx - 0.8, y1 + 0.3), (cx - 0.8, y1 - 0.5)], FS_IO, PAR)
        for a in acts:
            if a["key"] not in pos:
                continue
            x, y = pos[a["key"]]
            kind = next(k for ln, _, k in S.ASSETS if ln == a["asset"])
            ax.add_patch(FancyBboxPatch((x, y), BW, BH, boxstyle="round,pad=0,rounding_size=0.06", fc=EXT if kind == "ext" else INT, ec=EDGE, lw=0.9, zorder=4))
            lines = wrap(a["name"], 16)
            ax.text(x + BW / 2, y + 0.04 + lh(FS_NUM) / 2, a["num"], ha="center", va="center", fontsize=FS_NUM, fontweight="bold", color=INK, zorder=5)
            ax.text(x + BW / 2, y + 0.06 + lh(FS_NUM) + lh(FS_NAME) * len(lines) / 2, "\n".join(lines), ha="center", va="center", fontsize=FS_NAME, color=INK, zorder=5, linespacing=1.1)
            d = a["dist"]
            ax.text(x + BW / 2, y + BH - lh(FS_DIST) / 2 - 0.03, f"N({d[1]:g}, {d[2]:g})" if d[0] == "normal" else f"Exp(λ={d[1]:g})", ha="center", va="center", fontsize=FS_DIST, color="#4A4A4A", style="italic", zorder=5)
        fig.savefig(os.path.join(OUT, f"ad_sc{sc}_p{pi}.png"), dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)
    return panels, nl


def nominal_schedule(acts):
    """Start/end of each action with mean durations (sets the order of events in the sequence diagram)."""
    prod = {a["output"]: a for a in acts}
    t = {}

    def go(a):
        if a["key"] in t:
            return t[a["key"]]
        s = max([go(prod[i])[1] for i in a["inputs"]] or [0.0])
        m = a["dist"][1] if a["dist"][0] == "normal" else 1 / a["dist"][1]
        t[a["key"]] = (s, s + m)
        return t[a["key"]]

    for a in acts:
        go(a)
    return t


def sequence_diagram(sc):
    acts = S.actions(sc)
    sched = nominal_schedule(acts)
    order = sorted(acts, key=lambda a: (sched[a["key"]][0], a["n"]))
    row = {a["key"]: i for i, a in enumerate(order)}
    lanes = [a for a, _, _ in S.ASSETS]
    xs = {ln: i * 1.18 for i, ln in enumerate(lanes)}
    n = len(order)
    RH = 0.62
    fig, ax = plt.subplots(figsize=(11.0, 0.5 * n * 0.78 + 1.9))
    ax.set_xlim(-0.75, xs[lanes[-1]] + 0.75)
    ax.set_ylim(n * RH + 0.4, -1.15)
    ax.axis("off")
    ax.text(-0.75, -1.02, f"{S.SCENARIOS[sc]['id']} {S.SCENARIOS[sc]['title']} - sequence diagram (event trace, generated from the action diagram)", fontsize=9.5, fontweight="bold", va="center", color=INK)
    for ln in lanes:
        kind = next(k for a, _, k in S.ASSETS if a == ln)
        ax.add_patch(FancyBboxPatch((xs[ln] - 0.5, -0.78), 1.0, 0.62, boxstyle="round,pad=0,rounding_size=0.05", fc=EXT if kind == "ext" else INT, ec=EDGE, lw=0.9))
        ax.text(xs[ln], -0.47, f"{ln}\n{dict((a, nm) for a, nm, _ in S.ASSETS)[ln].replace(' Subsystem', '')}", ha="center", va="center", fontsize=6.3, color=INK, linespacing=0.95)
        ax.plot([xs[ln], xs[ln]], [-0.16, n * RH + 0.2], color="#9AA5B5", lw=0.7, ls=(0, (4, 3)), zorder=0)
    # par frame: actions whose scheduled intervals overlap another action's interval on a different asset inside the processing block
    par_keys = {"reqroute", "reqwx", "factor", "route", "wx", "resolve"} if sc == 2 else set()
    if par_keys:
        r0, r1 = min(row[k] for k in par_keys), max(row[k] for k in par_keys)
        ax.add_patch(Rectangle((-0.7, r0 * RH + 0.02), xs[lanes[-1]] + 1.4, (r1 - r0 + 1) * RH - 0.05, fc="none", ec=PAR, lw=0.9, ls="--", zorder=0))
        ax.text(-0.68, r0 * RH + 0.07, "par", fontsize=7, color=PAR, fontweight="bold", va="top")
    for a in order:
        r = row[a["key"]]
        x = xs[a["asset"]]
        ax.add_patch(Rectangle((x - 0.05, r * RH + 0.07), 0.1, RH - 0.17, fc="#FFFFFF", ec=EDGE, lw=0.9, zorder=3))
        ax.text(x + 0.09, r * RH + RH / 2 - 0.02, f"{a['num']} {a['name']}", fontsize=5.7, va="center", ha="left", color=INK, zorder=4, bbox=dict(fc="white", ec="none", pad=0.3, alpha=0.85))
    # messages: producer lifeline -> consumer lifeline, drawn just above the consumer's row
    seen = {}
    for p, c, io in edges(acts):
        if p["asset"] == c["asset"]:
            continue
        rc = row[c["key"]]
        k = seen.get(c["key"], 0)
        seen[c["key"]] = k + 1
        y = rc * RH + 0.05 - k * 0.15
        x0, x1 = xs[p["asset"]], xs[c["asset"]]
        ax.annotate("", xy=(x1 + (-0.05 if x1 > x0 else 0.05), y), xytext=(x0 + (0.05 if x1 > x0 else -0.05), y), arrowprops=dict(arrowstyle="-|>", color="#1F3A5F", lw=0.7, shrinkA=0, shrinkB=0), zorder=2)
        ax.text(x0 + (x1 - x0) * (0.5 if k == 0 else 0.5 + 0.22 * (1 if x1 > x0 else -1) * (1 if k % 2 else -1)), y - 0.015, io, fontsize=5.0, color="#1F3A5F", ha="center", va="bottom", zorder=5, bbox=dict(fc="white", ec="none", pad=0.2, alpha=0.9))
    fig.savefig(os.path.join(OUT, f"sq_sc{sc}.png"), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return order, [(p, c, io) for p, c, io in edges(acts) if p["asset"] != c["asset"]]


if __name__ == "__main__":
    for sc in (1, 2):
        check_consistency(sc)
        action_diagram(sc)
        order, msgs = sequence_diagram(sc)
        print(f"SC.{sc}: {len(S.actions(sc))} actions, {len(msgs)} cross-asset messages, layers {max(layers(S.actions(sc)).values()) + 1}")
