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
| slide list, order and every word on a slide | Rain | `slides.py` (she edits it, or tells one of us what to change) |
| the slide renderer | Rimuru | `build_deck.py` -> `prague-deck/slides/` |
| figures and charts | Ranma | `figures/` (generators, `lib/fdbars.py`, `data/*.csv`, `out/*.svg`); the `figure(...)` lines in `slides.py` that place them |
| credits table | Ranma (rows: Rain) | `figures/credits.py` + `figures/avatars/` -> `assets/credits.png`, placed by `static('022', ...)` |
| PowerPoint export | Rimuru | `export_pptx.py` -> `prague-deck.pptx` (release asset, not committed) |

**`slides.py` is the deck.** There is no Google Slides deck behind it any more; `source/talk.pdf` is the last
export, kept for the record and read by nothing. Ownership means "ask before changing", not "never touch".
Leave a note in the commit message when you cross a line.

## The pipeline, in order

```
figures/build.sh                                    # generators -> figures/out/*.svg (deterministic; byte-stable)
python3 build_deck.py                               # slides.py + figures/out + assets -> prague-deck/slides/*.png + slides.json/.js
python3 check_deck.py -v                            # the contract below; a second, standard library only
node test_deck.mjs "$KIROCREW_SCRATCH/deck-run"     # drives the page with clicker keys, one screenshot per phase
```
`./build.sh` runs the first three. Python deps: `requirements.txt` into `.venv` (see README).
`make_deck_page.py` is separate: it rebuilds `prague-deck/index.html` from Rimuru's untracked intro source and
only needs re-running when the intro or the player changes.

`build_deck.py` re-renders only the slides whose inputs changed (their line in `slides.py`, their SVG or PNG,
a font, the engine) and records a digest per slide in `prague-deck/slides/inputs.json`; `--all` re-renders
everything. The two of us render on different CPUs whose freetype antialiases glyph edges slightly
differently, so a full re-render on one host rewrites PNGs the other host just committed with no visible
change. Prefer the default; use `--all` only when the engine changes in a way the digest does not see.
Slide ids (`s012d`, `s016`) are labels inherited from the retired export's page numbers, not positions: the
order of the list in `slides.py` is the slide order.

`fieldday` (the struct-layout prober behind every figure) is pinned to a commit in `requirements.txt`
and needs a C compiler on PATH; the figures are byte-reproducible against that pin, so bump it on
purpose and re-run `figures/build.sh` in the same commit. The test needs Node >= 20 with `playwright`
and a Chromium it can launch.

## Changing a figure (Ranma's usual job)

1. Figures are generated, not copied: the generator lives in `figures/` and writes SVG to `figures/out/`
   via `figures/build.sh`. The generators carry their own C struct snippets (copied from a named Valkey
   commit, noted in a comment); nothing is read from a Valkey checkout. The 2x2 overhead charts come from
   `figures/overhead_2x2.py` over Rimuru's settled measurements in `figures/data/` (matplotlib, glyphs as
   paths so no font is needed at render time). Label text in the other figures is `Fira Mono`, resolved
   from `fonts/firamono/` through a generated `FONTCONFIG_FILE` at render time.
2. The slide that shows it is a `figure(id, 'name.svg', title=None, box=(x0, y0, x1, y1), trim=False)` line
   in `slides.py`. The SVG is rasterised at the box width and fitted inside the box, aspect preserved,
   centred. `trim=True` crops the SVG's own white margin first (the tree and allocation figures); not for
   the chain frames, whose shared canvas keeps every object in place from click to click. `margin(0.025)`
   is the whole slide minus a 2.5% safe zone (projector overscan; 0 reads as cropped). A click sequence
   is several `figure` lines with ids `012a`, `012b`, ...; adding a frame is adding a line.
   `animated=True` is for an SVG whose own `<style>` carries a CSS animation (slide 19, the lookup reads):
   the slide is then also written as `prague-deck/slides/sNNN.svg`, the whole 2560x1440 canvas with the figure
   nested at the same fitted box and Fira Mono embedded as data: URLs, and that SVG is what the manifest lists
   and the player shows (a CSS-animated SVG plays inside an `<img>`). The PNG is still rendered and committed:
   it is the still `export_pptx.py` places. The player reloads an SVG slide under a fresh URL each time it is
   shown so the animation starts at tick 0 (browsers share one timeline per image URL, and it would otherwise
   have been running since the page loaded). No header on an animated slide.
3. `python3 build_deck.py`, open `prague-deck/slides/sNNN.png` and look at it. Keep the figure grammar the
   deck already uses: orange pointers, grey overhead, blue user data, Fira Mono labels.
4. Commit the generator, `figures/out/*.svg`, `slides.py` if a line changed, and the regenerated PNGs (and
   slide SVGs) plus `slides/inputs.json` together. `check_deck.py` fails if any of those is out of step with
   the others.

## Checking your work

- `python3 check_deck.py -v` first, every time, before you commit. Standard library only, a second to run,
  and CI runs the same script on every push to `main`. It checks that `index.html` loads `slides/`, that
  the title and name are baked into the page, that nothing references the network, that the manifest
  agrees with the PNGs on disk and with `slides.py` (an animated slide is listed as its SVG and keeps its PNG
  still), that every PNG's recorded input digest matches the
  current inputs (so an edited `slides.py` or SVG without a rebuild fails, without rendering anything),
  and that every PNG is 2560x1440 (every slide SVG: a 2560x1440 canvas with its fonts embedded).
- `node test_deck.mjs <dir>` must list every slide in `prague-deck/slides/slides.js` (27 today) and the
  last screenshot must be the first body slide landing after the white-out.
- The deck opens from `file://` with no network. Anything that needs a server, a CDN or a font download
  is a regression; the venue wifi is not part of the design.
- Open Sans is vendored in `fonts/opensans/`, Fira Mono in `fonts/firamono/` (both OFL). The renderer
  reads them from there and the sign-on embeds Open Sans SemiBold into `index.html`. Do not depend on a
  system font.

## Style, so we stop re-deciding it

Black on white, Open Sans, one accent `#3F51C8` (Valkey periwinkle darkened to pass text contrast).
Body slides are fast-read: title + figure, **no captions, no footnotes, no corner markers**. Rain says
the numbers aloud; the slide shows the picture. Text is set only on slide 2, the four section slides and
the figure titles; `build_deck.py` has no caption primitive on purpose. Rain reverted a caption-heavy
version once; do not reintroduce it.
