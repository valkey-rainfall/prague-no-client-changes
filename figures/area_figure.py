#!/usr/bin/env python3
"""Fig 3: to-scale, correct-fanout (61) allocation figure, skiplist vs fbtree.

Every struct is a bar drawn by fieldday (bare mode, see fdbars.py): the
compiler supplies each member's offset and size, fieldday colors the bytes by
role (pointer / other overhead / user data), and this script only places the
bars and draws the links between them. Bars abut, so a row's length is the
byte total exactly.

Usage: area_figure.py [px_per_byte] [text_scale] [bar_height_factor]

Numbers assume a 20-byte member (the PR 4359 workload), a post-PR-2508
skiplist node (element embedded after the level array), raw struct bytes
(jemalloc size-class rounding is left to prose), and the 8-byte score counted
as user data on both sides. The one bar that is not a struct is the fbtree
inner node's 1/61 share: its pointer/overhead split is the probed inner node's
divided by 61.
"""
import pathlib
import random
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent / "lib"))   # fdbars; fieldday comes from pip (requirements.txt)

from fdbars import (Bar, FD_DEFS, FONT, C_MUTED, C_LINE, C_TEXT, theme,

                    zskiplist_node, zsl_roles, fbtree_item, ITEM_ROLES,
                    fbtree_leaf, LEAF_ROLES, fbtree_inner, INNER_ROLES)
import os
TALK = os.environ.get("TALK") == "1"   # talk mode: no titles/explainer prose (slide carries them)
TT = 1.4 if TALK else 1.0            # talk mode: row headings and legend scaled for a slide

MEMBER = 20                       # bytes of member string per entry
N = 61                            # fbtree fanout; also number of members drawn
PPB = float(sys.argv[1]) if len(sys.argv) > 1 else 0.18
FS = float(sys.argv[2]) if len(sys.argv) > 2 else 1.2    # text/vertical scale
HF = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0    # bar-height factor
H = round(26 * FS * HF)           # bar height

# ---- structs, laid out by the compiler through fieldday
zsl = {L: Bar(zskiplist_node(L, MEMBER), "zskiplistNode", zsl_roles(L), PPB, H, byte_sized=True) for L in (1, 2, 3, 4)}
item = Bar(fbtree_item(MEMBER), "fbtreeItem", ITEM_ROLES, PPB, H)
leaf = Bar(fbtree_leaf(N), "leafNode", LEAF_ROLES, PPB, H)
inner = Bar(fbtree_inner(N), "innerNode", INNER_ROLES, PPB, H)
assert (leaf.size, inner.size) == (512, 2048)

# ---- skiplist arm: 61 zskiplistNode, expected p=0.25 lane mix, spread along the row
levels = [1] * 46 + [2] * 11 + [3] * 3 + [4] * 1
random.Random(4359).shuffle(levels)

def role_sum(bars, scale=1.0):
    t = {"pointer": 0.0, "overhead": 0.0, "data": 0.0, "total": 0.0}
    for b in bars:
        r = b.role_bytes()
        t["pointer"] += r["pointer"] * scale
        t["overhead"] += (r["overhead"] + r["padding"]) * scale   # padding is overhead too
        t["data"] += r["data"] * scale
        t["total"] += b.size * scale
    return t

def summarize(name, t):
    print(f"{name:9s} total {t['total']:7.1f} B  per member {t['total']/N:5.1f}  "
          f"ptr {t['pointer']/N:5.1f}  other {t['overhead']/N:5.1f}  data {t['data']/N:5.1f}", file=sys.stderr)
    return t
sk_t = summarize("skiplist", role_sum(zsl[L] for L in levels))
fb_t = summarize("fbtree", {k: a + b for (k, a), b in zip(
    role_sum([item] * N + [leaf]).items(), role_sum([inner], 1 / N).values())})

# ---- drawing
out = []
C_PTR, C_OTHER, C_PAY = theme("role-pointer"), theme("role-overhead"), theme("role-data")

def place(b, x, y):
    """A fieldday bar plus the white hairline that separates abutting allocations."""
    out.append(b.at(x, y))
    out.append(f'<rect x="{x:.1f}" y="{y}" width="{b.width:.1f}" height="{b.height}" fill="none" stroke="#ffffff" stroke-width="1"/>')
    return b.width

def share_bar(x, y, b, divisor):
    """1/divisor of a struct, as a proportional bar (not a struct; see module doc)."""
    r = b.role_bytes(); cx = x
    for k, col in (("pointer", C_PTR), ("overhead", C_OTHER), ("data", C_PAY)):
        w = (r[k] + (r["padding"] if k == "overhead" else 0)) / divisor * PPB
        if w > 0:
            out.append(f'<rect x="{cx:.1f}" y="{y}" width="{w:.1f}" height="{H}" fill="{col}"/>'); cx += w
    w = b.size / divisor * PPB
    out.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{H}" fill="none" stroke="#ffffff" stroke-width="1"/>')
    return w

def text(x, y, s, size=13, weight=400, anchor="start", fill=C_TEXT):
    size = round(size * FS, 1)
    out.append(f'<text x="{x:.1f}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
               f'text-anchor="{anchor}" fill="{fill}">{s}</text>')

def hop(x1, x2, ly, peak):
    out.append(f'<path d="M {x1:.1f} {ly:.1f} Q {(x1+x2)/2:.1f} {ly-peak:.1f} {x2:.1f} {ly:.1f}" '
               f'fill="none" stroke="{C_LINE}" stroke-width="0.8" opacity="0.6"/>')

X0 = round(90 * FS)
LANE = round(11 * FS)
HEAD_W = round(14 * FS)           # small, in the margin: a sentinel, not a member
maxL = max(levels)

y = 30
if not TALK:
    text(X0, y, f"{N} consecutive sorted-set members: every allocation, to scale", 14, 700)

# ================= skiplist =================
y += round(30 * FS)
text(X0, y, f"skiplist \u00b7 {sk_t['total']/N:.1f} B/member", 12 * TT, 600)
y += LANE * (maxL + 1) + round(14 * FS)
def lane_y(L): return y - LANE * (L - 1)
xs = []; x = X0
for L in levels:
    xs.append(x); x += zsl[L].width
widest = x
centers = [xx + zsl[L].width / 2 for xx, L in zip(xs, levels)]
head_x = X0 - HEAD_W - round(6 * FS)
head_c = head_x + HEAD_W / 2
out.append(f'<rect x="{head_x}" y="{y}" width="{HEAD_W}" height="{H}" fill="none" stroke="{C_LINE}" '
           f'stroke-width="0.8" stroke-dasharray="3 2"/>')
text(head_c, y + H + round(11 * FS), "head", 9, 400, anchor="middle", fill=C_MUTED)
out.append(f'<line x1="{head_c:.1f}" y1="{y}" x2="{head_c:.1f}" y2="{lane_y(maxL + 1):.1f}" '
           f'stroke="{C_LINE}" stroke-width="1.2" opacity="0.7" stroke-dasharray="3 2"/>')
text(head_c, lane_y(maxL + 1) - 3, "...32", 8, 400, anchor="middle", fill=C_MUTED)
for i, L in enumerate(levels):
    if L >= 2:
        out.append(f'<line x1="{centers[i]:.1f}" y1="{y}" x2="{centers[i]:.1f}" y2="{lane_y(L):.1f}" '
                   f'stroke="{C_LINE}" stroke-width="1.2" opacity="0.7"/>')
for L in range(1, maxL + 1):
    pts = [head_c] + [centers[i] for i in range(N) if levels[i] >= L]
    ly_ = lane_y(L); peak = 4 if L == 1 else 7
    for x1, x2 in zip(pts, pts[1:]): hop(x1, x2, ly_, peak)
    text(X0 - HEAD_W - round(14 * FS), ly_ + 3, f"lane {L}", 9, 400, anchor="end", fill=C_MUTED)
for xx, L in zip(xs, levels): place(zsl[L], xx, y)
text(xs[-1] + zsl[levels[-1]].width + 6, y + H / 2 + 4, "tail", 9, 400, fill=C_MUTED)
y += H + round(40 * FS)

# ================= fbtree =================
# Everything the fbtree owns in ONE abutting row -- inner-node share, leaf,
# then the 61 items -- so the row length is the total byte count, exactly
# like the skiplist row. The leaf's child pointers fan up and over to their
# items, mirroring the skiplist lanes above the other row.
text(X0, y, f"fbtree \u00b7 {fb_t['total']/N:.1f} B/member", 12 * TT, 600)
y += round(10 * FS)
fan_h = round(70 * FS)                    # headroom for the fan
y += fan_h
ry = y
ix = X0
inner_w = share_bar(ix, ry, inner, N)
leaf_x = ix + inner_w
items_x0 = leaf_x + place(leaf, leaf_x, ry)
text(leaf_x + leaf.width / 2, ry + H / 2 + 4 * FS, "leaf", 10, 600, anchor="middle", fill="#ffffff")
text(ix + inner_w / 2, ry + H + round(12 * FS), "inner", 9, 400, anchor="middle", fill=C_MUTED)
text(ix + inner_w / 2, ry + H + round(23 * FS), f"1/{N}", 9, 400, anchor="middle", fill=C_MUTED)
for k in range(N):
    x = items_x0 + k * item.width
    sx = leaf_x + leaf.slot_x("values", k, 8)         # values[k], from the compiler's offset
    tx = x + item.width / 2
    peak = round(6 * FS) + (tx - sx) * 0.11           # farther child, higher arc: a nested fan
    out.append(f'<path d="M {sx:.1f} {ry:.1f} Q {(sx+tx)/2:.1f} {ry-peak:.1f} {tx:.1f} {ry:.1f}" '
               f'fill="none" stroke="{C_LINE}" stroke-width="0.5" opacity="0.28"/>')
    place(item, x, ry)
text(items_x0 + N * item.width + 6, ry + H / 2 + 4, "items", 9, 400, fill=C_MUTED)
widest = max(widest, items_x0 + N * item.width)
y = ry + H + round(48 * FS)

# ================= legend + summary =================
lx = X0
for col, label in ((C_PTR, "pointers"), (C_OTHER, "other overhead"), (C_PAY, "user data")):
    if lx > X0 and lx + (17 + len(label) * 6.6) * FS > widest + 20:
        lx = X0; y += round(18 * FS)
    out.append(f'<rect x="{lx:.1f}" y="{y-10*FS*TT:.1f}" width="{12*FS*TT:.1f}" height="{12*FS*TT:.1f}" fill="{col}"/>')
    text(lx + (12 * TT + 5) * FS, y, label, 11 * TT)
    lx += (12 * TT + 5 + len(label) * 6.6 * TT + 18) * FS
# the savings decomposition is printed for the caption, not drawn
saved = sk_t["total"] - fb_t["total"]
print(f"caption: same user data ({sk_t['data']:.0f} B) both sides; fbtree saves {saved:.0f} B ({100*saved/sk_t['total']:.0f}%): "
      f"{sk_t['pointer']-fb_t['pointer']:.0f} B of pointers, {sk_t['overhead']-fb_t['overhead']:.0f} B of other overhead", file=sys.stderr)

W = int(widest + 40)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {y+20}" width="{W}" height="{y+20}">'
       f'<rect width="100%" height="100%" fill="#ffffff"/>{FD_DEFS}' + "\n".join(out) + "</svg>")
sys.stdout.write(svg)
