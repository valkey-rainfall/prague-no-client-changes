#!/usr/bin/env python3
"""Figs 1 and 2: schematic topology of the ZSET skiplist and the fbtree B+tree,
drawn as a matched pair -- same canvas, same node height, same three-color
split as fig 3 (orange pointers / slate other overhead / blue user data).

Every node box is the real struct laid out by the compiler through fieldday
(bare mode, fdbars.py) and colored by role -- alignment padding folded into
"other overhead", since byte accounting is fig 3's job; this script places the boxes and
draws the links. Deliberately NOT to scale between figures and NOT at real
fanout: 8 members and 3 lanes for the skiplist, fanout 4 for the tree
(captioned "61 in practice"). Fig 3 is the honest one; these exist to make
the shapes legible. Captions carry the caveats (schematic, fanout drawn at
4, p = 1/4, up to 32 lanes); the figures themselves keep title + labels + legend.

Usage: topology_figures.py <outdir>
"""
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent / "lib"))   # fdbars; fieldday comes from pip (requirements.txt)
from fdbars import (Bar, fd_defs, FONT, C_LINE, C_MUTED, C_TEXT, theme,

                    zskiplist_node, zsl_roles, fbtree_item, ITEM_ROLES,
                    fbtree_leaf, LEAF_ROLES, fbtree_inner, INNER_ROLES)
import os
TALK = os.environ.get("TALK") == "1"   # talk mode: no titles/explainer prose (slide carries them)

C_PTR, C_OTHER, C_PAY = theme("role-pointer"), theme("role-overhead"), theme("role-data")
W = 720
NODE_H = 34

class Canvas:
    def __init__(self): self.out = []
    def rect(self, x, y, w, h, fill, stroke=None, dash=None, sw=1, rx=0):
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ' stroke="none"'
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{s}{d} rx="{rx}"/>')
    def text(self, x, y, s, size=11, weight=400, anchor="start", fill=C_TEXT):
        self.out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
                        f'text-anchor="{anchor}" fill="{fill}">{s}</text>')
    def _head(self, tx, ty, dx, dy, opacity):
        """Explicit arrowhead with tip (tx, ty) pointing along (dx, dy). Hand-drawn
        rather than marker orient=auto / auto-start-reverse: librsvg 2.40
        (ImageMagick's SVG path) mis-orients markers on curves and on
        right-to-left lines, drawing leftward heads pointing right."""
        import math
        n = math.hypot(dx, dy) or 1.0
        ux, uy = dx / n, dy / n
        nx, ny = -uy, ux
        hl, hw = 6.0, 3.0                                  # matches the old 6 px marker
        bx, by = tx - hl * ux, ty - hl * uy
        pts = f"{tx:.1f},{ty:.1f} {bx + hw*nx:.1f},{by + hw*ny:.1f} {bx - hw*nx:.1f},{by - hw*ny:.1f}"
        self.out.append(f'<polygon points="{pts}" fill="{C_LINE}" opacity="{opacity}"/>')
    def line(self, x1, y1, x2, y2, sw=1, opacity=1, dash=None, arrow=False):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{C_LINE}" '
                        f'stroke-width="{sw}" opacity="{opacity}"{d}/>')
        if arrow:
            self._head(x2, y2, x2 - x1, y2 - y1, opacity)
    def arc(self, x1, x2, y, peak, sw=1, opacity=0.8, arrow=True):
        """Quadratic hop from x1 to x2 (either direction); head on the analytic end
        tangent, which for Q(P0, M, P2) is P2 - M = ((x2-x1)/2, +peak) in SVG's
        y-down frame."""
        self.out.append(f'<path d="M {x1:.1f} {y:.1f} Q {(x1+x2)/2:.1f} {y-peak:.1f} {x2:.1f} {y:.1f}" fill="none" '
                        f'stroke="{C_LINE}" stroke-width="{sw}" opacity="{opacity}"/>')
        if arrow:
            self._head(x2, y, (x2 - x1) / 2, peak, opacity)
    def node(self, bar, x, y, label=None):
        """A fieldday bar with the schematic's outline (white hairline + ink)."""
        self.out.append(bar.at(x, y))
        self.rect(x, y, bar.width, bar.height, "none", stroke="#ffffff", sw=1)
        self.rect(x, y, bar.width, bar.height, "none", stroke=C_LINE, sw=0.6)
        if label:
            self.text(x + bar.width / 2, y + bar.height / 2 + 4, label, 10, 600, "middle", "#ffffff")
        return bar.width
    def svg(self, h):
        defs = ''                                    # arrowheads are explicit polygons (see _head)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}">'
                f'<rect width="100%" height="100%" fill="#ffffff"/>{defs}{fd_defs(padding_as_overhead=True)}' + "\n".join(self.out) + "</svg>")

def legend(c, x, y):
    lx = x
    for col, label in ((C_PTR, "pointers"), (C_OTHER, "other overhead"), (C_PAY, "user data")):
        c.rect(lx, y - 9, 10, 10, col); c.text(lx + 14, y, label, 10, fill=C_MUTED); lx += 14 + len(label) * 6 + 16

# ------------------------------------------------------------------ fig 1: skiplist
def fig1():
    c = Canvas()
    if not TALK:
        c.text(24, 26, "skiplist: one heap node per member, lanes built from pointers inside the nodes", 13, 700)

    levels = [1, 2, 1, 3, 1, 1, 2, 1]
    LANE = 18
    top = 104                                  # lane-1 baseline / node top
    def lane_y(L): return top - LANE * (L - 1)
    K = 0.78                                   # px per byte within this schematic
    bars = {L: Bar(zskiplist_node(L), "zskiplistNode", zsl_roles(L), K, NODE_H, byte_sized=True) for L in set(levels)}
    xs = []; x = 128
    for L in levels:
        xs.append(x); x += bars[L].width + 16
    centers = [xx + bars[L].width / 2 for xx, L in zip(xs, levels)]

    # head sentinel: member of every lane
    hx, hw = 70, 22
    c.rect(hx, top, hw, NODE_H, "none", stroke=C_LINE, dash="3 2", sw=0.8)
    c.text(hx + hw / 2, top + NODE_H + 12, "head", 9, anchor="middle", fill=C_MUTED)
    hc = hx + hw / 2
    c.line(hc, top, hc, lane_y(3) - 10, sw=1.2, dash="3 2", opacity=0.8)
    c.text(hc, lane_y(3) - 14, "…32", 8, anchor="middle", fill=C_MUTED)

    # towers
    for i, L in enumerate(levels):
        if L >= 2: c.line(centers[i], top, centers[i], lane_y(L), sw=1.4, opacity=0.85)
    # lanes: hops from head through members, arrowed
    for L in (1, 2, 3):
        pts = [hc] + [centers[i] for i, l in enumerate(levels) if l >= L]
        ly = lane_y(L)
        for x1, x2 in zip(pts, pts[1:]): c.arc(x1, x2, ly, 7 if L == 1 else 9, sw=1, opacity=0.8)
        c.text(hx - 6, ly + 3, f"lane {L}", 9, anchor="end", fill=C_MUTED)
    # nodes
    for L, xx in zip(levels, xs):
        c.node(bars[L], xx, top)
    # tail + the backward pointers (every node points at its predecessor; the
    # first node's backward is NULL, so there is no arc into the head)
    c.text(xs[-1] + bars[levels[-1]].width + 8, top + NODE_H / 2 + 4, "tail", 9, fill=C_MUTED)
    by = top + NODE_H + 8
    for a, b in zip(centers[1:], centers[:-1]):
        c.arc(a, b, by, -7, sw=1, opacity=0.8)                        # below the row, pointing left
    c.text((centers[4] + centers[5]) / 2, by + 20, "backward", 8, anchor="middle", fill=C_MUTED)

    # no per-member callouts: fig 4 shows the node layout exactly, legibly
    cy = top + NODE_H + 40
    legend(c, 24, cy)
    return c.svg(cy + 14)

# ------------------------------------------------------------------ fig 2: fbtree
def fig2():
    c = Canvas()
    if not TALK:
        c.text(24, 26, "fbtree: members packed in leaf arrays, routing data in the inner node", 13, 700)

    F = 4                                      # drawn fanout
    # inner node in REAL field order (struct-of-arrays, fbtree_internal.h),
    # reduced to fanout 4 with the prefix block and feature rows shortened;
    # the order, and which bytes are pointers, come from the compiler.
    S = 2.2                                    # px per byte for the inner node (wider so segment labels fit)
    inner = Bar(fbtree_inner(F, prefix_len=22, feature_row=F), "innerNode", INNER_ROLES, S, NODE_H)
    ix = (W - inner.width) / 2; iy = 58
    c.node(inner, ix, iy)
    c.text(ix - 8, iy + NODE_H / 2 + 4, "root", 9, anchor="end", fill=C_MUTED)
    # member labels above the node (so they never cross the child edges)
    for member, label in (("embedded_prefix", "prefix"), ("features", "features"), ("anchors", "anchors"),
                          ("children", "children"), ("child_sizes", "sizes")):
        off, size = inner.fields[member]
        c.text(ix + (off + size / 2) * S, iy - 6, label, 8, anchor="middle", fill=C_MUTED)
    slot_c = [ix + inner.slot_x("children", k, 8) for k in range(F)]

    # leaves at fanout 4: header | prev | next | values[4]
    leaf = Bar(fbtree_leaf(F), "leafNode", LEAF_ROLES, 1.0, NODE_H)
    ly = iy + NODE_H + 60
    leaf_gap = 104
    total = F * leaf.width + (F - 1) * leaf_gap
    lx0 = (W - total) / 2
    leaf_x = [lx0 + k * (leaf.width + leaf_gap) for k in range(F)]
    for k in range(F):
        c.line(slot_c[k], iy + NODE_H, leaf_x[k] + leaf.width / 2, ly, sw=1, opacity=0.8, arrow=True)
        c.node(leaf, leaf_x[k], ly, label="leaf" if k == 0 else None)
    # prev/next links between leaves
    for k in range(F - 1):
        x1 = leaf_x[k] + leaf.width; x2 = leaf_x[k + 1]
        c.line(x1 + 2, ly + NODE_H * 0.35, x2 - 2, ly + NODE_H * 0.35, sw=0.9, opacity=0.8, arrow=True)
        c.line(x2 - 2, ly + NODE_H * 0.65, x1 + 2, ly + NODE_H * 0.65, sw=0.9, opacity=0.8, arrow=True)
    c.text(leaf_x[-1] + leaf.width + 8, ly + NODE_H / 2 + 4, "next / prev", 9, fill=C_MUTED)

    # items under each leaf: one sds holding [score][member]
    item = Bar(fbtree_item(), "fbtreeItem", ITEM_ROLES, 1.0, NODE_H - 8)
    item_gap = 4
    ty = ly + NODE_H + 44
    for k in range(F):
        row_w = F * item.width + (F - 1) * item_gap
        x0 = leaf_x[k] + leaf.width / 2 - row_w / 2
        for j in range(F):
            sx = leaf_x[k] + leaf.slot_x("values", j, 8)
            tx = x0 + j * (item.width + item_gap)
            c.line(sx, ly + NODE_H, tx + item.width / 2, ty, sw=0.6, opacity=0.5)
            c.node(item, tx, ty)
    legend(c, 24, ty + NODE_H + 24)
    return c.svg(ty + NODE_H + 38)

if __name__ == "__main__":
    outdir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    (outdir / "fig1-skiplist-topology.svg").write_text(fig1())
    (outdir / "fig2-fbtree-topology.svg").write_text(fig2())
    print("wrote fig1-skiplist-topology.svg fig2-fbtree-topology.svg", file=sys.stderr)
