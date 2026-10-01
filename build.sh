#!/usr/bin/env bash
# The whole pipeline, in order: figures -> body slides (from slides.py) -> deck page.
#   ./build.sh                 (expects .venv from: python3 -m venv .venv && .venv/bin/pip install --only-binary=:all: -r requirements.txt)
# Every output is checked in; a clean `git status` afterwards means the tree was already current.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-.venv/bin/python}"; [ -x "$PY" ] || PY=python3
figures/build.sh
"$PY" build_deck.py "$@"          # slides.py + figures/out + assets -> prague-deck/slides/ (--all re-renders every slide)
"$PY" check_deck.py
