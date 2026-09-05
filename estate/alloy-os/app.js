/* SPDX-License-Identifier: Apache-2.0 */
'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function loadJSON(url) {
  const response = await fetch(url, {cache:'no-store', credentials:'omit', signal:AbortSignal.timeout(10000)});
  if (!response.ok) throw new Error('Snapshot unavailable (HTTP ' + response.status + ')');
  return response.json();
}
function safeLink(value) {
  try { const url = new URL(String(value), location.href); return url.protocol === 'https:' ? url.href : null; }
  catch (_) { return null; }
}
async function bootAlignment() {
  const rail = $('bake-rail'), table = $('align-table');
  if (!rail || !table) return;
  try {
    const live = await loadJSON('./live.json');
    const honest = live.product_honest?.doctrine_lock || {};
    const hf = live.hf_unauth || {};
    const rows = [
      ['Doctrine snapshot', honest.state ?? 'UNAVAILABLE', 'v11 ' + (honest.commit || '')],
      ['Locked formulas snapshot', honest.locked_formula_count ?? 'UNAVAILABLE', (honest.locked_formula_ids || []).join(' ')],
      ['Kept Spaces snapshot', Array.isArray(live.keep_spaces) ? live.keep_spaces.length : 'UNAVAILABLE', 'Baked inventory; not current uptime'],
      ['Listed Hub Spaces snapshot', Array.isArray(hf.spaces) ? hf.spaces.length : 'UNAVAILABLE', 'Unauthenticated inventory snapshot'],
      ['Hub models / datasets snapshot', (hf.models_listed ?? 'UNAVAILABLE') + ' / ' + (hf.datasets_listed ?? 'UNAVAILABLE'), 'Recorded counts; not current runtime evidence']
    ];
    rail.innerHTML = rows.map(([key,value,detail]) => `<article><span>${esc(key)}</span><b>${esc(value)}</b><p>${esc(detail)}</p></article>`).join('');
    const align = Array.isArray(live.alignment) ? live.alignment : [];
    table.innerHTML = `<p>RECORD — source locations and saved observations, not a live service certification.</p><table class="align"><thead><tr><th>Plane</th><th>Class</th><th>Bind</th></tr></thead><tbody>${align.map(row => {
      const url = safeLink(row.url);
      const link = url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(url)}</a>` : 'UNAVAILABLE';
      return `<tr><td>${esc(row.plane)}<br>${link}</td><td>${esc(row.class)}</td><td>${esc(row.note)}</td></tr>`;
    }).join('')}</tbody></table>`;
  } catch (error) {
    rail.textContent = 'Alignment snapshot UNAVAILABLE.';
    table.textContent = error.message;
  }
}
const compose = {title:'Session note', body:'A thought sealed on this device.', adapter:'alloy-local-v1', msg:'', tone:'', busy:false};
function renderKernel() {
  const el = $('kernel-app');
  if (!el || typeof Alloy === 'undefined') return;
  const receipts = Alloy.receipts.slice(-8).reverse().map(row => `<li>#${row.seq} <b>${esc(row.type)}</b> ${esc(row.note)} <span>${esc(Alloy.shortHex(row.digest))}</span></li>`).join('');
  const capsules = Alloy.capsules.slice(-6).reverse().map(row => `<li>${esc(row.title)} · ${esc(row.status)} · ${esc(Alloy.shortHex(row.digest))}</li>`).join('');
  const disabled = compose.busy || ['NOT_STARTED','UNAVAILABLE'].includes(Alloy.status) ? ' disabled' : '';
  el.innerHTML = `<div class="kbox"><div class="kcard">
    <p class="eyebrow">${esc(Alloy.status)} · kid ${esc(Alloy.identity?.kid || 'unavailable')} · epoch ${Alloy.epoch}</p>
    <label for="ktitle">Title (encrypted with payload)</label><input id="ktitle" maxlength="200" value="${esc(compose.title)}">
    <label for="kbody">Payload (local only)</label><textarea id="kbody" maxlength="32768">${esc(compose.body)}</textarea>
    <label for="kadapter">Adapter</label><select id="kadapter"><option value="${Alloy.ADAPTER_CURRENT}">${Alloy.ADAPTER_CURRENT} pinned</option><option value="alloy-local-v0"${compose.adapter === 'alloy-local-v0' ? ' selected' : ''}>alloy-local-v0 stale — rejected</option></select>
    <div class="kactions"><button class="button primary" id="ksubmit"${disabled}>Submit envelope</button><button class="button" id="ktamper"${disabled}>Test one-byte fault</button><button class="button" id="kheal"${disabled}>Verify and restore snapshot</button></div>
    <p role="status" aria-live="polite" class="${esc(compose.tone)}">${esc(compose.msg)}</p>
    <p>Private keys remain nonextractable in this origin's IndexedDB. Clearing browser data loses the local state. Same-origin scripts remain inside the trust boundary.</p>
  </div><div class="kcard"><p class="eyebrow">Local ledger ${Alloy.receipts.length} · capsules ${Alloy.capsules.length} · restored ${Alloy.health.healed} · blocked ${Alloy.health.blocked}</p>
    <p>Local chain verified: ${Alloy.health.ledgerReplayable ? 'MEASURED' : 'UNAVAILABLE'} · last verify ${esc(Alloy.health.lastVerify || '—')}</p><ol class="klog">${receipts || '<li>No local receipts yet.</li>'}</ol><p class="eyebrow">Capsules</p><ol class="klog">${capsules || '<li>None.</li>'}</ol>
    <p>Signatures establish local byte integrity, not semantic truth or product readiness. Restoration cannot repair a forged receipt chain or a missing verified snapshot.</p></div></div>`;
  async function action(operation) {
    if (compose.busy) return;
    compose.title = $('ktitle').value; compose.body = $('kbody').value; compose.adapter = $('kadapter').value;
    compose.busy = true; compose.msg = 'Working locally…'; compose.tone = ''; renderKernel();
    try { compose.msg = await operation(); compose.tone = compose.msg.startsWith('DENY') ? 'bad' : Alloy.status === 'DEGRADED' ? 'warn' : 'ok'; }
    catch (error) { compose.msg = 'UNAVAILABLE — ' + error.message; compose.tone = 'bad'; }
    finally { compose.busy = false; renderKernel(); }
  }
  $('ksubmit').onclick = () => action(async () => {
    const out = await Alloy.govern({title:compose.title,body:compose.body,adapter:compose.adapter,policyClass:'private'});
    return out.decision + ' — ' + out.reason + ' · local receipt ' + out.receipt.seq;
  });
  $('ktamper').onclick = () => action(() => Alloy.injectFault());
  $('kheal').onclick = () => action(async () => { const out = await Alloy.runWatchdog(); return 'Verified local chain; restored ' + out.restored + ' authenticated ciphertext snapshot(s).'; });
}
void bootAlignment();
if (typeof Alloy === 'undefined') {
  if ($('kernel-app')) $('kernel-app').textContent = 'UNAVAILABLE — the local kernel asset did not load. No data was stored.';
} else {
  Alloy.subscribe(renderKernel);
  Alloy.boot().then(renderKernel).catch(error => {
    if ($('kernel-app')) $('kernel-app').textContent = 'UNAVAILABLE — ' + error.message + '. Existing local state was not reset.';
  });
}
