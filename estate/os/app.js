const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const esc = (s) =>
  String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll(String.fromCharCode(34), "&quot;");

let DATA = null;
let view = "overview";
let slug = "";
let githubQ = "";
let githubClass = "all";
let hubKind = "all";
let ring = "all";
let selectedFrontier = "szl-frontier";
let selectedPassport = null;
let minted = [];
let lastMinted = null;
let paletteOpen = false;
let paletteQ = "";
let paletteIdx = 0;

const VIEWS = ["overview", "github", "hub", "queue", "fabric", "passports", "frontiers"];

function truth(t) {
  return `<span class="truth t-${esc(t)}">${esc(t)}</span>`;
}

function ghUrl(name) {
  return `https://github.com/szl-holdings/${encodeURIComponent(name)}`;
}

function hubUrl(h) {
  const ns = h.kind === "dataset" ? "datasets" : h.kind === "space" ? "spaces" : "";
  return ns
    ? `https://huggingface.co/${ns}/${h.id}`
    : `https://huggingface.co/${h.id}`;
}

function passports() {
  return minted;
}

function counts() {
  return DATA.counts;
}

function route() {
  const h = (location.hash || "#/overview").replace(/^#\/?/, "");
  const parts = h.split("/").filter(Boolean);
  view = VIEWS.includes(parts[0]) ? parts[0] : "overview";
  slug = parts[1] || "";
  if (view === "frontiers" && slug) selectedFrontier = slug;
  if (view === "passports" && slug) selectedPassport = slug;
  paletteOpen = false;
  render();
}

function go(hash) {
  if (location.hash === hash) route();
  else location.hash = hash;
}

function commands() {
  const cmds = [
    { g: "Go", id: "overview", label: "Overview", run: () => go("#/overview") },
    { g: "Go", id: "github", label: "GitHub inventory", run: () => go("#/github") },
    { g: "Go", id: "hub", label: "Hub inventory", run: () => go("#/hub") },
    { g: "Go", id: "queue", label: "Work queue", run: () => go("#/queue") },
    { g: "Go", id: "fabric", label: "Seven-lane fabric", run: () => go("#/fabric") },
    { g: "Go", id: "passports", label: "Action passports", run: () => go("#/passports") },
    { g: "Go", id: "frontiers", label: "Frontiers", run: () => go("#/frontiers") },
    { g: "Go", id: "estate", label: "Dated estate snapshot", run: () => { location.href = "/estate/"; } },
    { g: "Go", id: "product", label: "Product origin a-11-oy.com", run: () => window.open("https://a-11-oy.com", "_blank", "noopener") },
  ];
  for (const q of DATA.queue) {
    cmds.push({
      g: "Propose",
      id: `q-${q.id}`,
      label: `Propose · ${q.title}`,
      run: () => mintFromQueue(q),
    });
  }
  for (const f of DATA.frontiers) {
    if (f.gate === "LOCKED") {
      cmds.push({
        g: "Withhold",
        id: `f-${f.id}`,
        label: `Withhold · ${f.name} (LOCKED)`,
        run: () => withholdFrontier(f),
      });
    } else {
      cmds.push({
        g: "Frontiers",
        id: `f-${f.id}`,
        label: `Open · ${f.name}`,
        run: () => go(`#/frontiers/${f.id}`),
      });
    }
  }
  const q = paletteQ.trim().toLowerCase();
  return q ? cmds.filter((c) => `${c.g} ${c.label}`.toLowerCase().includes(q)) : cmds;
}

function mintPassport(input) {
  const now = new Date().toISOString();
  const id = `cap-propose-${Math.random().toString(36).slice(2, 10)}`;
  const p = {
    schema: "szl.counterfactual-action-passport/v1",
    passport_id: id,
    recorded_at: now,
    identity: {
      agent_id: "estate-os.hologram",
      principal_id: "local-operator",
      session_id: "browser",
      delegation_chain: ["local-operator", "estate-os.hologram"],
    },
    authority: {
      parent_scopes: ["estate.propose"],
      child_scopes: ["estate.propose"],
      tool: "estate.mint_passport",
      resource: input.resource,
      constraints: ["propose-only", "no-mutation", "session-only"],
    },
    evidence: {
      claims: [
        {
          claim_id: "claim-hologram",
          label: "MODELED",
          source_refs: ["operator-session", "a11oy.net/estate/os"],
          observed_at: now,
          digest_sha256: "0".repeat(64),
        },
      ],
      graph_sha3_256: "e".repeat(64),
    },
    policy_decision: input.decision || "REQUIRE_APPROVAL",
    human_oversight: {
      state: "PENDING",
      approver_id: null,
      recorded_at: null,
      approval_receipt_sha256: null,
    },
    expected_if_acted: {
      statement: input.acted,
      confidence_0_to_1: 0.5,
      evidence_claim_ids: ["claim-hologram"],
      recorded_at: now,
    },
    expected_if_withheld: {
      statement: input.withheld,
      confidence_0_to_1: 0.5,
      evidence_claim_ids: ["claim-hologram"],
      recorded_at: now,
    },
    action: {
      action_id: `act-${id}`,
      kind: "proposal",
      target: input.resource,
      parameters_sha3_256: "f".repeat(64),
      requested_at: now,
      executed_at: null,
      state: input.state || "PROPOSED",
    },
    outcome: {
      state: "NOT_MEASURED",
      measured_at: null,
      metrics: {},
      evidence_sha3_256: null,
    },
    rollback: {
      available: false,
      plan_sha3_256: null,
      state: "NOT_REQUIRED",
      executed_at: null,
    },
    signature: {
      state: "UNSIGNED",
      algorithm: null,
      digest_algorithm: "sha3-256",
      payload_sha3_256: "c".repeat(64),
      key_id: null,
      signature_b64: null,
      dsse_envelope_sha256: null,
      w3c_vc_sha256: null,
    },
    trust_factor_delta: 0,
    valid: true,
    veto: input.veto || null,
  };
  minted = [p, ...minted];
  lastMinted = id;
  selectedPassport = id;
  go(`#/passports/${id}`);
}

function mintFromQueue(item) {
  mintPassport({
    resource: `github:szl-holdings/${item.repo}`,
    acted: `If acted, "${item.title}" would still be a proposal. This hologram cannot merge, archive, or rename.`,
    withheld: `If withheld, ${item.id} stays on the queue. Fail-closed is the honest default.`,
    decision: "REQUIRE_APPROVAL",
  });
}

function proposeFrontier(f) {
  if (f.gate === "LOCKED") return withholdFrontier(f);
  mintPassport({
    resource: f.repo ? `github:szl-holdings/${f.repo}` : f.name,
    acted: f.ifPromoted,
    withheld: f.ifWithheld,
    decision: f.gate === "BLOCK" ? "BLOCK" : "REQUIRE_APPROVAL",
  });
}

function withholdFrontier(f) {
  mintPassport({
    resource: f.repo ? `github:szl-holdings/${f.repo}` : f.name,
    acted: f.ifPromoted,
    withheld: f.ifWithheld,
    decision: "BLOCK",
    state: "WITHHELD",
    veto: f.blocker,
  });
}

function renderOverview() {
  const c = counts();
  const later = DATA.laterRecapture;
  const bets = DATA.frontiers.filter((f) => ["szl-frontier", "nexus", "lambda"].includes(f.id));
  return `
    <p class="os-kicker">Overview · ${esc(DATA.scope)} · not a live dashboard</p>
    <h2 class="os-h2">Public inventory, fail-closed.</h2>
    <p class="os-lede">Bake ${esc(DATA.capturedAt)}. GitHub ${c.githubObserved} OBSERVED (${c.publicRepos} not archived, ${c.archived} ARCHIVED) plus ${c.privateUnavailable} private UNAVAILABLE. Hub ${c.hub.models} / ${c.hub.datasets} / ${c.hub.spaces} with ${c.hub.kernelsMisplaced} kernels still in the model namespace.</p>
    <div class="rail" style="margin:22px 0 0">
      <article><span>GitHub OBSERVED</span><b>${c.githubObserved}</b><p>${c.publicRepos} live public · ${c.archived} archived · ${c.privateUnavailable} private unnamed.</p></article>
      <article><span>Hub listing</span><b>${c.hub.models} / ${c.hub.datasets} / ${c.hub.spaces}</b><p>14 KERNEL cards occupy the model journey.</p></article>
      <article><span>Open queue</span><b>${c.openQueue}</b><p>${c.p0} P0. Mutations mint passports only.</p></article>
      <article><span>Production</span><b>BLOCKED</b><p>Trusted key maps are empty.</p></article>
    </div>
    <div class="blocked"><strong>PRODUCTION BLOCKED.</strong> ${esc(DATA.productionBlocker)}</div>
    <div class="handoff-line" style="margin-top:18px">
      <span class="empty-kicker">Later recapture · do not overwrite</span>
      ${esc(later.source)} at ${esc(later.capturedAt)} MEASURED GitHub search ${later.githubSearchTotal}, Hub ${later.huggingface.models}/${later.huggingface.datasets}/${later.huggingface.spaces_total} with ${later.huggingface.spaces_public} public Spaces. This hologram keeps the 16:49Z PUBLIC_PARTIAL bake and labels the drift.
    </div>
    <div class="os-kicker" style="margin-top:2rem">Origin drift · three origins, not four</div>
    <div class="os-grid three">
      ${DATA.domains.map((d) => `<article class="os-card"><p class="os-kicker">${esc(d.host)}</p><h3>${esc(d.required)}</h3><p>${esc(d.role)}</p></article>`).join("")}
    </div>
    <div class="os-kicker" style="margin-top:2rem">Frontier teaser</div>
    <div class="os-grid three">
      ${bets.map((f) => `<button type="button" class="os-card" data-go="#/frontiers/${esc(f.id)}"><p class="os-kicker">${esc(f.ring)} · ${esc(f.gate)}</p><h3>${esc(f.name)}</h3><p>${esc(f.role)}</p>${truth(f.truth)}</button>`).join("")}
    </div>`;
}

function renderGithub() {
  const classes = ["all", ...new Set(DATA.repos.map((r) => r.class))];
  const q = githubQ.trim().toLowerCase();
  const rows = DATA.repos.filter((r) => {
    if (githubClass !== "all" && r.class !== githubClass) return false;
    if (!q) return true;
    return `${r.name} ${r.description} ${r.role} ${(r.topics || []).join(" ")}`.toLowerCase().includes(q);
  });
  return `
    <p class="os-kicker">GitHub · szl-holdings · OBSERVED</p>
    <h2 class="os-h2">${counts().githubObserved} public records. ${counts().privateUnavailable} private unnamed.</h2>
    <p class="os-lede">Private repository names are not listed. 401/403/429 would be UNAVAILABLE, not BROKEN, and are not probed from this static origin.</p>
    <input class="os-search" id="ghq" type="search" value="${esc(githubQ)}" placeholder="Search repositories" aria-label="Search repositories" />
    <div class="os-row" id="gh-classes">
      ${classes.map((c) => `<button type="button" class="os-chip ${githubClass === c ? "on" : ""}" data-class="${esc(c)}">${esc(c)}</button>`).join("")}
    </div>
    <p class="muted mono" style="margin-top:12px">${rows.length} shown</p>
    <div class="os-table-wrap">
      <table class="os-table">
        <thead><tr><th>Name</th><th>Class</th><th>Role</th><th>Lang</th><th>Issues</th><th>Truth</th></tr></thead>
        <tbody>
          ${rows.map((r) => `<tr>
            <td><a href="${ghUrl(r.name)}" target="_blank" rel="noopener">${esc(r.name)}</a></td>
            <td class="mono">${esc(r.class)}</td>
            <td>${esc(r.role)}</td>
            <td class="mono">${esc(r.language || "—")}</td>
            <td class="mono">${r.openIssues}</td>
            <td>${truth(r.truth)}</td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

function renderHub() {
  const kinds = ["all", "model", "dataset", "space"];
  const rows = DATA.hub.filter((h) => hubKind === "all" || h.kind === hubKind);
  const misplaced = DATA.hub.filter((h) => h.misplaced && h.artifactClass === "KERNEL");
  return `
    <p class="os-kicker">Hugging Face · SZLHOLDINGS · OBSERVED</p>
    <h2 class="os-h2">Models, datasets, spaces. Kernels still sit in the model namespace.</h2>
    <p class="os-lede">${misplaced.length} KERNEL cards occupy the model journey. No bulk rename from this hologram. Later recapture at /estate.json is 43 / 36 / 45 with 7 public Spaces — that drift is labeled, not overwritten.</p>
    <div class="os-row">
      ${kinds.map((k) => `<button type="button" class="os-chip ${hubKind === k ? "on" : ""}" data-kind="${esc(k)}">${esc(k)}</button>`).join("")}
    </div>
    <div class="os-table-wrap">
      <table class="os-table">
        <thead><tr><th>Id</th><th>Kind</th><th>Class</th><th>Misplaced</th><th>Truth</th><th>Note</th></tr></thead>
        <tbody>
          ${rows.map((h) => `<tr>
            <td><a href="${hubUrl(h)}" target="_blank" rel="noopener">${esc(h.id)}</a></td>
            <td class="mono">${esc(h.kind)}</td>
            <td class="mono">${esc(h.artifactClass)}</td>
            <td class="${h.misplaced ? "misplaced" : ""}">${h.misplaced ? "YES" : "no"}</td>
            <td>${truth(h.truth)}</td>
            <td>${esc(h.note)}</td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

function renderQueue() {
  return `
    <p class="os-kicker">Queue · PROPOSE_ONLY</p>
    <h2 class="os-h2">Work stays a proposal. Nothing merges from here.</h2>
    <p class="os-lede">Each action mints a Counterfactual Action Passport in this browser session. There is no GitHub write, no Hub PUT, no archive, no delete.</p>
    ${lastMinted ? `<div class="mint-note">Last minted <a href="#/passports/${esc(lastMinted)}">${esc(lastMinted)}</a>. UNSIGNED. Session-only.</div>` : ""}
    <div class="os-grid two">
      ${DATA.queue.map((q) => `<article class="os-card">
        <p class="os-kicker">${esc(q.severity)} · ${esc(q.state)} · ${esc(q.repo)}</p>
        <h3>${esc(q.title)}</h3>
        <p>${esc(q.reason)}</p>
        <div class="os-row">
          ${truth(q.truth)}
          ${q.href ? `<a class="os-chip" href="${esc(q.href)}" target="_blank" rel="noopener">Evidence</a>` : ""}
          <button type="button" class="os-chip on" data-mint="${esc(q.id)}">Propose</button>
        </div>
      </article>`).join("")}
    </div>
    <form id="freeform" class="panel" style="margin-top:18px">
      <p class="os-kicker">Freeform proposal</p>
      <input class="os-search" name="title" placeholder="What would you propose?" aria-label="Freeform proposal" />
      <div class="os-row"><button type="submit" class="button primary">Mint passport</button></div>
    </form>`;
}

function laneScore(id) {
  const items = DATA.controls.filter((c) => c.lane === id);
  return {
    pass: items.filter((c) => c.state === "PASS").length,
    fail: items.filter((c) => c.state === "FAIL").length,
    unassessed: items.filter((c) => c.state === "UNASSESSED").length,
    total: items.length,
  };
}

function renderFabric() {
  return `
    <p class="os-kicker">Fabric · seven lanes</p>
    <h2 class="os-h2">Readiness is not a vibe. Production is BLOCKED.</h2>
    <p class="os-lede">${esc(DATA.productionBlocker)}</p>
    <div class="blocked"><strong>PRODUCTION_READY = false.</strong> Empty trusted-key maps cannot mint ASYMMETRIC_VERIFIED.</div>
    <div class="os-grid lanes">
      ${DATA.lanes.map((l) => {
        const s = laneScore(l.id);
        return `<article class="os-card"><p class="os-kicker">${esc(l.id)}</p><h3>${esc(l.title)}</h3><p>${esc(l.brief)}</p><p class="mono">${s.pass} PASS · ${s.fail} FAIL · ${s.unassessed} UNASSESSED</p></article>`;
      }).join("")}
    </div>
    <div class="os-table-wrap">
      <table class="os-table">
        <thead><tr><th>Control</th><th>Lane</th><th>State</th><th>Truth</th><th>Evidence</th></tr></thead>
        <tbody>
          ${DATA.controls.map((c) => `<tr>
            <td>${esc(c.title)}</td>
            <td class="mono">${esc(c.lane)}</td>
            <td class="mono">${esc(c.state)}</td>
            <td>${truth(c.truth)}</td>
            <td>${esc(c.evidence)}</td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

function renderPassports() {
  const list = passports();
  const current = list.find((p) => p.passport_id === selectedPassport) || list[0];
  if (!current) {
    return `<div class="empty-panel" data-kind="first-use"><span class="empty-kicker">No passports</span><b>Propose from the queue to mint one.</b></div>`;
  }
  return `
    <p class="os-kicker">Passports · szl.counterfactual-action-passport/v1</p>
    <h2 class="os-h2">C0 withhold. C1 acted. Authority attenuates.</h2>
    <p class="os-lede">UNSIGNED. Session-only. This hologram is not a DSSE signer and not a receipt database.</p>
    <div class="pass-split">
      <div class="pass-list">
        ${list.map((p) => `<button type="button" class="os-card ${p.passport_id === current.passport_id ? "on" : ""}" data-go="#/passports/${esc(p.passport_id)}">
          <p class="os-kicker">${esc(p.action.state)} · ${esc(p.policy_decision)}</p>
          <h3>${esc(p.passport_id)}</h3>
          <p>${esc(p.authority.resource)}</p>
        </button>`).join("")}
      </div>
      <article class="panel">
        <p class="os-kicker">Passport</p>
        <h3>${esc(current.passport_id)}</h3>
        <p class="mono">${esc(current.action.kind)} → ${esc(current.action.target)}</p>
        <div class="os-row">${truth(current.evidence.claims[0]?.label || "MODELED")}<span class="os-chip locked">${esc(current.signature.state)}</span><span class="os-chip">${esc(current.action.state)}</span></div>
        <p class="os-kicker" style="margin-top:1.25rem">Evidence claims</p>
        <ul>${current.evidence.claims.map((c) => `<li>${esc(c.claim_id)} · ${esc(c.label)} · ${esc((c.source_refs || []).join(", "))}</li>`).join("")}</ul>
        <div class="c0c1">
          <article><div class="k">C1 acted</div><p>${esc(current.expected_if_acted.statement)}</p></article>
          <article><div class="k">C0 withhold</div><p>${esc(current.expected_if_withheld.statement)}</p></article>
        </div>
        <p class="os-kicker" style="margin-top:1.25rem">Rollback</p>
        <p>${esc(current.rollback.state)} · available=${current.rollback.available ? "true" : "false"}</p>
        ${current.veto ? `<div class="blocked"><strong>Veto.</strong> ${esc(current.veto)}</div>` : ""}
      </article>
    </div>`;
}

function renderFrontiers() {
  const rings = ["all", ...DATA.rings.map((r) => r.id)];
  const list = DATA.frontiers.filter((f) => ring === "all" || f.ring === ring);
  const f = DATA.frontiers.find((x) => x.id === selectedFrontier) || DATA.frontiers[0];
  const locked = f.gate === "LOCKED";
  const pct = Math.round((f.modeledDistance || 0) * 100);
  return `
    <p class="os-kicker">Frontiers · promotion is a passport</p>
    <h2 class="os-h2">Distance is MODELED. Λ cannot be promoted.</h2>
    <p class="os-lede">A hologram is not a production source. Conjecture 1 stays a conjecture. Gold means OPEN, never proven.</p>
    <div class="os-row">
      ${rings.map((r) => `<button type="button" class="os-chip ${ring === r ? "on" : ""}" data-ring="${esc(r)}">${esc(r)}</button>`).join("")}
    </div>
    <div class="pass-split">
      <div class="pass-list">
        ${list.map((x) => `<button type="button" class="os-card ${x.id === f.id ? "on" : ""}" data-go="#/frontiers/${esc(x.id)}">
          <p class="os-kicker">${esc(x.ring)} · ${esc(x.gate)}</p>
          <h3>${esc(x.name)}</h3>
          <div class="bar modeled" aria-label="MODELED distance ${Math.round(x.modeledDistance * 100)} percent"><i style="--w:${Math.round(x.modeledDistance * 100)}%"></i></div>
        </button>`).join("")}
      </div>
      <article class="panel">
        <p class="os-kicker">${esc(f.ring)} · ${esc(f.gate)} · ${esc(f.truth)}</p>
        <h3>${esc(f.name)}</h3>
        <p class="os-lede">${esc(f.role)}</p>
        <p class="mono">MODELED distance ${pct} / 100 — not MEASURED.</p>
        <div class="bar modeled"><i style="--w:${pct}%"></i></div>
        <div class="c0c1">
          <article><div class="k">If promoted</div><p>${esc(f.ifPromoted)}</p></article>
          <article><div class="k">If withheld</div><p>${esc(f.ifWithheld)}</p></article>
        </div>
        ${f.blocker ? `<div class="blocked"><strong>Blocker.</strong> ${esc(f.blocker)}</div>` : ""}
        <div class="os-row">
          ${f.href ? `<a class="os-chip" href="${esc(f.href)}" target="_blank" rel="noopener">Location</a>` : ""}
          ${locked
            ? `<button type="button" class="os-chip locked" data-withhold="${esc(f.id)}">Withhold only</button>`
            : `<button type="button" class="os-chip on" data-propose="${esc(f.id)}">Propose</button>
               <button type="button" class="os-chip" data-withhold="${esc(f.id)}">Withhold</button>`}
        </div>
      </article>
    </div>`;
}

function renderPalette() {
  const cmds = commands();
  if (paletteIdx >= cmds.length) paletteIdx = Math.max(0, cmds.length - 1);
  const box = $("#palette");
  if (!paletteOpen) {
    box.hidden = true;
    box.innerHTML = "";
    return;
  }
  box.hidden = false;
  box.innerHTML = `<div class="palette" role="presentation">
    <div class="palette-box" role="dialog" aria-label="Estate OS command">
      <input id="cmdq" type="search" value="${esc(paletteQ)}" placeholder="Go, propose, withhold…" aria-label="Command search" />
      <div class="palette-list">
        ${cmds.length === 0 ? `<div class="empty-panel compact" data-kind="no-results"><span class="empty-kicker">No matches</span><b>Try overview, queue, or lambda.</b></div>` : cmds.map((c, i) => `<button type="button" aria-selected="${i === paletteIdx}" data-cmd="${esc(c.id)}"><span>${esc(c.label)}</span><span class="hint">${esc(c.g)}</span></button>`).join("")}
      </div>
    </div>
  </div>`;
  const input = $("#cmdq");
  input?.focus();
  input?.setSelectionRange(input.value.length, input.value.length);
}

function render() {
  $$(".os-subnav a").forEach((a) => a.classList.toggle("on", a.dataset.nav === view));
  const app = $("#app");
  if (view === "github") app.innerHTML = renderGithub();
  else if (view === "hub") app.innerHTML = renderHub();
  else if (view === "queue") app.innerHTML = renderQueue();
  else if (view === "fabric") app.innerHTML = renderFabric();
  else if (view === "passports") app.innerHTML = renderPassports();
  else if (view === "frontiers") app.innerHTML = renderFrontiers();
  else app.innerHTML = renderOverview();
  bind();
  renderPalette();
}

function bind() {
  $$("[data-go]").forEach((b) => b.addEventListener("click", () => go(b.dataset.go)));
  $$("[data-class]").forEach((b) => b.addEventListener("click", () => { githubClass = b.dataset.class; render(); }));
  $$("[data-kind]").forEach((b) => b.addEventListener("click", () => { hubKind = b.dataset.kind; render(); }));
  $$("[data-ring]").forEach((b) => b.addEventListener("click", () => { ring = b.dataset.ring; render(); }));
  $$("[data-mint]").forEach((b) => b.addEventListener("click", () => {
    const item = DATA.queue.find((q) => q.id === b.dataset.mint);
    if (item) mintFromQueue(item);
  }));
  $$("[data-propose]").forEach((b) => {
    const f = DATA.frontiers.find((x) => x.id === b.dataset.propose);
    if (f) b.addEventListener("click", () => proposeFrontier(f));
  });
  $$("[data-withhold]").forEach((b) => {
    const f = DATA.frontiers.find((x) => x.id === b.dataset.withhold);
    if (f) b.addEventListener("click", () => withholdFrontier(f));
  });
  const ghq = $("#ghq");
  if (ghq) {
    ghq.addEventListener("input", () => { githubQ = ghq.value; });
    ghq.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); render(); }
    });
    ghq.addEventListener("search", () => render());
  }
  const form = $("#freeform");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const title = (form.title.value || "").trim() || "untitled proposal";
      mintPassport({
        resource: "estate:freeform",
        acted: `If acted, "${title}" would still not mutate GitHub or Hub.`,
        withheld: "If withheld, the hologram remains a reader.",
      });
    });
  }
  $$("[data-cmd=open]").forEach((b) => b.addEventListener("click", () => { paletteOpen = true; paletteQ = ""; paletteIdx = 0; renderPalette(); }));
  const pal = $("#palette");
  pal?.querySelector(".palette")?.addEventListener("click", (e) => {
    if (e.target.classList.contains("palette")) { paletteOpen = false; renderPalette(); }
  });
  $$("[data-cmd]:not([data-cmd=open])").forEach((b) => {
    b.addEventListener("click", () => {
      const cmd = commands().find((c) => c.id === b.dataset.cmd);
      paletteOpen = false;
      cmd?.run();
      if (!location.hash.includes("passports")) render();
    });
  });
  const cmdq = $("#cmdq");
  if (cmdq) {
    cmdq.addEventListener("input", () => { paletteQ = cmdq.value; paletteIdx = 0; renderPalette(); });
  }
}

function onKey(e) {
  const meta = e.metaKey || e.ctrlKey;
  if ((meta && e.key.toLowerCase() === "k") || (e.key === "/" && !["INPUT", "TEXTAREA"].includes(e.target.tagName))) {
    e.preventDefault();
    paletteOpen = true;
    paletteQ = "";
    paletteIdx = 0;
    renderPalette();
    return;
  }
  if (!paletteOpen) return;
  const cmds = commands();
  if (e.key === "Escape") { paletteOpen = false; renderPalette(); }
  else if (e.key === "ArrowDown") { e.preventDefault(); paletteIdx = Math.min(cmds.length - 1, paletteIdx + 1); renderPalette(); }
  else if (e.key === "ArrowUp") { e.preventDefault(); paletteIdx = Math.max(0, paletteIdx - 1); renderPalette(); }
  else if (e.key === "Enter") {
    e.preventDefault();
    const cmd = cmds[paletteIdx];
    paletteOpen = false;
    cmd?.run();
    if (cmd && !String(location.hash).includes("passports")) render();
  }
}

async function boot() {
  const res = await fetch("./data.json", { redirect: "error" });
  if (!res.ok) {
    $("#app").innerHTML = `<div class="empty-panel" data-kind="error"><span class="empty-kicker">UNAVAILABLE</span><b>data.json did not load. This is not an observed-empty inventory.</b></div>`;
    return;
  }
  DATA = await res.json();
  minted = (DATA.passports || []).slice();
  window.addEventListener("hashchange", route);
  document.addEventListener("keydown", onKey);
  route();
}

boot();
