#!/usr/bin/env python3
"""2x2 per-key OVERHEAD staircase: String (+TTL), Hash, Set, Sorted set.

Overhead = jemalloc heap-profile total bytes/key minus the fixed user payload.
No title, no PR annotations: Rain annotates each drop in Slides as it is explained.
Each panel has its own y scale (all start at zero); no value labels.

Source: Rimuru's prague-memory package (armbench Graviton3, 5M items, jemalloc heap
profile), release-timeline-recommended.csv -- SETTLED numbers (no mid-rehash dict
inflation on 7.2.4/8.0). Every row used here has basis "measured settled" or
"hashtable era" (loaded == settled).
Run: figures/build.sh (writes figures/out/chart-overhead-2x2*.svg). Deterministic SVG: glyphs
as paths (no font dependency), fixed hash salt, no date metadata.
"""
import pathlib
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

HERE = pathlib.Path(__file__).parent
SRC = HERE / "data/release-timeline-recommended.csv"   # Rimuru's prague-memory package, settled numbers
OUTDIR = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "out")

RELEASES = ["7.2.4", "8.0", "8.1", "9.0", "9.1", "9.2"]
XLABELS = ["7.2", "8.0", "8.1", "9.0", "9.1", "9.2"]

import csv
with open(SRC) as f:
    ROWS = list(csv.DictReader(f))


def overhead(wl):
    """Settled overhead B/item per release, straight from Rimuru's recommended table."""
    by = {r["release"]: r for r in ROWS if r["workload"] == wl}
    for r in RELEASES:
        assert "settled" in by[r]["basis"] or "hashtable era" in by[r]["basis"], (wl, r, by[r]["basis"])
    return [float(by[r]["overhead_bytes_per_item"]) for r in RELEASES], int(by[RELEASES[0]]["payload_bytes"])


SERIES = {
    "string":     overhead("set-k16-v16"),
    "string_ttl": overhead("set-k16-v16-expire"),
    "hash":       overhead("hset-f16-v16"),
    "set":        overhead("sadd-m20"),
    "zset":       overhead("zadd-m20"),   # payload 28 = 20 B member + 8 B score
}

PANELS = [
    ("String", [("string_ttl", "with TTL"), ("string", "no TTL")]),
    ("Hash", [("hash", None)]),
    ("Set", [("set", None)]),
    ("Sorted Set", [("zset", None)]),
]
C_MAIN = "#1F4E79"
C_ALT = "#2A8C7A"          # teal for the with-TTL string line: a different hue, not a tint, so the two lines
                           # read apart where they touch at 8.0; not orange/magenta, which the deck uses for highlights
FUTURE = 1.0

from matplotlib import font_manager
for _f in sorted((HERE.parent / "fonts/opensans").glob("OpenSans-*.ttf")):   # the deck's text face, vendored (OFL)
    font_manager.fontManager.addfont(str(_f))
plt.rcParams.update({
    "font.family": "Open Sans",
    "font.size": 14, "axes.titlesize": 17, "axes.titleweight": "bold",
    "figure.facecolor": "#FFFFFF", "axes.facecolor": "#FFFFFF",
    "savefig.facecolor": "#FFFFFF", "axes.spines.top": False, "axes.spines.right": False,
    "svg.fonttype": "path", "svg.hashsalt": "prague",
})


def draw(ax, ys, color):
    xs = list(range(len(ys))) + [len(ys) - 1 + FUTURE]
    ax.plot(xs, ys + [ys[-1]], drawstyle="steps-post", color=color, lw=2.8, zorder=3)
    ax.plot(range(len(ys)), ys, "o", color=color, ms=7, zorder=4)


# Which drops belong to which technique: panel -> {release index of the drop: category}.
# Release index into RELEASES (the drop lands AT that release).
DROPS = {
    "String":     {1: "embedding", 2: "hashtable", 4: "embedding"},   # PR 541, 1186, 2516
    "Hash":       {2: "hashtable", 3: "embedding"},                   # PR 1502, 1579
    "Set":        {2: "hashtable"},                                    # PR 1176
    "Sorted Set": {2: "hashtable", 4: "embedding", 5: "B+ tree"},     # PR 1427, 2508, 4359
}
C_MARK = "#e07b39"   # the talk's orange: the change being explained on this slide
C_PRIOR = "#9a9a9a"  # grey: changes already explained on earlier slides
# Cumulative build order; each variant adds one category and greys out the earlier ones.
ORDER = ["embedding", "hashtable", "B+ tree"]
SUFFIX = {"embedding": "_step1_embedding", "hashtable": "_step2_hashtable",
          "B+ tree": "_step3_bptree"}


def mark(ax, heading, lines, category, color):
    for x, cat in DROPS[heading].items():
        if cat != category:
            continue
        tops = []
        for key, _ in lines:
            ys = SERIES[key][0]
            if abs(ys[x] - ys[x - 1]) >= 1.0:
                ax.plot([x, x], [ys[x - 1], ys[x]], color=color, lw=4.2, zorder=5,
                        solid_capstyle="butt")
                tops.append(ys[x])
        # one label per drop, right of the riser: above the new level in one-line panels,
        # below the lower line in the two-line String panel (the gap between lines is taken)
        ha = "left"
        if len(lines) == 1 and x == len(RELEASES) - 1:
            # last release: the right side is the unmarked tail and the panel edge
            at, off, va, ha = max(tops), (-8, 6), "bottom", "right"
        elif len(lines) == 1:
            at, off, va = max(tops), (8, 6), "bottom"
        elif (x + 1) in DROPS[heading]:
            # next step is one release away: no room on the right, go left under the lines
            at, off, va, ha = min(tops), (-8, -8), "top", "right"
        else:
            at, off, va = min(tops), (8, -8), "top"
        lab = ax.annotate(cat, (x, at), textcoords="offset points", xytext=off,
                          ha=ha, va=va, fontsize=14, fontweight="bold", color=color, zorder=6)
        lab.set_in_layout(False)   # identical panel geometry in every variant


def render(step):
    """step = number of ORDER categories to label (0 = plain chart)."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 6), sharex=True, sharey=False)
    for ax, (heading, lines) in zip(axes.flat, PANELS):
        for k, (key, tag) in enumerate(lines):
            color = C_MAIN if (len(lines) == 1 or k == 1) else C_ALT
            ys = SERIES[key][0]
            draw(ax, ys, color)
            if tag:
                ax.annotate(tag, (len(ys) - 1 + FUTURE, ys[-1]), textcoords="offset points",
                            xytext=(0, 6), ha="right", va="bottom", fontsize=14, color=color)
        for i, cat in enumerate(ORDER[:step]):
            mark(ax, heading, lines, cat, C_MARK if i == step - 1 else C_PRIOR)
        ax.set_title(heading, loc="left")
        top = max(max(SERIES[k][0]) for k, _ in lines)
        ax.set_ylim(0, top * 1.15)          # own scale per panel, still from zero
        ax.set_xlim(-0.4, len(RELEASES) - 1 + FUTURE)
        ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=4, integer=True))
        ax.grid(axis="y", ls=":", alpha=0.5)
    for ax in axes[1]:
        ax.set_xticks(range(len(RELEASES)))
        ax.set_xticklabels(XLABELS)
    fig.supylabel("Overhead bytes per key", fontsize=14)
    fig.tight_layout(h_pad=1.2, w_pad=2.0)
    out = OUTDIR / ("chart-overhead-2x2" + (SUFFIX[ORDER[step - 1]] if step else "") + ".svg")
    fig.savefig(out, format="svg", metadata={"Date": None})
    plt.close(fig)
    print(out)


def main():
    for step in range(len(ORDER) + 1):
        render(step)
    for k, (ys, user) in SERIES.items():
        print(f"  {k:11s} user {user:2d}  " + "  ".join(f"{y:6.1f}" for y in ys))


if __name__ == "__main__":
    main()
