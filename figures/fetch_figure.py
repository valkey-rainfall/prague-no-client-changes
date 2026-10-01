#!/usr/bin/env python3
"""Fig 7a: one lookup at blog-ish scale -- how many separate allocations does
each structure read? N = 61*61 = 3721 members, so the 100%-packed fbtree is
exactly root -> 61 leaves -> 61 items per leaf. The lookup drawn is an INSERT
of a new member (ZADD): the fbtree's leaf step is then a binary search that
dereferences item pointers, its honest worst case. (Rank/delete of an existing
member arrives with the item pointer from the hashtable and scans the leaf by
pointer identity instead: root + leaf, no item read. Caption material.)

Nothing about the skiplist path is chosen by hand. The script builds a p = 1/4
skiplist (server.h ZSKIPLIST_P) from a fixed seed, replays a zslInsert-style
descent for EVERY target, and draws the target whose distinct-node count is
the median. Every node the lookup touches is drawn, in key order, with the
untouched stretch between two drawn nodes snipped to a gap labeled with the
number of members skipped. Everything drawn on the skiplist row IS a fetch.

Fetch markers are numbered in the order the lookup reads them, so the numbers
jump: a node compared at a high lane and not taken is fetched early even
though it sits far to the right. The animated variant plays that same
sequence -- one compare per tick, both structures on one clock -- so the
fbtree visibly finishes while the skiplist is still hopping.

Boxes are uniform width and NOT to scale: the figure is about counts. Each box
keeps the role split of the real struct (fieldday byte counts).

Usage: fetch_figure.py <outdir>
  writes fig7a-lookup-fetches.svg and fig7a-lookup-fetches-animated.svg
"""
import bisect, random, statistics, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "lib"))   # fdbars; fieldday comes from pip (requirements.txt)

from fdbars import (Bar, zskiplist_node, zsl_roles, fbtree_item, ITEM_ROLES,
                    fbtree_leaf, LEAF_ROLES, fbtree_inner, INNER_ROLES, C_MUTED, C_TEXT, C_LINE, FONT, theme)
from topology_figures import Canvas, legend, W, NODE_H
from routing_figure import ACCENT, HI_DEFS, hi_arc, hi_line, outline
import os
TALK = os.environ.get("TALK") == "1"   # talk mode: no titles/explainer prose (slide carries them)


C_PTR, C_OTHER, C_PAY = theme("role-pointer"), theme("role-overhead"), theme("role-data")
FANOUT = 61
N = FANOUT * FANOUT          # 3721: root -> 61 leaves -> 61 items, exactly full
P = 0.25
SEED = 20260911
TICK = 0.45                  # seconds per compare in the animated variant
PAUSE_TICKS = 8              # hold the finished picture before looping


# ------------------------------------------------------------ models
def build_skiplist(n, p=P, seed=SEED, maxlevel=32):
    rng = random.Random(seed)
    levels = []
    for _ in range(n):
        L = 1
        while rng.random() < p and L < maxlevel: L += 1
        levels.append(L)
    top = max(levels)
    lanes = [[i for i, l in enumerate(levels) if l >= L] for L in range(top + 1)]
    return levels, lanes, top

def replay(lanes, top, t):
    """zslInsert/zslGetRank-style descent to member index t. Returns the ordered
    list of (lane, node, taken) compares; every compare reads that node."""
    cur = -1; path = []
    for L in range(top, 0, -1):
        lane = lanes[L]
        j = bisect.bisect_right(lane, cur)
        while j < len(lane):
            node = lane[j]
            taken = node < t
            path.append((L, node, taken))
            if taken: cur = node; j += 1
            else: break
    return path

def median_target(lanes, top, n):
    counts = [(len({nd for _, nd, _ in replay(lanes, top, t)}), t) for t in range(n)]
    med = int(statistics.median(c for c, _ in counts))
    cands = [t for c, t in counts if c == med]
    return min(cands, key=lambda t: abs(t - n // 2)), med, counts

def leaf_probes(pos, n=FANOUT):
    """leafNodeBinarySearch (lower bound) over a full leaf, target at slot pos."""
    left, right = 0, n; probes = []
    while left < right:
        mid = (left + right) // 2
        probes.append(mid)
        if mid < pos: left = mid + 1
        else: right = mid
    return probes


# ------------------------------------------------------------ drawing helpers
TS = 1.4 if TALK else 1.0            # talk mode: headings, read counts and badges scaled for a slide


def touch(c, x, y, n, r=6):
    r = r * (1.25 if TALK else 1.0)
    c.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{ACCENT}" stroke="#ffffff" stroke-width="1.1"/>')
    c.text(x, y + 2.8 * (1.25 if TALK else 1.0), str(n), 7.2 * (1.25 if TALK else 1.0), 700, "middle", "#ffffff")

def role_box(c, x, y, w, h, roles, stroke=C_LINE, dashed=False):
    """Uniform-width box split by the struct's real role byte fractions."""
    tot = sum(roles.get(k, 0) for k in ("pointer", "overhead", "data", "padding")) or 1
    xx = x
    for key, col in (("pointer", C_PTR), ("overhead", C_OTHER), ("padding", C_OTHER), ("data", C_PAY)):
        seg = w * roles.get(key, 0) / tot
        if seg > 0: c.rect(xx, y, seg, h, col); xx += seg
    c.rect(x, y, w, h, "none", stroke="#ffffff", sw=1)
    c.rect(x, y, w, h, "none", stroke=stroke, sw=0.6, dash="3 2" if dashed else None)

def snip(c, x1, x2, y_top, h, count):
    """The cut between two drawn nodes: the skipped-member count, rotated to fit
    the gap, at the boxes' mid-height; a dotted mark at the base."""
    mid = (x1 + x2) / 2
    c.line(x1 + 2, y_top + h + 4, x2 - 2, y_top + h + 4, sw=0.8, opacity=0.35, dash="2 3")
    c.out.append(f'<text x="{mid:.1f}" y="{y_top + h/2:.1f}" font-family="{FONT}" font-size="7.5" fill="{C_MUTED}" '
                 f'text-anchor="middle" transform="rotate(-90 {mid:.1f} {y_top + h/2:.1f})" dy="2.6">({count:,})</text>')

def step(c, k):
    """Everything appended until end_step() belongs to tick k of the lookup."""
    c.out.append(f'<g class="st st{k}">')
def end_step(c):
    c.out.append('</g>')
def faded(c, op=0.3):
    c.out.append(f'<g opacity="{op}">')
def end_faded(c):
    c.out.append('</g>')


# ------------------------------------------------------------ panel A: skiplist
def hop_path(x1, x2, ly, peak):
    """A symmetric lane hop (quadratic Bezier), peak capped relative to the span."""
    span = x2 - x1
    peak = min(peak, span * 0.28)
    return f"M {x1:.1f} {ly:.1f} Q {(x1+x2)/2:.1f} {ly-peak:.1f} {x2:.1f} {ly:.1f}", peak


HEAD_L, HEAD_W = 8.0, 4.0     # arrowhead length and half-width (the old marker was ~8 px)


def head(c, tx, ty, ux, uy, extra=""):
    """Explicit arrowhead with tip (tx, ty) pointing along the unit vector (ux, uy).
    Drawn by hand rather than with marker orient=auto because librsvg 2.40
    (ImageMagick's SVG path) orients markers on curves as if they were straight."""
    nx, ny = -uy, ux
    bx, by = tx - HEAD_L * ux, ty - HEAD_L * uy
    pts = f"{tx:.1f},{ty:.1f} {bx + HEAD_W*nx:.1f},{by + HEAD_W*ny:.1f} {bx - HEAD_W*nx:.1f},{by - HEAD_W*ny:.1f}"
    c.out.append(f'<polygon points="{pts}" fill="{ACCENT}"{extra}/>')


def hop(c, x1, x2, ly, peak, sw, extra=""):
    """Hop arc plus an explicit head at the curve's end tangent."""
    import math
    d, pk = hop_path(x1, x2, ly, peak)
    c.out.append(f'<path d="{d}" fill="none" stroke="{ACCENT}" stroke-width="{sw}"{extra}/>')
    ang = math.atan2(pk, (x2 - x1) / 2)          # Q end tangent = P2 - P1 = (span/2, +peak), y down
    head(c, x2, ly, math.cos(ang), math.sin(ang), extra)


def arrow_line(c, x1, y1, x2, y2, sw):
    """Straight accent line with an explicit head (same look as the hops)."""
    import math
    L = math.hypot(x2 - x1, y2 - y1) or 1.0
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    c.out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2 - ux*2:.1f}" y2="{y2 - uy*2:.1f}" '
                 f'stroke="{ACCENT}" stroke-width="{sw}"/>')
    head(c, x2, y2, ux, uy)


def panel_skiplist(c, y0):
    levels, lanes, top = build_skiplist(N)
    t, med, counts = median_target(lanes, top, N)
    path = replay(lanes, top, t)
    nodes = sorted({nd for _, nd, _ in path})
    fetch_no = {}                                  # node -> fetch ordinal (head = 1)
    for _, nd, _ in path:
        if nd not in fetch_no: fetch_no[nd] = len(fetch_no) + 2
    fetches = 1 + len(nodes)

    c.text(24, y0, "skiplist" if TALK else f"skiplist, {N:,} members: inserting one new member", 13 * TS, 700)
    LANE = 13
    top_y = y0 + 22 + LANE * top
    def lane_y(L): return top_y - LANE * (L - 1)

    BOX = 15; GAP0 = 5; GAPS = 20
    hx = 40; hw = 12; hc = hx + hw / 2
    xs = {}; x = hx + hw + GAPS; prev = -1
    for nd in nodes:
        skipped = nd - prev - 1
        if prev >= 0: x += GAPS if skipped > 0 else GAP0
        xs[nd] = x; x += BOX; prev = nd
    assert x < W - 60, f"row too wide: {x}"
    cx = {nd: xs[nd] + BOX / 2 for nd in nodes}
    roles = {L: Bar(zskiplist_node(L), "zskiplistNode", zsl_roles(L), 1, 10, byte_sized=True).role_bytes() for L in set(levels[nd] for nd in nodes)}

    # static scaffolding: lane labels, snips, towers, faded nodes
    for L in range(1, top + 1): c.text(hx - 6, lane_y(L) + 3, f"{L}", 7.5, anchor="end", fill=C_MUTED)
    c.text(hx - 6, lane_y(top) - 10, "lane", 7.5, anchor="end", fill=C_MUTED)
    c.text(hc, top_y + NODE_H + 12, "head", 8, anchor="middle", fill=C_MUTED)
    prev = -1; px = hx + hw
    for nd in nodes:
        skipped = nd - prev - 1
        if skipped > 0: snip(c, px, xs[nd], top_y, NODE_H, skipped)
        prev = nd; px = xs[nd] + BOX
    faded(c)
    c.rect(hx, top_y, hw, NODE_H, "none", stroke=C_LINE, dash="3 2", sw=0.8)
    c.line(hc, top_y, hc, lane_y(top) - 6, sw=1.0, dash="3 2", opacity=0.6)
    for nd in nodes:
        L = levels[nd]
        if L >= 2: c.line(cx[nd], top_y, cx[nd], lane_y(L), sw=1.2, opacity=0.7)
        role_box(c, xs[nd], top_y, BOX, NODE_H, roles[L])
    end_faded(c)
    arrow_line(c, cx[t], top_y + NODE_H + 22, cx[t], top_y + NODE_H + 3, sw=1.0)
    c.text(cx[t], top_y + NODE_H + 32, "target", 8, 600, "middle", ACCENT)

    # tick 0: the head is read
    step(c, 0)
    c.rect(hx, top_y, hw, NODE_H, "none", stroke=ACCENT, dash="3 2", sw=1.2)
    touch(c, hc, top_y + NODE_H / 2, 1)
    end_step(c)
    # one tick per compare: the arc, and (first time) the node at full strength + its number
    cur_x = hc; cur_L = top; seen = set()
    lo, hi = -1, N; ranges = [N]                     # candidates left after each compare
    for k, (L, nd, taken) in enumerate(path, 1):
        step(c, k)
        if L < cur_L:                                # dropped a lane at the current node
            hi_line(c, cur_x, lane_y(cur_L), cur_x, lane_y(L) - 1, sw=1.2, arrow=False)
        x2 = cx[nd]
        again = nd in seen                           # compared before at a higher lane: no new fetch
        op = ' opacity="0.45"' if again else ''
        if taken:
            lo = nd
            hop(c, cur_x, x2, lane_y(L), 6 + L, 1.6, op)
        else:
            hi = min(hi, nd)
            # blog: dashed = compared, not stepped onto (explained in the caption lines).
            # talk: those lines are gone, so every read is drawn the same way.
            dash = '' if TALK else ' stroke-dasharray="3 2"'
            hop(c, cur_x, x2 - 3, lane_y(L), 6 + L, 1.6 if TALK else 1.1, dash + op)
        ranges.append(hi - lo)
        if nd not in seen:
            seen.add(nd)
            Ln = levels[nd]
            if Ln >= 2: c.line(cx[nd], top_y, cx[nd], lane_y(Ln), sw=1.2, opacity=0.7)
            role_box(c, xs[nd], top_y, BOX, NODE_H, roles[Ln])
            touch(c, cx[nd], top_y + NODE_H / 2, fetch_no[nd])
        end_step(c)
        cur_L = L
        if taken: cur_x = x2
    step(c, len(path))
    c.text(W - 24, y0, f"{fetches} reads", 12 * TS, 700, "end", ACCENT)
    end_step(c)
    if not TALK:
        c.text(24, top_y + NODE_H + 46,
               "boxes: nodes read, numbered in reading order.  (n): members skipped between two boxes.", 8, fill=C_MUTED)
        c.text(24, top_y + NODE_H + 58,
               "dashed arc: compared, not followed.  faint arc: compared again, no new read.", 8, fill=C_MUTED)
    return top_y + NODE_H + 66, fetches, len(path), ranges


# ------------------------------------------------------------ panel B: fbtree
def panel_fbtree(c, y0):
    t = N // 2
    leaf_i, pos = divmod(t, FANOUT)
    probes = leaf_probes(pos)
    fetches = 2 + len(probes)
    c.text(24, y0, "fbtree" if TALK else f"fbtree, {N:,} members: inserting one new member", 13 * TS, 700)

    inner_roles = Bar(fbtree_inner(), "innerNode", INNER_ROLES, 1, 10).role_bytes()
    leaf_roles = Bar(fbtree_leaf(), "leafNode", LEAF_ROLES, 1, 10).role_bytes()
    item_roles = Bar(fbtree_item(), "fbtreeItem", ITEM_ROLES, 1, 10).role_bytes()

    cx0 = W / 2
    RW = 200; ry = y0 + 22
    LW = 120; ly = ry + NODE_H + 52
    IW = 8; iy = ly + NODE_H + 44; ix0 = cx0 - FANOUT * IW / 2
    IH = NODE_H - 10

    # static scaffolding: faded root/leaf/items, sibling hints, child comb
    faded(c)
    role_box(c, cx0 - RW / 2, ry, RW, NODE_H, inner_roles)
    for k in range(FANOUT):
        if k == leaf_i: continue
        sx = cx0 - RW / 2 + (k + 0.5) * RW / FANOUT
        ex = cx0 + (k - leaf_i) * 9.5
        fade = max(0.08, 1 - abs(k - leaf_i) / 34)
        c.out.append(f'<line x1="{sx:.1f}" y1="{ry+NODE_H:.1f}" x2="{ex:.1f}" y2="{ly-6:.1f}" stroke="{C_LINE}" stroke-width="0.6" opacity="{fade:.2f}"/>')
    for d in (1, 2, 3):
        for sgn in (-1, 1):
            xx = cx0 + sgn * d * (LW + 14) - LW / 2
            c.out.append(f'<g opacity="{max(0.05, 0.45 - 0.13*d):.2f}">')
            role_box(c, xx, ly, LW, NODE_H, leaf_roles)
            c.out.append('</g>')
    role_box(c, cx0 - LW / 2, ly, LW, NODE_H, leaf_roles)
    for k in range(FANOUT):
        x = ix0 + k * IW
        role_box(c, x, iy, IW - 1, IH, item_roles)
        sx = cx0 - LW / 2 + (k + 0.5) * LW / FANOUT
        c.out.append(f'<line x1="{sx:.1f}" y1="{ly+NODE_H:.1f}" x2="{x+IW/2:.1f}" y2="{iy:.1f}" stroke="{C_LINE}" stroke-width="0.4" opacity="0.18"/>')
    end_faded(c)
    c.text(cx0 - RW / 2 - 8, ry + NODE_H / 2 + 4, "root", 9, anchor="end", fill=C_MUTED)
    c.text(cx0 - 3 * (LW + 14) - LW / 2 - 6, ly + NODE_H / 2 + 4, "…", 12, anchor="end", fill=C_MUTED)
    c.text(cx0 + 3 * (LW + 14) + LW / 2 + 6, ly + NODE_H / 2 + 4, "…", 12, fill=C_MUTED)
    c.text(cx0 + LW / 2 + 8, ly + NODE_H / 2 + 4, f"leaf {leaf_i} of {FANOUT}", 9, fill=C_MUTED)
    c.text(ix0 + FANOUT * IW + 10, iy + IH / 2 + 4, f"{FANOUT} items", 9, fill=C_MUTED)

    # tick 0: root read; tick 1: child chosen (fig 7b) and leaf read; ticks 2..: item probes
    step(c, 0)
    role_box(c, cx0 - RW / 2, ry, RW, NODE_H, inner_roles)
    outline(c, cx0 - RW / 2, ry, RW, NODE_H)
    touch(c, cx0, ry + NODE_H / 2, 1)
    end_step(c)
    step(c, 1)
    arrow_line(c, cx0 - RW / 2 + (leaf_i + 0.5) * RW / FANOUT, ry + NODE_H, cx0, ly, sw=1.6)
    role_box(c, cx0 - LW / 2, ly, LW, NODE_H, leaf_roles)
    outline(c, cx0 - LW / 2, ly, LW, NODE_H)
    touch(c, cx0, ly + NODE_H / 2, 2)
    end_step(c)
    # marker row under the items: same left-to-right order as the probed slots,
    # pushed apart to a minimum spacing so neighbours never touch
    order = sorted(range(len(probes)), key=lambda i: probes[i])
    mx = [ix0 + probes[i] * IW + IW / 2 for i in order]
    MIN = 18
    for i in range(1, len(mx)): mx[i] = max(mx[i], mx[i - 1] + MIN)
    for i in range(len(mx) - 2, -1, -1): mx[i] = min(mx[i], mx[i + 1] - MIN)
    marker_x = {order[i]: mx[i] for i in range(len(order))}
    my = iy + IH + 22
    lo, hi = 0, FANOUT; ranges = [N, FANOUT, FANOUT]   # after root: one leaf; leaf read: still 61
    for n_, k in enumerate(probes, 3):
        step(c, n_ - 1)
        x = ix0 + k * IW
        sx = cx0 - LW / 2 + (k + 0.5) * LW / FANOUT
        arrow_line(c, sx, ly + NODE_H, x + IW / 2, iy, sw=1.0)
        role_box(c, x, iy, IW - 1, IH, item_roles)
        outline(c, x, iy, IW - 1, IH)
        c.out.append(f'<line x1="{x + IW/2:.1f}" y1="{iy + IH + 2:.1f}" x2="{marker_x[n_-3]:.1f}" y2="{my - 7:.1f}" stroke="{ACCENT}" stroke-width="0.7" opacity="0.7"/>')
        touch(c, marker_x[n_ - 3], my, n_)
        if k == pos:
            c.out.append(f'<line x1="{marker_x[n_-3]:.1f}" y1="{my + 7:.1f}" x2="{marker_x[n_-3]:.1f}" y2="{my + 13:.1f}" stroke="{ACCENT}" stroke-width="0.7" opacity="0.7"/>')
            c.text(marker_x[n_ - 3], my + 22, "target", 8, 600, "middle", ACCENT)
        if k < pos: lo = k + 1
        else: hi = k
        ranges.append(hi - lo)
        end_step(c)
    step(c, fetches - 1)
    c.text(W - 24, y0, f"{fetches} reads", 12 * TS, 700, "end", ACCENT)
    end_step(c)
    return iy + IH + 50, fetches, fetches, ranges


def panel_ranges(c, y0, sk_ranges, fb_ranges):
    """Members still possible after each read, log scale, one bar per tick.
    Both rows start at N and end at 1; row length is the fetch count."""
    import math
    c.text(24, y0, "members still possible after each read (log scale)", 10, 600)
    BW = 13; GAP = 3; BH = 44
    x0 = 118
    def bar_h(v): return BH * math.log(max(v, 1) + 1) / math.log(sk_ranges[0] + 1)
    for row, (label, ranges) in enumerate((("skiplist", sk_ranges), ("fbtree", fb_ranges))):
        by = y0 + 14 + row * (BH + 16)
        c.text(x0 - 8, by + BH - 2, label, 9, anchor="end", fill=C_MUTED)
        c.line(x0, by + BH, x0 + len(ranges) * (BW + GAP), by + BH, sw=0.6, opacity=0.5)
        for k, v in enumerate(ranges):
            step(c, k)
            h = bar_h(v)
            c.rect(x0 + k * (BW + GAP), by + BH - h, BW, h, ACCENT if k else C_OTHER)
            if k in (0, len(ranges) - 1) or (v <= 61 and (k == 0 or ranges[k-1] > 61)):
                c.text(x0 + k * (BW + GAP) + BW / 2, by + BH - h - 3, f"{max(v, 1):,}", 7, anchor="middle", fill=C_MUTED)
            end_step(c)
    # how many reads until 61 or fewer members remain
    sk_to_leaf = next(k for k, v in enumerate(sk_ranges) if v <= FANOUT)
    fb_to_leaf = next(k for k, v in enumerate(fb_ranges) if v <= FANOUT)
    global _caption_printed
    if not globals().get("_caption_printed"):
        print(f"caption: skiplist needs {sk_to_leaf} reads to get under {FANOUT} candidates, fbtree {fb_to_leaf}", file=sys.stderr)
        _caption_printed = True
    return y0 + 14 + 2 * (BH + 16) + 4


def animation_style(total_ticks):
    """Each tick-k group is hidden until tick k, then stays; all loop together."""
    period = (total_ticks + PAUSE_TICKS) * TICK
    rules = [f".st{{animation:{period:.2f}s linear infinite}}",
             "@media (prefers-reduced-motion: reduce){.st{animation:none}}"]   # final state, no motion
    for k in range(total_ticks):
        at = 100.0 * k / (total_ticks + PAUSE_TICKS)
        rules.append(f".st{k}{{animation-name:t{k}}}@keyframes t{k}{{0%,{at:.2f}%{{opacity:0}}{min(at+0.01,100):.2f}%,100%{{opacity:1}}}}")
    return "<style>" + "".join(rules) + "</style>"


def fig7a(animated=False, strip=True):
    """strip=False drops the 'members still possible' panel: a shorter figure with a
    slide-friendly aspect ratio, keeping the two read-path rows and their counts."""
    c = Canvas()
    c.out.append(HI_DEFS)
    y, sk, sk_ticks, sk_ranges = panel_skiplist(c, 26)
    y, fb, fb_ticks, fb_ranges = panel_fbtree(c, y + 26)
    if strip:
        y = panel_ranges(c, y + 18, sk_ranges, fb_ranges)
    else:
        y -= 20
    legend(c, 24, y + 20)
    c.rect(W - 24 - 10, y + 11, 10, 10, ACCENT); c.text(W - 24 - 14, y + 20, "read by the lookup", 10, anchor="end", fill=C_MUTED)
    if animated:
        c.out.insert(1, animation_style(max(sk_ticks, fb_ticks) + 1))
    if not animated:
        print(f"skiplist {sk} reads over {sk_ticks} compares; fbtree {fb} reads", file=sys.stderr)
    return c.svg(y + 34)


def fig7a_panel(which):
    """TALK mode: one read-path row per figure (one slide each), with its legend."""
    c = Canvas()
    c.out.append(HI_DEFS)
    panel = panel_skiplist if which == "skiplist" else panel_fbtree
    y, n, ticks, ranges = panel(c, 26)
    y -= 20
    legend(c, 24, y + 20)
    c.rect(W - 24 - 10, y + 11, 10, 10, ACCENT); c.text(W - 24 - 14, y + 20, "read by the lookup", 10, anchor="end", fill=C_MUTED)
    return c.svg(y + 34)


if __name__ == "__main__":
    outdir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    (outdir / "fig7a-lookup-fetches.svg").write_text(fig7a())
    (outdir / "fig7a-lookup-fetches-animated.svg").write_text(fig7a(animated=True))
    if TALK:
        (outdir / "fig7a-lookup-fetches-nostrip.svg").write_text(fig7a(strip=False))
        (outdir / "fig7a-lookup-fetches-skiplist.svg").write_text(fig7a_panel("skiplist"))
        (outdir / "fig7a-lookup-fetches-fbtree.svg").write_text(fig7a_panel("fbtree"))
    print("wrote fig7a-lookup-fetches.svg fig7a-lookup-fetches-animated.svg", file=sys.stderr)
