#!/usr/bin/env python3
"""Static checks on the committed web deck in prague-deck/. Standard library only, so it runs
unchanged on a laptop, on a benchmark host and in CI.

Each check guards a contract the deck has already broken once, or that a wrong rebuild would
break silently:

  player   index.html loads slides/slides.js (and falls back to slides/slides.json when served). A rebuild
           of the page from a stale builder once pointed it at a folder that no longer exists.
  baked    the talk title and speaker name are literal text in index.html, so the page works
           opened bare from disk without ?title= / ?name= parameters.
  offline  index.html references no http(s) resource other than XML namespaces. The venue's
           wifi is not part of the design.
  manifest slides/slides.json and slides/slides.js agree with each other and with the files on disk:
           every listed file present, every slide's PNG present (an animated slide is listed as its SVG and
           keeps its PNG still beside it), no stray PNG or SVG that nothing lists.
  spec     the manifest lists exactly the slides in slides.py, in that order. slides.py is the deck.
  current  every committed PNG was rendered from the current inputs: the digest build_deck.py stamped
           into slides/inputs.json equals the digest of the slide's line in slides.py, its SVG/PNG, the
           fonts and the engine. An edit to any of those without a rebuild fails here, without rendering.
  size     every PNG is 2560x1440; every slide SVG declares a 2560x1440 canvas and embeds its fonts.

Exit status is the number of failed checks (0 = clean). Pass -v to print passing checks too.
"""
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DECK = ROOT / 'prague-deck'
TITLE, NAME = 'No Client Changes Required', 'Rain Valentine'
SLIDE_PX = (2560, 1440)
VERBOSE = '-v' in sys.argv[1:]
failures = []


def check(name, ok, detail=''):
    if ok:
        if VERBOSE:
            print(f'  ok   {name}' + (f'  ({detail})' if detail else ''))
    else:
        failures.append(name)
        print(f'  FAIL {name}' + (f': {detail}' if detail else ''))


def png_size(p):
    with open(p, 'rb') as fh:
        head = fh.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n' or head[12:16] != b'IHDR':
        return None
    return struct.unpack('>II', head[16:24])


def stems(rel_paths):
    return [Path(r).stem for r in rel_paths]


def read_js_list(p):
    m = re.search(r'window\.SLIDES\s*=\s*(\[.*?\]);', p.read_text(), re.S)
    return json.loads(m.group(1)) if m else None


def main():
    html = (DECK / 'index.html').read_text()

    # player: both the <script src> and the fetch fallback must point at slides/
    srcs = re.findall(r'<script src="([^"]*slides[^"]*\.js)"', html)
    fetches = re.findall(r"fetch\('([^']*slides[^']*\.json)'\)", html)
    check('player: <script src> loads slides/slides.js', srcs == ['slides/slides.js'], str(srcs))
    check('player: fetch fallback loads slides/slides.json', fetches == ['slides/slides.json'], str(fetches))

    # baked: title and name are literal text, not URL-parameter defaults
    check('baked: talk title present in index.html', TITLE in html)
    check('baked: speaker name present in index.html', NAME in html or NAME.upper() in html)

    # offline: no network resources
    urls = [u for u in re.findall(r'https?://[^"\'\s)<>]+', html) if 'www.w3.org/' not in u]
    check('offline: no http(s) references in index.html', not urls, ', '.join(urls[:5]))

    # manifest: the two lists agree with each other and with disk
    d = DECK / 'slides'
    js, jsn = read_js_list(d / 'slides.js'), json.loads((d / 'slides.json').read_text())
    check('manifest: slides/slides.js parses', js is not None)
    check('manifest: slides/slides.js == slides.json', js == jsn)
    check('manifest: entries live in slides/', all(r.startswith('slides/') for r in jsn), str(jsn[:2]))
    missing = [r for r in jsn if not (DECK / r).is_file()]
    check('manifest: every listed file exists', not missing, ', '.join(missing[:5]))
    stills = [r for r in jsn if not (DECK / r).with_suffix('.png').is_file()]
    check('manifest: every slide has its PNG still (animated slides included)', not stills, ', '.join(stills[:5]))
    on_disk = sorted(p.name for p in d.glob('s*.png'))
    listed = sorted(Path(r).with_suffix('.png').name for r in jsn)
    check('manifest: lists every PNG on disk, no strays', on_disk == listed,
          f'disk-only={sorted(set(on_disk) - set(listed))[:5]} list-only={sorted(set(listed) - set(on_disk))[:5]}')
    svg_strays = sorted(p.name for p in d.glob('s*.svg') if f'slides/{p.name}' not in jsn)
    check('manifest: no stray slide SVG', not svg_strays, ', '.join(svg_strays[:5]))

    # spec + current: slides.py is the deck; every PNG was rendered from what is committed now
    sys.path.insert(0, str(ROOT))
    import build_deck
    from slides import SLIDES
    want = [f"slides/{build_deck.shown_as(s)}" for s in SLIDES]
    check('spec: manifest == slides.py, same slides, same order', jsn == want,
          f'manifest-only={sorted(set(jsn) - set(want))[:5]} spec-only={sorted(set(want) - set(jsn))[:5]}')
    stamped = json.loads((d / 'inputs.json').read_text()) if (d / 'inputs.json').is_file() else {}
    stale = [f"s{s['id']}" for s in SLIDES if stamped.get(f"s{s['id']}.png") != build_deck.inputs_digest(s)]
    check('current: every PNG rendered from the current slides.py / figures / fonts / engine', not stale,
          'rebuild with build_deck.py: ' + ', '.join(stale[:8]))

    # size
    wrong = [(str(p.relative_to(DECK)), png_size(p)) for p in DECK.glob('slides/s*.png') if png_size(p) != SLIDE_PX]
    check(f'size: every slide PNG is {SLIDE_PX[0]}x{SLIDE_PX[1]}', not wrong, str(wrong[:5]))
    canvas = f'width="{SLIDE_PX[0]}" height="{SLIDE_PX[1]}" viewBox="0 0 {SLIDE_PX[0]} {SLIDE_PX[1]}"'
    bad_svg = [p.name for p in DECK.glob('slides/s*.svg')
               if canvas not in p.read_text(errors='replace')[:400] or 'data:font/ttf;base64,' not in p.read_text(errors='replace')]
    check(f'size: every slide SVG is a {SLIDE_PX[0]}x{SLIDE_PX[1]} canvas with embedded fonts', not bad_svg, ', '.join(bad_svg[:5]))

    n = len(failures)
    print(f'check_deck: {"OK" if not n else f"{n} check(s) FAILED"}')
    return n


if __name__ == '__main__':
    sys.exit(main())
