#!/usr/bin/env bash
# Regenerate every figure SVG into figures/out/ from the generators beside this script.
# Deterministic: a clean tree after running this means the checked-in SVGs are current.
#   figures/build.sh            uses .venv/bin/python if present, else python3
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$HERE/.."
PY="${PYTHON:-$ROOT/.venv/bin/python}"; [ -x "$PY" ] || PY=python3
OUT="$HERE/out"; mkdir -p "$OUT"
# Slide variants: no legend (narrated), no string-header/NUL callouts (narrated). See AGENTS.md.
"$PY" "$HERE/embed_figures.py"     "$OUT" --no-legend --no-sds-callouts >/dev/null
"$PY" "$HERE/hashtable_figures.py" "$OUT" --no-legend --no-sds-callouts >/dev/null
"$PY" "$HERE/fbtree_figures.py"    "$OUT" >/dev/null
TALK=1 "$PY" "$HERE/topology_figures.py" "$OUT"
TALK=1 "$PY" "$HERE/fetch_figure.py"    "$OUT" 2>/dev/null
TALK=1 "$PY" "$HERE/area_figure.py" 0.18 1.2 2.0 > "$OUT/fig-fb-4-allocations-to-scale.svg" 2>/dev/null
"$PY" "$HERE/overhead_2x2.py"      "$OUT" >/dev/null
mv "$OUT/fig1-skiplist-topology.svg" "$OUT/fig-fb-1-skiplist-topology.svg"
mv "$OUT/fig2-fbtree-topology.svg"   "$OUT/fig-fb-2-fbtree-topology.svg"
mv "$OUT/fig7a-lookup-fetches-nostrip.svg" "$OUT/fig-fb-6b-lookup-reads-short.svg"   # the deck's page 19
rm -f "$OUT"/fig7a-lookup-fetches*.svg                  # with-strip and animated variants: not in the deck
rm -f "$OUT"/captions.md "$OUT"/fig-ht-1-path-3.svg   # captions live in the talk workspace; the 3-row capstone is not in the deck
"$PY" "$HERE/credits.py" >/dev/null                        # -> assets/credits.png (slide s022)
ls "$OUT" | wc -l
