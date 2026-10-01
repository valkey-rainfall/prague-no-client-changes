# No Client Changes Required -- ValkeyConf Prague 2026

Rain Valentine's talk deck as a single self-contained web page: the Valkey sign-on intro (live
WebAudio, nothing to loop or line up), a CRT-off bridge into white, then the body slides.

## Watch it

Open `prague-deck/index.html` in Chrome or Safari straight from disk (no server, no network),
press **F** for fullscreen, **Space** to begin. Sound starts on that first key. Keys, flow and URL
options are in `prague-deck/README.md`.

To proofread the body slides alone, browse `prague-deck/slides/` -- one PNG per slide, in the order of
`slides.py`. A PowerPoint version (`prague-deck.pptx`) is attached to every GitHub Release as a backup,
or build one with `python3 export_pptx.py`.

## Layout

| path | what |
|---|---|
| `slides.py` | **the deck**: every body slide, in order, with its title, text and figure. Edit this. |
| `build_deck.py` | renders `slides.py` -> `prague-deck/slides/*.png` (2560x1440) + `slides.json`/`slides.js` |
| `prague-deck/index.html` | the talk as one page: intro + bridge + slide player, fully self-contained |
| `prague-deck/slides/` | the rendered body slides (checked in so a plain checkout opens) |
| `figures/` | every figure and chart: generators (C-struct layouts probed by `fieldday`, pinned in `requirements.txt`; charts from `figures/data/*.csv` via matplotlib) and their output `figures/out/*.svg` |
| `assets/credits.png` | the credits table, a finished PNG used as is |
| `fonts/` | Open Sans and Fira Mono (OFL), the only faces the deck uses |
| `make_deck_page.py` | writes `prague-deck/index.html` (intro, bridge, player, key handling) |
| `export_pptx.py` | one full-bleed PNG per slide into a 16:9 `.pptx`, sign-on still in front |
| `check_deck.py` | the contract CI enforces: manifest, spec, freshness, offline, 2560x1440 |
| `test_deck.mjs` | headless run-through: drives the page with clicker keys, screenshots each phase |
| `mock_slide2.py` | the three slide-2 mockups (A was chosen) |
| `source/talk.pdf` | the last Google Slides export, kept for the record; nothing reads it |

## Rebuild (after editing `slides.py` or a figure)

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # once
./build.sh                                              # figures/out/ -> prague-deck/slides/ -> check_deck.py
node test_deck.mjs /tmp/deck-run                        # optional: screenshots of the whole run
```

`build.sh` runs, in order: `figures/build.sh` (generators -> `figures/out/*.svg`), `build_deck.py`
(`slides.py` -> `prague-deck/slides/`; only slides whose inputs changed are re-rendered, `--all` for
everything), `check_deck.py`. Needs a C compiler on PATH (`fieldday` compiles a tiny program per struct
to read `offsetof()`); the test needs Node >= 20 with `playwright`.
Keep the first body slide's background pure white so the bridge lands on it with no visible cut.

## Style

Black on white, Open Sans, one accent: Valkey periwinkle darkened to `#3F51C8` so it reads as text.
Figures keep their own grammar (orange pointers, grey overhead, blue user data) and are not re-drawn here.
