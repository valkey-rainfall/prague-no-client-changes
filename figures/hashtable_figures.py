#!/usr/bin/env python3
"""Hashtable figures for the ValkeyConf talk (see OUTLINE.md).

H1 -- one string key's path from the table to its value, on the keyspace
(16 B key, 16 B value). Two-row version (dict vs hashtable) and three-row
version (adds the value-pointer step, tying back to the embedding series):

  Valkey 8.0  dict pointer table -> embedded dictEntry -> robj [ptr | embstr value]   (3 fetches)
  Valkey 8.1  bucket table       -> robj [ptr | key | embstr value]                  (2 fetches)
  Valkey 9.1  bucket table       -> robj [key | embstr value]                        (2 fetches)

A value up to 44 B has been EMBSTR (inside the robj allocation) since 7.2, so at 16 B the
value string never was a separate fetch; the 4 -> 3 -> 2 story holds only above 44 B
(fig 5's 64 B aside). Sizes verified against object.c createEmbeddedStringObject /
createEmbeddedStringObjectWithKeyAndExpire (1 B key-header-size prefix + sdshdr5 + NUL; a
16 B key is under 32 B so it gets the 1-byte sds5 header, the embedded value is always sdshdr8).
Orange marks the pointers a lookup follows (= fetches - 1): 2, 1, 1 down the rows. Every box
is a real C struct laid out by fieldday (via fbtree-blog/fdbars) from the
layouts at 3eb8314be (PR 1186) and its parent, and 0ee423450 (PR 2516). Same
frame, palette and label machinery as ../embedding-figures/embed_figures.py,
at 4 px/byte so a 64 B bucket fits the row. The table is drawn as a stack of
slots (dict: 8 B pointers; hashtable: 64 B buckets) with the neighbours faded.
Circled numerals count the memory locations fetched on a lookup.

Usage: hashtable_figures.py [outdir] [--scheme NAME] [--no-legend] [--with-text]
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE / "lib"))   # fdbars; embed_figures is beside this file
import embed_figures as E                                  # noqa: E402
from embed_figures import (text, outline, label_fields, arrow_color, arrow_defs,  # noqa: E402
                           swatch, arrow_lane, W, PAD, BAR_H, GAP, C_LINE, C_TEXT, C_MUTED,
                           FD_DEFS, theme, CALLOUT_ROW)
from fdbars import Bar                                     # noqa: E402

PPB = 4.0            # px per byte (a 64 B bucket = 256 px)
STACK_N = 2          # faded neighbour slots drawn under the active one
STACK_H = 10         # px, height of a faded neighbour
STACK_GAP = 3

# ---------------------------------------------------------------- probes
# 8.0: one slot of the dict table (dictEntry **). Each entry is zmalloc'd on
# its own and chained through next.
SLOT = "struct dictSlot { void *entry; };"
# 8.0: keyspace dictEntry after PR 541 -- value + next pointers, then the key
# sds embedded (1 B header-size prefix + sdshdr5 + body + NUL): 16 + 1 + 18 = 35 B.
def entry_80(key_len: int = 16) -> str:
    return f"""
struct embeddedDictEntry {{
    void *v;
    struct dictEntry *next;
    char key_hdr[2];
    char key[{key_len}];
    char key_nul;
}};
"""
ENTRY_ROLES = {"v": "pointer", "next": "pointer", "key_hdr": "overhead", "key": "data",
               "key_nul": "overhead"}
# 8.0: the value object, key-less. A value up to 44 B is EMBSTR: the sds lives in
# the same allocation right after the robj, and ptr points at it (object.c
# createEmbeddedStringObject). 16 + 3 + 16 + 1 = 36 B for a 16 B value.
def robj_80(value_len: int = 16) -> str:
    return f"""
struct robj80 {{
    uint64_t header_bits;
    void *ptr;
    char v_hdr[3];
    char value[{value_len}];
    char v_nul;
}};
"""
ROBJ_80_ROLES = {"header_bits": "overhead", "ptr": "pointer", "v_hdr": "overhead", "value": "data", "v_nul": "overhead"}
# 8.1: one hashtable bucket (hashtable.c): metadata byte (chained bit +
# 7 presence bits), one hash byte per slot, 7 entry pointers = 64 B.
# The 7th slot is split out (same layout) so the one followed pointer can be lit.
BUCKET = "struct hashtableBucket { uint8_t meta; uint8_t hashes[7]; void *entries[6]; void *entry_last; };"
BUCKET_ROLES = {"meta": "overhead", "hashes": "overhead", "entries": "pointer", "entry_last": "pointer"}
# 8.1: the value object with the key embedded (createEmbeddedStringObjectWithKeyAndExpire,
# no expire): header, ptr, 1 B key-header-size prefix + key sds, then the embstr value.
# 16 + 1 + 18 + 20 = 55 B for 16 B key and value.
def robj_81(key_len: int = 16, value_len: int = 16) -> str:
    return f"""
struct robj81 {{
    uint64_t header_bits;
    void *ptr;
    char key_hdr[2];
    char key[{key_len}];
    char key_nul;
    char v_hdr[3];
    char value[{value_len}];
    char v_nul;
}};
"""
ROBJ_81_ROLES = {"header_bits": "overhead", "ptr": "pointer", "key_hdr": "overhead",
                 "key": "data", "key_nul": "overhead", "v_hdr": "overhead", "value": "data", "v_nul": "overhead"}
# 9.1: same, without the value pointer (PR 2516; fig 4): 8 + 1 + 18 + 20 = 47 B.
def robj_91(key_len: int = 16, value_len: int = 16) -> str:
    return f"""
struct robj91 {{
    uint64_t header_bits;
    char key_hdr[2];
    char key[{key_len}];
    char key_nul;
    char v_hdr[3];
    char value[{value_len}];
    char v_nul;
}};
"""
ROBJ_91_ROLES = {"header_bits": "overhead", "key_hdr": "overhead", "key": "data",
                 "key_nul": "overhead", "v_hdr": "overhead", "value": "data", "v_nul": "overhead"}
# The separately allocated value string (8.0 and 8.1).
def sds(value_len: int = 20) -> str:
    return f"struct valueSds {{ char hdr[3]; char body[{value_len}]; char nul; }};"
SDS_ROLES = {"hdr": "overhead", "body": "data", "nul": "overhead"}


ACCENT = "#7b86e6"   # periwinkle: a second highlight for a field that MOVES (the expiry in H5)


def bar(snippet, struct, roles, spot=(), height=BAR_H, accent=()):
    """Spotlight: `spot` members take the highlight color, `accent` members the
    periwinkle accent, the rest is grey. Element dividers show at 8 B (pointer
    slots) but not at 1 B (hash bytes)."""
    if E.SPOTLIGHT:
        roles = {k: ("pointer" if k in spot else "data" if k in accent else "overhead") for k in roles}
    return Bar(snippet, struct, roles, PPB, height, border=C_LINE, byte_sized=True,
               min_divider_px=PPB * 2 + 1,
               theme={"role-pointer": E.SCHEME["highlight"], "role-overhead": E.SCHEME["rest"],
                      "role-data": ACCENT})


# ------------------------------------------------------------- composition
CALLOUT_H = 18 + CALLOUT_ROW
ARROW_LANE = 14
BADGE_H = 32         # band for the circled fetch numbers (two lines), above the arrow lane
BADGE_LINE = 14      # px between the two badge lines
NAME_PX = 12.5       # item names above a bar (was 10.5)
BADGE_CHAR = NAME_PX * 0.6   # approx advance of the mono theme font at NAME_PX
STACK_EXTRA = STACK_N * (STACK_H + STACK_GAP)


def hop_arrow(parts, ax, y, tx, rows=None):
    """Over-the-top pointer arrow from x=ax (inside a source bar whose top is y)
    to the left edge x=tx of the target bar, landing at mid-height. The lane sits
    just above the callout rows in use on this line."""
    top = y - arrow_lane(rows)
    dx = tx - GAP + 6
    mid = y + BAR_H / 2
    parts.append(f'<path d="M{ax:.1f},{y:.1f} L{ax:.1f},{top:.1f} L{dx:.1f},{top:.1f} '
                 f'L{dx:.1f},{mid:.1f} L{tx - 2:.1f},{mid:.1f}" stroke="{arrow_color()}" '
                 f'stroke-width="2" fill="none" marker-end="url(#arrowhead)"/>')


def fetch_badge(parts, x, y, n, label):
    """Circled fetch number + item name above a bar's left end."""
    parts.append(f'<circle cx="{x + 7:.1f}" cy="{y:.1f}" r="7" fill="{theme("background")}" '
                 f'stroke="{C_TEXT}" stroke-width="1"/>')
    parts.append(text(x + 7, y + 3.4, str(n), size=9.5, weight="bold", anchor="middle"))
    parts.append(text(x + 19, y + 3.6, label, size=NAME_PX, fill=C_MUTED))


class Item:
    """One box in a row. `stack` draws faded neighbour slots under it (a table);
    `rise` is the byte position an arrow leaves from (None = no outgoing arrow)."""
    def __init__(self, bar_, labels, name, size, rise=None, stack=None):
        self.bar, self.labels, self.name, self.size, self.rise, self.stack = \
            bar_, labels, name, size, rise, stack


RIGHT = [0.0]        # right-most content x seen by row()/place(), for auto-cropping the canvas


def callout_rows_used(b, x, labels, avoid=None, rows=None):
    """Dry-run label placement to learn which callout rows a bar will use."""
    rows = rows if rows is not None else [-1e9, -1e9]
    label_fields(b, x, 0, labels, callout_y=-6, rows=rows, avoid_x=avoid)
    return rows


def top_clear(rows, has_arrow):
    """Vertical clearance above a bar's top edge before other content may start:
    the arrow lane if the line has an arrow, else just the callout rows in use."""
    if has_arrow:
        return arrow_lane(rows)
    used = 2 if rows[1] > -1e8 else (1 if rows[0] > -1e8 else 0)
    return {0: 4, 1: 16, 2: 28}[used]


def row(parts, label, items, y, numbered=True, geometry=False, x0=PAD, compact=False):
    """Draw one line of boxes. label=None: a continuation line with no row heading.
    numbered=False: item names without the fetch circles. geometry=True returns
    (y_next, xs, y_bar) so a caller can draw arrows between lines. The headroom
    above the bars is measured, not fixed: item names sit just above the arrow
    lane (or the callouts) of this line."""
    if label is not None:
        parts.append(text(PAD, y + 12, label, size=13, weight="bold", fill=C_MUTED))
        y += 22
    xs, x = [], x0
    for it in items:
        xs.append(x)
        x += it.bar.width + GAP
    # measure: callout rows in use, arrow presence, badge lines needed
    probe = [-1e9, -1e9]
    for i, it in enumerate(items):
        ax = xs[i] + it.rise * PPB if it.rise is not None else (xs[i] - GAP + 6 if i else None)
        callout_rows_used(it.bar, xs[i], it.labels, ax, probe)
    has_arrow = any(it.rise is not None for it in items[:-1])
    clear = top_clear(probe, has_arrow)
    badge_line = []
    for i, it in enumerate(items):
        right = xs[i] + 19 + len(it.name) * BADGE_CHAR
        up = i + 1 < len(items) and right > xs[i + 1] - 4
        badge_line.append(1 if up and not (badge_line and badge_line[-1] == 1) else 0)
    nlines = 1 + max(badge_line)
    y += clear + 20 + BADGE_LINE * (nlines - 1)
    badge_y = y - clear - 12            # circle centre / name baseline-3.6 of line 1
    rows = [-1e9, -1e9]
    for i, it in enumerate(items):
        b = it.bar
        parts.append(b.at(xs[i], y))
        parts.append(outline(xs[i], y, b.width, BAR_H))
        ax = xs[i] + it.rise * PPB if it.rise is not None else (xs[i] - GAP + 6 if i else None)
        parts.append(label_fields(b, xs[i], y, it.labels, callout_y=y - 6, rows=rows, avoid_x=ax))
        sy = y + BAR_H
        if it.stack is not None:
            for k in range(STACK_N):
                sy += STACK_GAP
                parts.append(f'<g opacity="0.35">{it.stack.at(xs[i], sy)}'
                             f'{outline(xs[i], sy, b.width, STACK_H)}</g>')
                sy += STACK_H
        hw = len(it.size) * BADGE_CHAR * 11 / 10.5 / 2
        parts.append(text(max(xs[i] + b.width / 2, hw + 8), sy + 14, it.size, size=E.SIZE_PX,
                          fill=C_MUTED, anchor="middle"))
        by = badge_y - badge_line[i] * BADGE_LINE
        RIGHT[0] = max(RIGHT[0], xs[i] + b.width, xs[i] + 19 + len(it.name) * BADGE_CHAR)
        if numbered:
            fetch_badge(parts, xs[i], by, i + 1, it.name)
        else:
            parts.append(text(xs[i], by + 3.6, it.name, size=NAME_PX, fill=C_MUTED))
    for i, it in enumerate(items):
        if it.rise is not None and i + 1 < len(items):
            hop_arrow(parts, xs[i] + it.rise * PPB, y, xs[i + 1], rows)
    stack_extra = STACK_EXTRA if any(it.stack is not None for it in items) else 0
    y_next = y + BAR_H + stack_extra + 14 + 26
    return (y_next, xs, y) if geometry else y_next


def finish(parts, y, wmax=W) -> str:
    """Close the SVG, sized to the content: height y, width = right-most content + PAD."""
    w = min(wmax, int(RIGHT[0] + PAD))
    parts.append("</svg>")
    return "\n".join(p for p in parts if p).replace("{H}", str(int(y))).replace("{W}", str(w))


def legend(parts, y, entries):
    y -= 9                        # roughly half the inter-row gap between the last size label and the legend
    if E.SHOW_LEGEND:
        lx = PAD
        for role, label in entries:
            parts.append(f'<rect x="{lx}" y="{y}" width="12" height="12" fill="{swatch(role)}"/>')
            parts.append(text(lx + 17, y + 10, label, size=E.LEGEND_PX, fill=C_MUTED))
            lx += 17 + 8 * len(label) + 22
        RIGHT[0] = max(RIGHT[0], lx - 22)
        y += 12
    return y + PAD


def svg_open():
    RIGHT[0] = 0.0
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{{W}}" viewBox="0 0 {{W}} {{H}}" '
            f'font-family="{theme("font")}">',
            f"<defs>{FD_DEFS}{arrow_defs()}</defs>",
            f'<rect width="{{W}}" height="{{H}}" fill="{theme("background")}"/>']


def path_figure(three_rows: bool) -> str:
    """One 16 B key with a 16 B value across releases. The value is EMBSTR (inside the
    robj allocation) at every release, so the fetch count is 3 -> 2 -> 2; the 4 -> 3 -> 2
    story only holds for values over the 44 B embstr limit (fig 5's 64 B aside)."""
    parts = svg_open()
    y = PAD
    HDR, NUL = E.sds_labels()
    key_lbl = {"key_hdr": HDR, "key": "key (16 B)", "key_nul": NUL}
    val_lbl = {"v_hdr": HDR, "value": "value (16 B)", "v_nul": NUL}

    # ---- Valkey 8.0: dict
    slot = bar(SLOT, "dictSlot", {"entry": "pointer"}, spot=("entry",))
    slot_faded = bar(SLOT, "dictSlot", {"entry": "pointer"}, height=STACK_H)
    ent = bar(entry_80(16), "embeddedDictEntry", ENTRY_ROLES, spot=("v",))
    ro = bar(robj_80(16), "robj80", ROBJ_80_ROLES)
    y = row(parts, "Valkey 8.0" if three_rows else "Before", [
        Item(slot, {"entry": ""}, "dict pointer table", "8 B / slot", rise=4, stack=slot_faded),
        Item(ent, {"v": "*value", "next": "*next", **key_lbl}, "dictEntry", "35 B", rise=4),
        Item(ro, {"header_bits": "robj", "ptr": "*value", **val_lbl}, "object", "36 B"),
    ], y)

    # ---- Valkey 8.1: hashtable
    bkt = bar(BUCKET, "hashtableBucket", BUCKET_ROLES, spot=("entry_last",))
    bkt_faded = bar(BUCKET, "hashtableBucket", BUCKET_ROLES, height=STACK_H)
    rk = bar(robj_81(16, 16), "robj81", ROBJ_81_ROLES)
    y = row(parts, "Valkey 8.1" if three_rows else "After", [
        Item(bkt, {"meta": "", "hashes": "hashes", "entries": "7 entry pointers", "entry_last": ""},
             "hashtable bucket table", "64 B / bucket = one cache line", rise=60, stack=bkt_faded),
        Item(rk, {"header_bits": "robj", "ptr": "*value", **key_lbl, "key_nul": "", **val_lbl},
             "object with key and value", "55 B"),
    ], y)

    # ---- Valkey 9.1: the value pointer goes (PR 2516)
    if three_rows:
        rkv = bar(robj_91(16, 16), "robj91", ROBJ_91_ROLES)
        y = row(parts, "Valkey 9.1", [
            Item(bkt, {"meta": "", "hashes": "hashes", "entries": "7 entry pointers", "entry_last": ""},
                 "hashtable bucket table", "64 B / bucket = one cache line", rise=60, stack=bkt_faded),
            Item(rkv, {"header_bits": "robj", **key_lbl, "key_nul": "", **val_lbl},
                 "object with key and value", "47 B"),
        ], y)

    y = legend(parts, y, (("highlight", "pointers followed to reach the value"), ("rest", "everything else")))
    return finish(parts, y)


# ------------------------------------------------------------- H5: keys with a TTL
# 8.0: a volatile key has TWO dict entries -- one in the keyspace dict (the PR 541
# embedded-key entry) and one in the expires dict: a generic dictEntry whose key*
# points at the key inside the main entry and whose value is the expiry
# (db.c setExpire: kvstoreDictAddRaw(db->expires, ..., dictGetKey(kde))).
# 8.1 (PR 1186): both tables are hashtables and both point at the SAME robj
# (server.c kvstoreExpiresHashtableType: entryDestructor NULL, "shared with
# keyspace table"); the expiry is an 8 B field inside the robj, placed before
# the embedded key (createObjectWithKeyAndExpire).
EXPIRES_ENTRY = "struct expiresEntry { void *key; long long expire; struct dictEntry *next; };"
EXPIRES_ROLES = {"key": "pointer", "expire": "data", "next": "pointer"}
def robj_81_ttl(key_len: int = 16, value_len: int = 16) -> str:
    return f"""
struct robj81ttl {{
    uint64_t header_bits;
    void *ptr;
    long long expire;
    char key_hdr[2];
    char key[{key_len}];
    char key_nul;
    char v_hdr[3];
    char value[{value_len}];
    char v_nul;
}};
"""
ROBJ_81_TTL_ROLES = {"header_bits": "overhead", "ptr": "pointer", "expire": "data",
                     "key_hdr": "overhead", "key": "data", "key_nul": "overhead",
                     "v_hdr": "overhead", "value": "data", "v_nul": "overhead"}


def cross_arrow(parts, ax, y_from, tx, y_to_bottom):
    """Arrow from a slot in a LOWER line (top edge y_from) up into the bottom edge
    of a bar in the line above (y_to_bottom), via a lane just under that line's
    size labels."""
    lane = y_to_bottom + STACK_EXTRA + 14 + 10
    parts.append(f'<path d="M{ax:.1f},{y_from:.1f} L{ax:.1f},{lane:.1f} L{tx:.1f},{lane:.1f} '
                 f'L{tx:.1f},{y_to_bottom + 2:.1f}" stroke="{arrow_color()}" stroke-width="2" '
                 f'fill="none" marker-end="url(#arrowhead)"/>')


TTL_LEGEND = (("highlight", "pointers followed"), (ACCENT, "the expiry (8 B)"), ("rest", "everything else"))


def ttl_before(parts, y, label="Before"):
    """One band: keyspace path (slot -> dictEntry -> object) and, to its right, the
    expires path (slot -> dictEntry holding the expiry)."""
    HDR, NUL = E.sds_labels()
    key_lbl = {"key_hdr": HDR, "key": "key (16 B)", "key_nul": NUL}
    slot = bar(SLOT, "dictSlot", {"entry": "pointer"}, spot=("entry",))
    ent = bar(entry_80(16), "embeddedDictEntry", ENTRY_ROLES, spot=("v",))
    ro = bar(robj_80(16), "robj80", ROBJ_80_ROLES)
    xent = bar(EXPIRES_ENTRY, "expiresEntry", EXPIRES_ROLES, accent=("expire",))
    val_lbl = {"v_hdr": HDR, "value": "value (16 B)", "v_nul": NUL}
    left = [Item(slot, {"entry": ""}, "keyspace dict", "8 B / slot", rise=4),
            Item(ent, {"v": "*value", "next": "*next", **key_lbl}, "dictEntry", "35 B", rise=4),
            Item(ro, {"header_bits": "robj", "ptr": "*value", **val_lbl}, "object", "36 B")]
    y_next, xs, _ = row(parts, label, left, y, numbered=False, geometry=True)
    x_right = xs[-1] + ro.width + 60
    right = [Item(slot, {"entry": ""}, "expires dict", "8 B / slot", rise=4),
             Item(xent, {"key": "*key", "expire": "expiry", "next": "*next"}, "dictEntry", "24 B")]
    row(parts, None, right, y + (22 if label else 0), numbered=False, x0=x_right)
    return y_next


def ttl_after(parts, y, label="After"):
    """Keyspace bucket above, expires bucket below, ONE object between them with
    both followed slots pointing at it."""
    HDR, NUL = E.sds_labels()
    key_lbl = {"key_hdr": HDR, "key": "key (16 B)", "key_nul": NUL}
    bkt = bar(BUCKET, "hashtableBucket", BUCKET_ROLES, spot=("entry_last",))
    rk = bar(robj_81_ttl(16, 16), "robj81ttl", ROBJ_81_TTL_ROLES, accent=("expire",))
    obj_lbl = {"header_bits": "robj", "ptr": "*value", "expire": "expiry", **key_lbl, "key_nul": "",
               "v_hdr": HDR, "value": "value (16 B)", "v_nul": NUL}
    bl = {"meta": "", "hashes": "hashes", "entries": "7 entry pointers", "entry_last": ""}
    y1, xs, ya = row(parts, label, [Item(bkt, bl, "keyspace hashtable", "64 B / bucket")],
                     y, numbered=False, geometry=True)
    y2, _, yb = row(parts, None, [Item(bkt, bl, "expires hashtable", "64 B / bucket")],
                    y1 - 6, numbered=False, geometry=True)
    xo = xs[0] + bkt.width + GAP
    yo = (ya + yb + BAR_H) / 2 - BAR_H / 2
    parts.append(rk.at(xo, yo))
    parts.append(outline(xo, yo, rk.width, BAR_H))
    parts.append(label_fields(rk, xo, yo, obj_lbl, callout_y=yo - 6, avoid_x=xo - GAP + 6))
    obj_clear = top_clear(callout_rows_used(rk, xo, obj_lbl, xo - GAP + 6), False)
    parts.append(text(xo, yo - obj_clear - 8, "object", size=NAME_PX, fill=C_MUTED))
    parts.append(text(xo + rk.width / 2, yo + BAR_H + 14, "63 B", size=E.SIZE_PX, fill=C_MUTED, anchor="middle"))
    RIGHT[0] = max(RIGHT[0], xo + rk.width + 40)      # NUL callout overhang
    ax = xs[0] + 60 * PPB
    c = arrow_color()
    for y_from, y_land in ((ya + BAR_H, yo + 14), (yb, yo + BAR_H - 14)):
        parts.append(f'<path d="M{ax:.1f},{y_from:.1f} L{ax:.1f},{y_land:.1f} L{xo - 2:.1f},{y_land:.1f}" '
                     f'stroke="{c}" stroke-width="2" fill="none" marker-end="url(#arrowhead)"/>')
    return y2


def ttl_figure(part: str = "both") -> str:
    parts = svg_open()
    y = PAD
    if part in ("before", "both"):
        y = ttl_before(parts, y)
    if part == "both":
        y += 6
    if part in ("after", "both"):
        y = ttl_after(parts, y)
    y = legend(parts, y, TTL_LEGEND)
    return finish(parts, y)


# ------------------------------------------------------------- H6: the collision chain
# Four frames of ONE table slot whose chain holds three colliding keys, keyspace
# on the left and the expires table on the right, so the audience watches the
# chain's allocations disappear one mechanism at a time:
#   a  Valkey 7.2   slot -> dictEntry{*key,*val,*next} -> object, -> key sds; expires dictEntry{*key,expiry,*next}
#   b  Valkey 8.0   PR 541: the key moves into the dictEntry                                    (12 -> 9 allocations)
#   c  (no release) the key moves on into the object (the real 8.1 no-TTL object, 55 B)   (9, byte-neutral)
#   d  (no release) the expiry follows; both dicts now point at one object, entries = 2 ptrs (9, byte-neutral)
#   e  Valkey 8.1   PR 1186: the chain of 1-entry nodes becomes one 7-entry bucket            (9 -> 3)
# Frames c and d are a didactic decomposition of PR 1186 (which did b->e in one step);
# their structs are real C layouts that never shipped, and their labels say so.
# Highlight rule (same in every frame): orange = the pointer the NEXT frame removes,
# periwinkle = the data item the NEXT frame moves; everything else grey, frame e all grey.
# Arrows are drawn for every pointer regardless. The key string sits on the FAR side of
# the object in frame a so the entry's two arrows (*key is left of *value) go over the top
# in nested lanes without crossing, and the *next chain can drop straight down.
# Columns are fixed across frames so the objects stay put during the reveal.
CHAIN_N = 3
LANE1, LANE2 = 20, 30        # over-the-top arrow lanes above a bar (no callouts in these frames)
NEXT_DROP = 22               # *next leaves the bottom of its field, jogs left BELOW the under lane, drops into the first byte below
UNDER_LANE = 10              # the expires *key runs under the row to wherever the key lives (a: string, b: entry, c: object)
SIZE_DY = BAR_H + 32         # size-label baseline below a bar (clears the under lane)
LINK_PITCH = BAR_H + 62      # the jog at y+66 sits above the next link's lanes (-30/-20)
NAME_DY, NAME_DY2 = 44, 58   # item-name baselines above link 1 (second line when names would collide)
CHAIN_W = 1000               # wider canvas than the 720 px embedding frame (three columns)

ENTRY_C = "struct dictEntryC { void *v; struct dictEntry *next; };"            # 16 B, never shipped
ENTRY_C_ROLES = {"v": "pointer", "next": "pointer"}
XENTRY_C = "struct expiresEntryC { void *obj; struct dictEntry *next; };"      # 16 B, never shipped
XENTRY_C_ROLES = {"obj": "pointer", "next": "pointer"}
BUCKET7 = ("struct hashtableBucket7 { uint8_t meta; uint8_t hashes[7]; "
           + " ".join(f"void *e{i};" for i in range(7)) + " };")                # BUCKET with the 7 slots named
BUCKET7_ROLES = {"meta": "overhead", "hashes": "overhead", **{f"e{i}": "pointer" for i in range(7)}}
CHAIN_LEGEND = (("highlight", "the pointer the next step removes"), (ACCENT, "the data the next step moves"),
                ("rest", "everything else"))


def poly_arrow(parts, pts, head):
    """Orthogonal polyline arrow with an explicit triangular head. librsvg mis-orients
    <marker> heads on right-to-left and vertical end segments (the F1/F2 bug), so the
    chain frames draw every head themselves. head: right | left | down."""
    c = arrow_color()
    d = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    parts.append(f'<path d="{d}" stroke="{c}" stroke-width="2" fill="none"/>')
    x, y = pts[-1]
    h, w = 8, 4
    tri = {"right": [(x, y), (x - h, y - w), (x - h, y + w)],
           "left": [(x, y), (x + h, y - w), (x + h, y + w)],
           "down": [(x, y), (x - w, y - h), (x + w, y - h)],
           "up": [(x, y), (x - w, y + h), (x + w, y + h)]}[head]
    parts.append('<polygon points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in tri) + f'" fill="{c}"/>')


def hop_right(parts, ax, y, tx, lane=LANE1):
    """From field centre ax in a bar whose top is y, over the top, into the left edge tx."""
    mid = y + BAR_H / 2
    poly_arrow(parts, [(ax, y), (ax, y - lane), (tx - 26, y - lane), (tx - 26, mid), (tx - 2, mid)], "right")


def hop_left(parts, ax, y, tx, lane=LANE1):
    """Mirror of hop_right: into the RIGHT edge tx of a bar to the left."""
    mid = y + BAR_H / 2
    poly_arrow(parts, [(ax, y), (ax, y - lane), (tx + 26, y - lane), (tx + 26, mid), (tx + 2, mid)], "left")


def next_down(parts, ex, y, b, next_name, y_to):
    """The *next link: out of the bottom of the next field, a short run left, straight
    down into the first byte of the identical struct below."""
    nx = ex + b.x_of(next_name, b.fields[next_name][1] / 2)
    run = y + BAR_H + NEXT_DROP
    poly_arrow(parts, [(nx, y + BAR_H), (nx, run), (ex + 6, run), (ex + 6, y_to - 1)], "down")


def under_left(parts, ax, y, tx):
    """From field centre ax, out of the bottom of the bar, left under the row, up into
    the bottom edge of a field centred at tx in a bar to the left. Planar with the *next
    chain because *next sits to the right of the field this leaves from."""
    lane = y + BAR_H + UNDER_LANE
    poly_arrow(parts, [(ax, y + BAR_H), (ax, lane), (tx, lane), (tx, y + BAR_H + 1)], "up")


def place(parts, b, x, y, labels, size=None, size_anchor="middle"):
    """A bar with its field labels and a size label under it (anchor 'start'/'end'
    keeps a wide label clear of arrows below the bar)."""
    parts.append(b.at(x, y))
    parts.append(outline(x, y, b.width, BAR_H))
    parts.append(label_fields(b, x, y, labels, callout_y=y - 6))
    if size:
        sx = {"middle": x + b.width / 2, "start": x, "end": x + b.width}[size_anchor]
        parts.append(text(sx, y + SIZE_DY, size, size=E.SIZE_PX, fill=C_MUTED, anchor=size_anchor))
    RIGHT[0] = max(RIGHT[0], x + b.width)


def names_above(parts, y, names):
    """Item names on the line above link 1; a name that would run into the next one
    moves up a line (as row() does with its badge lines)."""
    names = sorted(names)
    for i, (x, s) in enumerate(names):
        up = i + 1 < len(names) and x + len(s) * BADGE_CHAR > names[i + 1][0] - 4
        parts.append(text(x, y - (NAME_DY2 if up else NAME_DY), s, size=NAME_PX, fill=C_MUTED))
        RIGHT[0] = max(RIGHT[0], x + len(s) * BADGE_CHAR)


def chain_figure(frame: str, links: int = CHAIN_N, expires: bool = True) -> str:
    """frame a..e; `links` < CHAIN_N and `expires=False` give the scene-setting builds of
    frame a (one key, then the chain, then the second table). Canvas size is fixed."""
    HDR, NUL = E.sds_labels()
    val_lbl = {"v_hdr": HDR, "value": "value (16 B)", "v_nul": NUL}
    key_lbl = {"key_hdr": HDR, "key": "key (16 B)", "key_nul": NUL}
    slot = bar(SLOT, "dictSlot", {"entry": "pointer"})
    # fixed columns: the 64 B bucket of frame d sets where the object column starts, the
    # widest object (63 B, frames c/d; frame a's 36 B object + key string fit the same span)
    # sets where the expires column starts
    x_ent = PAD + slot.width + GAP
    x_obj = PAD + 64 * PPB + GAP
    x_exp = x_obj + 63 * PPB + GAP
    x_xent = x_exp + slot.width + GAP

    parts = svg_open()
    label = {"a": "Valkey 7.2", "b": "Valkey 8.0 \u2014 the key moves into the entry (PR 541)",
             "c": "the key moves on into the object \u2014 a step no release shipped",
             "d": "the expiry follows it \u2014 a step no release shipped",
             "e": "Valkey 8.1 \u2014 the chain becomes a bucket (PR 1186)"}[frame]
    parts.append(text(PAD, PAD + 12, label, size=13, weight="bold", fill=C_MUTED))
    y1 = PAD + 22 + NAME_DY2 + 12
    ys_all = [y1 + i * LINK_PITCH for i in range(CHAIN_N)]
    ys = ys_all[:links]
    last = ys[-1]

    if frame in "abcd":
        ksds = None
        if frame == "a":        # next: the key moves into the entry, so *key goes and the key body moves
            ent = bar(E.DICT_BEFORE, "dictEntry", E.DICT_BEFORE_ROLES, spot=("key",))
            ent_lbl = {"key": "*key", "v": "*value", "next": "*next"}
            obj = bar(robj_80(16), "robj80", ROBJ_80_ROLES)
            obj_lbl = {"header_bits": "robj", "ptr": "*value", **val_lbl}
            ksds = bar(E.sds5("keySds", 16), "keySds", E.SDS_ROLES, accent=("body",))
            xent = bar(EXPIRES_ENTRY, "expiresEntry", EXPIRES_ROLES)
            xent_lbl = {"key": "*key", "expire": "expiry", "next": "*next"}
        elif frame == "b":      # next: the key moves on into the object
            ent = bar(E.dict_after(16), "embeddedDictEntry", E.DICT_AFTER_ROLES, accent=("key",))
            ent_lbl = {"v": "*value", "next": "*next", **key_lbl}
            obj = bar(robj_80(16), "robj80", ROBJ_80_ROLES)
            obj_lbl = {"header_bits": "robj", "ptr": "*value", **val_lbl}
            xent = bar(EXPIRES_ENTRY, "expiresEntry", EXPIRES_ROLES)
            xent_lbl = {"key": "*key", "expire": "expiry", "next": "*next"}
        elif frame == "c":      # next: the expiry moves into the object, the expires *key goes
            ent = bar(ENTRY_C, "dictEntryC", ENTRY_C_ROLES)
            ent_lbl = {"v": "*value", "next": "*next"}
            obj = bar(robj_81(16, 16), "robj81", ROBJ_81_ROLES)
            obj_lbl = {"header_bits": "robj", "ptr": "*value", **key_lbl, "key_nul": "", **val_lbl}
            xent = bar(EXPIRES_ENTRY, "expiresEntry", EXPIRES_ROLES, spot=("key",), accent=("expire",))
            xent_lbl = {"key": "*key", "expire": "expiry", "next": "*next"}
        else:                   # next: the entries go altogether
            ent = bar(ENTRY_C, "dictEntryC", ENTRY_C_ROLES, spot=("v", "next"))
            ent_lbl = {"v": "*value", "next": "*next"}
            obj = bar(robj_81_ttl(16, 16), "robj81ttl", ROBJ_81_TTL_ROLES)
            obj_lbl = {"header_bits": "robj", "ptr": "*value", "expire": "expiry", **key_lbl, "key_nul": "",
                       **val_lbl}
            xent = bar(XENTRY_C, "expiresEntryC", XENTRY_C_ROLES, spot=("obj", "next"))
            xent_lbl = {"obj": "*object", "next": "*next"}
        x_key = x_obj + obj.width + GAP
        for i, y in enumerate(ys):
            bottom = y == last
            if i == 0:
                place(parts, slot, PAD, y, {"entry": ""}, "8 B")
                hop_right(parts, PAD + slot.width / 2, y, x_ent)
                if expires:
                    place(parts, slot, x_exp, y, {"entry": ""}, "8 B")
                    hop_right(parts, x_exp + slot.width / 2, y, x_xent)
            place(parts, ent, x_ent, y, ent_lbl, f"{ent.size} B" if bottom else None)
            place(parts, obj, x_obj, y, obj_lbl, f"{obj.size} B" if bottom else None)
            if expires:
                place(parts, xent, x_xent, y, xent_lbl, f"{xent.size} B" if bottom else None)
            hop_right(parts, x_ent + ent.x_of("v", 4), y, x_obj, LANE1)
            if ksds is not None:
                place(parts, ksds, x_key, y, {"hdr": HDR, "body": "key (16 B)", "nul": NUL},
                      f"{ksds.size} B" if bottom else None)
                hop_right(parts, x_ent + ent.x_of("key", 4), y, x_key, LANE2)
            if not expires:
                pass
            elif frame == "d":
                hop_left(parts, x_xent + xent.x_of("obj", 4), y, x_obj + obj.width, LANE2)
            else:   # the expires *key is the SAME key the keyspace holds (setExpire reuses it), never a copy
                kx = (x_key + ksds.x_of("body", 8) if frame == "a" else
                      x_ent + ent.x_of("key", 8) if frame == "b" else x_obj + obj.x_of("key", 8))
                under_left(parts, x_xent + xent.x_of("key", 4), y, kx)
            if not bottom:
                next_down(parts, x_ent, y, ent, "next", ys[i + 1])
                if expires:
                    next_down(parts, x_xent, y, xent, "next", ys[i + 1])
        names = [(PAD, "keyspace dict"), (x_ent, "dictEntry"), (x_obj, "object")]
        if expires:
            names += [(x_exp, "expires dict"), (x_xent, "dictEntry")]
        if ksds is not None:
            names.append((x_key, "key"))
        names_above(parts, y1, names)
    else:
        kb = bar(BUCKET7, "hashtableBucket7", BUCKET7_ROLES)
        bl = {"meta": "", "hashes": "hashes", **{f"e{i}": "" for i in range(7)}}
        obj = bar(robj_81_ttl(16, 16), "robj81ttl", ROBJ_81_TTL_ROLES)
        obj_lbl = {"header_bits": "robj", "ptr": "*value", "expire": "expiry", **key_lbl, "key_nul": "", **val_lbl}
        place(parts, kb, PAD, y1, bl, "64 B / bucket", size_anchor="start")
        place(parts, kb, x_exp, y1, {**bl, "hashes": ""}, "64 B / bucket", size_anchor="end")   # e0's arrow rises here
        for y in ys:
            place(parts, obj, x_obj, y, obj_lbl, f"{obj.size} B" if y == last else None)
        # nearest slot -> top object over the lane; the others drop below the bucket and
        # run in, the further slot to the lower object so nothing crosses
        hop_right(parts, PAD + kb.x_of("e6", 4), y1, x_obj)
        hop_left(parts, x_exp + kb.x_of("e0", 4), y1, x_obj + obj.width)
        for slot_name, y in (("e5", ys[1]), ("e4", ys[2])):
            ax = PAD + kb.x_of(slot_name, 4)
            poly_arrow(parts, [(ax, y1 + BAR_H), (ax, y + BAR_H / 2), (x_obj - 2, y + BAR_H / 2)], "right")
        for slot_name, y in (("e1", ys[1]), ("e2", ys[2])):
            ax = x_exp + kb.x_of(slot_name, 4)
            poly_arrow(parts, [(ax, y1 + BAR_H), (ax, y + BAR_H / 2), (x_obj + obj.width + 2, y + BAR_H / 2)], "left")
        names_above(parts, y1, [(PAD, "keyspace hashtable"), (x_obj, "object"), (x_exp, "expires hashtable")])
    RIGHT[0] = max(RIGHT[0], x_exp + 64 * PPB + 20)   # same canvas in every frame (frame e is the widest)
    y = ys_all[-1] + SIZE_DY + 26          # same height whatever the build shows
    y = legend(parts, y, CHAIN_LEGEND)
    return finish(parts, y, wmax=CHAIN_W)


CHAIN_CAPTION = """
## H6 — The collision chain, five frames (fig-ht-6a..e) plus two builds of a (6a1, 6a2)

Builds: **a1** one key in the keyspace dict (slot → dictEntry → object, → key string), **a2**
the slot's chain of three colliding keys, **a** adds the expires dict with its own chain.

One table slot whose chain holds three colliding keys (16 B key, 16 B value, each with a
TTL); keyspace on the left, expires table on the right. The frames keep every column in
place so the slides can reveal one change at a time. Counting allocations for the three
keys (tables excluded):

- **a — Valkey 7.2.** dictEntry {*key, *value, *next} 24 B → value object 36 B, → key
  string 18 B; the expires dict has its own dictEntry {*key, expiry, *next} 24 B per key.
  Four allocations per key: **12**.
- **b — Valkey 8.0, PR 541.** The key moves into the dictEntry (35 B). Three per key: **9**.
- **c — no release.** The key moves on into the value object (55 B: the real 8.1 object for
  a key without a TTL); the keyspace entry is down to {*value, *next} 16 B. Still **9**, and
  the same bytes: this step rearranges, it does not save.
- **d — no release.** The expiry follows the key into the object (63 B); the expires entry
  is down to {*object, *next} 16 B and its own *key pointer is gone. Still **9**, still the
  same bytes. c and d never shipped — PR 1186 did b → e in one step — they are here so
  that by e every entry is nothing but two pointers, which is what makes it deletable.
- **e — Valkey 8.1, PR 1186.** The chain of two-pointer nodes becomes one 64 B bucket
  (7 slots, a hash byte each, one cache line) in each table. One per key: **3**, plus the
  two shared buckets. Collisions still chain (a full bucket links a child bucket), but a
  link now holds seven entries instead of one, and the table resizes so chains rarely form.

The expires entry's *key is never a copy: setExpire reuses the keyspace key (db.c "Reuse the
sds from the main dict in the expire dict"; the expires dict type has no key dup or
destructor). In 7.2 it points at the shared key string, in 8.0 into the key embedded in
the keyspace dictEntry (dictGetKey returns &key_buf[hdr]), in frame c into the key inside
the object. The frames draw it as the arrow running under the row; it disappears in d.

Spoken color key on frame a: orange is the pointer the next step removes, periwinkle the
data the next step moves; everything grey stays as it is. Frame e has nothing left to
highlight. The *next chain drops out of the bottom of each entry into the first byte of
the one below; the tables are not drawn as arrays (say it: a slot in an array of slots, a
bucket in an array of buckets).
"""

CAPTION = """# Hashtable figures — slide text

## H1 — One key's path: dict vs hashtable (fig-ht-1-path)

Keyspace, 16-byte key, 16-byte value. Before (Valkey 8.0, after PR 541): dict pointer
table slot → dictEntry (35 B, own allocation, key embedded, chained via *next) → value
object (36 B: robj header, a pointer, and the value string embedded right behind it):
three memory fetches. After (Valkey 8.1, PR 1186): 64 B bucket (one cache line, 7 entries
with a hash byte each) → one object holding key and value (55 B): two fetches, one
allocation fewer. Orange is the pointers a lookup follows; the dict's pointer table and
the dictEntry go away, the key moves into the object. The object's own *value pointer
(grey) points a few bytes further into the same allocation, so following it is not a fetch.

Speaker note (the number): measured index cost per entry (Rimuru, 5M entries, settled) is
~37 B with dict and ~15 B with the hashtable, the same 15 B on every workload. The table
itself did not get cheaper (~12 B of pointer slots became ~15 B of bucket share); the
per-entry allocation is what went away. Say it while the dictEntry is orange; do not put
the number on the slide.

Measured at 16 B key / 16 B value (Rimuru, set-k16-v16, settled): 93 → 71 B per key, −22.5.
(The earlier −29 was measured mid-rehash, with both dict tables allocated.)

## H1 (three rows) — One string key across releases (fig-ht-1-path-3)

Same as above, plus Valkey 9.1 (PR 2516): the value pointer inside the object goes too
(55 → 47 B). Three fetches and three allocations per key (besides the table) in 8.0; two
fetches and one allocation from 8.1 on. Orange in each row is the pointers a lookup
follows: two, one, one. Perf aside: every circled number is a trip to memory. For values
over 44 B the value was a separate allocation until 9.2 (PR 3397, fig 5), which is where
the 4 → 3 → 2 version of this slide applies.

## H4 — Where the hashtable was applied (slide table, no figure)

All four conversions shipped in Valkey 8.1 (verified: commits are ancestors of 8.1.0 and
not of 8.0.0). Deltas are Rimuru's measured bytes per entry, 8.0 → 8.1, SETTLED (dict
finished rehashing), at 16 B key / 16 B value, 20 B members, 16 B field / 16 B value.

| Data type | PR | The hashtable entry is… | What the dict entry was | Δ per entry |
|---|---|---|---|---|
| Keyspace (keys, expires, pubsub) | 1186 | the value object, key embedded (`robj`) | 35 B embedded-key entry (PR 541) | −22.5 B (−37 B with TTL) |
| Sorted set | 1427 | the skiplist node (`zskiplistNode`) | 24 B `dictEntry` | −22.5 B |
| Hash | 1502 | `hashTypeEntry`: field embedded, value pointer | 24 B `dictEntry` | −6.5 B |
| Set | 1176 | the member string itself (`sds`) | 16 B no-value entry | −2.5 B |

Why the deltas differ: the index cost after conversion is the same ~15 B per entry for every
type; what differed was how big the dict entry being deleted was (16, 24 or 35 B). The set
barely moves because its no-value dict entry (16 B, in a 16 B class) was already the member
pointer and nothing else; the hash gains least of the rest because PR 1502 kept a value
pointer. Speaker line: "Same trick, four places, one release; the saving is the entry you
no longer allocate."

## H5 — Keys with a TTL (fig-ht-5a-ttl-before + fig-ht-5b-ttl-after; fig-ht-5-ttl is both stacked)

Before (Valkey 8.0): a key with an expiry lives in two dicts. The keyspace dict has the
embedded-key dictEntry (35 B) pointing at the value object (36 B, value embedded); the
expires dict has a second dictEntry (24 B) whose *key points at the key inside the first
one and whose value is the expiry. Two pointer tables, two entry allocations. After
(Valkey 8.1, PR 1186): the expires table is still a separate hashtable, but both tables
point at the same object, and the expiry is an 8 B field inside it (63 B object: header,
pointer, expiry, key, value). Two bucket shares, zero entry allocations: index cost per
volatile key 98 → 30 B, the object 36 → 63 B, net −37 B per key (Rimuru, settled, 16 B values) vs −22.5 B
without a TTL. Orange follows the expiry from its own entry into the object.
"""


def build_all(outdir: pathlib.Path):
    for name, three in (("fig-ht-1-path.svg", False), ("fig-ht-1-path-3.svg", True)):
        (outdir / name).write_text(path_figure(three))
        print("wrote", name)
    for name, part in (("fig-ht-5-ttl.svg", "both"), ("fig-ht-5a-ttl-before.svg", "before"),
                       ("fig-ht-5b-ttl-after.svg", "after")):
        (outdir / name).write_text(ttl_figure(part))
        print("wrote", name)
    builds = [("a1", dict(frame="a", links=1, expires=False)), ("a2", dict(frame="a", expires=False))]
    builds += [(f, dict(frame=f)) for f in "abcde"]
    for tag, kw in builds:
        name = f"fig-ht-6{tag}-chain.svg"
        (outdir / name).write_text(chain_figure(**kw))
        print("wrote", name)
    (outdir / "captions.md").write_text(CAPTION + CHAIN_CAPTION)
    print("wrote captions.md")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--scheme" in args:
        i = args.index("--scheme"); E.SCHEME = E.SCHEMES[args[i + 1]]; del args[i:i + 2]
    if "--no-legend" in args:
        E.SHOW_LEGEND = False; args.remove("--no-legend")
    if "--no-sds-callouts" in args:
        E.SDS_CALLOUTS = False; args.remove("--no-sds-callouts")
    if "--with-text" in args:
        E.FIGURE_TEXT = True; args.remove("--with-text")
    outdir = pathlib.Path(args[0] if args else HERE / "figures")
    outdir.mkdir(parents=True, exist_ok=True)
    build_all(outdir)
