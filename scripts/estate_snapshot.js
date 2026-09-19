(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SZLEstateSnapshot = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const DAY_MS = 24 * 60 * 60 * 1000;
  function safePath(pointer) {
    return pointer && typeof pointer.path === 'string' &&
      /^\/estate-observed-\d{4}-\d{2}-\d{2}\.json$/.test(pointer.path) ? pointer.path : null;
  }
  function evaluate(pointer, record, actualHash, now) {
    const unavailable = { state: 'UNAVAILABLE', reason: 'Snapshot binding could not be verified.' };
    if (!pointer || !record || !safePath(pointer) || !Number.isFinite(now) ||
        pointer.schema !== 'szl.proof-snapshot-pointer/v1' ||
        record.schema !== 'szl.proof-estate-observation/v1' ||
        record.scope !== 'public_repositories_only' || record.production_authorization !== false ||
        !/^[a-f0-9]{64}$/.test(pointer.sha256 || '') || pointer.sha256 !== actualHash ||
        pointer.captured_at !== record.captured_at ||
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(record.captured_at || '')) return unavailable;
    const captured = Date.parse(record.captured_at);
    if (!Number.isFinite(captured) || new Date(captured).toISOString() !== record.captured_at.replace('Z', '.000Z') || captured > now) return unavailable;
    const age = now - captured;
    return {
      state: age > DAY_MS ? 'STALE' : 'SNAPSHOT',
      reason: age > DAY_MS ? 'This observation is over 24 hours old.' : 'Dated observation; not live runtime or release approval.',
      captured_at: record.captured_at,
      age_hours: Math.floor(age / 3600000),
      path: pointer.path,
    };
  }
  async function readJson(url, fetcher, maxBytes) {
    const response = await fetcher(url, { cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(10000) });
    if (!response.ok || !(response.headers.get('content-type') || '').toLowerCase().includes('json')) throw new Error('snapshot_response_unavailable');
    const reader = response.body.getReader();
    const chunks = []; let total = 0;
    try {
      while (true) {
        const part = await reader.read();
        if (part.done) break;
        total += part.value.byteLength;
        if (total > maxBytes) throw new Error('snapshot_response_oversized');
        chunks.push(part.value);
      }
    } finally {
      await reader.cancel().catch(function () {});
    }
    const bytes = new Uint8Array(total); let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    return { bytes: bytes, data: JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)) };
  }
  async function load(fetcher, cryptoProvider, now) {
    try {
      const pointer = (await readJson('/estate-current.json', fetcher, 4096)).data;
      const path = safePath(pointer);
      if (!path || !cryptoProvider || !cryptoProvider.subtle) throw new Error('snapshot_binding_unavailable');
      const response = await readJson(path, fetcher, 512 * 1024);
      const hash = Array.from(new Uint8Array(await cryptoProvider.subtle.digest('SHA-256', response.bytes)))
        .map(function (b) { return b.toString(16).padStart(2, '0'); }).join('');
      return evaluate(pointer, response.data, hash, now);
    } catch (_error) {
      return { state: 'UNAVAILABLE', reason: 'Snapshot fetch or verification failed; use the dated records below.' };
    }
  }
  if (typeof document === 'object') {
    const node = document.getElementById('estate-snapshot-state');
    if (node) {
      const refresh = function () {
        load(globalThis.fetch.bind(globalThis), globalThis.crypto, Date.now()).then(function (result) {
          node.textContent = result.state + ' — ' + result.reason +
            (result.captured_at ? ' Captured ' + result.captured_at + '; age ' + result.age_hours + 'h.' : '');
          node.dataset.state = result.state;
        });
      };
      refresh();
      // Re-evaluate age without reloading the reader's page.
      setInterval(refresh, 60000);
    }
  }
  return { safePath: safePath, evaluate: evaluate, load: load };
});
