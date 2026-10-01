#!/usr/bin/env python3
"""Static checks on the committed web deck in prague-deck/. Standard library only, so it runs
unchanged on a laptop, on a benchmark host and in CI.

Each check guards a contract the deck has already broken once, or that a wrong rebuild would
break silently:

  player   index.html loads slides-lite/ (the export with the re-typeset slides), not slides/
           (the raw export). A rebuild of the page from the wrong builder flipped this once.
  baked    the talk title and speaker name are literal text in index.html, so the page works
           opened bare from disk without ?title= / ?name= parameters.
  offline  index.html references no http(s) resource other than XML namespaces. The venue's
           wifi is not part of the design.
  manifest slides.json, slides.js and slides-lite/{slides.json,slides.js} agree with each other
           and with the PNGs on disk: same slide stems, same order, every file present, no stray
           PNG that nothing lists.
  lite     slides-lite/ differs from slides/ in exactly the re-typeset set (LITE_KEEP in
           makeover/makeover.py) and is byte-identical everywhere else. This is the "title plus
           figure, no captions" rule: a caption-heavy render of a body slide fails here.
  size     every PNG in both folders is 2560x1440.

Exit status is the number of failed checks (0 = clean). Pass -v to print passing checks too.
"""
import filecmp
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

    # player: both the <script src> and the fetch fallback must point at slides-lite/
    srcs = re.findall(r'<script src="([^"]*slides[^"]*\.js)"', html)
    fetches = re.findall(r"fetch\('([^']*slides[^']*\.json)'\)", html)
    check('player: <script src> loads slides-lite/slides.js', srcs == ['slides-lite/slides.js'], str(srcs))
    check('player: fetch fallback loads slides-lite/slides.json', fetches == ['slides-lite/slides.json'], str(fetches))

    # baked: title and name are literal text, not URL-parameter defaults
    check('baked: talk title present in index.html', TITLE in html)
    check('baked: speaker name present in index.html', NAME in html or NAME.upper() in html)

    # offline: no network resources
    urls = [u for u in re.findall(r'https?://[^"\'\s)<>]+', html) if 'www.w3.org/' not in u]
    check('offline: no http(s) references in index.html', not urls, ', '.join(urls[:5]))

    # manifest: the four lists agree with each other and with disk
    # The raw export's lists sit beside index.html (make_slides.py writes them there); the lite set's
    # lists sit inside slides-lite/ (makeover.py). Both point at files relative to prague-deck/.
    lists = {}
    for folder, where in (('slides', DECK), ('slides-lite', DECK / 'slides-lite')):
        d = DECK / folder
        js, jsn = read_js_list(where / 'slides.js'), json.loads((where / 'slides.json').read_text())
        check(f'manifest: {folder}/slides.js parses', js is not None)
        check(f'manifest: {folder}/slides.js == slides.json', js == jsn)
        check(f'manifest: {folder}/ entries live in {folder}/', all(r.startswith(folder + '/') for r in jsn), str(jsn[:2]))
        missing = [r for r in jsn if not (DECK / r).is_file()]
        check(f'manifest: {folder}/ every listed file exists', not missing, ', '.join(missing[:5]))
        on_disk = sorted(p.name for p in d.glob('s*.png'))
        listed = sorted(Path(r).name for r in jsn)
        check(f'manifest: {folder}/ lists every PNG on disk, no strays', on_disk == listed,
              f'disk-only={sorted(set(on_disk) - set(listed))[:5]} list-only={sorted(set(listed) - set(on_disk))[:5]}')
        lists[folder] = jsn
    check('manifest: slides/ and slides-lite/ have the same slides in the same order',
          stems(lists['slides']) == stems(lists['slides-lite']),
          f"{len(lists['slides'])} vs {len(lists['slides-lite'])}")

    # lite: only LITE_KEEP differs from the raw export
    mk = (ROOT / 'makeover' / 'makeover.py').read_text()
    m = re.search(r"LITE_KEEP\s*=\s*\{([^}]*)\}", mk)
    keep = set(re.findall(r"'(\w+)'", m.group(1))) if m else set()
    check('lite: LITE_KEEP read from makeover/makeover.py', bool(keep), ','.join(sorted(keep)))
    changed, same = [], []
    for rel in lists['slides-lite']:
        name = Path(rel).name
        a, b = DECK / 'slides' / name, DECK / 'slides-lite' / name
        if a.is_file() and b.is_file():
            (same if filecmp.cmp(a, b, shallow=False) else changed).append(Path(rel).stem[1:])
    unexpected = sorted(set(changed) - keep)
    unchanged_keep = sorted(keep & set(same))
    check('lite: no body slide outside LITE_KEEP differs from the export', not unexpected, ','.join(unexpected))
    check('lite: every LITE_KEEP slide is actually re-typeset', not unchanged_keep, ','.join(unchanged_keep))

    # size
    wrong = [(str(p.relative_to(DECK)), png_size(p)) for p in DECK.glob('slides*/s*.png') if png_size(p) != SLIDE_PX]
    check(f'size: every slide PNG is {SLIDE_PX[0]}x{SLIDE_PX[1]}', not wrong, str(wrong[:5]))

    n = len(failures)
    print(f'check_deck: {"OK" if not n else f"{n} check(s) FAILED"}')
    return n


if __name__ == '__main__':
    sys.exit(main())
