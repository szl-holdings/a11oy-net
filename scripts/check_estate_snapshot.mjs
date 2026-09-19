import assert from 'node:assert/strict';
import { createHash, webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import policy from './estate_snapshot.js';

const now = Date.parse('2026-09-19T18:00:00Z');
const digest = 'a'.repeat(64);
const pointer = {
  schema: 'szl.proof-snapshot-pointer/v1',
  path: '/estate-observed-2026-09-19.json',
  sha256: digest,
  captured_at: '2026-09-19T14:48:19Z',
  scope: 'public_repositories_only',
};
const record = {
  schema: 'szl.proof-estate-observation/v1',
  captured_at: pointer.captured_at,
  scope: 'public_repositories_only',
  production_authorization: false,
  github: { scope: 'explicitly_public_repositories' },
  hugging_face: { scope: 'anonymous_public_listing' },
};
assert.equal(policy.evaluate(pointer, record, digest, now).state, 'SNAPSHOT');
assert.equal(policy.evaluate(pointer, record, digest, now + 86400000).state, 'STALE');
assert.equal(policy.evaluate(pointer, record, digest, NaN).state, 'UNAVAILABLE');
assert.equal(policy.evaluate(pointer, record, 'b'.repeat(64), now).state, 'UNAVAILABLE');
assert.equal(policy.evaluate(pointer, { ...record, production_authorization: true }, digest, now).state, 'UNAVAILABLE');
assert.equal(policy.evaluate(pointer, { ...record, scope: 'authenticated' }, digest, now).state, 'UNAVAILABLE');
assert.equal(policy.evaluate({ ...pointer, scope: 'authenticated' }, record, digest, now).state, 'UNAVAILABLE');
assert.equal(policy.evaluate(pointer, { ...record, github: { scope: 'authenticated' } }, digest, now).state, 'UNAVAILABLE');
assert.equal(policy.evaluate(pointer, { ...record, hugging_face: { scope: 'authenticated' } }, digest, now).state, 'UNAVAILABLE');
assert.equal(policy.evaluate(pointer, { ...record, github: null }, digest, now).state, 'UNAVAILABLE');
assert.equal(policy.evaluate(pointer, { ...record, hugging_face: null }, digest, now).state, 'UNAVAILABLE');
assert.equal(policy.evaluate(pointer, { ...record, captured_at: '2026-09-19T15:00:00Z' }, digest, now).state, 'UNAVAILABLE');
assert.equal(policy.evaluate(pointer, record, digest, now - 86400000).state, 'UNAVAILABLE');
for (const path of ['https://example.org/record.json', '//example.org/record.json', '/../record.json', '/%2e%2e/record.json', '/estate-observed-2026-09-19.json?x=1']) {
  assert.equal(policy.safePath({ ...pointer, path }), null, path);
}
const invalidDate = '2026-02-30T12:00:00Z';
assert.equal(policy.evaluate({ ...pointer, captured_at: invalidDate }, { ...record, captured_at: invalidDate }, digest, now).state, 'UNAVAILABLE');

// The shipped pointer must bind the exact committed bytes, and the page must
// visibly separate this observation from its preserved historical table.
const root = new URL('../', import.meta.url);
const shippedPointer = JSON.parse(readFileSync(new URL('estate-current.json', root), 'utf8'));
const path = policy.safePath(shippedPointer);
assert.ok(path);
const bytes = readFileSync(new URL(path.slice(1), root));
const shippedRecord = JSON.parse(bytes);
const hash = createHash('sha256').update(bytes).digest('hex');
assert.equal(policy.evaluate(shippedPointer, shippedRecord, hash, Date.parse(shippedRecord.captured_at)).state, 'SNAPSHOT');
assert.equal(shippedRecord.hugging_face.scope, 'anonymous_public_listing');
assert.equal(shippedRecord.github.scope, 'explicitly_public_repositories');
const html = readFileSync(new URL('status/index.html', root), 'utf8');
assert.ok(html.includes('id="estate-snapshot-state"'));
assert.ok(html.includes('/estate-current.json'));
assert.ok(html.includes('Historical observation'));
const evidence = JSON.parse(readFileSync(new URL('evidence.json', root), 'utf8'));
assert.ok(evidence.entrypoints.some(x => x.name === 'latest_estate_observation' && x.url === 'https://a11oy.net/estate-current.json'));
assert.ok(!evidence.entrypoints.find(x => x.name === 'origin_lock_contract').scope.includes('www Cloudflare 404'));
// Exercise the actual bounded fetch/digest path, not only the pure policy.
const jsonResponse = body => new Response(body, { headers: { 'Content-Type': 'application/json' } });
const fetchSnapshot = async (url, options) => {
  assert.equal(options.cache, 'no-store');
  assert.equal(options.redirect, 'error');
  assert.ok(options.signal instanceof AbortSignal);
  return jsonResponse(url === '/estate-current.json' ? JSON.stringify(shippedPointer) : bytes);
};
assert.equal((await policy.load(fetchSnapshot, webcrypto, now)).state, 'SNAPSHOT');
assert.equal((await policy.load(fetchSnapshot, webcrypto, now + 86400000)).state, 'STALE');
assert.equal((await policy.load(fetchSnapshot, null, now)).state, 'UNAVAILABLE');
for (const fetcher of [
  async () => { throw new Error('offline'); },
  async () => new Response('missing', { status: 404 }),
  async () => new Response('{}', { headers: { 'Content-Type': 'text/html' } }),
  async () => jsonResponse('{'),
  async () => jsonResponse(' '.repeat(4097)),
  async url => jsonResponse(url === '/estate-current.json' ? JSON.stringify(shippedPointer) : ' '.repeat(512 * 1024 + 1)),
  async url => jsonResponse(url === '/estate-current.json' ? JSON.stringify(shippedPointer) : JSON.stringify({ ...shippedRecord, altered: true })),
  async () => jsonResponse(new Uint8Array([0xff])),
]) {
  assert.equal((await policy.load(fetcher, webcrypto, now)).state, 'UNAVAILABLE');
}
console.log('PASS: snapshot digest, scope, age, future-date, path confinement, and published-page contracts');
