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

Body slides: `index.html` shows `slides/`, rendered by `../build_deck.py` from `../slides.py` (the slide
list: titles, text, which figure goes where). Edit `slides.py`, run `python3 ../build_deck.py`, reload.
Keep the first slide's background pure white so the bridge lands on it without a visible cut.
