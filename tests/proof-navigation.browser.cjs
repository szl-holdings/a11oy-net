/* Browser regression for the shared proof navigation and reading surface.
 * Run with Playwright available on NODE_PATH. PROOF_BROWSER_EXECUTABLE may
 * select an already installed Chromium. All external requests are blocked;
 * this checks local source behavior, never production/runtime readiness.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const root = process.env.PROOF_BROWSER_ROOT
  ? path.resolve(process.env.PROOF_BROWSER_ROOT) : path.resolve(__dirname, '..');
const assetManifestPath = path.join(root, 'frontend-assets.json');
const assetManifest = fs.existsSync(assetManifestPath)
  ? JSON.parse(fs.readFileSync(assetManifestPath, 'utf8')) : null;
const mime = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.webmanifest': 'application/manifest+json' };
const server = http.createServer((request, response) => {
  let target = path.join(root, decodeURIComponent(new URL(request.url, 'http://localhost').pathname));
  if (target !== root && !target.startsWith(root + path.sep)) {
    response.writeHead(403).end(); return;
  }
  try {
    if (fs.statSync(target).isDirectory()) target = path.join(target, 'index.html');
    response.setHeader('Content-Type', mime[path.extname(target)] || 'application/octet-stream');
    fs.createReadStream(target).pipe(response);
  } catch { response.writeHead(404).end('Not found'); }
});

async function run() {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const artifacts = process.env.PROOF_BROWSER_ARTIFACTS;
  if (artifacts) fs.mkdirSync(artifacts, { recursive: true });
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
  async function pageAt(width, height, pathname = '/', options = {}) {
    const page = await browser.newPage({ viewport: { width, height }, reducedMotion: 'reduce', ...options });
    const errors = [];
    const staleAssetRequests = [];
    page.on('request', request => {
      const url = new URL(request.url());
      if (assetManifest && url.origin === origin && assetManifest.assets[url.pathname.slice(1)]) {
        staleAssetRequests.push(url.pathname);
      }
    });
    page.on('pageerror', error => errors.push(error.message));
    page.on('requestfailed', request => {
      if (new URL(request.url()).origin === origin) errors.push(`${request.url()}: ${request.failure()?.errorText}`);
    });
    await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    await page.goto(origin + pathname, { waitUntil: 'networkidle' });
    page.proofErrors = errors;
    page.staleAssetRequests = staleAssetRequests;
    const variant = options.forcedColors ? '-forced-colors'
      : options.reducedMotion === 'no-preference' ? '-motion'
      : options.javaScriptEnabled === false ? '-no-script' : '';
    if (artifacts) await page.screenshot({ path: path.join(artifacts,
      `${pathname.replace(/[^a-z0-9]/gi, '') || 'root'}-${width}x${height}${variant}.png`) });
    return page;
  }
  try {
    for (const [width, height] of [[320, 740], [390, 844], [768, 1024], [1024, 768], [1440, 1000], [844, 390]]) {
      const page = await pageAt(width, height);
      await inspect(`reachable rail and readable geometry ${width}x${height}`, async () => {
        assert.deepEqual(page.proofErrors, [], 'local source scripts must load without errors');
        assert.deepEqual(page.staleAssetRequests, [], 'staged pages and dynamic loaders must request content-addressed assets');
        const geometry = await page.locator('.szl-proof-rail').evaluate(node => {
          const rect = node.getBoundingClientRect();
          return { top: rect.top, bottom: rect.bottom, width: rect.width,
            viewportWidth: innerWidth, viewportHeight: innerHeight,
            pageWidth: document.documentElement.scrollWidth };
        });
        assert(geometry.top >= 0 && geometry.bottom <= geometry.viewportHeight + 1,
          `journey rail must be in view: ${JSON.stringify(geometry)}`);
        assert(geometry.pageWidth <= width + 1, 'page must not overflow horizontally');
        assert(geometry.width <= width, 'rail must fit viewport');
        if (width <= 820) {
          assert.equal(await page.locator('.szl-proof-links').isVisible(), false,
            'closed menu must hide its links');
          assert.equal(await page.locator('.szl-proof-toggle').getAttribute('aria-expanded'), 'false');
          await page.locator('.szl-proof-toggle').focus();
          await page.keyboard.press('Enter');
          assert.equal(await page.locator('.szl-proof-links').isVisible(), true);
          assert.equal(await page.locator('.szl-proof-toggle').getAttribute('aria-label'), 'Close journey navigation');
          if (artifacts && width === 390) await page.screenshot({ path: path.join(artifacts, 'root-mobile-menu-open.png') });
          await page.keyboard.press('Tab');
          assert.equal(await page.evaluate(() => document.activeElement.classList.contains('szl-proof-link')), true,
            'next Tab after the menu button enters the disclosed links');
          await page.keyboard.press('Escape');
          assert.equal(await page.locator('.szl-proof-links').isVisible(), false);
          assert.equal(await page.evaluate(() => document.activeElement.classList.contains('szl-proof-toggle')), true);
          if (width === 390) {
            await page.keyboard.press('ArrowDown');
            assert.equal(await page.evaluate(() => document.activeElement.classList.contains('szl-proof-link')), true);
            await page.locator('h1').click();
            assert.equal(await page.locator('.szl-proof-links').isVisible(), false,
              'clicking outside dismisses the disclosure');
          }
        } else {
          assert.equal(await page.locator('.szl-proof-toggle').isVisible(), false);
          assert.equal(await page.locator('.szl-proof-links').isVisible(), true);
        }
      });
      if (width === 1440) await inspect('dossier explanations are not visually truncated', async () => {
        const clipped = await page.locator('.dossier-row small').evaluateAll(nodes => nodes
          .filter(node => node.scrollWidth > node.clientWidth + 1 && getComputedStyle(node).overflow === 'hidden')
          .map(node => node.textContent));
        assert.deepEqual(clipped, []);
      });
      await page.close();
    }
    const motion = await pageAt(1440, 1000, '/', { reducedMotion: 'no-preference' });
    await inspect('decorative entry effects never hide evidence sections', async () => {
      const hidden = await motion.locator('main > section').evaluateAll(nodes => nodes
        .filter(node => Number(getComputedStyle(node).opacity) < 1 || getComputedStyle(node).filter !== 'none').map(node => node.id));
      assert.deepEqual(hidden, []);
    });
    await motion.close();
    for (const pathname of ['/record/', '/diligence/']) {
      const page = await pageAt(390, 844, pathname, { javaScriptEnabled: false });
      await inspect(`zero-JavaScript navigation remains usable ${pathname}`, async () => {
        assert.equal(await page.locator('script').count(), 0);
        const links = page.locator('.szl-proof-static-rail .szl-proof-link');
        assert.equal(await links.count(), 5);
        for (const link of await links.all()) assert.equal(await link.isVisible(), true);
        assert.equal(await page.locator('.szl-proof-toggle').count(), 0);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      });
      await page.close();
    }
    const contrast = await pageAt(390, 844, '/', { forcedColors: 'active' });
    await inspect('forced-color menu retains a visible focus indicator', async () => {
      await contrast.locator('.szl-proof-toggle').focus();
      assert.notEqual(await contrast.locator('.szl-proof-toggle').evaluate(node => getComputedStyle(node).outlineStyle), 'none');
    });
    await contrast.close();
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
  console.log(JSON.stringify({ scope: assetManifest ? 'staged Pages artifact; external requests blocked' : 'local source; external requests blocked',
    sourceRevision: assetManifest?.source_revision || null, browser: browser.version(), passed: checks, failed: failures.length, failures }, null, 2));
  if (failures.length) process.exitCode = 1;
}
run().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
