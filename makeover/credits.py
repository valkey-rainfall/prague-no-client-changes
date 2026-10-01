"""Credits slide (page 22), re-typeset: one row per memory-saving PR, GitHub avatars beside names.

Same frame as the other re-typeset slides (makeover.py): 1920x1080 design coordinates rendered at
2560x1440, Open Sans from fonts/opensans/, the header at (120, 84), 120 px side margins, the deck's
ink/grey/muted/accent palette. Release and PR numbers are set in Fira Mono (fonts/firamono/), the
deck's face for code-like tokens; everything else is Open Sans. Avatars live in makeover/avatars/.
Rows come from CREDITS-SLIDE.md in the talk workspace (evidence per name in CREDITS.md there).

Imported by makeover.py: render() returns the PIL image for save(im, '022').
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
FONTS = HERE.parent / 'fonts'
AV = HERE / 'avatars'

S = 2560 / 1920
W, H = 2560, 1440
INK, GREY, MUTED, ACCENT, RULE = '#111111', '#555555', '#8a8a8a', '#3F51C8', '#dddddd'


def P(v): return round(v * S)
def sans(w, size): return ImageFont.truetype(str(FONTS / f'opensans/OpenSans-{w}.ttf'), P(size))
def mono(w, size): return ImageFont.truetype(str(FONTS / f'firamono/FiraMono-{w}.ttf'), P(size))


PEOPLE = {
    'Harkrishn Patro': 'hpatro', 'Madelyn Olson': 'madolson', 'Viktor Söderqvist': 'zuiderkwast',
    'Rain Valentine': 'rainsupreme', 'Uri Yagelnik': 'uriyage', 'Ran Shidlansik': 'ranshid',
    'chzhoo': 'chzhoo', 'Nikhil Manglore': 'Nikhil-Manglore', 'Abhishek Kumar': 'dubey02',
    'Eran Ifrah': 'eifrah-aws', 'Jim Brunner': 'JimB123', 'Ping Xie': 'PingXie',
    'Zvi Schneider': 'zvi-code',
}

ROWS = [
    ('8.0', ['541'], 'Key embedded in dict entry',
     ['Harkrishn Patro', 'Madelyn Olson'], ['Viktor Söderqvist', 'Ping Xie', 'Zvi Schneider']),
    ('8.1', ['1186'], 'New hashtable for the keyspace',
     ['Viktor Söderqvist', 'Rain Valentine', 'Uri Yagelnik'], ['Madelyn Olson', 'Jim Brunner']),
    ('8.1', ['1176', '1427', '1502'], 'Hashtable for sets, sorted sets, hashes',
     ['Rain Valentine'], ['Viktor Söderqvist', 'Ran Shidlansik']),
    ('9.0', ['1579'], 'Hash value embedded in entry',
     ['Viktor Söderqvist'], ['Ran Shidlansik']),
    ('9.1', ['2508'], 'Member embedded in skiplist node',
     ['chzhoo', 'Viktor Söderqvist'], ['Ran Shidlansik']),
    ('9.1', ['2516'], 'Value pointer dropped from string object',
     ['Rain Valentine'], ['Viktor Söderqvist', 'Jim Brunner', 'Ran Shidlansik', 'Madelyn Olson']),
    ('9.2', ['3397'], 'Embedding limit 64 \u2192 128 B',
     ['Nikhil Manglore'], ['Viktor Söderqvist']),
    ('9.2', ['3579', '3840', '4206', '4359'], 'B+ tree for sorted sets',
     ['Rain Valentine', 'Abhishek Kumar'], ['Eran Ifrah', 'Jim Brunner', 'Ran Shidlansik']),
]

# design-unit geometry. PEOPLE_FIRST drops the Change column (the PR numbers already appeared on the
# figure slides and Rain says the change aloud) and spends the width on names and avatars.
PEOPLE_FIRST = True
X0, X1 = (80, 1840) if PEOPLE_FIRST else (120, 1800)     # side margins (the frame's are 120)
TABLE_TOP = 185                         # under the header
if PEOPLE_FIRST:
    COLS = [('Release', 140), ('PR', 260), ('Authors', 660), ('Reviewers', 700)]
    BODY, NUM, AVATAR, TEXT_LINE_H = 30, 27, 46, 40
else:
    COLS = [('Release', 125), ('PR', 200), ('Change', 365), ('Authors', 480), ('Reviewers', 510)]
    BODY, NUM, AVATAR, TEXT_LINE_H = 25, 23, 36, 33
assert sum(w for _, w in COLS) == X1 - X0
PAD_X = 12                              # cell text inset
HEAD = 19                               # column labels, SemiBold, tracked, muted
CHIP_GAP_X, CHIP_GAP_Y = 24, 8
CELL_PAD_Y = 12

f_body, f_name, f_num, f_head = sans('Regular', BODY), sans('Regular', BODY), mono('Regular', NUM), sans('SemiBold', HEAD)
# Open Sans has no U+2192; borrow the arrow from DejaVu Sans at the same size (as makeover.py does)
f_arrow = ImageFont.truetype('/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf', P(BODY))


def tw(font, text): return font.getlength(text) / S


def wrap(tokens, width, font, sep=' '):
    lines, cur = [], ''
    for t in tokens:
        cand = t if not cur else cur + sep + t
        if cur and tw(font, cand) > width:
            lines.append(cur); cur = t
        else:
            cur = cand
    return lines + [cur]


def chip_w(name): return AVATAR + 12 + tw(f_name, name)


def layout_chips(names, width):
    lines, cur, cur_w = [], [], 0.0
    for n in names:
        w = chip_w(n)
        add = w if not cur else CHIP_GAP_X + w
        if cur and cur_w + add > width:
            lines.append(cur); cur, cur_w = [n], w
        else:
            cur.append(n); cur_w += add
    return lines + [cur]


_av = {}


def avatar(handle):
    if handle not in _av:
        d = P(AVATAR)
        im = Image.open(AV / f'{handle}.png').convert('RGB').resize((d * 4, d * 4), Image.LANCZOS)
        mask = Image.new('L', (d * 4, d * 4), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
        _av[handle] = (im.resize((d, d), Image.LANCZOS), mask.resize((d, d), Image.LANCZOS))
    return _av[handle]


def draw_text(d, x, y, s, font, fill):
    """Left-middle anchored text; the arrow glyph comes from DejaVu."""
    for i, part in enumerate(s.split('\u2192')):
        d.text((P(x), P(y)), part, font=font, fill=fill, anchor='lm'); x += tw(font, part)
        if i < s.count('\u2192'):
            d.text((P(x), P(y)), '\u2192', font=f_arrow, fill=fill, anchor='lm'); x += tw(f_arrow, '\u2192')


def row_plan(row):
    rel, prs, change, authors, reviewers = row
    inner = [w - 2 * PAD_X for _, w in COLS]
    ca, cr = (2, 3) if PEOPLE_FIRST else (3, 4)
    pr_l = wrap(prs, inner[1], f_num, sep=', ')
    ch_l = [] if PEOPLE_FIRST else wrap(change.split(' '), inner[2], f_body)
    a_l = layout_chips(authors, inner[ca])
    r_l = layout_chips(reviewers, inner[cr])
    h_text = max(len(pr_l), len(ch_l)) * TEXT_LINE_H
    h_chip = max(len(a_l), len(r_l)) * (AVATAR + CHIP_GAP_Y) - CHIP_GAP_Y
    return pr_l, ch_l, a_l, r_l, max(h_text, h_chip) + 2 * CELL_PAD_Y


def render():
    im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
    d.text((P(X0), P(84)), 'Thank you', font=sans('SemiBold', 54), fill=INK)
    plans = [row_plan(r) for r in ROWS]
    head_h = 44
    total = head_h + sum(p[-1] for p in plans)
    assert TABLE_TOP + total <= 1060, f'table too tall: {TABLE_TOP + total}'
    xs = [X0]
    for _, w in COLS:
        xs.append(xs[-1] + w)
    y = TABLE_TOP
    for (label, _), x in zip(COLS, xs):
        # tracked small caps, as the section eyebrows
        cx = x + PAD_X
        for ch in label.upper():
            d.text((P(cx), P(y + head_h / 2)), ch, font=f_head, fill=MUTED, anchor='lm'); cx += tw(f_head, ch) + 2.5
    y += head_h
    d.line((P(X0), P(y), P(X1), P(y)), fill=ACCENT, width=P(2))
    for (rel, prs, change, authors, reviewers), (pr_l, ch_l, a_l, r_l, h) in zip(ROWS, plans):
        def block(lines, col, font, fill):
            y0 = y + h / 2 - len(lines) * TEXT_LINE_H / 2
            for i, ln in enumerate(lines):
                draw_text(d, xs[col] + PAD_X, y0 + (i + 0.5) * TEXT_LINE_H, ln, font, fill)
        block([rel], 0, f_num, GREY)
        block(pr_l, 1, f_num, INK)
        if not PEOPLE_FIRST:
            block(ch_l, 2, f_body, INK)
        for col, lines in (((2, a_l), (3, r_l)) if PEOPLE_FIRST else ((3, a_l), (4, r_l))):
            y0 = y + h / 2 - (len(lines) * (AVATAR + CHIP_GAP_Y) - CHIP_GAP_Y) / 2
            for i, ln in enumerate(lines):
                x = xs[col] + PAD_X; yy = y0 + i * (AVATAR + CHIP_GAP_Y)
                for name in ln:
                    av, mask = avatar(PEOPLE[name])
                    im.paste(av, (P(x), P(yy)), mask)
                    d.ellipse((P(x), P(yy), P(x + AVATAR), P(yy + AVATAR)), outline=RULE, width=1)
                    draw_text(d, x + AVATAR + 12, yy + AVATAR / 2, name, f_name, INK)
                    x += chip_w(name) + CHIP_GAP_X
        y += h
        d.line((P(X0), P(y), P(X1), P(y)), fill=RULE, width=P(1))
    return im


if __name__ == '__main__':
    import sys
    out = Path(sys.argv[1] if len(sys.argv) > 1 else HERE.parent / 'prague-deck/slides-lite/s022.png')
    render().save(out); print(out)
