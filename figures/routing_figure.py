#!/usr/bin/env python3
"""Fig 7 (prototype): one lookup, skiplist vs fbtree -- a pointer chase versus
one node per level with the child picked by a feature-row compare.

Same grammar as figs 1-2 (same bars, same Canvas, same three roles); the new
ingredient is a single highlighted search path with everything off the path
dimmed, plus a callout that zooms into the inner node's `features` rows at the
REAL fanout and shows the candidate set narrowing row by row -- computed by a
port of fbtree.c's featureSearchSIMD_scalar narrowing on generated keys, not
drawn by hand. Pass 2 (sdscmp on anchors) is shown confined to the survivors.

Top panel : fig 1's 8-member skiplist; lookup of member g. Every hop reads a
            different heap node.
Bottom    : fig 2's fanout-4 tree; root -> one child -> leaf -> binary search
            over the leaf's item pointers. Zoom: features[4][61].

Usage: routing_figure.py <outdir>     (writes fig7a-lookup-paths.svg, fig7b-feature-routing.svg)
"""
import random, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "lib"))   # fdbars; fieldday comes from pip (requirements.txt)

from fdbars import (Bar, zskiplist_node, zsl_roles, fbtree_item, ITEM_ROLES,
                    fbtree_leaf, LEAF_ROLES, fbtree_inner, INNER_ROLES, C_MUTED, C_TEXT, C_LINE)
from topology_figures import Canvas, legend, W, NODE_H

ACCENT = "#c2185b"          # the search path / target; unused by the role palette
DIM = 0.28                  # opacity of everything the lookup does not touch
FANOUT = 61                 # real fanout for the features zoom
FEATURE_ROWS = 4


# ------------------------------------------------------------ small helpers
def dim(c):
    c.out.append(f'<g opacity="{DIM}">')
def undim(c):
    c.out.append('</g>')

def touch(c, x, y, n):
    """Numbered 'memory touch' marker: one per heap allocation read."""
    c.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{ACCENT}" stroke="#ffffff" stroke-width="1.2"/>')
    c.text(x, y + 3.4, str(n), 8.5, 700, "middle", "#ffffff")

def hi_arc(c, x1, x2, y, peak, sw=2.0):
    c.out.append(f'<path d="M {x1:.1f} {y:.1f} Q {(x1+x2)/2:.1f} {y-peak:.1f} {x2:.1f} {y:.1f}" fill="none" '
                 f'stroke="{ACCENT}" stroke-width="{sw}" marker-end="url(#hiarrow)"/>')

def hi_line(c, x1, y1, x2, y2, sw=2.0, arrow=True, dash=None):
    m = ' marker-end="url(#hiarrow)"' if arrow else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    c.out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{ACCENT}" '
                 f'stroke-width="{sw}"{d}{m}/>')

def outline(c, x, y, w, h):
    c.rect(x - 1.5, y - 1.5, w + 3, h + 3, "none", stroke=ACCENT, sw=1.6)

HI_DEFS = ('<defs><marker id="hiarrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
           f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{ACCENT}"/></marker></defs>')


# ------------------------------------------------------------ feature search model
def feature_narrowing(anchors, target, rows=FEATURE_ROWS):
    """Port of featureSearchSIMD_scalar's mask narrowing. anchors: sorted
    prefix-stripped high keys (anchors[i] is the LARGEST key in child i), target
    likewise. After each row, returns the children the lookup could still land
    in: the keys still byte-equal so far, plus the first key already known to
    be greater (findChildIndex returns the first anchor >= target). Also
    returns the final [left, right) equal range -- empty in the common case,
    which means no anchor string is compared at all."""
    n = len(anchors)
    def fb(s, j): return s[j] if j < len(s) else 0
    ge = set(range(n)); le = set(range(n))
    states = []
    for row in range(rows):
        t = fb(target, row)
        undecided = ge & le
        for i in list(undecided):
            k = fb(anchors[i], row)
            if t < k: ge.discard(i)
            elif t > k: le.discard(i)
        undecided = ge & le
        greater = le - ge
        possible = set(undecided)
        if greater: possible.add(min(greater))
        states.append(sorted(possible))
    left = min(le) if le else n
    lonly = le - ge
    right = min(lonly) if lonly else n
    return states, left, right

PREFIX = b"i love val"
LOOKUP = b"i love valkey!"

def demo_keys(seed=7):
    """61 sorted anchors (high keys of the children) that all share the prefix
    "i love val", so the node's embedded prefix is "i love val" and the feature
    rows start at byte 10. Contrived only in the letter mix: 13 anchors continue
    with 'k', 4 of those with "ke", 2 with "key" -- and none with "key!", so the
    lookup "i love valkey!" matches no anchor in all four bytes. That is the
    common case: the child is fixed by the feature rows alone and no anchor
    string is compared."""
    rng = random.Random(seed)
    # 13 'k' anchors, 4 of them "ke", 2 of them "key", none "key!"
    fixed = [b"kyrie", b"kyries", b"kayak", b"kiwi", b"kilo", b"kelp", b"keel", b"keys", b"keystone",
             b"kind", b"knot", b"koala", b"kraken",
             b"halla", b"ley", b"or", b"ue", b"entine", b"iant", b"ise", b"id", b"idation", b"ence", b"ve"]
    keys = set(fixed)
    while len(keys) < FANOUT:
        first = rng.choice(b"abcdeghilmnoprstu")
        body = bytes([first]) + bytes(rng.choice(b"aeiou" if j % 2 == 0 else b"bcdlmnprst") for j in range(rng.choice((3, 4, 5))))
        keys.add(body)
    keys = sorted(keys)
    return keys, LOOKUP[len(PREFIX):]

# ------------------------------------------------------------ panel A: skiplist
def panel_skiplist(c, y0):
    c.text(24, y0, "skiplist lookup: a pointer chase — every hop reads a different heap node", 13, 700)
    levels = [1, 2, 1, 3, 1, 1, 2, 1]
    LANE = 18
    top = y0 + 78
    def lane_y(L): return top - LANE * (L - 1)
    K = 0.78
    bars = {L: Bar(zskiplist_node(L), "zskiplistNode", zsl_roles(L), K, NODE_H) for L in set(levels)}
    xs = []; x = 128
    for L in levels:
        xs.append(x); x += bars[L].width + 16
    centers = [xx + bars[L].width / 2 for xx, L in zip(xs, levels)]
    hx, hw = 70, 22; hc = hx + hw / 2

    # --- the search: target is member index 6. Hops (lane, from, to):
    #   L3: head -> n3 (n3 < target, advance); next is tail -> drop
    #   L2: n3 -> n6 (n6 >= target: compared, not taken) -> drop
    #   L1: n3 -> n4 -> n5 -> n6 (found)
    TARGET = 6
    visited_order = [3, 6, 4, 5]                    # distinct heap nodes read, in order
    taken = [(3, hc, centers[3]), (1, centers[3], centers[4]), (1, centers[4], centers[5]), (1, centers[5], centers[6])]
    peeked = [(2, centers[3], centers[6])]
    drops = [(centers[3], 3, 1)]

    # everything not on the path, dimmed
    dim(c)
    c.rect(hx, top, hw, NODE_H, "none", stroke=C_LINE, dash="3 2", sw=0.8)
    c.line(hc, top, hc, lane_y(3) - 10, sw=1.2, dash="3 2", opacity=0.8)
    c.text(hc, lane_y(3) - 14, "…32", 8, anchor="middle", fill=C_MUTED)
    for i, L in enumerate(levels):
        if L >= 2: c.line(centers[i], top, centers[i], lane_y(L), sw=1.4, opacity=0.85)
    for L in (1, 2, 3):
        pts = [hc] + [centers[i] for i, l in enumerate(levels) if l >= L]
        for x1, x2 in zip(pts, pts[1:]): c.arc(x1, x2, lane_y(L), 7 if L == 1 else 9, sw=1, opacity=0.8)
    for i, (L, xx) in enumerate(zip(levels, xs)):
        if i not in visited_order: c.node(bars[L], xx, top)
    c.text(xs[-1] + bars[levels[-1]].width + 8, top + NODE_H / 2 + 4, "tail", 9, fill=C_MUTED)
    undim(c)
    c.text(hx + hw / 2, top + NODE_H + 12, "head", 9, anchor="middle", fill=C_MUTED)
    for L in (1, 2, 3): c.text(hx - 6, lane_y(L) + 3, f"lane {L}", 9, anchor="end", fill=C_MUTED)

    # visited nodes, full strength, outlined
    for i in visited_order:
        c.node(bars[levels[i]], xs[i], top)
        outline(c, xs[i], top, bars[levels[i]].width, NODE_H)
    # the path
    for L, x1, x2 in taken: hi_arc(c, x1, x2, lane_y(L), 9 if L > 1 else 7)
    for L, x1, x2 in peeked:
        hi_line(c, x1, lane_y(L), x2 - 4, lane_y(L), sw=1.4, dash="3 2")
    for xx, Lfrom, Lto in drops: hi_line(c, xx, lane_y(Lfrom), xx, lane_y(Lto) - 2, sw=1.6, arrow=False)
    c.text(centers[TARGET], top + NODE_H + 12, "target", 9, 600, "middle", ACCENT)
    c.text(24, top + NODE_H + 28, "each hop: load a node, compare, follow its pointer", 9, fill=C_MUTED)
    return top + NODE_H + 34


# ------------------------------------------------------------ panel B: fbtree
def panel_fbtree(c, y0):
    c.text(24, y0, "fbtree lookup: one node per level, child picked by comparing feature bytes", 13, 700)
    F = 4; S = 2.2
    inner = Bar(fbtree_inner(F, prefix_len=22, feature_row=F), "innerNode", INNER_ROLES, S, NODE_H)
    ix = (W - inner.width) / 2; iy = y0 + 32
    leaf = Bar(fbtree_leaf(F), "leafNode", LEAF_ROLES, 1.0, NODE_H)
    ly = iy + NODE_H + 60
    leaf_gap = 104
    total = F * leaf.width + (F - 1) * leaf_gap
    lx0 = (W - total) / 2
    leaf_x = [lx0 + k * (leaf.width + leaf_gap) for k in range(F)]
    slot_c = [ix + inner.slot_x("children", k, 8) for k in range(F)]
    item = Bar(fbtree_item(), "fbtreeItem", ITEM_ROLES, 1.0, NODE_H - 8)
    item_gap = 4
    ty = ly + NODE_H + 44
    CHILD = 2                     # the child the lookup descends into
    PROBES = [2, 3]               # leaf binary search over 4 slots: mid=2, then mid=3
    FOUND = 3

    def items_x(k):
        row_w = F * item.width + (F - 1) * item_gap
        x0 = leaf_x[k] + leaf.width / 2 - row_w / 2
        return [x0 + j * (item.width + item_gap) for j in range(F)]

    # dimmed: node itself drawn at full strength, but non-path children/leaves/items faded
    c.node(inner, ix, iy)
    c.text(ix - 8, iy + NODE_H / 2 + 4, "root", 9, anchor="end", fill=C_MUTED)
    for member, label in (("embedded_prefix", "prefix"), ("features", "features"), ("anchors", "anchors"),
                          ("children", "children"), ("child_sizes", "sizes")):
        off, size = inner.fields[member]
        c.text(ix + (off + size / 2) * S, iy - 6, label, 8, anchor="middle", fill=C_MUTED)
    dim(c)
    for k in range(F):
        if k == CHILD: continue
        c.line(slot_c[k], iy + NODE_H, leaf_x[k] + leaf.width / 2, ly, sw=1, opacity=0.8, arrow=True)
        c.node(leaf, leaf_x[k], ly)
    for k in range(F - 1):
        x1 = leaf_x[k] + leaf.width; x2 = leaf_x[k + 1]
        c.line(x1 + 2, ly + NODE_H * 0.35, x2 - 2, ly + NODE_H * 0.35, sw=0.9, opacity=0.8, arrow=True)
        c.line(x2 - 2, ly + NODE_H * 0.65, x1 + 2, ly + NODE_H * 0.65, sw=0.9, opacity=0.8, arrow=True)
    txs = items_x(CHILD)
    for j in range(F):
        if j in PROBES: continue
        c.line(leaf_x[CHILD] + leaf.slot_x("values", j, 8), ly + NODE_H, txs[j] + item.width / 2, ty, sw=0.6, opacity=0.5)
        c.node(item, txs[j], ty)
    undim(c)

    # the path: features segment -> children[CHILD] -> leaf -> probes -> item
    fx0 = ix + inner.x_of("features"); fw = inner.bytes_of("features") * S
    outline(c, fx0, iy, fw, NODE_H)
    hi_line(c, slot_c[CHILD], iy + NODE_H, leaf_x[CHILD] + leaf.width / 2, ly)
    c.node(leaf, leaf_x[CHILD], ly, label="leaf")
    outline(c, leaf_x[CHILD], ly, leaf.width, NODE_H)
    for j in PROBES:
        sx = leaf_x[CHILD] + leaf.slot_x("values", j, 8)
        hi_line(c, sx, ly + NODE_H, txs[j] + item.width / 2, ty, sw=1.4)
        c.node(item, txs[j], ty)
        outline(c, txs[j], ty, item.width, NODE_H - 8)
    c.text(txs[FOUND] + item.width / 2, ty + NODE_H - 8 + 12, "target", 9, 600, "middle", ACCENT)
    c.text(24, ty + NODE_H - 8 + 12, "one node per level; the child is chosen inside the node", 9, fill=C_MUTED)
    return ty + NODE_H + 22, (fx0, fx0 + fw, iy + NODE_H)


# ------------------------------------------------------------ zoom: the features rows
def panel_features(c, y0, callout_from):
    keys, target = demo_keys()
    states, left, right = feature_narrowing(keys, target)
    assert right == left, "figure wants the no-exact-match case"
    assert states[-1] == [left], (states[-1], left)
    lookup = LOOKUP.decode(); prefix = PREFIX.decode()
    child_anchor = (PREFIX + keys[left]).decode()

    CW, CH = 8, 11
    gx = 118
    gw = FANOUT * CW

    # the lookup string, split the way the node reads it
    c.text(gx - 8, y0, "lookup", 9, 600, anchor="end", fill=C_TEXT)
    bx = gx; by = y0 - 10
    seg_w = 26
    pw = 68
    c.rect(bx, by, pw, 14, "#eeeeee", stroke=C_LINE, sw=0.6)
    c.text(bx + pw / 2, by + 10.5, prefix, 10, 600, "middle", C_TEXT)
    bx += pw + 6
    cells = [chr(b) for b in target[:FEATURE_ROWS]]
    for ch in cells:
        c.rect(bx, by, seg_w, 14, "#ffffff", stroke=ACCENT, sw=1.0)
        c.text(bx + seg_w / 2, by + 10.5, ch, 10, 600, "middle", ACCENT)
        bx += seg_w + 4
    c.text(bx + 8, by + 10.5, f"\"{prefix.strip()} \" = the node's shared prefix, checked once; then one row per byte", 8.5, fill=C_MUTED)

    gy = y0 + 30
    fx0, fx1, fy = callout_from
    c.line(fx0, fy + 2, gx, gy - 4, sw=0.7, opacity=0.6, dash="2 2")
    c.line(fx1, fy + 2, gx + gw, gy - 4, sw=0.7, opacity=0.6, dash="2 2")
    c.text(gx - 8, gy - 6 + 3, "byte", 8, anchor="end", fill=C_MUTED)
    c.text(gx + gw + 8, gy - 6 + 3, "could be the child", 8, fill=C_MUTED)
    for r in range(FEATURE_ROWS):
        y = gy + r * (CH + 2)
        prev = set(range(FANOUT)) if r == 0 else set(states[r - 1])
        cur = set(states[r])
        for i in range(FANOUT):
            if i in cur: fill, op = ACCENT, 1.0
            elif i in prev: fill, op = ACCENT, 0.25
            else: fill, op = "#e6e6e6", 1.0
            c.out.append(f'<rect x="{gx + i*CW:.1f}" y="{y:.1f}" width="{CW-1}" height="{CH}" fill="{fill}" opacity="{op}"/>')
        c.text(gx - 8, y + CH - 2, cells[r], 9, 600, "end", ACCENT)
        c.text(gx + gw + 8, y + CH - 2, f"{len(cur)} of {FANOUT}", 9, fill=C_MUTED)
    by2 = gy + FEATURE_ROWS * (CH + 2) + 2
    c.line(gx, by2, gx + gw, by2, sw=0.8, opacity=0.7)
    c.text(gx + gw / 2, by2 + 11, f"{FANOUT} children compared per row in one SIMD pass (64 B = one cache line)", 8.5, anchor="middle", fill=C_MUTED)
    # the answer
    ax = gx + left * CW + CW / 2
    c.text(gx + gw + 8, by2 + 11, f"→ child {left}", 9, 600, fill=ACCENT)
    c.text(ax, by2 + 26, f"child {left} (anchor \"{child_anchor}\"): no anchor matched all four bytes, so no string is compared",
           8, anchor="middle", fill=ACCENT)
    return by2 + 30


def lookup_legend(c, y):
    legend(c, 24, y)
    c.rect(W - 24 - 10, y - 9, 10, 10, ACCENT); c.text(W - 24 - 14, y, "matching children", 10, anchor="end", fill=C_MUTED)

def fig7a():
    """The two lookup paths, schematic (fig 1 / fig 2 shapes)."""
    c = Canvas()
    c.out.append(HI_DEFS)
    y = panel_skiplist(c, 26)
    y, _ = panel_fbtree(c, y + 30)
    lookup_legend(c, y + 20)
    return c.svg(y + 34)

def fig7b():
    """Inside one inner node: the feature rows at real fanout."""
    c = Canvas()
    c.out.append(HI_DEFS)
    c.text(24, 26, "choosing the child inside an inner node: compare feature bytes, not strings", 13, 700)
    F = 4; S = 2.2
    inner = Bar(fbtree_inner(F, prefix_len=22, feature_row=F), "innerNode", INNER_ROLES, S, NODE_H)
    ix = (W - inner.width) / 2; iy = 58
    c.node(inner, ix, iy)
    c.text(ix - 8, iy + NODE_H / 2 + 4, "inner node", 9, anchor="end", fill=C_MUTED)
    for member, label in (("embedded_prefix", "prefix"), ("features", "features"), ("anchors", "anchors"),
                          ("children", "children"), ("child_sizes", "sizes")):
        off, size = inner.fields[member]
        c.text(ix + (off + size / 2) * S, iy - 6, label, 8, anchor="middle", fill=C_MUTED)
    fx0 = ix + inner.x_of("features"); fw = inner.bytes_of("features") * S
    outline(c, fx0, iy, fw, NODE_H)
    y = panel_features(c, iy + NODE_H + 40, (fx0, fx0 + fw, iy + NODE_H))
    lookup_legend(c, y + 20)
    return c.svg(y + 34)


if __name__ == "__main__":
    outdir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    # fig 7a (lookup fetch counts at scale) lives in fetch_figure.py; the
    # toy-scale path panels here are kept only as building blocks.
    (outdir / "fig7b-feature-routing.svg").write_text(fig7b())
    print("wrote fig7b-feature-routing.svg", file=sys.stderr)
