"""The body of the talk: every slide after the sign-on, in order. This file IS the deck.

Edit it, run `python3 build_deck.py`, commit the result. There is no Google Slides deck behind it any more
(the last export is kept at source/talk.pdf for the record).

Each entry is one slide: a 2560x1440 PNG named s<id>.png. Ids are labels, not positions -- the ORDER OF THIS
LIST is the slide order. The ids happen to be the page numbers of the retired Google Slides export, which is
why there is no 13 and why the chain sequence is 012a..012g; renaming them would only churn the PNGs.

Four kinds of slide:
  headline(id, ...)                 the two big numbers (slide 2)
  section(id, eyebrow, word, claim, detail)   a section opener: one big word, the accent line, a claim
  figure(id, svg, title=None, box=..., trim=False, animated=False)   a figure from figures/out/, with an optional title above it
  static(id, png)                   a finished PNG from assets/, used as is (the credits table)

Boxes are (x0, y0, x1, y1) in slide pixels (2560x1440): the figure is fitted inside, aspect preserved, centred.
`margin(f)` is the whole slide minus a fraction f on every side. trim=True crops the SVG's own white margin
first so the drawing fills the box; NOT for the chain frames, whose shared canvas keeps every object in place
from one click to the next. animated=True is for an SVG that carries a CSS animation: the slide is then shown as
an SVG (s<id>.svg, the figure nested at the same box) so the animation plays in the player; the PNG is still
rendered as the still for the PowerPoint export. Titles are Open Sans SemiBold; no subtitles and no captions on
figure slides (Rain says that aloud; a caption-heavy version was tried and reverted 2026-10-01).
"""
from build_deck import headline, section, figure, static, margin

CHART = (0, 80, 2560, 1360)             # the four charts share one frame so the axes stay put between them
EMBED = (0, 285, 2560, 1320)            # byte-layout figures under a title

SLIDES = [
    headline('002', 'Upgrading from 7.2 to 9.2', 'Same dataset, same commands, no client changes',
             cols=[('20%', '16 B keys, 1–128 B values', '43% less overhead: 31 B saved per key'),
                   ('28%', 'large sorted sets, 10–128 B elements', '54% less overhead: 46 B saved per element')],
             footnote='Averaged over the size range; every size in the range improves. Results vary with allocator rounding.'),
    figure('003', 'chart-overhead-2x2.svg', box=CHART),                 # overhead per key, release by release (plain)

    # ---- Part 1: embedding ----------------------------------------------------------------------------------
    section('004', 'Part 1 of 3', 'Embedding', 'One allocation instead of two',
            'The key, field or member moves into the entry that pointed at it: 7–14 B saved per item'),
    figure('005', 'fig-embed-1-dict-key.svg',         title='Dictionary entry',                 box=EMBED),  # PR 541   8.0
    figure('006', 'fig-embed-2-hash-value.svg',       title='Hash entry',                       box=EMBED),  # PR 1579  9.0
    figure('007', 'fig-embed-3-zset-member.svg',      title='Sorted set: skiplist node',        box=EMBED),  # PR 2508  9.1
    figure('008', 'fig-embed-4-embstr-ptr.svg',       title='String object',                    box=EMBED),  # PR 2516  9.1
    figure('009', 'fig-embed-5-embstr-threshold.svg', title='Raised string embedding threshold', box=EMBED),  # PR 3397  9.1 (merged to the 9.1 branch 2026-04-07, in 9.1.0-rc2 and 9.1.0)
    figure('010', 'chart-overhead-2x2_step1_embedding.svg', box=CHART),

    # ---- Part 2: dict -> hashtable --------------------------------------------------------------------------
    section('011', 'Part 2 of 3', 'Dict → Hashtable', 'One cache line per lookup',
            'A bucket holds seven entries in 64 B; key and value share one object: 79 B → 64 B per key'),
    # the collision-chain sequence: 7.2 -> 8.0 -> (key, expiry into the object) -> 8.1, one click per frame
    *[figure(f'012{c}', f'fig-ht-6{t}-chain.svg', box=margin(0.025))
      for c, t in zip('abcdefg', ('a1', 'a2', 'a', 'b', 'c', 'd', 'e'))],
    figure('014', 'chart-overhead-2x2_step2_hashtable.svg', box=CHART),

    # ---- Part 3: skiplist -> B+ tree ------------------------------------------------------------------------
    section('015', 'Part 3 of 3', 'Skiplist → B+ Tree', '62.2 B → 40.9 B per member',
            'Members packed into leaves instead of one node each; a lookup is 7 reads instead of 19'),
    figure('016', 'fig-fb-1-skiplist-topology.svg',   box=(0, 412, 2560, 1028), trim=True),
    figure('017', 'fig-fb-2-fbtree-topology.svg',     box=(0, 216, 2560, 1224), trim=True),
    figure('018', 'fig-fb-4-allocations-to-scale.svg', box=(-4, 0, 2560, 1440), trim=True),   # every allocation of 61 members, to scale
    figure('019', 'fig-fb-6b-lookup-reads-short-animated.svg', box=(292, 0, 2268, 1440), trim=True, animated=True),   # 19 reads -> 7 reads, one compare per 0.45 s, loops
    figure('020', 'chart-overhead-2x2_step3_bptree.svg', box=CHART),

    # ---- close -----------------------------------------------------------------------------------------------
    section('021', None, 'The Future', None, None),
    static('022', 'credits.png'),                                           # release / PR / change / authors / reviewers
]
