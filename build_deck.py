#!/usr/bin/env python3
"""Render the body slides listed in slides.py -> prague-deck/slides/s<id>.png (2560x1440) + slides.json/slides.js.

Everything on a slide comes from this repo: figures from figures/out/*.svg (figures/build.sh), the credits table
from assets/, text set in the vendored Open Sans (fonts/opensans/). No PDF, no Google Slides, no network.
Byte-stable: the same inputs on the same PIL/cairo versions give the same PNGs, so a no-op rebuild is a clean
`git status`.

A slide is re-rendered only when something it depends on changed (its line in slides.py, its SVG or PNG, a
font, this file); prague-deck/slides/inputs.json records the digests. Two hosts' freetype builds antialias glyph
edges differently, so byte-identity across hosts is not a goal; "every committed PNG is current" is, and
check_deck.py verifies it from the digests without rendering anything.

An animated figure (figure(..., animated=True); the SVG carries CSS @keyframes) is additionally written as
s<id>.svg: the whole 2560x1440 slide as one SVG with the figure nested at the same fitted box and Fira Mono
embedded, which is what the manifest lists for that slide and what the player shows (a CSS-animated SVG plays
inside an <img>; a PNG cannot). The PNG is still rendered, as the still for the PowerPoint export.

usage: build_deck.py            render the slides whose inputs changed
       build_deck.py --all      render every slide
"""
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path
try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:                        # check_deck.py imports the spec and digests only; it never renders
    Image = None

HERE = Path(__file__).resolve().parent
DECK = HERE / 'prague-deck'
OUT = DECK / 'slides'
FIGS = HERE / 'figures' / 'out'
ASSETS = HERE / 'assets'
FONTS = HERE / 'fonts'

W, H = 2560, 1440
S = W / 1920                               # text layouts are designed at 1920x1080 and rendered at 2560x1440
INK, GREY, MUTED, ACCENT, RULE = '#111111', '#555555', '#8a8a8a', '#3F51C8', '#dddddd'
MONO = 'Fira Mono'                         # the figures' label face; cairosvg does not walk a CSS font stack, so the
                                           # SVG's family list is replaced by this one name before rasterising


# ---- the slide kinds (slides.py calls these; they only record what to draw) ------------------------------------
def headline(id, title, subtitle, cols, footnote): return dict(id=id, kind='headline', title=title, subtitle=subtitle, cols=cols, footnote=footnote)
def section(id, eyebrow, word, claim, detail): return dict(id=id, kind='section', eyebrow=eyebrow, word=word, claim=claim, detail=detail)
def figure(id, svg, title=None, box=(0, 0, W, H), trim=False, animated=False): return dict(id=id, kind='figure', svg=svg, title=title, box=box, trim=trim, animated=animated)
def shown_as(slide): return f"s{slide['id']}." + ('svg' if slide.get('animated') else 'png')   # the file the manifest lists for this slide
def static(id, png): return dict(id=id, kind='static', png=png)
def margin(f): return (round(W * f), round(H * f), round(W * (1 - f)), round(H * (1 - f)))


# ---- text ----------------------------------------------------------------------------------------------------
def font(w, size): return ImageFont.truetype(str(FONTS / 'opensans' / f'OpenSans-{w}.ttf'), round(size * S))
def P(v): return round(v * S)


ARROW = '→'
DEJAVU = {'Light': '/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-ExtraLight.ttf'}


def arrow_font(f):
    """Open Sans has no U+2192; borrow it from DejaVu Sans at the same pixel size."""
    name = Path(f.path).stem.split('-')[1]
    return ImageFont.truetype(DEJAVU.get(name, '/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf'), f.size)


def text_len(s, f):
    return sum((arrow_font(f) if c == ARROW else f).getlength(c) for c in s)


def text(d, xy, s, f, fill=INK, anchor='la', tracking=0):
    x, y = P(xy[0]), P(xy[1])
    if ARROW in s and not tracking:
        if anchor[0] == 'r': x -= text_len(s, f)
        if anchor[0] == 'm': x -= text_len(s, f) / 2
        parts = s.split(ARROW)
        for i, part in enumerate(parts):
            d.text((x, y), part, font=f, fill=fill, anchor='l' + anchor[1]); x += f.getlength(part)
            if i < len(parts) - 1:
                af = arrow_font(f); d.text((x, y), ARROW, font=af, fill=fill, anchor='l' + anchor[1]); x += af.getlength(ARROW)
        return
    if not tracking:
        d.text((x, y), s, font=f, fill=fill, anchor=anchor); return
    t = P(tracking)
    if anchor[0] == 'r':
        x -= text_len(s, f) + t * (len(s) - 1)
    for c in s:
        cf = arrow_font(f) if c == ARROW else f
        d.text((x, y), c, font=cf, fill=fill, anchor='l' + anchor[1]); x += cf.getlength(c) + t


def canvas(): im = Image.new('RGB', (W, H), 'white'); return im, ImageDraw.Draw(im)


def header(d, title, subtitle=None):
    text(d, (120, 84), title, font('SemiBold', 54), INK)
    if subtitle:
        text(d, (120, 162), subtitle, font('Regular', 30), GREY)


# ---- figures -------------------------------------------------------------------------------------------------
def fontconfig_for_vendored_fonts():
    """Point fontconfig (which cairo uses to resolve family names) at the repo's fonts/ as well as the system's,
    via a generated FONTCONFIG_FILE, so Fira Mono resolves on any host with nothing installed. Must run before
    cairo initialises fontconfig, i.e. before cairosvg is imported."""
    if os.environ.get('FONTCONFIG_FILE', '').endswith('prague-fonts.conf'):
        return
    conf = Path(tempfile.gettempdir()) / 'prague-fonts.conf'
    conf.write_text(f'''<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <dir>{FONTS}</dir>
  <cachedir>{Path(tempfile.gettempdir()) / 'prague-fc-cache'}</cachedir>
</fontconfig>
''')
    os.environ['FONTCONFIG_FILE'] = str(conf)


def rasterise(svg_path, width):
    fontconfig_for_vendored_fonts()
    import cairosvg
    svg = re.sub(r'font-family="[^"]*"', f'font-family="{MONO}"', svg_path.read_text())
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=width))).convert('RGBA')


def ink_bbox(im, pad=12):
    """Bounding box of the ink (anything darker than near-white), plus a small margin; None for a blank image."""
    flat = Image.new('RGB', im.size, (255, 255, 255)); flat.paste(im, mask=im.split()[3])
    bbox = ImageOps.invert(flat.convert('L')).point(lambda v: 255 if v > 20 else 0).getbbox()
    if not bbox:
        return None
    return (max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(im.width, bbox[2] + pad), min(im.height, bbox[3] + pad))


def trimmed(im, pad=12):
    """Crop to the ink, plus a small margin."""
    bbox = ink_bbox(im, pad)
    return im.crop(bbox) if bbox else im


def place_figure(im, svg, box, trim):
    bw, bh = box[2] - box[0], box[3] - box[1]
    fig = rasterise(FIGS / svg, bw * 2 if trim else bw)      # trimmed figures grow to fill the box: start oversize so the fit downscales
    if trim:
        fig = trimmed(fig)
    s = min(bw / fig.width, bh / fig.height)
    fig = fig.resize((round(fig.width * s), round(fig.height * s)), Image.LANCZOS)
    im.paste(fig, (box[0] + (bw - fig.width) // 2, box[1] + (bh - fig.height) // 2), fig)


def animated_slide_svg(slide):
    """The slide as one SVG: a white 2560x1440 canvas with the figure nested at its box. The nested <svg>'s
    preserveAspectRatio='xMidYMid meet' is the fit place_figure gives the PNG (smallest scale, centred); trim becomes
    the nested viewBox, measured on a raster exactly as for the PNG. Fira Mono rides along as @font-face data: URLs,
    because an SVG shown through <img> may load nothing external. The figure's own <style> (the CSS animation) is
    passed through untouched."""
    import base64
    assert not slide['title'], f"s{slide['id']}: an animated slide has no header; the figure is the whole slide"
    box, trim = slide['box'], slide['trim']
    bw, bh = box[2] - box[0], box[3] - box[1]
    text = (FIGS / slide['svg']).read_text()
    root = re.search(r'<svg\b[^>]*>', text)
    attrs = dict(re.findall(r'([\w:-]+)="([^"]*)"', root.group(0)))
    vx, vy, vw, vh = (float(v) for v in attrs['viewBox'].split())
    if trim:
        px = rasterise(FIGS / slide['svg'], bw * 2)
        bb = ink_bbox(px)
        if bb:
            f = vw / px.width                                 # raster px -> figure user units
            vx, vy, vw, vh = vx + bb[0] * f, vy + bb[1] * f, (bb[2] - bb[0]) * f, (bb[3] - bb[1]) * f
    inner = re.sub(r'font-family="[^"]*"', f'font-family="{MONO}, monospace"', text[root.end():])   # up to and including </svg>
    faces = ''.join(f"@font-face{{font-family:'{MONO}';font-weight:{wt};src:url(data:font/ttf;base64,"
                    f"{base64.b64encode((FONTS / 'firamono' / f'FiraMono-{name}.ttf').read_bytes()).decode()}) format('truetype')}}"
                    for wt, name in ((400, 'Regular'), (700, 'Bold')))      # the figures use 400, 600 and 700; 600 resolves to Bold
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
            f'<style>{faces}</style>\n<rect width="{W}" height="{H}" fill="#ffffff"/>\n'
            f'<svg x="{box[0]}" y="{box[1]}" width="{bw}" height="{bh}" viewBox="{vx:.3f} {vy:.3f} {vw:.3f} {vh:.3f}" '
            f'preserveAspectRatio="xMidYMid meet">' + inner + '\n</svg>\n')


# ---- the four kinds ------------------------------------------------------------------------------------------
def render(slide):
    k = slide['kind']
    if k == 'static':
        im = Image.open(ASSETS / slide['png']).convert('RGB')
        assert im.size == (W, H), f"{slide['png']}: {im.size}, want {(W, H)}"
        return im
    im, d = canvas()
    if k == 'headline':
        header(d, slide['title'], slide['subtitle'])
        for x, (big, ds, ov) in zip((120, 1000), slide['cols']):
            text(d, (x, 640), big, font('Light', 300), INK, 'ls')
            text(d, (x + 8, 715), 'less memory', font('SemiBold', 44), ACCENT)
            text(d, (x + 8, 790), ds, font('Regular', 34), GREY)
            text(d, (x + 8, 840), ov, font('Regular', 34), GREY)
        d.line([(P(960), P(420)), (P(960), P(900))], fill=RULE, width=P(2))
        text(d, (120, 1010), slide['footnote'], font('Regular', 26), MUTED, 'ls')
    elif k == 'section':
        if slide['eyebrow']: text(d, (120, 300), slide['eyebrow'].upper(), font('SemiBold', 22), MUTED, tracking=3)
        text(d, (112, 540), slide['word'], font('Light', 150), INK, 'ls')
        d.rectangle([P(120), P(590), P(120 + 140), P(590 + 6)], fill=ACCENT)
        if slide['claim']: text(d, (120, 650), slide['claim'], font('SemiBold', 44), ACCENT)
        if slide['detail']: text(d, (120, 725), slide['detail'], font('Regular', 34), GREY)
    elif k == 'figure':
        if slide['title']: header(d, slide['title'])
        place_figure(im, slide['svg'], slide['box'], slide['trim'])
    else:
        raise ValueError(k)
    return im


def inputs_digest(slide):
    """Everything a slide's pixels depend on: its spec line, the SVG/PNG it draws, the fonts, and this engine.
    Rimuru and Ranma render on different CPUs whose freetype antialiases glyph edges differently, so a
    byte-for-byte rebuild of an unchanged slide would still churn its PNG; the digest lets a rebuild leave
    unchanged slides alone and re-render only what actually changed (or everything, with --all)."""
    import hashlib
    h = hashlib.sha256(json.dumps(slide, sort_keys=True).encode())
    for p in [FIGS / slide['svg']] if slide['kind'] == 'figure' else [ASSETS / slide['png']] if slide['kind'] == 'static' else []:
        h.update(p.read_bytes())
    for p in sorted(FONTS.rglob('*.ttf')) + [HERE / 'build_deck.py']:
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def build(out, force=False):
    from slides import SLIDES
    ids = [s['id'] for s in SLIDES]
    assert len(ids) == len(set(ids)), 'duplicate slide id'
    out.mkdir(parents=True, exist_ok=True)
    stamp = out / 'inputs.json'
    seen = json.loads(stamp.read_text()) if stamp.exists() and not force else {}
    names, digests, rendered = [], {}, 0
    for s in SLIDES:
        png, dg = out / f"s{s['id']}.png", inputs_digest(s)
        shown = out / shown_as(s)                              # the PNG, or the SVG for an animated slide
        if force or seen.get(png.name) != dg or not png.exists() or not shown.exists():
            render(s).save(png); rendered += 1                 # the PNG is always rendered: the still for export_pptx.py
            if s.get('animated'):
                shown.write_text(animated_slide_svg(s))
            print(f"s{s['id']}  {s['kind']:8s} {s.get('svg') or s.get('png') or s.get('title') or s.get('word')}")
        digests[png.name] = dg
        names.append(f"{out.name}/{shown.name}")
    keep = {f"s{s['id']}.png" for s in SLIDES} | {shown_as(s) for s in SLIDES}
    for p in list(out.glob('s*.png')) + list(out.glob('s*.svg')):   # a slide removed (or no longer animated) leaves no stray file
        if p.name not in keep: p.unlink()
    stamp.write_text(json.dumps(digests, indent=1, sort_keys=True))
    (out / 'slides.json').write_text(json.dumps(names, indent=1))
    (out / 'slides.js').write_text('window.SLIDES = ' + json.dumps(names) + ';\n')   # file:// cannot fetch(); a script tag can
    print(f'{rendered} rendered, {len(names) - rendered} unchanged')
    return names


if __name__ == '__main__':
    names = build(OUT, force='--all' in sys.argv)
    print(len(names), 'slides ->', OUT)
