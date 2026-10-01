#!/usr/bin/env python3
"""Body slides for prague-deck: a PDF export (Google Slides: File > Download > PDF) -> slides/sNNN.png + slides.json.

usage: make_slides.py <deck.pdf> [width_px=2560] [--skip N]   (--skip N drops the first N pages, e.g. a title slide the intro already covers)
Re-run after every export; it replaces the slides/ folder. 2560 px wide is sharp on a 4K projector and
still ~300-600 KB per slide for a black-on-white deck.
"""
import json
import shutil
import sys
from pathlib import Path
import fitz  # PyMuPDF

args = sys.argv[1:]
skip = int(args.pop(args.index('--skip') + 1)) if '--skip' in args else 0
if '--skip' in args: args.remove('--skip')
pdf, width = Path(args[0]), int(args[1]) if len(args) > 1 else 2560
root = Path(__file__).parent / 'prague-deck'
out = root / 'slides'
if out.exists():
    shutil.rmtree(out)
out.mkdir()
doc = fitz.open(pdf)
names = []
for i, page in enumerate(doc, 1):
    if i <= skip:
        continue
    zoom = width / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    name = f'slides/s{i:03d}.png'
    pix.save(root / name)
    names.append(name)
(root / 'slides.json').write_text(json.dumps(names, indent=1))
(root / 'slides.js').write_text('window.SLIDES = ' + json.dumps(names) + ';\n')   # file:// cannot fetch(); a script tag can
print(f'{len(names)} slides (skipped first {skip}), {pix.width}x{pix.height}, first page ratio {page.rect.width / page.rect.height:.3f} -> {root / "slides.json"}')
