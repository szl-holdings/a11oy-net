/* Browser regression for /estate/plane search focus, its label, and style-src.
 * Serves this checkout on loopback and blocks every external request.
 * Run with Playwright available on NODE_PATH. PROOF_BROWSER_EXECUTABLE may
 * select an already installed Chromium. Checks local source behavior only.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const mime = {
  '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.webmanifest': 'application/manifest+json',
};
const views = ['overview', 'github', 'hub', 'queue', 'fabric', 'passports', 'frontiers'];
let failData = false;

const server = http.createServer((request, response) => {
  const url = new URL(request.url, 'http://127.0.0.1');
  if (failData && url.pathname === '/estate/plane/data.json') {
    response.writeHead(503, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
    response.end('{"error":"UNAVAILABLE"}');
    return;
  }
  let target = path.join(root, decodeURIComponent(url.pathname));
  if (target !== root && !target.startsWith(root + path.sep)) {
    response.writeHead(403).end();
    return;
  }
  try {
    if (fs.statSync(target).isDirectory()) target = path.join(target, 'index.html');
    response.setHeader('Content-Type', mime[path.extname(target)] || 'application/octet-stream');
    response.setHeader('Cache-Control', 'no-store');
    fs.createReadStream(target).pipe(response);
  } catch {
    response.writeHead(404).end('Not found');
  }
});

async function run() {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.PROOF_BROWSER_EXECUTABLE || undefined,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  let checks = 0;
  const failures = [];
  const inspect = async (name, callback) => {
    try { await callback(); checks += 1; console.log(`PASS ${name}`); }
    catch (error) { failures.push(`${name}: ${error.message}`); console.error(`FAIL ${name}: ${error.message}`); }
  };

  async function openView(hash) {
    const page = await browser.newPage();
    const violations = [];
    page.on('console', message => {
      if (/content security policy/i.test(message.text())) violations.push(message.text());
    });
    await page.route('**/*', route => {
      return new URL(route.request().url()).origin === origin ? route.continue() : route.abort();
    });
    await page.goto(`${origin}/estate/plane/${hash}`, { waitUntil: 'load' });
    await page.waitForFunction(() => {
      const text = document.querySelector('#app')?.textContent || '';
      return text.length > 0 && !text.includes('Loading estate plane');
    });
    await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 50)));
    page.cspViolations = violations;
    return page;
  }

  try {
    for (const view of views) {
      const page = await openView(`#/${view}`);
      await inspect(`${view} has zero CSP console violations`, async () => {
        assert.deepEqual(page.cspViolations, [], 'style-src \'self\' rejects inline style attributes');
      });
      if (view === 'github') {
        await inspect('typing sz keeps the value and focus on #q', async () => {
          const box = page.locator('#q');
          await box.click();
          await page.keyboard.type('sz');
          assert.equal(await box.inputValue(), 'sz');
          assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.id), 'q');
          assert.deepEqual(page.cspViolations, []);
        });
        await inspect('Filter this list labels exactly one control', async () => {
          assert.equal(await page.getByLabel('Filter this list').count(), 1);
        });
      }
      await page.close();
    }

    failData = true;
    const unavailable = await openView('#/overview');
    await inspect('a 503 bake fails closed with an alert', async () => {
      const alert = unavailable.getByRole('alert');
      await alert.waitFor();
      assert.match((await alert.innerText()).trim(), /^Bake UNAVAILABLE/);
    });
    await unavailable.close();
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
  console.log(JSON.stringify({
    scope: 'local source; external requests blocked',
    browser: browser.version(),
    passed: checks,
    failed: failures.length,
    failures,
  }, null, 2));
  if (failures.length) process.exitCode = 1;
}

run().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
