#!/usr/bin/env python3
"""Three mockups for slide 2 ("If I were to update Valkey 7.2 to 9.2...") in Open Sans, 1920x1080.

usage: mock_slide2.py <outdir>
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

F = Path(__file__).resolve().parent / 'fonts/opensans'  # in-repo copy (OFL); falls back to a user install
if not F.exists(): F = Path.home() / '.local/share/fonts/opensans'
def font(w, size): return ImageFont.truetype(str(F / f'OpenSans-{w}.ttf'), size)

W, H = 1920, 1080
INK, GREY, MUTED, ACCENT = '#111111', '#555555', '#8a8a8a', '#3F51C8'
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)


def text(d, xy, s, f, fill=INK, anchor='la', tracking=0):
    if not tracking:
        d.text(xy, s, font=f, fill=fill, anchor=anchor); return
    x, y = xy
    if anchor[0] == 'm':
        total = sum(f.getlength(c) for c in s) + tracking * (len(s) - 1); x -= total / 2
    for c in s:
        d.text((x, y), c, font=f, fill=fill, anchor='l' + anchor[1]); x += f.getlength(c) + tracking


def footer(d, s='Results vary with allocator rounding.'):
    text(d, (120, H - 70), s, font('Regular', 26), MUTED, 'ls')


# ---- A: two big numbers side by side ------------------------------------------------------------
def mock_a():
    im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
    text(d, (120, 120), 'Upgrading from 7.2 to 9.2', font('SemiBold', 64), INK)
    text(d, (120, 215), 'Same dataset, same commands, no client changes', font('Regular', 36), GREY)
    cols = [(120, '20%', 'less memory', '16 B keys, 1–128 B values', '43% less overhead: 31 B saved per key'),
            (1000, '28%', 'less memory', 'large sorted sets, 10–128 B elements', '54% less overhead: 46 B saved per element')]
    for x, big, lab, ds, ov in cols:
        text(d, (x, 640), big, font('Light', 300), INK, 'ls')
        text(d, (x + 8, 715), lab, font('SemiBold', 44), ACCENT)
        text(d, (x + 8, 790), ds, font('Regular', 34), GREY)
        text(d, (x + 8, 840), ov, font('Regular', 34), GREY)
    d.line([(960, 420), (960, 900)], fill='#dddddd', width=2)
    footer(d, 'Averaged over the size range; every size in the range improves. Results vary with allocator rounding.'); im.save(out / 'A-two-numbers.png')


# ---- B: statement + table ------------------------------------------------------------------------
def mock_b():
    im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
    text(d, (120, 120), 'If I upgrade from 7.2 to 9.2…', font('SemiBold', 64), INK)
    hdr = font('SemiBold', 28); cell = font('Regular', 40); big = font('SemiBold', 72)
    cols = [120, 820, 1260]
    for x, h in zip(cols, ['DATASET', 'MEMORY', 'OVERHEAD']):
        text(d, (x, 330), h, hdr, MUTED, tracking=3)
    d.line([(120, 375), (1800, 375)], fill='#cccccc', width=2)
    rows = [('16 B keys, 16 B values', '−40%', '−59%'), ('sorted sets, 20 B members', '−47%', '−63%')]
    y = 440
    for ds, m, o in rows:
        text(d, (cols[0], y + 50), ds, cell, INK, 'ls')
        text(d, (cols[1], y + 50), m, big, ACCENT, 'ls')
        text(d, (cols[2], y + 50), o, big, INK, 'ls')
        y += 190
        d.line([(120, y - 60), (1800, y - 60)], fill='#eeeeee', width=2)
    text(d, (120, 860), 'Overhead = everything that is not your key and value.', font('Regular', 34), GREY)
    footer(d); im.save(out / 'B-table.png')


# ---- C: one headline number ----------------------------------------------------------------------
def mock_c():
    im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
    text(d, (120, 150), 'A 16 B key / 16 B value dataset, moved from 7.2 to 9.2, uses', font('Regular', 44), GREY)
    text(d, (105, 640), '40% less memory', font('Light', 190), INK, 'ls')
    text(d, (120, 700), 'with no client changes.', font('Regular', 44), GREY)
    d.line([(120, 800), (1800, 800)], fill='#dddddd', width=2)
    text(d, (120, 860), 'Large sorted sets with 20 B members: ', font('Regular', 36), GREY)
    text(d, (120 + font('Regular', 36).getlength('Large sorted sets with 20 B members: '), 860), '47% less memory', font('SemiBold', 36), ACCENT)
    footer(d); im.save(out / 'C-headline.png')


mock_a(); mock_b(); mock_c()
print('wrote', sorted(p.name for p in out.iterdir()))
