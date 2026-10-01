#!/usr/bin/env python3
"""F3 -- one sorted-set member's bytes, before and after the B+ tree (PR 4359),
in the same Before/After frame as the embedding series.

  Before (9.1)  zskiplistNode, level 1, 20-byte member: 55 B -- plus a hatched 5.3 B
                segment for the expected extra levels: each level above the first costs
                16 B (forward + span) with probability 1/4 per level, so
                16 * (1/4 + 1/16 + 1/64 + ...) = 16 * (1/3) = 5.33 B; 60.3 B on average.
  After  (9.2)  the item, one sds [string header][score][member] (30 B) -- plus a hatched
                9.0 B box: the 8 B leaf slot that points at it and each member's share of
                the leaf header and the inner nodes, 24/61 + 2048 * (1/61^2 + 1/61^3 + ...)
                = 0.39 + 0.56 = 0.95 B. 39.0 B per member.

A plain bar chart: solid = the member's own struct, laid out by fieldday (fdbars); hatched
= the per-member average of everything around it. No pointer highlight and no arrow, so
the two bar lengths compare directly: 60.3 -> 39.0 B/member (the chart's drop is -18 B).

Usage: fbtree_figures.py [outdir] [--scheme NAME] [--no-legend]
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE / "lib"))   # fdbars; the other generators are beside this file
import hashtable_figures as H                                  # noqa: E402
import embed_figures as E                                      # noqa: E402
from fdbars import zskiplist_node, zsl_roles                   # noqa: E402

H.PPB = 6.0            # same scale as the embedding series (a 55 B node = 330 px)

# ---------------------------------------------------------------- probes
# The fbtree item (ordered_index.c packScoreElement -> sdsnewlen): one sds whose
# body is [8-byte sortable score][member]; a 28 B body gets the 1-byte sdshdr5
# (sdsReqType: under 32 B), drawn as the "string header" block.
def fbtree_item(member_len: int = 20) -> str:
    hdr = 1 if member_len + 8 < 32 else 3
    return f"""
struct fbtreeItem {{
    char hdr[{hdr}];
    unsigned char score[8];
    char member[{member_len}];
    char nul;
}};
"""
ITEM_ROLES = {"hdr": "overhead", "score": "data", "member": "data", "nul": "overhead"}
SLOT_B = 8                                   # the leaf array slot: one pointer per member
# Expected values (geometric series), drawn hatched:
#   skiplist: 16 B per extra level, P(level > k) = (1/4)^k  ->  16 * (1/4)/(1 - 1/4) = 5.33 B
#   fbtree:   leaf header 24 B / 61 + inner nodes 2048 B * sum_{k>=2} 61^-k = 0.39 + 0.56 = 0.95 B
LEVEL_B, P = 16, 0.25
EXTRA_B = LEVEL_B * P / (1 - P)
LEAF_HDR, INNER, FANOUT = 24, 2048, 61
SHARE_B = LEAF_HDR / FANOUT + INNER * (1 / FANOUT ** 2) / (1 - 1 / FANOUT)


def hatch_defs() -> str:
    """Diagonal stripes in the box-border colour on the page background: the highest-contrast
    texture available, and no new colour (colour carries meaning elsewhere in the deck)."""
    return (f'<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate(45)"><rect width="6" height="6" fill="{H.theme("background")}"/>'
            f'<line x1="0" y1="0" x2="0" y2="6" stroke="{H.C_LINE}" stroke-width="1.4"/></pattern></defs>')


def hatched(parts, x, y, w, h=H.BAR_H):
    parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="url(#hatch)" '
                 f'stroke="{H.C_LINE}" stroke-width="1.2"/>')
    H.RIGHT[0] = max(H.RIGHT[0], x + w)


def legend(parts, y, entries):
    """Like hashtable_figures.legend, but a fill may be a pattern reference."""
    y -= 9
    if E.SHOW_LEGEND:
        lx = H.PAD
        for fill, label in entries:
            parts.append(f'<rect x="{lx}" y="{y}" width="12" height="12" fill="{fill}" '
                         f'stroke="{H.C_LINE}" stroke-width="1"/>')
            parts.append(H.text(lx + 17, y + 10, label, size=E.LEGEND_PX, fill=H.C_MUTED))
            lx += 17 + 8 * len(label) + 22
        H.RIGHT[0] = max(H.RIGHT[0], lx - 22)
        y += 12
    return y + H.PAD


def f3() -> str:
    parts = H.svg_open()
    parts.append(hatch_defs())
    y = H.PAD
    # backward/forward_1 are probed pointers and would self-assign the highlight; name them grey
    node = H.bar(zskiplist_node(1), "zskiplistNode",
                 {**zsl_roles(1), "backward": "overhead", "forward_1": "overhead"})
    y, xs, yb = H.row(parts, "Before", [
        H.Item(node, {"score": "score", "backward": "*backward", "forward_1": "level 1\nforward",
                      "span_1": "level 1\nspan", "ele_hdr": "string header", "ele": "member (20 B)",
                      "ele_nul": "NUL"}, "zskiplistNode", "55 B"),
    ], y, numbered=False, geometry=True)
    # expected extra levels, appended to the node as a hatched segment
    hx = xs[0] + node.width
    hatched(parts, hx, yb, EXTRA_B * H.PPB)
    parts.append(H.text(hx, yb + H.BAR_H + 14, f"+ {EXTRA_B:.1f} B expected extra levels = "
                        f"{55 + EXTRA_B:.1f} B", size=E.SIZE_PX, fill=H.C_MUTED))
    H.RIGHT[0] = max(H.RIGHT[0], hx + 7.9 * 38)

    item = H.bar(fbtree_item(20), "fbtreeItem", ITEM_ROLES)
    y, xs, yb = H.row(parts, "After", [
        H.Item(item, {"hdr": "string header", "score": "score", "member": "member (20 B)", "nul": "NUL"},
               "item", "30 B"),
    ], y, numbered=False, geometry=True)
    # the leaf slot (8 B) and the per-member share of leaf header + inner nodes, one hatched box
    hx = xs[0] + item.width
    hatched(parts, hx, yb, (SLOT_B + SHARE_B) * H.PPB)
    parts.append(H.text(hx, yb + H.BAR_H + 14, f"+ {SLOT_B + SHARE_B:.0f} B share of B+ tree nodes "
                        f"= {30 + SLOT_B + SHARE_B:.0f} B", size=E.SIZE_PX, fill=H.C_MUTED))
    H.RIGHT[0] = max(H.RIGHT[0], hx + 7.9 * 36)

    y = legend(parts, y, ((H.swatch("rest"), "fields of the struct"),
                          ("url(#hatch)", "per-member average of everything around it")))
    return H.finish(parts, y)


CAPTION = f"""# fbtree figures — slide text

## F3 — One member's bytes: skiplist node vs B+ tree item (fig-fb-3-member-bytes)

Sorted set, 20-byte member, drawn as two bars: solid is the member's own struct, hatched
is the per-member average of everything around it.

Before (Valkey 9.1, after PR 2508): one zskiplistNode per member. A level-1 node is 55 B
(score, backward, one forward/span pair, the embedded member with its 2 B string header).
Every extra level adds 16 B (forward + span), and a node has one with probability 1/4, two
with 1/16, three with 1/64 … so the expected extra cost is 16 × (1/4 + 1/16 + 1/64 + …) =
16 × 1/3 = {EXTRA_B:.1f} B: {55 + EXTRA_B:.1f} B per member on average.

After (Valkey 9.2, PR 4359): the member is an item, one 30 B sds holding the score and the
member. Around it: the 8 B leaf slot that points at it, and the same kind of series with
ratio 1/61 instead of 1/4 for the tree above: 24 B leaf header / 61 + 2048 B × (1/61² +
1/61³ + …) = {SHARE_B:.2f} B. {30 + SLOT_B + SHARE_B:.1f} B per member. {55 + EXTRA_B:.1f} → {30 + SLOT_B + SHARE_B:.1f}: −21 B of struct;
Rimuru's settled measurement is −18 B (jemalloc rounds the 55/71/87 B nodes to 64/72/96 and the 30 B item to 32).

Two pointers per member (backward, forward) become one (the leaf slot); the span counter
and the node's string header go away; the item's own string header is new.
"""


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--scheme" in args:
        i = args.index("--scheme"); E.SCHEME = E.SCHEMES[args[i + 1]]; del args[i:i + 2]
    if "--no-legend" in args:
        E.SHOW_LEGEND = False; args.remove("--no-legend")
    outdir = pathlib.Path(args[0] if args else HERE / "figures")
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "fig-fb-3-member-bytes.svg").write_text(f3())
    (outdir / "captions.md").write_text(CAPTION)
    print("wrote fig-fb-3-member-bytes.svg captions.md")
