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
| figures inside the body slides | Ranma | `figures/` (generators, `lib/fdbars.py`, `out/*.svg`), the `FIGURES` map in `makeover/patch_figures.py` |
| slide content and order | Rain (Google Slides) | `source/talk.pdf` is her export; replace it, never edit it |

Ownership means "ask before changing", not "never touch". Leave a note in the commit message when you
cross a line.

## The pipeline, in order

```
figures/build.sh                                    # generators -> figures/out/*.svg (deterministic; byte-stable)
python3 make_slides.py source/talk.pdf --skip 1     # PDF pages 2..22 -> prague-deck/slides/sNNN.png (2560 px)
python3 makeover/patch_figures.py source/talk.pdf   # paste figures/out/* over the baked figures (pages in FIGURES)
python3 makeover/makeover.py                        # 5 re-typeset slides + the rest -> prague-deck/slides-lite/
node test_deck.mjs "$KIROCREW_SCRATCH/deck-run"     # drives the page with clicker keys, one screenshot per phase
```
`./build.sh` runs the first four. Python deps: `requirements.txt` into `.venv` (see README).

Each step overwrites the next step's inputs, so after changing anything run every step from that point
down. `make_slides.py` resets `slides/` to the raw export, which **undoes `patch_figures.py`**; that is
why the figure swap is a script and not a one-off edit. File names are PDF page numbers: `s016.png` is
Google Slides page 16, so a page number in conversation with Rain maps straight to a file.

`fieldday` (the struct-layout prober behind every figure) is pinned to a commit in `requirements.txt`
and needs a C compiler on PATH; the figures are byte-reproducible against that pin, so bump it on
purpose and re-run `figures/build.sh` in the same commit. The test needs Node >= 20 with `playwright`
and a Chromium it can launch.

## Swapping a figure (Ranma's usual job)

1. Figures are generated, not copied: the generator lives in `figures/` and writes SVG to `figures/out/`
   via `figures/build.sh`. The generators carry their own C struct snippets (copied from a named Valkey
   commit, noted in a comment); nothing is read from a Valkey checkout. A one-off PNG is still accepted
   by `patch_figures.py` (>= 3136 px wide, or it goes soft), but say why in the commit.
2. Add or change the page -> file line in `FIGURES` in `makeover/patch_figures.py`. The script reads the
   figure rectangle from the PDF page, so the new figure lands exactly where Google Slides put the old one.
   It asserts the page has exactly one baked image; a page with text on it needs a different approach.
   `BOX` overrides the baked rectangle with the whole slide minus a margin fraction (page 12 uses 0.025:
   a 2-4% safe zone survives projector overscan; 0 reads as cropped). A page may map to a LIST of figures (it becomes one slide per figure, `s012a.png`, `s012b.png`, ...,
   a step sequence drawn in the figure) or to `None` (dropped). The script then rewrites
   `prague-deck/slides.json` / `slides.js`, so the count can differ from the PDF's page count.
3. Run the pipeline from step 2 down, open `prague-deck/slides-lite/sNNN.png` and look at it. Keep the
   figure grammar the deck already uses: orange pointers, grey overhead, blue user data, DejaVu Mono labels.
4. Commit `makeover/figures/*`, `patch_figures.py` and the regenerated PNGs together.

## Checking your work

- `node test_deck.mjs <dir>` must list every slide in `prague-deck/slides.js` (26 since the chain sequence
  replaced pages 12-13) and the last screenshot must be the first body slide landing after the white-out.
  If the count disagrees with `slides.js`, the lists are stale: rerun from `patch_figures.py` down.
- The deck opens from `file://` with no network. Anything that needs a server, a CDN or a font download
  is a regression; the venue wifi is not part of the design.
- Open Sans is vendored in `fonts/opensans/` (OFL). Scripts look there first, then
  `~/.local/share/fonts/opensans`. Do not depend on a system font.

## Style, so we stop re-deciding it

Black on white, Open Sans, one accent `#3F51C8` (Valkey periwinkle darkened to pass text contrast).
Body slides are fast-read: title + figure, **no captions, no footnotes, no corner markers**. Rain says
the numbers aloud; the slide shows the picture. The five re-typeset slides are the only place text is
set by us. Rain reverted a caption-heavy version once; do not reintroduce it.
