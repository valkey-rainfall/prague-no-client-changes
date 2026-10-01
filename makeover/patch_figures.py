"""Swap corrected figures into exported body slides, in place of the figure Google Slides baked in.

Each entry maps a PDF page number to a replacement PNG. The slide's figure rectangle comes from the PDF
itself (the page's single image placement), so the new figure lands exactly where the old one was,
fitted inside that box and centred. Run after make_slides.py, before makeover.py:

    python3 make_slides.py deck.pdf --skip 1
    python3 makeover/patch_figures.py deck.pdf
    python3 makeover/makeover.py
"""
import sys
from pathlib import Path
import fitz
from PIL import Image

HERE = Path(__file__).parent
DECK = HERE.parent / 'prague-deck'
FIGURES = {16: HERE / 'figures/p16-skiplist.png',          # Ranma's arrowhead fix, 2026-10-01
           17: HERE / 'figures/p17-small-fbtree.png'}

pdf = fitz.open(sys.argv[1])
for page_no, fig in FIGURES.items():
    page = pdf[page_no - 1]
    imgs = page.get_images(full=True)
    assert len(imgs) == 1, f'page {page_no}: expected one baked figure, found {len(imgs)}'
    rect = page.get_image_rects(imgs[0][0])[0]
    slide_path = DECK / f'slides/s{page_no:03d}.png'
    slide = Image.open(slide_path).convert('RGB')
    k = slide.width / page.rect.width
    box = tuple(round(v * k) for v in (rect.x0, rect.y0, rect.x1, rect.y1))
    bw, bh = box[2] - box[0], box[3] - box[1]
    new = Image.open(fig).convert('RGBA')
    s = min(bw / new.width, bh / new.height)
    new = new.resize((round(new.width * s), round(new.height * s)), Image.LANCZOS)
    slide.paste((255, 255, 255), box)                      # clear the old figure
    x = box[0] + (bw - new.width) // 2; y = box[1] + (bh - new.height) // 2
    slide.paste(new, (x, y), new)
    slide.save(slide_path)
    print(f's{page_no:03d}: {fig.name} -> box {box}, scaled x{s:.2f}')
