# Prague talk deck (web)

Open `index.html` in Chrome or Safari (double-click works; no server needed), press **F** for
fullscreen, then **Space** to begin. Sound starts on that first key.

| key | does |
|---|---|
| Space / Right / Down / PageDown / Enter / click | next (loader quartile, boot, bridge, slide) |
| Left / Up / PageUp / Backspace | previous (loader quartile, slide) |
| F | fullscreen on/off |
| B | black screen on/off |

Flow: black -> loader 25/50/75/100% (each click; the vamp thickens one layer on the next bar) ->
click at 100%: the sign-on, title, name -> holds lit -> click: CRT-off into white -> your slides.
Clicks during the sign-on are ignored until the name has landed, so a nervous thumb cannot cut it.

URL options: `?title=...&name=...&score=fm|launch|turbine|sid` (defaults are the talk's).

Body slides: `index.html` shows `slides-lite/` -- the Google Slides export with five slides re-typeset
(slide 2 and the section slides 4, 11, 15, 21: Open Sans, periwinkle accent line). Rebuild from a new PDF
export (Google Slides: File > Download > PDF) with two commands:
`python3 ../make_slides.py deck.pdf --skip 1` (originals -> `slides/`), then
`python3 ../makeover/makeover.py` (the five re-typeset slides + originals -> `slides-lite/`).
Keep the first slide's background pure white so the bridge lands on it without a visible cut.
