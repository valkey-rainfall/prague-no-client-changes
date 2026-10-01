#!/usr/bin/env python3
"""Struct bars for the blog figures, drawn by fieldday (bare mode).

Every box in figs 1-3 is a real C struct laid out by the compiler through
fieldday, colored by role (pointer / overhead / data) from fieldday's theme,
and placed by the composer. Nothing here types a byte count or a hex color.

    bar = Bar(snippet, "leafNode", roles={...}, ppb=0.18, height=52)
    bar.size                 # struct size in bytes (compiler)
    bar.width                # px
    bar.offset("values")     # byte offset of a member (compiler)
    bar.at(x, y)             # <g transform=...> with the boxes
    bar.slot_x("values", k, 8)   # px of the center of the k-th 8-byte slot

Figures embed `FD_DEFS` once at the root (fieldday's hatch pattern) and may
use `theme()` for legend swatches so the legend and the bars can never drift.

The bars are drawn with no field borders and square corners: at 0.18 px/byte
a 3-byte sds header is half a pixel wide and a 1 px border would be the only
thing visible. The composer outlines each allocation instead, as before.
"""
from __future__ import annotations

import re

from fieldday.cparse import parse_snippet
from fieldday.probe import compute_layouts
from fieldday.render import (DEFAULT_THEME, HATCH, RenderOptions, render_struct,
                             _inline_presentation)

# fieldday's hatch pattern with its colors baked in as presentation
# attributes (the figures carry no <style> block, so class-only would be black)
def fd_defs(padding_as_overhead: bool = False) -> str:
    """The figure-root <defs>. With padding_as_overhead the hatch pattern is
    made solid slate, so alignment padding reads as 'other overhead' -- for
    schematics whose point is not byte accounting. Fig 3 keeps the hatch."""
    if padding_as_overhead:
        slate = DEFAULT_THEME["role-overhead"]
        return _inline_presentation(HATCH, {"padding-fill": slate, "padding-stroke": slate})
    return _inline_presentation(HATCH, {})


FD_DEFS = fd_defs()
# fieldday's own theme drives figure text and lines too (blog light scheme)
FONT = DEFAULT_THEME["font"]
C_TEXT = DEFAULT_THEME["text"]
C_MUTED = DEFAULT_THEME["muted"]
C_LINE = DEFAULT_THEME["field-border"]


def theme(key: str) -> str:
    return DEFAULT_THEME[key]


def strip_tail_padding(sl):
    """Drop the compiler's trailing alignment padding. For allocations that are
    sized in bytes rather than as a C struct instance -- the zskiplistNode is
    zmalloc(node_size + 1 + sds_size) -- the tail padding is not real memory."""
    while sl.fields and sl.fields[-1].is_padding:
        pad = sl.fields.pop()
        sl.size -= pad.size
    return sl


class Bar:
    def __init__(self, snippet: str, struct: str, roles: dict, ppb: float, height: int,
                 border: str | None = None, corner_radius: int = 0, byte_sized: bool = False,
                 theme: dict | None = None, min_divider_px: float = 4.0):
        """theme: optional fieldday theme overrides (e.g. role-pointer / role-overhead
        fills) for figures that use their own palette; None keeps the default.
        min_divider_px: hide array-element dividers packed tighter than this (fieldday
        default 4.0); raise it to draw a char[] as one solid block."""
        layouts = [s for s in compute_layouts(parse_snippet(snippet)) if s.name == struct]
        if not layouts:
            raise ValueError(f"no struct {struct!r} in snippet")
        sl = layouts[0]
        if byte_sized:
            strip_tail_padding(sl)
        sl.roles = dict(roles)
        self.layout = sl
        self.size = sl.size
        self.ppb = ppb
        self.height = height
        self.fields = {f.name: (f.offset, f.size) for f in sl.fields if not f.is_padding}
        self.padding = sl.padding_bytes
        # roles are explicit here: the probe flags scalar pointers but not
        # pointer arrays, and fig 3 counts the sds header/NUL as overhead
        opts = RenderOptions(bare=True, px_per_byte=ppb, bar_height=height,
                             corner_radius=corner_radius, min_divider_px=min_divider_px,
                             theme={"field-border": border or "none",
                                    "padding-stroke": border or "none",
                                    **(theme or {})})
        svg = render_struct(sl, opts)
        self.width = self.size * ppb          # exact; the SVG canvas is int()-truncated
        # keep only the drawn elements: one <style>/<defs> copy lives at the figure root
        body = svg.split("</defs>", 1)[1].rsplit("</svg>", 1)[0]
        self.body = body.strip("\n")

    def offset(self, member: str) -> int:
        return self.fields[member][0]

    def bytes_of(self, *members: str) -> int:
        return sum(self.fields[m][1] for m in members)

    def role_bytes(self) -> dict:
        """Bytes per role as drawn: pointer / overhead / data / padding."""
        out = {"pointer": 0, "overhead": 0, "data": 0, "padding": self.padding}
        roles = self.layout.roles
        for f in self.layout.fields:
            if f.is_padding:
                continue
            r = roles.get(f.name) or ("pointer" if f.is_pointer else None)
            if r and r != "none":
                out[r] += f.size
        return out

    def x_of(self, member: str, plus_bytes: float = 0) -> float:
        """px (relative to the bar's origin) of a byte position inside a member."""
        return (self.offset(member) + plus_bytes) * self.ppb

    def slot_x(self, member: str, k: int, slot_bytes: int) -> float:
        """px center of the k-th slot_bytes-wide element of an array member."""
        return self.x_of(member, k * slot_bytes + slot_bytes / 2)

    def at(self, x: float, y: float) -> str:
        return f'<g transform="translate({x:.2f} {y:.2f})">{self.body}</g>'


# ------------------------------------------------------------- probe snippets
# All snippets are 64-bit layouts of the real Valkey structs (src/server.h,
# src/fbtree_internal.h, src/ordered_index.c) with two honest substitutions
# so the compiler, not the author, supplies the byte counts:
#   * flexible tails (zskiplistNode.level[], sds bodies) are spelled out for
#     the case drawn -- L lanes, a 20-byte member;
#   * #defines are inlined (NODE_SIZE=61 etc.), or reduced to the drawn
#     fanout for the schematic figs, which say so in their captions.

NODE_HDR = """
typedef struct node {
    bool is_leaf;
    uint8_t num_items;
} node;
"""


def zskiplist_node(levels: int, member_len: int = 20) -> str:
    """Post PR 2508 node (t_zset.c zslCreateNode): score, backward, level[L],
    then ONE byte holding the sds header size (so zslGetNodeElement can find
    the string without knowing its sds type), then the element embedded as an
    sds: sdsReqType() picks sdshdr5 (1 B) for a member under 32 B and sdshdr8
    (3 B) above, + bytes + NUL. Level 0's span field holds the node height
    rather than a span."""
    hdr = 1 + (1 if member_len < 32 else 3)
    lanes = "\n".join(
        f"    struct zskiplistNode *forward_{i}; unsigned long span_{i};"
        for i in range(1, levels + 1))
    return f"""
struct zskiplistNode {{
    double score;
    struct zskiplistNode *backward;
{lanes}
    uint8_t ele_hdr[{hdr}];   /* 1 B sds header size (written by zslCreateNode) + the member's sds header */
    char ele[{member_len}];
    char ele_nul;
}};
"""


ZSL_ROLES = {"score": "data", "ele": "data", "ele_hdr": "overhead", "ele_nul": "overhead"}
# backward / forward_k are probed pointers and self-assign 'pointer'; span_k
# are unlisted non-pointers and stay neutral -- name them explicitly:
def zsl_roles(levels: int) -> dict:
    return {**ZSL_ROLES, **{f"span_{i}": "overhead" for i in range(1, levels + 1)}}


def fbtree_item(member_len: int = 20) -> str:
    """One fbtree item: an sds holding [8-byte sortable score][member] --
    ordered_index.c packScoreElement. Header is sdshdr8, body byte-packed."""
    return f"""
struct fbtreeItem {{
    uint8_t len; uint8_t alloc; uint8_t flags;   /* sdshdr8 */
    unsigned char score[8];                      /* big-endian sortable double */
    char member[{member_len}];
    char nul;
}};
"""


ITEM_ROLES = {"len": "overhead", "alloc": "overhead", "flags": "overhead",
              "score": "data", "member": "data", "nul": "overhead"}


def fbtree_leaf(fanout: int = 61) -> str:
    return NODE_HDR + f"""
typedef struct leafNode {{
    node header;
    struct leafNode *prev;
    struct leafNode *next;
    sds values[{fanout}];
}} leafNode;
"""


LEAF_ROLES = {"header": "overhead", "prev": "pointer", "next": "pointer", "values": "pointer"}


def fbtree_inner(fanout: int = 61, prefix_len: int = 254, feature_row: int = 64) -> str:
    """features is FEATURE_SIZE (4) rows of FEATURE_ROW_SIZE (64) bytes: one
    byte position across all children per row, padded to a SIMD width."""
    return NODE_HDR + f"""
typedef struct innerNode {{
    node header;
    char embedded_prefix[{prefix_len}];
    size_t prefix_len;
    char features[4][{feature_row}];
    sds anchors[{fanout}];
    node *children[{fanout}];
    size_t child_sizes[{fanout}];
    uint8_t child_num_items[{fanout}];
}} innerNode;
"""


INNER_ROLES = {"header": "overhead", "embedded_prefix": "overhead", "prefix_len": "overhead",
               "features": "overhead", "anchors": "pointer", "children": "pointer",
               "child_sizes": "overhead", "child_num_items": "overhead"}


if __name__ == "__main__":
    # self-check: the spelled-out snippets reproduce the real sizes
    import sys
    checks = [
        ("zskiplistNode L=1", Bar(zskiplist_node(1), "zskiplistNode", zsl_roles(1), 1, 10, byte_sized=True), 55),
        ("zskiplistNode L=4", Bar(zskiplist_node(4), "zskiplistNode", zsl_roles(4), 1, 10, byte_sized=True), 103),
        ("fbtreeItem", Bar(fbtree_item(), "fbtreeItem", ITEM_ROLES, 1, 10), 32),
        ("leafNode", Bar(fbtree_leaf(), "leafNode", LEAF_ROLES, 1, 10), 512),
        ("innerNode", Bar(fbtree_inner(), "innerNode", INNER_ROLES, 1, 10), 2048),
    ]
    ok = True
    for name, bar, want in checks:
        flag = "ok " if bar.size == want else "BAD"
        ok &= bar.size == want
        print(f"{flag} {name:18s} {bar.size:5d} B  roles {bar.role_bytes()}", file=sys.stderr)
    sys.exit(0 if ok else 1)
