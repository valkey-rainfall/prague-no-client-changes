#!/usr/bin/env python3
"""Derive prague-deck/index.html from talk-web/talk.html: the whole talk as one web page.

  idle   black                     first key/click starts the loader (the gesture also unlocks audio)
  load   tape loader 25/50/75/100% each click: next quartile, vamp thickens one layer on the next bar
  signon click at 100%: boot        the fixed sign-on (power-on, milestones, wireframe, unlock, title, name)
  lit    holds on the lit sign      talk over it as long as you like
  bridge click: CRT-off into white  0.23s squeeze + 0.10s flare + 0.37s open (same curve as build_bridge.py)
  body   your slides as images      next/prev on the clicker; slides.json lists them in order

Keys: next = Right / Down / PageDown / Space / Enter / click; prev = Left / Up / PageUp / Backspace;
F = fullscreen; B = black screen toggle; hold T = elapsed time + slide n/N (amber at 13:00, red at 15:00). ?title= ?name= ?score=fm|launch|turbine|sid as on talk.html.
Sound and picture come from one clock (the page's own), so nothing has to be lined up and the vamp loops
with no seam: it is generated, not played back.
"""
from pathlib import Path

SRC = Path(__file__).parent / 'talk-web' / 'talk.html'
OUT = Path(__file__).parent / 'prague-deck' / 'index.html'
html = SRC.read_text()


def swap(old, new, count=1):
    global html
    assert html.count(old) == count, f'expected {count} match(es) for: {old[:70]!r}, got {html.count(old)}'
    html = html.replace(old, new)


# the talk title and speaker are baked in, so opening index.html from disk needs no ?title= parameter
swap("(qq.get('title') || 'Your Talk Title Arrives Here')", "(qq.get('title') || 'No Client Changes Required')")
swap("(qq.get('name') || 'Rain Valentine')", "(qq.get('name') || 'Rain Valentine')")
# never download the wasm; the loader is driven by the clicker
swap("const REAL = new URLSearchParams(location.search).get('mock') === null;", 'const REAL = false;')
swap('if (REAL) startRealLoader(...loaderParams()); else startLoader(...loaderParams());', 'deckLoader();', count=2)  # startAll + startFast (unused)
# quartile -> vamp layer: 25%=0, 50%=1, 75%=2, 100%=3 (the stills' four steps)
swap('const layer = Math.min(3, Math.floor(loader.progress * 4));',
     'const layer = Math.min(3, Math.max(0, Math.ceil(loader.progress * 4 - 1e-6) - 1));')
# the loader line is the talk's own gag, not the web page's download readout
swap("LOADING ${REAL ? 'VALKEY-SERVER.WASM' : 'EMULATOR'}", 'OPTIMIZING VALKEY MEMORY')
# the held loader is not a stalled download
swap("const stalled = !done && performance.now() - loader.lastBytesAt > 350;", 'const stalled = false;')
# no try-valkey chrome, no cursor once started
swap('  @keyframes fadein{from{opacity:0}to{opacity:1}}', '''  #ui,#skip,#termbar,#replay{display:none !important}
  .started{cursor:none}
  #stage.off{animation:crtoff .23s cubic-bezier(.33,1,.68,1) forwards}
  @keyframes crtoff{from{transform:scaleY(1);filter:brightness(1)}to{transform:scaleY(.004);filter:brightness(3.5)}}
  #bline{position:fixed;left:0;right:0;top:50%;height:6px;margin-top:-3px;background:#fff;opacity:0;pointer-events:none}
  #bwhite{position:fixed;inset:0;background:#fff;transform:scaleY(0);pointer-events:none}
  #bwhite.open{animation:bopen .37s cubic-bezier(.33,1,.68,1) forwards}
  @keyframes bopen{from{transform:scaleY(.005)}to{transform:scaleY(1)}}
  #deck{position:fixed;inset:0;background:#fff;display:none;align-items:center;justify-content:center}
  body.deck #deck{display:flex} body.deck #stage,body.deck #bline{display:none}
  #deck img{width:100vw;height:100vh;object-fit:contain;display:none}
  #deck img.cur{display:block}
  #blackout{position:fixed;inset:0;background:#000;display:none;z-index:9} body.black #blackout{display:block}
  #clock{position:fixed;right:22px;bottom:16px;font:600 22px/1 ui-monospace,Menlo,monospace;letter-spacing:.06em;color:#555;background:rgba(255,255,255,.92);padding:8px 12px;border-radius:6px;display:none;z-index:8}
  #clock.show{display:block} #clock.late{color:#b42318} #clock.amber{color:#9a6700}
  #preload{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);font:400 15px/1 ui-monospace,Menlo,monospace;letter-spacing:.08em;color:#9aa;display:none;z-index:9}
  #preload.show{display:block}
  #hint{position:fixed;right:18px;bottom:14px;font:11px/1 ui-monospace,Menlo,monospace;letter-spacing:.25em;color:#1a2244;transition:opacity .6s}
  .started #hint{opacity:0}
  @keyframes fadein{from{opacity:0}to{opacity:1}}''')
# The player shows slides-lite/ (the export with five slides re-typeset), never slides/ (the raw export).
swap('<div id="ui" class="mono">', '''<script src="slides-lite/slides.js"></script>
<div id="bline"></div><div id="bwhite"></div>
<div id="deck" aria-label="slides"></div><div id="blackout"></div>
<div id="hint">PRESS SPACE TO BEGIN</div><div id="clock"></div><div id="preload"></div>
<div id="ui" class="mono">''')

# the deck controller
swap('</script>\n</body>', r'''
/* ============================ DECK: clicker-driven talk ============================ */
const DECK = {step: 'idle', qi: 0, slides: [], idx: -1, litAt: null, t0: null};
const TALK_MIN = 15;                           // 20-minute slot, 5 kept for questions
const QUARTILES = [0.25, 0.5, 0.75, 1.0];
const deckScore = q.get('score') || 'fm';
function deckLoader() {                      // replaces startLoader/startRealLoader: progress moves on the clicker
  Object.assign(loader, {phase: 'download', lines: [], ready: false, marks: [false, false, false, false], lastBytesAt: performance.now()});
  deckQuartile(0);
}
function deckQuartile(i) {
  DECK.qi = i; loader.progress = QUARTILES[i]; loader.bytes = loader.progress * loader.total; loader.lastBytesAt = performance.now();
}
function deckBoot() {                        // the click at 100%: boot, every marker already there -> status pops on the beat, unlock at holdMin
  DECK.t0 = performance.now(); DECK.step = 'signon'; loader.phase = 'boot'; loader.lines = BOOT_LINES.slice(0, 12); loader.marks = [true, true, true, true]; loader.ready = true;
  // the sign-on starts on the next bar; lit (title + name done) is TALK.end after the unlock
  const watch = () => { if (phase === 'post') { DECK.litAt = signonStart + UNLOCK.at + TALK.end; DECK.step = 'post'; } else setTimeout(watch, 50); };
  watch();
}
function bridgeSound(t0) {                   // build_bridge.py's thump + whine + hiss + landing click, as a buffer
  const SR = ctx.sampleRate, dur = 1.03, n = Math.ceil(SR * dur), buf = ctx.createBuffer(2, n, SR);
  let seed = 7; const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const gauss = () => { const u = rnd() || 1e-9, v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  const L = buf.getChannelData(0), R = buf.getChannelData(1); let wph = 0; const tc = 10 / 30;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const thump = .55 * Math.sin(2 * Math.PI * (70 * t - 25 * t * t)) * Math.exp(-t / .09);
    wph += 2 * Math.PI * (15700 + (9000 - 15700) * (i / n)) / SR;
    const whine = .05 * Math.sin(wph) * Math.exp(-t / .12);
    const hiss = .06 * gauss() * Math.exp(-t / .05);
    const click = t >= tc ? .25 * gauss() * Math.exp(-(t - tc) / .004) : 0;
    const fade = Math.min(1, Math.max(0, (dur - t) / .15));
    L[i] = R[i] = Math.max(-1, Math.min(1, (thump + whine + hiss + click) * fade));
  }
  const src = ctx.createBufferSource(), g = ctx.createGain(); src.buffer = buf; g.gain.value = .9;
  src.connect(g); g.connect(ctx.destination); src.start(t0);
}
function deckBridge() {
  DECK.step = 'bridge'; phase = 'done'; netRunning = false; vampShow(false);
  if (ctx) { const t = ctx.currentTime; try { master.gain.setValueAtTime(master.gain.value, t); master.gain.linearRampToValueAtTime(0, t + .25); } catch (e) {} bridgeSound(t + .01); }
  stage.classList.add('off');
  const line = document.getElementById('bline'), white = document.getElementById('bwhite');
  setTimeout(() => { stage.style.visibility = 'hidden'; line.style.opacity = 1; line.style.height = '4px'; }, 230);
  setTimeout(() => { line.style.height = '7px'; }, 263);
  setTimeout(() => { line.style.height = '5px'; }, 297);
  setTimeout(() => { line.style.opacity = 0; white.classList.add('open'); }, 330);
  // Land on the white bridge, then enter the body ONLY once every slide has
  // decoded (DECK.ready). On file:// / a warm cache this resolves before the
  // 700ms bridge animation finishes, so entry is unchanged; on a cold Pages
  // load it holds on the white screen (seamless -- slide backgrounds are white
  // too) rather than advancing into a half-fetched slide. A tiny counter shows
  // only if the hold is actually visible.
  setTimeout(() => {
    const hold = setTimeout(() => {
      const n = DECK.slides ? DECK.slides.length : 0;
      const el = document.getElementById('preload');
      if (el) { el.textContent = `loading ${DECK.decoded || 0}/${n}`; el.classList.add('show'); }
    }, 120);
    Promise.resolve(DECK.ready).then(() => {
      clearTimeout(hold);
      const el = document.getElementById('preload'); if (el) el.classList.remove('show');
      document.body.classList.add('deck'); DECK.step = 'body'; deckShow(0);
    });
  }, 700);
}
function deckShow(i) {
  const imgs = document.querySelectorAll('#deck img'); if (!imgs.length) { DECK.idx = -1; return; }
  DECK.idx = Math.max(0, Math.min(imgs.length - 1, i));
  imgs.forEach((im, k) => im.classList.toggle('cur', k === DECK.idx));
}
async function deckLoadSlides() {                   // slides-lite/slides.js (file://) or slides-lite/slides.json (served)
  try {
    if (window.SLIDES) DECK.slides = window.SLIDES;
    else { const r = await fetch('slides-lite/slides.json'); if (!r.ok) return; DECK.slides = await r.json(); }
    const d = document.getElementById('deck');
    DECK.decoded = 0;
    // Decode every slide upfront and track completion. deckBridge() waits on
    // DECK.ready before showing slide 0, so from a server (Pages) a slow fetch
    // can never land mid-talk; from file:// decode is instant and this is a
    // no-op. img.decode() rejects on a genuinely broken image -- count it as
    // settled so a single bad slide can't wedge the whole deck.
    DECK.ready = Promise.all(DECK.slides.map(s => {
      const im = document.createElement('img'); im.src = s; im.decoding = 'sync'; d.appendChild(im);
      return im.decode().catch(() => {}).then(() => { DECK.decoded++; });
    }));
  } catch (e) { console.warn('no slides.json', e); }
}
function deckNext() {
  switch (DECK.step) {
    case 'idle':
      DECK.step = 'load'; ui.classList.add('hidden');
      document.getElementById('sound').checked = true; document.getElementById('tape').checked = false;
      document.querySelector(`input[name=score][value=${deckScore}]`).checked = true;
      document.querySelector('input[name=mode][value=connect]').checked = true;
      startAll(); break;
    case 'load': if (DECK.qi < 3) deckQuartile(DECK.qi + 1); else deckBoot(); break;
    case 'signon': break;                                          // the sign-on is not interruptible
    case 'post': if (nowS() >= DECK.litAt) deckBridge(); break;    // ... until the name has landed
    case 'bridge': break;
    case 'body': deckShow(DECK.idx + 1); break;
  }
}
function deckPrev() {
  if (DECK.step === 'load' && DECK.qi > 0) deckQuartile(DECK.qi - 1);
  else if (DECK.step === 'body') deckShow(DECK.idx - 1);
}
function clockShow(on) {                     // hold T: elapsed since the sign-on, slide n/N, nothing the room needs to see for long
  const c = document.getElementById('clock'); c.classList.toggle('show', on); if (!on) return;
  const tick = () => {
    if (!c.classList.contains('show')) return;
    const s = DECK.t0 ? Math.floor((performance.now() - DECK.t0) / 1000) : 0, m = Math.floor(s / 60);
    const n = document.querySelectorAll('#deck img').length;
    c.textContent = `${m}:${String(s % 60).padStart(2, '0')}  ·  ${DECK.step === 'body' ? DECK.idx + 1 : 0}/${n}`;
    c.classList.toggle('late', s >= TALK_MIN * 60); c.classList.toggle('amber', s >= (TALK_MIN - 2) * 60 && s < TALK_MIN * 60);
    setTimeout(tick, 250);
  };
  tick();
}
document.addEventListener('keyup', e => { if (e.key === 't' || e.key === 'T') clockShow(false); }, true);
const NEXT = ['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter', 'n', 'N'], PREV = ['ArrowLeft', 'ArrowUp', 'PageUp', 'Backspace', 'p', 'P'];
document.addEventListener('keydown', e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (NEXT.includes(e.key)) { e.preventDefault(); deckNext(); }
  else if (PREV.includes(e.key)) { e.preventDefault(); deckPrev(); }
  else if (e.key === 'f' || e.key === 'F') { if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen(); }
  else if (e.key === 'b' || e.key === 'B') document.body.classList.toggle('black');
  else if (e.key === 't' || e.key === 'T') { e.preventDefault(); clockShow(true); }
  else if (e.key === 'Escape') e.preventDefault();                 // never the try-valkey skip
}, true);
document.addEventListener('click', e => { deckNext(); }, true);
window.__deck = DECK; window.__deckNext = deckNext;
deckLoadSlides();
</script>
</body>''')
# a browser that has seen try-valkey before would auto-start the silent fast path: never here
swap("else if (q.get('t') === null && !introMode && (seenBefore || matchMedia('(prefers-reduced-motion: reduce)').matches)) {",
     'else if (false) {')
# the page's own Escape = skip-intro handler must not fire
swap("document.addEventListener('keydown', e => { if (e.key === 'Escape') skipIntro(); });", '')

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(html)
print(f'WROTE {OUT} ({len(html)} bytes)')
