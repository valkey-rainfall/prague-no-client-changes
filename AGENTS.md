# Working in this repo (for agents)

Two AI agents work here: **Rimuru** (Rain's agent on benchdev; built the intro and the deck page) and
**Ranma** (Rain's agent on the arm desktop; draws the figures). Rain reviews in her browser and presents
from a laptop. This file is the shared contract so neither agent has to re-derive it. Keep it short and
keep it true; edit it when the contract changes.

## Ground rules

- **Push to a branch, then merge it yourself.** Rain allows direct pushes here, but both agents' runtimes
  refuse `git push` to `main` outright, so the equivalent is: push `your-branch`, then
  `gh pr merge <n> --rebase --delete-branch`. No review step is required. Keep history linear (rebase,
  not squash) so a bad render is one `git revert` away.
- **Commits are Rain's**: author `Rain Valentine <rsg000@gmail.com>`, `-s` (DCO sign-off). One commit
  per logical change; say what the slide now shows, not which script ran.
- **Never commit videos, PPTX or render scratch.** `.gitignore` is an allowlist; if a new file does not
  appear in `git status`, that is deliberate. Add a `!path` line only for something others need to rebuild.
- **Generated files are checked in on purpose** (`prague-deck/index.html`, every PNG under
  `prague-deck/slides*/`) so Rain can open the deck from a plain checkout. Regenerate them with the
  scripts; do not hand-edit them. If you change a builder, commit its output in the same commit.

## Who owns what

| area | owner | files |
|---|---|---|
| intro, bridge, slide player, key handling | Rimuru | `make_deck_page.py` -> `prague-deck/index.html` |
| the five re-typeset slides (2, 4, 11, 15, 21) | Rimuru | `makeover/makeover.py` -> `prague-deck/slides-lite/` |
| figures inside the body slides | Ranma | `makeover/figures/`, the `FIGURES` map in `makeover/patch_figures.py` |
| slide content and order | Rain (Google Slides) | `source/talk.pdf` is her export; replace it, never edit it |

Ownership means "ask before changing", not "never touch". Leave a note in the commit message when you
cross a line.

## The pipeline, in order

```
python3 make_slides.py source/talk.pdf --skip 1     # PDF pages 2..22 -> prague-deck/slides/sNNN.png (2560 px)
python3 makeover/patch_figures.py source/talk.pdf   # paste makeover/figures/* over the baked figures (pages in FIGURES)
python3 makeover/makeover.py                        # 5 re-typeset slides + the rest -> prague-deck/slides-lite/
node test_deck.mjs "$KIROCREW_SCRATCH/deck-run"     # drives the page with clicker keys, one screenshot per phase
```

Each step overwrites the next step's inputs, so after changing anything run every step from that point
down. `make_slides.py` resets `slides/` to the raw export, which **undoes `patch_figures.py`**; that is
why the figure swap is a script and not a one-off edit. File names are PDF page numbers: `s016.png` is
Google Slides page 16, so a page number in conversation with Rain maps straight to a file.

Needs Python 3 with `PyMuPDF`, `Pillow`, `cairosvg` (for SVG figures); the test needs Node with
`playwright` and a Chromium it can launch.

## Swapping a figure (Ranma's usual job)

1. Put the figure in `makeover/figures/` as SVG (preferred; rasterised at the slide's native box width)
   or PNG at >= 3136 px wide (the figure box on a 2560 px slide is ~1600-2000 px; smaller PNGs get
   upscaled and go soft).
2. Add or change the page -> file line in `FIGURES` in `makeover/patch_figures.py`. The script reads the
   figure rectangle from the PDF page, so the new figure lands exactly where Google Slides put the old one.
   It asserts the page has exactly one baked image; a page with text on it needs a different approach.
3. Run the pipeline from step 2 down, open `prague-deck/slides-lite/sNNN.png` and look at it. Keep the
   figure grammar the deck already uses: orange pointers, grey overhead, blue user data, DejaVu Mono labels.
4. Commit `makeover/figures/*`, `patch_figures.py` and the regenerated PNGs together.

## Checking your work

- `node test_deck.mjs <dir>` must list 21 slides and the last screenshot must be the first body slide
  landing after the white-out. If a slide count changes, `prague-deck/slides-lite/slides.js` is wrong.
- The deck opens from `file://` with no network. Anything that needs a server, a CDN or a font download
  is a regression; the venue wifi is not part of the design.
- Open Sans is vendored in `fonts/opensans/` (OFL). Scripts look there first, then
  `~/.local/share/fonts/opensans`. Do not depend on a system font.

## Style, so we stop re-deciding it

Black on white, Open Sans, one accent `#3F51C8` (Valkey periwinkle darkened to pass text contrast).
Body slides are fast-read: title + figure, **no captions, no footnotes, no corner markers**. Rain says
the numbers aloud; the slide shows the picture. The five re-typeset slides are the only place text is
set by us. Rain reverted a caption-heavy version once; do not reintroduce it.
