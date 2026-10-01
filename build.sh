#!/usr/bin/env bash
# The whole pipeline, in order: figures -> body slides -> figure swap -> re-typeset slides.
#   ./build.sh                 (expects .venv from: python3 -m venv .venv && .venv/bin/pip install --only-binary=:all: -r requirements.txt)
# Every output is checked in; a clean `git status` afterwards means the tree was already current.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-.venv/bin/python}"; [ -x "$PY" ] || PY=python3
figures/build.sh
"$PY" make_slides.py source/talk.pdf --skip 1
"$PY" makeover/patch_figures.py source/talk.pdf
"$PY" makeover/makeover.py
