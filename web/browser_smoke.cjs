// Run against a locally served web/dist after installing playwright-core.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');

async function main() {
  const browser = await chromium.launch({
    executablePath: process.env.GAMETRIX_CHROME,
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader', '--use-angle=swiftshader'],
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1200, height: 750 }, deviceScaleFactor: 2 });
    const errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    const py = code => page.evaluate(source => window.gamePython.runPython(source), code);
    const json = async code => JSON.parse(await py(`import json\njson.dumps(${code})`));

    async function ready() {
      await page.waitForFunction(() => document.querySelector('#status').textContent === 'Ready'
        || document.querySelector('#details').textContent, null, { timeout: 120000 });
      if (await page.locator('#status').textContent() !== 'Ready') {
        throw new Error(await page.locator('#details').textContent());
      }
      await page.waitForTimeout(1000);
    }
    async function coordinates(x, y) {
      const box = await page.locator('canvas').boundingBox();
      return { x: box.x + x / 1680 * box.width, y: box.y + (1050 - y) / 1050 * box.height };
    }
    async function click(x, y) {
      const p = await coordinates(x, y);
      await page.mouse.click(p.x, p.y);
      await page.waitForTimeout(200);
    }
    async function drag(x1, y1, x2, y2) {
      const a = await coordinates(x1, y1);
      const b = await coordinates(x2, y2);
      await page.mouse.move(a.x, a.y);
      await page.mouse.down();
      await page.mouse.move(b.x, b.y, { steps: 8 });
      await page.mouse.up();
      await page.waitForTimeout(400);
    }
    async function handPosition(id) {
      const cards = await json('[(cid,list(rect)) for cid,rect in window.current_view.hand_rects()]');
      const [, rect] = cards.find(card => card[0] === id);
      return [rect[0] + rect[2] / 2, rect[1] + rect[3] - 30];
    }

    await page.goto(process.env.GAMETRIX_WEB_URL || 'http://127.0.0.1:8000/');
    await ready();
    const seed = await py('window.current_view.seed.text');
    await click(200, 323);
    await page.keyboard.press('End');
    await page.keyboard.type('9');
    assert.equal(await py('window.current_view.seed.text'), seed + '9');
    // Seed 3 deals a transpose, so the following drag uses the real UI.
    await py("window.current_view.seed.text='3'");
    await click(575, 739);
    assert.equal(await py('window.current_view.mode'), 'student');
    await click(290, 223);
    assert.equal(await py('type(window.current_view).__name__'), 'Board');
    assert.equal(await py('window.current_view.save_warning'), '');
    const blue = await py("next(c.id for c in window.current_view.game.matrices if c.color=='blue')");
    const operation = await py("next(c['id'] for c in window.current_view.game.operations if c['code']=='transpose')");
    await drag(...await handPosition(blue), 1179, 860);
    await drag(...await handPosition(operation), 1373, 860);
    assert.equal(await py("window.current_view.layout.slots['A']"), blue);
    assert.equal(await py("window.current_view.layout.slots['operation']"), operation);
    const values = (await json('[[str(x) for x in row] for row in window.current_view.preview_values]')).flat();
    const fields = await json('[(f.left,f.bottom,f.width,f.height) for f in window.current_view.fields]');
    assert.equal(fields.length, values.length);
    for (let i = 0; i < fields.length; i++) {
      const [x, y, w, h] = fields[i];
      await click(x + w / 2, y + h / 2);
      await page.keyboard.type(values[i]);
    }
    await page.keyboard.press('Enter');
    await page.waitForTimeout(200);
    assert.equal(await py('window.current_view.preview_verified'), true);
    assert.equal(await py('len(window.current_view.game.history)'), 0);
    await click(1580, 372);
    assert.equal(await py('len(window.current_view.game.history)'), 1);
    assert.equal(await page.evaluate(() => !!localStorage.getItem('gametrix.browser.v1:student.json')), true);
    await page.waitForTimeout(5000);
    assert.equal(await py('pyglet.app.event_loop.is_running'), true);
    assert.equal(await py('_browser_loop_error'), '');

    await page.reload();
    await ready();
    await click(575, 739);
    await click(570, 223);
    assert.equal(await py('type(window.current_view).__name__'), 'Board');
    assert.equal(await py('len(window.current_view.game.history)'), 1);
    await page.setViewportSize({ width: 800, height: 500 });
    await page.waitForTimeout(800);
    const reds = await json("[c.id for c in window.current_view.game.matrices if c.color=='red']");
    await drag(...await handPosition(reds[0]), 1179, 467);
    assert.equal(await py("window.current_view.layout.slots['remove']"), reds[0]);
    await drag(...await handPosition(reds[1]), 1179, 467);
    assert.equal(await py("window.current_view.layout.slots['remove']"), reds[1]);
    assert.equal(await py(`any(c.id=='${reds[0]}' for c in window.current_view.game._removed_matrices)`), true);
    assert.equal(await py('pyglet.app.event_loop.is_running'), true);
    assert.deepEqual(errors, []);
    console.log('Browser smoke test passed: input, drawing, save/reload, resize, and removal.');
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
