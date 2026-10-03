import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash, webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
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
// Pages is built from immutable Git blobs, so validate the exact published
// bytes rather than a checkout that may have platform newline conversion.
const bytes = execFileSync('git', [
  '-C', fileURLToPath(root), 'show', `HEAD:${path.slice(1)}`,
]);
const shippedRecord = JSON.parse(bytes);
const hash = createHash('sha256').update(bytes).digest('hex');
assert.equal(policy.evaluate(shippedPointer, shippedRecord, hash, Date.parse(shippedRecord.captured_at)).state, 'SNAPSHOT');
assert.equal(shippedRecord.hugging_face.scope, 'anonymous_public_listing');
assert.equal(shippedRecord.github.scope, 'explicitly_public_repositories');
assert.equal(shippedPointer.path, '/estate-observed-2026-10-02.json');
assert.equal(shippedRecord.github.repositories, 127);
assert.equal(shippedRecord.github.pagination_complete, true);
assert.equal(shippedRecord.github.page_lengths.reduce((sum, count) => sum + count, 0), shippedRecord.github.repositories);
assert.equal(shippedRecord.github.default_branch_files_enumerated, null);
assert.equal(shippedRecord.github.text_files_scanned, null);
assert.equal(shippedRecord.hugging_face.models, 47);
assert.equal(shippedRecord.hugging_face.datasets, 36);
assert.equal(shippedRecord.hugging_face.spaces_author_api, 33);
assert.equal(shippedRecord.hugging_face.organization_profile_space_rows, 1);
assert.equal(shippedRecord.hugging_face.spaces_public_projection,
  shippedRecord.hugging_face.spaces_author_api + shippedRecord.hugging_face.organization_profile_space_rows);
assert.equal(shippedRecord.hugging_face.kernels, 14);
assert.equal(shippedRecord.hugging_face.collections, 7);
assert.equal(shippedRecord.hugging_face.buckets, 2);
assert.equal(shippedRecord.hugging_face.private_assets, 'NOT_OBSERVED');
assert.equal(shippedRecord.hugging_face.pagination_complete, true);
assert.equal(shippedRecord.hugging_face.next_page_links_observed, false);
assert.equal(shippedRecord.observation_date_local, '2026-10-02');
assert.equal(shippedRecord.observation_timezone, 'America/New_York');
assert.ok(Date.parse(shippedRecord.collection_completed_at) >= Date.parse(shippedRecord.captured_at));
assert.equal(shippedRecord.product_readiness_observation.source_revision_matches_runtime, false);
assert.notEqual(shippedRecord.product_readiness_observation.source_revision,
  shippedRecord.product_readiness_observation.observed_runtime_revision);
assert.equal(shippedRecord.product_readiness_observation.probe_verdict_available, false);
assert.equal(shippedRecord.proof_origin_observation.source_to_deployment_equivalence, 'EXACT_SOURCE_REVISION_OBSERVED');
assert.equal(shippedRecord.proof_origin_observation.live_static_health_matches_current_source, true);
assert.equal(shippedRecord.proof_origin_observation.live_static_health_sha,
  shippedRecord.proof_origin_observation.source_revision);
assert.equal(shippedRecord.proof_origin_observation.github_pages_certificate_state, 'bad_authz');
assert.equal(shippedRecord.proof_origin_observation.live_security_headers_present, false);
assert.equal(shippedRecord.proof_origin_observation.github_pages_https_enforced, false);

// A successful release must bind its CPU witness to the published v1 commit,
// and its source and signer to the release's historical publisher revision.
// A later Forge main revision must not silently replace that release identity.
function validateKernelRelease(release) {
  const sha = /^[a-f0-9]{40}$/;
  const digest = /^[a-f0-9]{64}$/;
  assert.equal(release.status, 'PUBLISHED_AND_EXACT_READBACK_VERIFIED');
  assert.equal(release.run_conclusion, 'success');
  assert.match(release.source_revision, sha);
  assert.match(release.release_publisher_revision, sha);
  assert.equal(release.authorization.source_revision, release.source_revision);
  assert.equal(release.authorization.publisher_revision, release.release_publisher_revision);
  assert.equal(release.authorization.status, 'AUTHORIZED_PROTECTED_MAIN');
  assert.equal(release.authorization.persistent_hub_secret_used, false);
  assert.equal(release.release_publisher_is_current,
    release.release_publisher_revision === release.publisher_current_source_revision);
  assert.match(release.artifact.sha256, digest);
  assert.match(release.artifact.source_binding_report_sha256, digest);
  assert.equal(release.first_class_kernel.repo_type, 'kernel');
  for (const branch of ['main', 'v1']) {
    assert.match(release.first_class_kernel.branches_after[branch], sha);
    assert.equal(release.first_class_kernel.readback[branch], 'EXACT_BYTES_VERIFIED');
  }
  const runtime = release.first_class_kernel.runtime;
  assert.equal(runtime.revision, release.first_class_kernel.branches_after.v1);
  assert.equal(runtime.status, 'STABLE_GET_KERNEL_VERIFIED');
  assert.equal(runtime.device, 'cpu');
  assert.equal(runtime.selfcheck_ok, true);
  assert.equal(runtime.retrieval_chain_verified, true);
  assert.equal(runtime.retrieval_receipt_authenticity, 'UNSIGNED');
  assert.equal(runtime.retrieval_quality, 'NOT_MEASURED');
  assert.equal(runtime.gpu_acceleration_claim, false);
  const signature = release.first_class_kernel.signature;
  assert.equal(signature.status, 'SIGNED_AND_IDENTITY_VERIFIED');
  assert.equal(signature.publisher_revision, release.release_publisher_revision);
  assert.equal(signature.certificate_identity,
    'https://github.com/szl-holdings/szl-forge/.github/workflows/publish-szl-kernels.yml@refs/heads/main');
  assert.equal(signature.oidc_issuer, 'https://token.actions.githubusercontent.com');
  assert.match(signature.bundle_sha256, digest);
  assert.match(signature.metadata_sha256, digest);
  const mirror = release.legacy_model_mirror;
  assert.equal(mirror.repo_type, 'model');
  assert.equal(mirror.readback, 'EXACT_BYTES_VERIFIED');
  assert.equal(mirror.independent_readback.revision, mirror.revision_after);
  assert.equal(mirror.independent_readback.files_checked, mirror.declared_file_count);
  assert.equal(mirror.independent_readback.files_matched, mirror.declared_file_count);
  assert.match(mirror.independent_readback.report_sha256, digest);
}
validateKernelRelease(shippedRecord.kernel_release_observation);
for (const mutate of [
  release => { release.first_class_kernel.runtime.revision = '0'.repeat(40); },
  release => { release.authorization.source_revision = '0'.repeat(40); },
  release => { release.first_class_kernel.signature.publisher_revision = release.publisher_current_source_revision; },
  release => { release.legacy_model_mirror.independent_readback.files_matched -= 1; },
  release => { release.first_class_kernel.runtime.gpu_acceleration_claim = true; },
]) {
  const altered = structuredClone(shippedRecord.kernel_release_observation);
  mutate(altered);
  assert.throws(() => validateKernelRelease(altered));
}
const html = readFileSync(new URL('status/index.html', root), 'utf8');
assert.ok(html.includes('id="estate-snapshot-state"'));
assert.ok(html.includes('/estate-current.json'));
assert.ok(html.includes('/estate-observed-2026-09-30.json'));
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
const shippedNow = Date.parse(shippedRecord.captured_at);
assert.equal((await policy.load(fetchSnapshot, webcrypto, shippedNow)).state, 'SNAPSHOT');
assert.equal((await policy.load(fetchSnapshot, webcrypto, shippedNow + 86400001)).state, 'STALE');
assert.equal((await policy.load(fetchSnapshot, null, shippedNow)).state, 'UNAVAILABLE');
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
  assert.equal((await policy.load(fetcher, webcrypto, shippedNow)).state, 'UNAVAILABLE');
}
console.log('PASS: snapshot digest, scope, age, future-date, path confinement, and published-page contracts');
