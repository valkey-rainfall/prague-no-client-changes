#!/usr/bin/env python3
"""Makeover of the Prague body slides: Open Sans, black on white, periwinkle #3F51C8 accent.

Keeps every figure (chart / byte-layout / tree) as exported from Google Slides and re-typesets the frame
around it: titles, a section marker top-right, a caption with the number each slide earns, four section
slides with their claims, slide 2 in the "A" layout, and slide 13 split into before/after.
Output: prague-deck/slides-makeover/sNNN.png at 2560x1440 (+ slides.json/slides.js there).

usage: makeover.py          section slides (4, 11, 15, 21) and slide 2 re-typeset; every slide with a chart
                            or diagram is the original export, untouched -> prague-deck/slides-lite/
       makeover.py --full   the earlier full makeover (captions, split slide 13) -> prague-deck/slides-makeover/
                            Kept for the record; Rain reverted it 2026-10-01.
"""
import json
import shutil
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

LITE = '--full' not in sys.argv
LITE_KEEP = {'002', '004', '011', '015', '021', '022'}   # 022: credits, re-typeset in credits.py

HERE = Path(__file__).parent
SRC = HERE / 'src'
DECK = HERE.parent / 'prague-deck'
OUT = DECK / ('slides-lite' if LITE else 'slides-makeover')
OUT.mkdir(exist_ok=True)

S = 2560 / 1920                     # design at 1920x1080, render at 2560x1440
W, H = 2560, 1440
INK, GREY, MUTED, ACCENT, RULE = '#111111', '#555555', '#8a8a8a', '#3F51C8', '#dddddd'
FONTS = HERE.parent / 'fonts/opensans'  # in-repo copy (OFL); falls back to a user install
if not FONTS.exists(): FONTS = Path.home() / '.local/share/fonts/opensans'


def font(w, size): return ImageFont.truetype(str(FONTS / f'OpenSans-{w}.ttf'), round(size * S))
def P(v): return round(v * S)


DEJAVU = {'Light': '/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-ExtraLight.ttf'}
ARROW = '→'


def arrow_font(f):
    """Open Sans has no U+2192; borrow it from DejaVu Sans at the same pixel size."""
    name = Path(f.path).stem.split('-')[1]
    return ImageFont.truetype(DEJAVU.get(name, '/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf'), f.size)


def text_len(s, f):
    return sum((arrow_font(f) if c == ARROW else f).getlength(c) for c in s)


def text(d, xy, s, f, fill=INK, anchor='la', tracking=0):
    x, y = P(xy[0]), P(xy[1])
    if ARROW in s and not tracking:
        if anchor[0] == 'r': x -= text_len(s, f)
        if anchor[0] == 'm': x -= text_len(s, f) / 2
        parts = s.split(ARROW)
        for i, part in enumerate(parts):
            d.text((x, y), part, font=f, fill=fill, anchor='l' + anchor[1]); x += f.getlength(part)
            if i < len(parts) - 1:
                af = arrow_font(f); d.text((x, y), ARROW, font=af, fill=fill, anchor='l' + anchor[1]); x += af.getlength(ARROW)
        return
    if not tracking:
        d.text((x, y), s, font=f, fill=fill, anchor=anchor); return
    t = P(tracking)
    if anchor[0] == 'r':
        x -= text_len(s, f) + t * (len(s) - 1)
    for c in s:
        cf = arrow_font(f) if c == ARROW else f
        d.text((x, y), c, font=cf, fill=fill, anchor='l' + anchor[1]); x += cf.getlength(c) + t


def canvas(): im = Image.new('RGB', (W, H), 'white'); return im, ImageDraw.Draw(im)


def header(d, title, subtitle=None, section=None):
    text(d, (120, 84), title, font('SemiBold', 54), INK)
    if subtitle:
        text(d, (120, 162), subtitle, font('Regular', 30), GREY)
    # section marker top-right removed (Rain, 2026-10-01): one less thing to read on a fast slide.
    # Callers still pass `section` so the structure stays on record; it is not drawn.


def caption(d, s, y=1040):
    """Bottom caption: the first segment in accent, the rest grey."""
    head, _, tail = s.partition('|')
    f = font('Regular', 30)
    text(d, (120, y), head, font('SemiBold', 30), ACCENT, 'ls')
    text(d, (120 + text_len(head, font('SemiBold', 30)) / S, y), tail, f, GREY, 'ls')


def place(im, name, box, crop=None, autocrop=False):
    """Fit image `name` inside box=(x0,y0,x1,y1) in design coords, preserving aspect, centred."""
    src = Image.open(SRC / name).convert('RGB')
    if crop:
        src = src.crop(crop)
    if autocrop:
        bbox = ImageOps.invert(src.convert('L')).point(lambda v: 255 if v > 20 else 0).getbbox()
        if bbox:
            pad = 24
            src = src.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(src.width, bbox[2] + pad), min(src.height, bbox[3] + pad)))
    x0, y0, x1, y1 = (P(v) for v in box)
    r = min((x1 - x0) / src.width, (y1 - y0) / src.height)
    src = src.resize((round(src.width * r), round(src.height * r)), Image.LANCZOS)
    im.paste(src, (x0 + ((x1 - x0) - src.width) // 2, y0 + ((y1 - y0) - src.height) // 2))


def save(im, n):
    if LITE and n not in LITE_KEEP: return None          # lite mode: the original export is used instead
    im.save(OUT / f's{n}.png'); return f'{OUT.name}/s{n}.png'


names = []

# ---- 2: headline numbers (layout A) --------------------------------------------------------------
im, d = canvas()
header(d, 'Upgrading from 7.2 to 9.2', 'Same dataset, same commands, no client changes')
cols = [(120, '20%', '16 B keys, 1–128 B values', '43% less overhead: 31 B saved per key'),
        (1000, '28%', 'large sorted sets, 10–128 B elements', '54% less overhead: 46 B saved per element')]
for x, big, ds, ov in cols:
    text(d, (x, 640), big, font('Light', 300), INK, 'ls')
    text(d, (x + 8, 715), 'less memory', font('SemiBold', 44), ACCENT)
    text(d, (x + 8, 790), ds, font('Regular', 34), GREY)
    text(d, (x + 8, 840), ov, font('Regular', 34), GREY)
d.line([(P(960), P(420)), (P(960), P(900))], fill=RULE, width=P(2))
text(d, (120, 1010), 'Averaged over the size range; every size in the range improves. Results vary with allocator rounding.',
     font('Regular', 26), MUTED, 'ls')
names.append(save(im, '002'))

# ---- chart slides ---------------------------------------------------------------------------------
CHART_BOX = (120, 230, 1800, 1000)
CHART_SUB = '16 B keys, 16 B values, jemalloc · overhead = everything that is not your key and value'


def chart(n, name, title, section, sub=None, cap=None):   # no subtitle: Rain says it aloud
    im, d = canvas()
    header(d, title, sub, section)
    place(im, name, CHART_BOX)
    # no subtitle, no caption on chart slides: that text is what Rain says aloud (cap kept for the record)
    names.append(save(im, n))


chart('003', 'p03_x23.png', 'Overhead per key, release by release', None,
      cap='Four data types, six releases. |Each step is one change; the next three sections walk through them.')

# ---- 4: section Embedding -------------------------------------------------------------------------
def section(n, eyebrow, title, claim, detail):
    im, d = canvas()
    if eyebrow: text(d, (120, 300), eyebrow.upper(), font('SemiBold', 22), MUTED, tracking=3)
    text(d, (112, 540), title, font('Light', 150), INK, 'ls')
    d.rectangle([P(120), P(590), P(120 + 140), P(590 + 6)], fill=ACCENT)
    if claim: text(d, (120, 650), claim, font('SemiBold', 44), ACCENT)
    if detail: text(d, (120, 725), detail, font('Regular', 34), GREY)
    names.append(save(im, n))


section('004', 'Part 1 of 3', 'Embedding', 'One allocation instead of two',
        'The key, field or member moves into the entry that pointed at it: 7–14 B saved per item')

# ---- 5–9: byte layouts ------------------------------------------------------------------------------
LAYOUT_BOX = (120, 240, 1800, 975)


def layout(n, name, title, section, cap, box=LAYOUT_BOX):
    im, d = canvas()
    header(d, title, None, section)
    place(im, name, box, autocrop=True)
    caption(d, cap)
    names.append(save(im, n))


layout('005', 'p05_x35.png', 'Dictionary entry', 'Embedding', '42 B → 35 B per key. |Key string embedded in the entry; one pointer and one allocation fewer.')
layout('006', 'p06_x44.png', 'Hash entry', 'Embedding', '52 B → 38 B per field. |Field and value share one allocation.')
layout('007', 'p07_x53.png', 'Sorted set: skiplist node', 'Embedding', '62 B → 55 B per member. |Member string embedded in the node.')
layout('008', 'p08_x62.png', 'String object', 'Embedding', '55 B → 47 B. |Value embedded in the object; the *ptr goes away.')
layout('009', 'p09_x71.png', 'Raised string embedding threshold', 'Embedding', '103 B → 95 B for a 64 B value. |Embedding limit raised from 64 B to 128 B in 9.2.')

chart('010', 'p10_x80.png', 'Overhead per key: embedding', 'Embedding',
      cap='Orange: |the steps embedding accounts for.')

# ---- 11: section Dict -> Hashtable ------------------------------------------------------------------
section('011', 'Part 2 of 3', 'Dict → Hashtable', 'One cache line per lookup',
        'A bucket holds seven entries in 64 B; key and value share one object: 79 B → 64 B per key')

layout('012', 'p12_x93.png', 'A key in the keyspace', 'Dict → Hashtable',
       '3 allocations → 2. |The pointer table, entry and object become one bucket slot and one object.',
       box=(120, 230, 1800, 965))

# ---- 13 split: before / after -----------------------------------------------------------------------
im, d = canvas()
header(d, 'A key with a TTL: before', None, 'Dict → Hashtable')
place(im, 'p13_x100.png', (120, 250, 1800, 940), crop=(0, 30, 1914, 470), autocrop=True)
caption(d, '8 + 35 + 36 + 8 + 24 = 111 B. |Two dicts, two entries, one object; the expiry in its own dict entry.')
names.append(save(im, '013a'))
im, d = canvas()
header(d, 'A key with a TTL: after', None, 'Dict → Hashtable')
place(im, 'p13_x100.png', (120, 250, 1800, 940), crop=(0, 530, 1914, 1260), autocrop=True)
caption(d, '9 + 63 + 9 ≈ 81 B. |Two hashtables, one object; the expiry moves into the object.')
names.append(save(im, '013b'))

chart('014', 'p14_x107.png', 'Overhead per key: hashtable', 'Dict → Hashtable',
      cap='Orange: |the hashtable steps. Grey: embedding, from the last section.')

# ---- 15: section Skiplist -> B+ tree -----------------------------------------------------------------
section('015', 'Part 3 of 3', 'Skiplist → B+ Tree', '62.2 B → 40.9 B per member',
        'Members packed into leaves instead of one node each; a lookup is 7 reads instead of 19')

layout('016', 'p16_x119.png', 'Skiplist', 'Skiplist → B+ Tree',
       'One node per member, |each with a tower of forward pointers; the lanes let a search skip ahead.',
       box=(120, 300, 1800, 900))
layout('017', 'p17_x126.png', 'B+ tree', 'Skiplist → B+ Tree',
       'Members packed into leaves. |Inner nodes carry prefix, anchors, children and sizes; leaves link to each other for range reads.',
       box=(120, 230, 1800, 960))
layout('018', 'p18_x135.png', 'Bytes per member', 'Skiplist → B+ Tree',
       '62.2 B → 40.9 B per member. |Same members, same order, a third less memory.',
       box=(120, 190, 1800, 990))
layout('019', 'p19_x142.png', 'One lookup', 'Skiplist → B+ Tree',
       '19 reads → 7. |Fewer dependent memory reads per lookup, and the last ones land in the same leaf.',
       box=(120, 180, 1800, 995))

chart('020', 'p20_x149.png', 'Overhead per key: B+ tree', 'Skiplist → B+ Tree',
      cap='Orange: |the B+ tree step. Grey: hashtable and embedding.')

# ---- 21: The Future ----------------------------------------------------------------------------------
section('021', None, 'The Future', None, None)

# ---- 22: credits, re-typeset (makeover/credits.py; Ranma crossed into the re-typeset set for this, 2026-10-01)
from credits import render as render_credits   # noqa: E402
names.append(save(render_credits(), '022'))

if LITE:
    # Slide order follows the original export; only LITE_KEEP come from the renders above.
    names = []
    for p in sorted((DECK / 'slides').glob('s*.png')):
        if p.stem[1:] not in LITE_KEEP: shutil.copy(p, OUT / p.name)
        names.append(f'{OUT.name}/{p.name}')
    for p in OUT.glob('s*.png'):                           # drop leftovers from an earlier full run
        if f'{OUT.name}/{p.name}' not in names: p.unlink()

(OUT / 'slides.json').write_text(json.dumps(names, indent=1))
(OUT / 'slides.js').write_text('window.SLIDES = ' + json.dumps(names) + ';\n')
print(len(names), 'slides ->', OUT)
