#!/usr/bin/env python3
"""Before/after struct figures for the "simple embedding" memory changes in Valkey:
two allocations, one pointing at the other, folded into one allocation and the
8-byte pointer dropped.

Same design language as the fbtree blog (fbtree-blog/): every box is a real C
struct laid out by the compiler through fieldday and colored by role -- brand
blue `role-data`, orange `role-pointer`, slate `role-overhead`. None of these
layouts has padding, so the legend carries no padding swatch. The 3-byte sds
header is always called out as "string hdr" (the blog's fig 4 wording).
Nothing here types a byte count. Titles are computed from the probes.

Each figure = one SVG, 720 px column:
  BEFORE row : struct box (with the orange pointer field) --arrow--> separately
               allocated payload box (its own sds header = the second allocation)
  AFTER  row : one box; pointer gone; payload embedded.

The four changes, with the commit each "before"/"after" is taken from:
  1. PR 541  (8faf2788a)  key embedded into the dict entry
  2. PR 1579 (52c55d7e3)  hash value embedded in the hash-type entry
  3. PR 2508 (33bfac37b)  zset member embedded in the skiplist node
  4. PR 2516 (0ee423450)  embstr: the robj's value pointer is dropped (key + value
                          already embedded; a flag says the value follows the key)

Usage: embed_figures.py <outdir>
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "lib"))   # fdbars; fieldday comes from pip (requirements.txt)
from fdbars import Bar, FD_DEFS, FONT, C_TEXT, C_MUTED, C_LINE, theme, strip_tail_padding  # noqa: E402

HERE = pathlib.Path(__file__).parent
W = 720            # valkey.io column
PPB = 6.0          # px per byte -- small structs, so draw big
BAR_H = 44
GAP = 34           # px between the two allocations in the BEFORE row (room for the arrow shaft)
ROW_GAP = 34       # vertical gap between rows
PAD = 16

# ---------------------------------------------------------------- probes
# Payload sizes drawn (stated in captions): 16-byte key, 16-byte field and value,
# 20-byte member, 64-byte value for the threshold figure. sds bodies are spelled
# out so the compiler lays out the whole allocation. Header sizes follow
# sdsReqType(): a string under 32 B gets the 1-byte sdshdr5 (flags carry the
# length); the embedded VALUE of a string object is forced to sdshdr8 (3 B: len,
# alloc, flags) so it can be resized in place. Where an embedded sds is prefixed
# by its 1-byte header-size byte, that byte is lumped into the header block
# (char[2] for an sds5 key/member). Verified against object.c
# createEmbeddedStringObjectWithKeyAndExpire, dict.c createEmbeddedEntry (8.0),
# t_zset.c zslCreateNode (9.1), t_hash.c (8.1) / entry.c (9.x).

def sds8(name: str, n: int) -> str:
    """A separately allocated sdshdr8 string of n bytes: header, body, NUL."""
    return f"""
struct {name} {{
    char hdr[3];
    char body[{n}];
    char nul;
}};
"""


def sds5(name: str, n: int) -> str:
    """A separately allocated sdshdr5 string (n < 32): 1 B header, body, NUL."""
    assert n < 32, "sds5 only holds strings shorter than 32 B"
    return f"""
struct {name} {{
    char hdr[1];
    char body[{n}];
    char nul;
}};
"""

SDS_ROLES = {"hdr": "overhead", "body": "data", "nul": "overhead"}

# ---- 1. dict entry key embed (PR 541) ---------------------------------------
# before: dictEntry {key*, v, next*} + separate key sds (16 B)
DICT_BEFORE = """
struct dictEntry {
    void *key;
    union { void *val; uint64_t u64; int64_t s64; double d; } v;
    struct dictEntry *next;
};
"""
DICT_BEFORE_ROLES = {"key": "pointer", "v": "pointer", "next": "pointer"}
# after: embeddedDictEntry {v, next*, key_header_size, key_buf[]} -- the key
# sds (1 B hdr size + sdshdr5 + 16 B + NUL) lives in key_buf; no key pointer.
def dict_after(key_len: int = 16) -> str:
    return f"""
struct embeddedDictEntry {{
    union {{ void *val; uint64_t u64; int64_t s64; double d; }} v;
    struct dictEntry *next;
    char key_hdr[2];
    char key[{key_len}];
    char key_nul;
}};
"""
DICT_AFTER_ROLES = {"v": "pointer", "next": "pointer", "key_hdr": "overhead",
                    "key": "data", "key_nul": "overhead"}

# ---- 2. hash entry value embed (PR 1579) ------------------------------------
# before (8.1 t_hash.c): struct hashTypeEntry { sds value; char field_offset;
# char field_data[]; } -- sizeof() is 16 because field_offset is padded out to the
# pointer boundary, and zmalloc(sizeof + field sds) keeps that padding. Then the
# field as sdshdr5. 16 + 1 + 16 + 1 = 34 B, plus the separate value sds.
def hash_before(field_len: int = 16) -> str:
    return f"""
struct hashEntryBefore {{
    void *value_ptr;
    char field_offset;
    char pad[7];
    char f_hdr[1];
    char field[{field_len}];
    char f_nul;
}};
"""
HASH_BEFORE_ROLES = {"value_ptr": "pointer", "field_offset": "overhead", "pad": "overhead",
                     "f_hdr": "overhead", "field": "data", "f_nul": "overhead"}
# after (PR 1579): [field sdshdr5 "field" \0][value sdshdr8 "value" \0], one
# allocation; the entry pointer IS the field sds. 1 + 16 + 1 + 3 + 16 + 1 = 38 B.
def hash_after(field_len: int = 16, value_len: int = 16) -> str:
    return f"""
struct hashEntryAfter {{
    char f_hdr[1];
    char field[{field_len}];
    char f_nul;
    char v_hdr[3];
    char value[{value_len}];
    char v_nul;
}};
"""
HASH_AFTER_ROLES = {"f_hdr": "overhead", "field": "data", "f_nul": "overhead",
                    "v_hdr": "overhead", "value": "data", "v_nul": "overhead"}

# ---- 3. zset member embed (PR 2508) -----------------------------------------
# before: zskiplistNode {ele*, score, backward, level[1]} + separate member sds
ZSL_BEFORE = """
struct zskiplistNodeBefore {
    char *ele;
    double score;
    struct zskiplistNodeBefore *backward;
    struct zskiplistNodeBefore *forward_1; unsigned long span_1;
};
"""
ZSL_BEFORE_ROLES = {"ele": "pointer", "score": "data", "backward": "pointer",
                    "forward_1": "pointer", "span_1": "overhead"}
# after: score, backward, level[1], then 1 B sds-hdr-size + sdshdr5 + member + NUL
def zsl_after(member_len: int = 20) -> str:
    return f"""
struct zskiplistNodeAfter {{
    double score;
    struct zskiplistNodeAfter *backward;
    struct zskiplistNodeAfter *forward_1; unsigned long span_1;
    char ele_hdr[2];
    char ele[{member_len}];
    char ele_nul;
}};
"""
ZSL_AFTER_ROLES = {"score": "data", "backward": "pointer", "forward_1": "pointer",
                   "span_1": "overhead", "ele_hdr": "overhead", "ele": "data",
                   "ele_nul": "overhead"}

# ---- 4. embstr ptr slot (PR 2516) -------------------------------------------
# A key's value object in 9.x embeds the key (PR 1186) and, for a small string,
# the value too -- so it was ALREADY one allocation: robj header, the value
# pointer, [1 B key sds-hdr size + key sds], then the value sds. The waste was
# that the robj still spent 8 B on a pointer to a value a few bytes further on.
# Layout per createEmbeddedStringObjectWithKeyAndExpire (no expire field).
def robj_before(key_len: int = 16, value_len: int = 20) -> str:
    return f"""
struct robjBefore {{
    uint64_t header_bits;
    void *ptr;
    char key_hdr[2];
    char key[{key_len}];
    char k_nul;
    char v_hdr[3];
    char value[{value_len}];
    char v_nul;
}};
"""
ROBJ_BEFORE_ROLES = {"header_bits": "overhead", "ptr": "pointer", "key_hdr": "overhead",
                     "key": "data", "k_nul": "overhead",
                     "v_hdr": "overhead", "value": "data", "v_nul": "overhead"}
# after: the pointer slot is dropped (hasembval flag instead); key and value
# shift up 8 B and the value is found by walking past the key.
def robj_after(key_len: int = 16, value_len: int = 20) -> str:
    return f"""
struct robjAfter {{
    uint64_t header_bits;
    char key_hdr[2];
    char key[{key_len}];
    char k_nul;
    char v_hdr[3];
    char value[{value_len}];
    char v_nul;
}};
"""
ROBJ_AFTER_ROLES = {k: v for k, v in ROBJ_BEFORE_ROLES.items() if k != "ptr"}

# ---- 5. embedding threshold 64 -> 128 B (PR 3397) ---------------------------
# shouldEmbedStringObject() sums the WHOLE object -- robj header (minus the
# reusable pointer slot), the embedded key, the value sds -- and embeds when
# that is <= the limit. A 16 B key + 64 B value object is 95 B: over the old
# 64 B limit (RAW: value in its own allocation behind val_ptr, per
# createUnembeddedObjectWithKeyAndExpire), under the new 128 B one (embedded,
# same layout as robjAfter). No expire field drawn.
def raw_before(key_len: int = 16) -> str:
    return f"""
struct robjRaw {{
    uint64_t header_bits;
    void *val_ptr;
    char key_hdr[2];
    char key[{key_len}];
    char k_nul;
}};
"""
RAW_BEFORE_ROLES = {"header_bits": "overhead", "val_ptr": "pointer", "key_hdr": "overhead",
                    "key": "data", "k_nul": "overhead"}


# ------------------------------------------------------------- composition
def text(x, y, s, size=13, weight="normal", fill=None, anchor="start"):
    fill = fill or C_TEXT
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{s}</text>')


def outline(x, y, w, h):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="none" stroke="{C_LINE}" stroke-width="1.2"/>')


def arrow_color() -> str:
    return SCHEME["highlight"] if SPOTLIGHT else theme("role-pointer")


def arrow(x1, y1, x2, y2):
    c = arrow_color()
    return (f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" stroke="{c}" stroke-width="2" '
            f'fill="none" marker-end="url(#arrowhead)"/>')


def arrow_defs() -> str:
    return (f'<marker id="arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="4" '
            f'orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{arrow_color()}"/></marker>')


def size_label(x, w, y, n):
    return text(x + w / 2, y, f"{n} B", size=SIZE_PX, fill=C_MUTED, anchor="middle")


MIN_INBOX_PX = 30   # a field narrower than this gets a callout above instead
INBOX_PX = 11       # cap for in-box field labels (shrink-to-fit below this, floor 8)
CHAR_PX = 6.3       # approx advance of the mono theme font at 10.5 px (Fira Mono and DejaVu Sans Mono both ~0.6 em)
CALLOUT_ROW = 12    # px between the two callout rows (second row is used only on collision)
# Slide readability: text outside the bars is lifted (a 720 px canvas on a 12 in slide puts
# 13 px at ~15.6 pt); in-box field labels stay at 10.5 px since a wider font needs a wider bar.
SIZE_PX = 13        # "37 B" under a bar
LEGEND_PX = 13
CALLOUT_PX = 11     # field callouts above a bar (10.5 under DejaVu; Fira Mono's x-height is ~5% lower)


def label_fields(b: Bar, x0: float, y0: float, relabel: dict | None = None,
                 callout_y: float | None = None, merge: dict | None = None,
                 rows: list | None = None, avoid_x: float | None = None) -> str:
    """Field names positioned from the compiler-probed offsets. Wide fields get
    a white in-box label (multi-line via '\\n', as the blog's fig 4), shrunk to
    fit the box. Consecutive narrow fields (sds header bytes) are MERGED into
    one callout so their labels never collide; a lone narrow field (NUL) gets
    its own callout. `merge` maps a run of field names -> one label:
        merge={("len","alloc","flags"): "sds hdr"}
    Padding is never labeled.
    Callouts are placed first-fit on two rows; `rows` (right edge per row) may be
    shared between the bars of one row so labels never collide across bars.
    `avoid_x` is the x of the pointer arrow's vertical rise: a callout label that
    would sit under it is nudged right (its tick still marks the field)."""
    relabel = relabel or {}
    merge = merge or {}
    out = []
    cy = callout_y if callout_y is not None else y0 - 8
    if rows is None:
        rows = [-1e9, -1e9]   # right edge of the last label on each callout row
    fields = [f for f in b.layout.fields if not f.is_padding]
    # build merge groups: name -> (group_start_offset, group_size, label)
    grouped = {}
    for names, lbl in merge.items():
        fs = [f for f in fields if f.name in names]
        if fs:
            start = min(f.offset for f in fs)
            end = max(f.offset + f.size for f in fs)
            for f in fs:
                grouped[f.name] = (start, end - start, lbl)
    done_groups = set()
    for f in fields:
        if f.name in grouped:
            start, size, lbl = grouped[f.name]
            if (start, size) in done_groups:
                continue
            done_groups.add((start, size))
            fx, fw, name = x0 + start * b.ppb, size * b.ppb, lbl
        else:
            name = relabel.get(f.name, f.name)
            if not name:
                continue
            fx, fw = x0 + f.offset * b.ppb, f.size * b.ppb
        cx = fx + fw / 2
        lines = name.split("\n")
        if fw >= MIN_INBOX_PX:
            longest = max(len(ln) for ln in lines)
            # shrink to fit the box width, floor at 8px
            fs = min(INBOX_PX, max(8.0, (fw - 6) / (longest * (CHAR_PX / 10.5))))
            lh = fs + 1
            total = lh * len(lines)
            ty = y0 + b.height / 2 - total / 2 + fs * 0.85
            role = b.layout.roles.get(f.name)
            ink = (SCHEME["text_on_highlight"] if role in ("pointer", "data") else SCHEME["text_on_rest"]) \
                if SPOTLIGHT else "#ffffff"
            for ln in lines:
                out.append(text(cx, ty, ln, size=fs, fill=ink, anchor="middle"))
                ty += lh
        else:
            # keep the label inside the canvas; the tick above still marks the field.
            # A callout that would overlap the previous one moves up one row.
            lbl = " ".join(lines)
            hw = len(lbl) * CALLOUT_PX * (CHAR_PX / 10.5) / 2
            lx = cx
            if avoid_x is not None and lx - hw < avoid_x + 3 and lx + hw > avoid_x - 3:
                lx = avoid_x + 3 + hw
            lx = min(max(lx, hw + 2), W - hw - 2)
            for i, right in enumerate(rows):
                if lx - hw >= right + 10:
                    break
            else:
                i = len(rows) - 1          # nothing fits: top row, and accept it
            rows[i] = lx + hw
            row_y = cy - i * CALLOUT_ROW
            out.append(f'<path d="M{cx:.1f},{y0:.1f} L{cx:.1f},{row_y + 3:.1f}" stroke="{C_LINE}" '
                       f'stroke-width="0.8" fill="none"/>')
            out.append(text(lx, row_y, lbl, size=CALLOUT_PX, fill=C_TEXT, anchor="middle"))
    return "\n".join(out)


def arrow_lane(rows) -> float:
    """Height above a bar's top for the over-the-top arrow: just clear of the
    callout rows in use (row 1 baseline at y-6, row 2 at y-6-CALLOUT_ROW)."""
    two_rows = rows is not None and rows[1] > -1e8
    return 20 + (CALLOUT_ROW if two_rows else 0)


def wrap(s: str, width: int = 88) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def pair_figure(title: str, subtitle: str,
                before_struct: Bar, before_payload: Bar | None, ptr_member: str,
                after_struct: Bar, before_note: str, after_note: str,
                ptr_target: str | None = None,
                before_labels: dict | None = None, payload_labels: dict | None = None,
                after_labels: dict | None = None,
                before_merge: dict | None = None, payload_merge: dict | None = None,
                after_merge: dict | None = None, saving_text: str | None = None) -> str:
    """Compose one before/after figure.
    Two-allocation before: before_payload is the separately allocated thing the
    pointer points at (drawn as a second box with an arrow to it).
    One-allocation before: before_payload=None and ptr_target names the member
    inside before_struct the pointer points at (arrow curls within the box).
    *_labels are relabel maps (field name -> display text; '' hides)."""
    before_total = before_struct.size + (before_payload.size if before_payload else 0)
    saving = before_total - after_struct.size
    CALLOUT_H = 18 + CALLOUT_ROW   # headroom above each bar for two rows of callouts
    ARROW_LANE = 14     # extra headroom for the over-the-top pointer arrow (before row)
    y = PAD
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" '
             f'viewBox="0 0 {W} {{H}}" font-family="{FONT}">',
             f"<defs>{FD_DEFS}{arrow_defs()}</defs>",
             f'<rect width="{W}" height="{{H}}" fill="{theme("background")}"/>']

    # title + subtitle (computed saving) -- drawn only with FIGURE_TEXT; always
    # recorded for captions.md so the slide text can quote the computed numbers
    saving_line = saving_text or f"{saving} B saved per entry"
    CAPTIONS.append(f"## {title}\n\n{subtitle} \u2014 {saving_line}\n\n"
                    f"- Before ({before_total} B): {before_note}\n"
                    f"- After ({after_struct.size} B): {after_note}\n")
    if FIGURE_TEXT:
        y += 18
        parts.append(text(PAD, y, title, size=16, weight="bold"))
        y += 20
        parts.append(text(PAD, y, subtitle + "  \u2014  " + saving_line, size=12, fill=C_MUTED))
        y += 22

    def note(y_, s):
        if not FIGURE_TEXT:
            return y_ - 6       # no sentence: tighten the gap below the size label
        yy = y_
        for ln in wrap(s):
            parts.append(text(PAD, yy, ln, size=11, fill=C_MUTED))
            yy += 14
        return yy

    # ---- BEFORE row -- headroom measured from the callouts this row will use
    parts.append(text(PAD, y + 12, "Before", size=13, weight="bold", fill=C_MUTED))
    bx = PAD
    probe = [-1e9, -1e9]
    ax0 = bx + before_struct.x_of(ptr_member) + before_struct.bytes_of(ptr_member) * PPB / 2
    label_fields(before_struct, bx, 0, before_labels, callout_y=-6, merge=before_merge, rows=probe, avoid_x=ax0)
    if before_payload is not None:
        px0 = bx + before_struct.width + GAP
        label_fields(before_payload, px0, 0, payload_labels, callout_y=-6, merge=payload_merge,
                     rows=probe, avoid_x=px0 - GAP + 6)
    y += 22 + arrow_lane(probe) + 6
    parts.append(before_struct.at(bx, y))
    parts.append(outline(bx, y, before_struct.width, BAR_H))
    ax = bx + before_struct.x_of(ptr_member) + before_struct.bytes_of(ptr_member) * PPB / 2
    rows = [-1e9, -1e9]
    parts.append(label_fields(before_struct, bx, y, before_labels, callout_y=y - 6, merge=before_merge,
                              rows=rows, avoid_x=ax))
    parts.append(size_label(bx, before_struct.width, y + BAR_H + 14, before_struct.size))
    c = arrow_color()
    if before_payload is not None:
        px = bx + before_struct.width + GAP
        dx = bx + before_struct.width + 6      # x of the arrow's descending stroke
        parts.append(before_payload.at(px, y))
        parts.append(outline(px, y, before_payload.width, BAR_H))
        parts.append(label_fields(before_payload, px, y, payload_labels, callout_y=y - 6, merge=payload_merge,
                                  rows=rows, avoid_x=dx))
        parts.append(size_label(px, before_payload.width, y + BAR_H + 14, before_payload.size))
        # arrow goes OVER the bar (not through the labels): up out of the pointer
        # field, across a lane just above the callout rows actually in use, down
        # just past the source struct, then a clear horizontal shaft across the
        # gap into the payload's left edge -- the corner turn stays visible
        top = y - arrow_lane(rows)
        mid = y + BAR_H / 2
        parts.append(f'<path d="M{ax:.1f},{y:.1f} L{ax:.1f},{top:.1f} L{dx:.1f},{top:.1f} L{dx:.1f},{mid:.1f} L{px - 2:.1f},{mid:.1f}" '
                     f'stroke="{c}" stroke-width="2" fill="none" marker-end="url(#arrowhead)"/>')
    else:
        # same over-the-top route as the two-allocation case, landing on the
        # box's top edge at the target member (caller must leave that spot
        # free of callouts -- see fig 4, whose header labels live in AFTER only)
        tx = bx + before_struct.x_of(ptr_target)
        top = y - arrow_lane(rows)
        parts.append(f'<path d="M{ax:.1f},{y:.1f} L{ax:.1f},{top:.1f} L{tx:.1f},{top:.1f} L{tx:.1f},{y - 2:.1f}" '
                     f'stroke="{c}" stroke-width="2" fill="none" marker-end="url(#arrowhead)"/>')
    y = note(y + BAR_H + 32, before_note) + ROW_GAP - 14

    # ---- AFTER row
    parts.append(text(PAD, y + 12, "After", size=13, weight="bold", fill=C_MUTED))
    probe = [-1e9, -1e9]
    label_fields(after_struct, bx, 0, after_labels, callout_y=-6, merge=after_merge, rows=probe)
    used = 2 if probe[1] > -1e8 else (1 if probe[0] > -1e8 else 0)
    y += 22 + {0: 4, 1: 16, 2: 28}[used] + 4
    parts.append(after_struct.at(bx, y))
    parts.append(outline(bx, y, after_struct.width, BAR_H))
    parts.append(label_fields(after_struct, bx, y, after_labels, callout_y=y - 6, merge=after_merge))
    parts.append(size_label(bx, after_struct.width, y + BAR_H + 14, after_struct.size))
    y = note(y + BAR_H + 32, after_note) + (6 if FIGURE_TEXT else -3)

    # legend (fieldday roles, so it can never drift from the bars). No padding
    # swatch: none of these layouts has any, so advertising it would mislead.
    if SHOW_LEGEND:
        lx = PAD
        for role, label in LEGEND:
            parts.append(f'<rect x="{lx}" y="{y}" width="12" height="12" fill="{swatch(role)}"/>')
            parts.append(text(lx + 17, y + 10, label, size=LEGEND_PX, fill=C_MUTED))
            lx += 17 + 8 * len(label) + 22
        y += 12
    y += PAD

    parts.append("</svg>")
    return "\n".join(parts).replace("{H}", str(int(y)))


def bar(snippet, struct, roles, byte_sized=True, spot=()):
    """spot: member names that keep the highlight 'pointer' role in SPOTLIGHT
    mode (the pointer the change removes). Everything else takes the scheme's
    'rest' color so the eye goes to the one field that disappears between
    BEFORE and AFTER."""
    if SPOTLIGHT:
        roles = {k: ("pointer" if k in spot else "overhead") for k in roles}
    return Bar(snippet, struct, roles, PPB, BAR_H, border=C_LINE, byte_sized=byte_sized,
               min_divider_px=PPB + 1,   # a char[] draws as one solid block
               theme={"role-pointer": SCHEME["highlight"], "role-overhead": SCHEME["rest"],
                      "role-data": SCHEME["rest"]})


# True: highlight only the removed pointer, shade the rest (talk version).
# False: full role coloring (blue data / orange pointers / slate overhead), as the blog.
SPOTLIGHT = True

# False (slide version): no title, subtitle or explainer sentences in the SVG --
# the slide carries those. The text is still composed and written to
# captions.md beside the figures. True (--with-text): draw it in the figure.
FIGURE_TEXT = False
CAPTIONS: list[str] = []

# False (--no-legend): omit the legend row -- for a run of these figures on
# consecutive slides, where the first one has taught what orange means.
SHOW_LEGEND = True

# False (--no-sds-callouts): drop the "string header" / "NUL" callouts above the
# 1-2 B sds header and terminator slivers. They are not part of any slide's
# story, and they are the labels that stack two rows deep (figs 4, 5, H5b) or
# spill past the bar's left edge (fig 2 after). The slivers stay drawn,
# unlabeled; the speaker names them once.
SDS_CALLOUTS = True


def sds_labels() -> tuple[str, str]:
    """(header label, NUL label) honouring SDS_CALLOUTS; '' suppresses a callout."""
    return ("string header", "NUL") if SDS_CALLOUTS else ("", "")


# Spotlight palettes: highlight = the removed pointer (also the arrow), rest =
# every other field, text_on_rest / text_on_highlight = in-box label colors.
SCHEMES = {
    # fieldday's own orange + slate, white labels (what the blog uses)
    "slate":      dict(highlight="#e07b39", rest="#9aa7b5", text_on_rest="#ffffff", text_on_highlight="#ffffff"),
    # same orange, but a light neutral grey so the orange carries the figure
    "lightgrey":  dict(highlight="#e07b39", rest="#dde2e8", text_on_rest="#3a4550", text_on_highlight="#ffffff"),
    # copper highlight on a pale periwinkle field
    "copper":     dict(highlight="#b87333", rest="#cfd2f5", text_on_rest="#2f3470", text_on_highlight="#ffffff"),
    # periwinkle highlight on light grey (cool, no orange at all)
    "periwinkle": dict(highlight="#7b86e6", rest="#e1e5ea", text_on_rest="#3a4550", text_on_highlight="#ffffff"),
    # fieldday's orange on a pale tint of Valkey's brand blue (#6983ff, fieldday role-data)
    "valkey":     dict(highlight="#e07b39", rest="#d2daff", text_on_rest="#2b3270", text_on_highlight="#ffffff"),
}
SCHEME = SCHEMES["lightgrey"]
LEGEND = ((("highlight", "the pointer that goes away"), ("rest", "everything else"))
          if SPOTLIGHT else
          (("role-data", "user data"), ("role-pointer", "pointer"), ("role-overhead", "overhead")))


def swatch(key: str) -> str:
    """Legend / arrow color: a raw '#rrggbb', a scheme key, or a fieldday role."""
    if key.startswith("#"):
        return key
    return SCHEME[key] if key in SCHEME else theme(key)


def build_all(outdir: pathlib.Path):
    out = {}
    HDR, NUL = sds_labels()
    SDS_LBL = {"hdr": HDR, "body": None, "nul": NUL}

    # 1. dict key embed
    b = bar(DICT_BEFORE, "dictEntry", DICT_BEFORE_ROLES, byte_sized=False, spot=("key",))
    p = bar(sds5("keySds", 16), "keySds", SDS_ROLES)
    a = bar(dict_after(16), "embeddedDictEntry", DICT_AFTER_ROLES)
    out["fig-embed-1-dict-key.svg"] = pair_figure(
        "Keyspace entry: the key moves into the dict entry",
        "Valkey 8.0, PR 541 \u2014 16-byte key",
        b, p, "key", a,
        "dictEntry holds a pointer to a separately allocated key sds (two allocations).",
        "The key sds is stored inside the entry. The 8 B key pointer is gone; 1 B records the key\u2019s sds header size.",
        before_labels={"key": "*key", "v": "value", "next": "*next"},
        payload_labels={**SDS_LBL, "body": "key (16 B)"},
        after_labels={"v": "value", "next": "*next", "key_hdr": HDR, "key": "key (16 B)", "key_nul": NUL})

    # 2. hash value embed
    b = bar(hash_before(16), "hashEntryBefore", HASH_BEFORE_ROLES, spot=("value_ptr",))
    p = bar(sds5("valueSds", 16), "valueSds", SDS_ROLES)
    a = bar(hash_after(16, 16), "hashEntryAfter", HASH_AFTER_ROLES)
    out["fig-embed-2-hash-value.svg"] = pair_figure(
        "Hash field: the value moves into the entry",
        "Valkey 9.0, PR 1579 \u2014 16-byte field, 16-byte value",
        b, p, "value_ptr", a,
        "The entry starts with a pointer to a separately allocated value sds (two allocations).",
        "Field and value share one allocation (when they fit in 128 B); the 8 B value pointer is gone.",
        # the field's NUL is not called out: it sits between two "string header"
        # callouts and there is no room for three labels in 30 px
        before_labels={"value_ptr": "*value", "field_offset": "", "pad": "pad", "f_hdr": HDR, "field": "field (16 B)", "f_nul": ""},
        payload_labels={**SDS_LBL, "body": "value (16 B)"},
        after_labels={"f_hdr": HDR, "field": "field (16 B)", "f_nul": "",
                      "v_hdr": HDR, "value": "value (16 B)", "v_nul": NUL})

    # 3. zset member embed
    b = bar(ZSL_BEFORE, "zskiplistNodeBefore", ZSL_BEFORE_ROLES, byte_sized=False, spot=("ele",))
    p = bar(sds5("memberSds", 20), "memberSds", SDS_ROLES)
    a = bar(zsl_after(20), "zskiplistNodeAfter", ZSL_AFTER_ROLES)
    out["fig-embed-3-zset-member.svg"] = pair_figure(
        "Sorted set node: the member moves into the skiplist node",
        "Valkey 9.1, PR 2508 \u2014 level-1 node, 20-byte member",
        b, p, "ele", a,
        "Each node points at a separately allocated member sds (two allocations).",
        "The member is embedded after the level array. The 8 B ele pointer is gone; 1 B records the member\u2019s sds header size.",
        before_labels={"ele": "*ele", "score": "score", "backward": "*backward",
                       "forward_1": "level 1\nforward", "span_1": "level 1\nspan"},
        payload_labels={**SDS_LBL, "body": "member (20 B)"},
        after_labels={"score": "score", "backward": "*backward", "forward_1": "level 1\nforward",
                      "span_1": "level 1\nspan", "ele_hdr": HDR, "ele": "member (20 B)",
                      "ele_nul": NUL})

    # 4. embstr ptr slot -- already ONE allocation before (key + value embedded);
    # only the pointer is wasted
    b = bar(robj_before(16, 16), "robjBefore", ROBJ_BEFORE_ROLES, spot=("ptr",))
    a = bar(robj_after(16, 16), "robjAfter", ROBJ_AFTER_ROLES)
    out["fig-embed-4-embstr-ptr.svg"] = pair_figure(
        "Small string: the value pointer is dropped from the object",
        "Valkey 9.1, PR 2516 \u2014 16-byte key, 16-byte value",
        b, None, "ptr", a,
        "Already one allocation: the object embeds its key and its value, yet still spends 8 B on a pointer to the value a few bytes further on.",
        "A flag replaces the pointer; the value is found by walking past the key. Key and value shift up 8 B.",
        ptr_target="v_hdr",
        # BEFORE keeps only the trailing NUL callout: the arrow lands on the
        # value's header and the key's callouts would sit under its path;
        # the AFTER row directly below labels every byte
        before_labels={"header_bits": "robj", "ptr": "*ptr", "key_hdr": "", "key": "key (16 B)",
                       "k_nul": "", "v_hdr": "", "value": "value (16 B)", "v_nul": NUL},
        after_labels={"header_bits": "robj", "key_hdr": HDR, "key": "key (16 B)", "k_nul": NUL,
                      "v_hdr": HDR, "value": "value (16 B)", "v_nul": NUL})

    # 5. embedding threshold 64 -> 128 B: a 16 B key + 64 B value object is
    # 97 B, so it flips from RAW (two allocations) to embedded (one).
    b = bar(raw_before(16), "robjRaw", RAW_BEFORE_ROLES, spot=("val_ptr",))
    p = bar(sds8("valueSds64", 64), "valueSds64", SDS_ROLES)
    a = bar(robj_after(16, 64), "robjAfter", ROBJ_AFTER_ROLES)
    out["fig-embed-5-embstr-threshold.svg"] = pair_figure(
        "Medium string: the embedding limit rises from 64 to 128 B",
        "Valkey 9.2, PR 3397 \u2014 16-byte key, 64-byte value",
        b, p, "val_ptr", a,
        "At 95 B the object is over the old 64 B embedding limit, so the value lives in its own allocation behind a pointer.",
        "Under the new 128 B limit the same object is embedded: one allocation, no pointer. The limit counts the whole object, not just the value.",
        saving_text="one allocation fewer per key",
        before_labels={"header_bits": "robj", "val_ptr": "*val", "key_hdr": HDR, "key": "key (16 B)",
                       "k_nul": NUL},
        payload_labels={**SDS_LBL, "body": "value (64 B)"},
        after_labels={"header_bits": "robj", "key_hdr": HDR, "key": "key (16 B)", "k_nul": NUL,
                      "v_hdr": HDR, "value": "value (64 B)", "v_nul": NUL})

    for name, svg in out.items():
        (outdir / name).write_text(svg)
        print("wrote", name)
    (outdir / "captions.md").write_text(
        "# Embedding figures \u2014 slide text\n\n"
        "Titles, subtitles and explainer sentences removed from the SVGs (FIGURE_TEXT=False); "
        "use as slide titles / speaker notes. Byte totals are compiler-probed.\n\n"
        + "\n".join(CAPTIONS))
    print("wrote captions.md")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--scheme" in args:
        i = args.index("--scheme")
        SCHEME = SCHEMES[args[i + 1]]
        del args[i:i + 2]
    if "--with-text" in args:
        FIGURE_TEXT = True
        args.remove("--with-text")
    if "--no-legend" in args:
        SHOW_LEGEND = False
        args.remove("--no-legend")
    if "--no-sds-callouts" in args:
        SDS_CALLOUTS = False
        args.remove("--no-sds-callouts")
    outdir = pathlib.Path(args[0] if args else HERE / "figures")
    outdir.mkdir(parents=True, exist_ok=True)
    build_all(outdir)
