"""The credits slide (s022): one row per release, the memory-saving changes stacked, GitHub avatars beside
the authors and reviewers. Writes assets/credits.png, which slides.py places with static('022', ...).

Same frame as build_deck.py's slides: 1920x1080 design coordinates rendered at 2560x1440, Open Sans from
fonts/opensans/, the 'Thank you' header where the other slides put their title, the deck's
ink/grey/muted/accent palette. Release numbers are Fira Mono (fonts/firamono/), the deck's face for
code-like tokens; everything else is Open Sans. Avatars live in figures/avatars/. Rows are per PR
(ROWS; evidence per name in the talk workspace's CREDITS.md) and merged per release for display
(MODE='release'); MODE='change' keeps one row per PR.

Run: figures/build.sh (or: python3 figures/credits.py [out.png]).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
FONTS = HERE.parent / 'fonts'
AV = HERE / 'avatars'
OUT = HERE.parent / 'assets/credits.png'

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
    ('9.1', ['3397'], 'Embedding limit 64 \u2192 128 B',
     ['Nikhil Manglore'], ['Viktor Söderqvist']),
    ('9.2', ['3579', '3840', '4206', '4359'], 'B+ tree for sorted sets',
     ['Rain Valentine', 'Abhishek Kumar'], ['Eran Ifrah', 'Jim Brunner', 'Ran Shidlansik']),
]

SHORT = {  # change column, kept to a few words: the PR numbers appeared on the figure slides, the change is said aloud
    '541': 'Key into the dict entry', '1186': 'Hashtable for the keyspace', '1176': 'Hashtable for set, zset, hash',
    '1579': 'Hash value into the entry', '2508': 'Member into the skiplist node', '2516': 'String value pointer dropped',
    '3397': 'Embedding limit 64 \u2192 128 B', '3579': 'B+ tree for sorted sets',
}

# design-unit geometry. MODE 'change': one row per contribution, Release | Change | Authors | Reviewers.
# MODE 'release': one row per release, the changes stacked, names deduplicated across that release's PRs.
# The PR numbers are not shown in either: nobody looks one up from a slide, and they were on the figure slides.
MODE = 'release'
X0, X1 = 80, 1840                       # side margins (the frame's own are 120)
TABLE_TOP = 185
if MODE == 'change':
    COLS = [('Release', 130), ('Change', 400), ('Authors', 600), ('Reviewers', 630)]
    BODY, NUM, AVATAR, TEXT_LINE_H = 30, 27, 46, 40
else:
    COLS = [('Release', 130), ('Changes', 440), ('Authors', 580), ('Reviewers', 610)]
    BODY, NUM, AVATAR, TEXT_LINE_H = 32, 29, 56, 42
assert sum(w for _, w in COLS) == X1 - X0
PAD_X = 12                              # cell text inset
HEAD = 19                               # column labels, SemiBold, tracked, muted
CHIP_GAP_X, CHIP_GAP_Y = 24, 8
CELL_PAD_Y = 12
CHANGE_PX = 26                          # the change column, a notch under the names


def display_rows():
    """(release, [change lines], authors, reviewers) per table row."""
    if MODE == 'change':
        return [(rel, [SHORT[prs[0]]], a, r) for rel, prs, _, a, r in ROWS]
    out = {}
    for rel, prs, _, a, r in ROWS:
        rel_, ch, aa, rr = out.setdefault(rel, (rel, [], [], []))
        ch.append(SHORT[prs[0]])
        for n in a:
            if n not in aa: aa.append(n)
        for n in r:
            if n not in rr and n not in aa: rr.append(n)
    return list(out.values())


f_body, f_name, f_num, f_head = sans('Regular', CHANGE_PX), sans('Regular', BODY), mono('Regular', NUM), sans('SemiBold', HEAD)
# Open Sans has no U+2192; borrow the arrow from DejaVu Sans at the same size (as makeover.py does)
f_arrow = ImageFont.truetype('/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf', P(CHANGE_PX))


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
    rel, changes, authors, reviewers = row
    inner = [w - 2 * PAD_X for _, w in COLS]
    ch_l = [ln for c in changes for ln in wrap(c.split(' '), inner[1], f_body)]
    a_l = layout_chips(authors, inner[2])
    r_l = layout_chips(reviewers, inner[3])
    h_text = len(ch_l) * TEXT_LINE_H
    h_chip = max(len(a_l), len(r_l)) * (AVATAR + CHIP_GAP_Y) - CHIP_GAP_Y
    return ch_l, a_l, r_l, max(h_text, h_chip) + 2 * CELL_PAD_Y


def render():
    im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
    d.text((P(X0), P(84)), 'Thank you', font=sans('SemiBold', 54), fill=INK)
    rows = display_rows()
    plans = [row_plan(r) for r in rows]
    head_h = 44
    total = head_h + sum(p[-1] for p in plans)
    assert TABLE_TOP + total <= 1060, f'table too tall: {TABLE_TOP + total}'
    xs = [X0]
    for _, w in COLS:
        xs.append(xs[-1] + w)
    y = TABLE_TOP
    for (label, _), x in zip(COLS, xs):
        cx = x + PAD_X
        for ch in label.upper():                                  # tracked small caps, as the section eyebrows
            d.text((P(cx), P(y + head_h / 2)), ch, font=f_head, fill=MUTED, anchor='lm'); cx += tw(f_head, ch) + 2.5
    y += head_h
    d.line((P(X0), P(y), P(X1), P(y)), fill=ACCENT, width=P(2))
    for (rel, changes, authors, reviewers), (ch_l, a_l, r_l, h) in zip(rows, plans):
        def block(lines, col, font, fill):
            y0 = y + h / 2 - len(lines) * TEXT_LINE_H / 2
            for i, ln in enumerate(lines):
                draw_text(d, xs[col] + PAD_X, y0 + (i + 0.5) * TEXT_LINE_H, ln, font, fill)
        block([rel], 0, f_num, GREY)
        block(ch_l, 1, f_body, GREY if MODE == 'release' else INK)
        for col, lines in ((2, a_l), (3, r_l)):
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
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    render().save(out); print(out)
