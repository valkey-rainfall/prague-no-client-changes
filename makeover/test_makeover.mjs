// Drive prague-deck/index-makeover.html like a clicker, in real time, and screenshot each phase.
// usage: node test_deck.mjs <outDir>
import { chromium } from '/home/rainval/.toolbox/tools/kirocrew/0.8.0.3/browser/cli/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const [, , outDir] = process.argv;
mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required', '--force-color-profile=srgb'] });
const page = await browser.newPage({ viewport: { width: +(process.env.VW || 1920), height: +(process.env.VH || 1080) } });
page.on('pageerror', e => console.error('PAGEERROR', e.message));
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('CONSOLE', m.type(), m.text()); });
const wait = ms => new Promise(r => setTimeout(r, ms));
const shot = async name => { await page.screenshot({ path: `${outDir}/${name}.png` }); const d = await page.evaluate(() => ({ step: window.__deck.step, qi: window.__deck.qi, idx: window.__deck.idx, phase: typeof phase !== 'undefined' ? phase : null })); console.log(name.padEnd(14), JSON.stringify(d)); };

await page.goto('http://127.0.0.1:8735/index-makeover.html', { waitUntil: 'load' });   // bare, as opened from disk: title/name must be baked in
await wait(500); await shot('00-idle');
await page.keyboard.press('Space'); await wait(1500); await shot('01-load25');
await page.keyboard.press('ArrowRight'); await wait(1500); await shot('02-load50');
await page.keyboard.press('ArrowRight'); await wait(1500); await shot('03-load75');
await page.keyboard.press('ArrowRight'); await wait(2500); await shot('04-load100');
await page.keyboard.press('ArrowLeft'); await wait(1200); await shot('04b-back75');
await page.keyboard.press('ArrowRight'); await wait(1200); await shot('04c-load100');
await page.keyboard.press('ArrowRight'); await wait(1200); await shot('05-signon');
await page.keyboard.press('ArrowRight'); await wait(300); await shot('05b-ignored');   // stray click during the sign-on
await wait(4000); await shot('06-title');
await wait(3500); await shot('07-lit');
await page.keyboard.press('ArrowRight'); await wait(150); await shot('08-off');
await wait(130); await shot('08b-line');
await wait(250); await shot('08c-open');
await wait(400); await shot('09-slide1');
await page.keyboard.press('PageDown'); await wait(200); await shot('10-slide2');
await page.keyboard.press('PageUp'); await wait(200); await shot('11-slide1');
await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowRight'); await wait(200); await shot('12-last');
await page.keyboard.down('t'); await wait(400); await shot('13-clock'); console.log('clock', await page.evaluate(() => document.getElementById('clock').textContent)); await page.keyboard.up('t'); await wait(100); console.log('clock hidden', await page.evaluate(() => !document.getElementById('clock').classList.contains('show')));
const r = await page.evaluate(() => { const im = document.querySelector('#deck img.cur'); const b = im.getBoundingClientRect(); return { img: [im.naturalWidth, im.naturalHeight], shown: [Math.round(b.width), Math.round(b.height)], view: [innerWidth, innerHeight], n: document.querySelectorAll('#deck img').length }; });
console.log('slide fit', JSON.stringify(r));
await browser.close();
