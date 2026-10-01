# No Client Changes Required -- ValkeyConf Prague 2026

Rain Valentine's talk deck as a single self-contained web page: the Valkey sign-on intro (live
WebAudio, nothing to loop or line up), a CRT-off bridge into white, then the body slides.

## Watch it

Open `prague-deck/index.html` in Chrome or Safari straight from disk (no server, no network),
press **F** for fullscreen, **Space** to begin. Sound starts on that first key. Keys, flow and URL
options are in `prague-deck/README.md`.

To proofread the body slides alone, browse `prague-deck/slides-lite/` -- one PNG per slide, named by
the Google Slides page number (`s002.png` = page 2).

## Layout

| path | what |
|---|---|
| `prague-deck/index.html` | the deck: intro + bridge + slide player, fully self-contained |
| `prague-deck/slides/` | body slides exactly as exported from Google Slides (pages 2..22) |
| `prague-deck/slides-lite/` | what `index.html` shows: the export with 5 slides re-typeset (slide 2 and the section slides 4, 11, 15, 21) |
| `source/talk.pdf` | the Google Slides PDF export the slides come from |
| `make_deck_page.py` | writes `prague-deck/index.html` (intro, bridge, player, key handling) |
| `make_slides.py` | renders a PDF export to `prague-deck/slides/` at 2560 px (`--skip 1` drops the title page) |
| `makeover/patch_figures.py` | pastes replacement figures into slides (page -> figure map inside; figures in `makeover/figures/`) |
| `makeover/makeover.py` | renders the 5 re-typeset slides and assembles `slides-lite/` |
| `mock_slide2.py` | the three slide-2 mockups (A was chosen) |
| `test_deck.mjs` | headless run-through: drives the page with clicker keys, screenshots each phase |
| `fonts/opensans/` | Open Sans (OFL) used by the re-typeset slides |

## Rebuild after a new Google Slides export

```
python3 make_slides.py source/talk.pdf --skip 1        # PDF -> prague-deck/slides/
python3 makeover/patch_figures.py source/talk.pdf       # swap in figures from makeover/figures/ (optional)
python3 makeover/makeover.py                            # 5 re-typeset slides + originals -> slides-lite/
node test_deck.mjs /tmp/deck-run                        # optional: screenshots of the whole run
```

Needs Python 3 with `PyMuPDF` and `Pillow`; the test needs Node with `playwright`.
Keep the first body slide's background pure white so the bridge lands on it with no visible cut.

## Style

Black on white, Open Sans, one accent: Valkey periwinkle darkened to `#3F51C8` so it reads as text.
Figures keep their own grammar (orange pointers, grey overhead, blue user data) and are not re-drawn here.
