/* Estate OS control-plane hologram. PROPOSE_ONLY. No mutations. Not a live dashboard. */
const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) =>
  String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const VIEWS = ["overview", "github", "hub", "queue", "fabric", "passports", "frontiers"];

let DATA = null;
let view = "overview";
let q = "";
let minted = [];
let selectedPassport = null;
let selectedFrontier = null;

function truth(t) {
  const k = String(t || "UNAVAILABLE").replace(/\s+/g, "-");
  return `<span class="truth t-${esc(k)}">${esc(t)}</span>`;
}

function route() {
  const h = (location.hash || "#/overview").replace(/^#\/?/, "");
  const parts = h.split("/").filter(Boolean);
  view = VIEWS.includes(parts[0]) ? parts[0] : "overview";
  if (parts[0] === "passports" && parts[1]) selectedPassport = parts[1];
  if (parts[0] === "frontiers" && parts[1]) selectedFrontier = parts[1];
}

function setHash(v, id) {
  location.hash = id ? `#/${v}/${id}` : `#/${v}`;
}

function mintProposal(input) {
  const now = new Date().toISOString();
  const id = "cap-propose-" + Date.now().toString(36);
  const decision = input.decision === "REQUIRE_APPROVAL" ? "REQUIRE_APPROVAL" : "ALLOW";
  return {
    schema: "szl.counterfactual-action-passport/v1",
    passport_id: id,
    recorded_at: now,
    identity: {
      agent_id: "estate-os.operator-session",
      principal_id: "local-operator",
      session_id: "browser",
      delegation_chain: ["local-operator"],
    },
    authority: {
      parent_scopes: ["estate.propose"],
      child_scopes: ["estate.propose"],
      tool: "estate.mint_passport",
      resource: input.resource,
      constraints: ["propose-only", "no-mutation"],
    },
    policy_decision: decision,
    expected_if_acted: { statement: input.acted, confidence_0_to_1: 0.5 },
    expected_if_withheld: { statement: input.withheld, confidence_0_to_1: 0.5 },
    action: { action_id: "act-" + id, kind: "proposal", target: input.resource, state: "PROPOSED", executed_at: null },
    outcome: { state: "NOT_MEASURED" },
    signature: { state: "UNSIGNED" },
    local_only: true,
  };
}

function passports() {
  return minted.concat(DATA.passports || []);
}

function renderOverview() {
  const c = DATA.counts;
  return `
    <div class="plane-grid">
      <article class="plane-card"><span>GitHub observed</span><b>${c.githubObserved}</b><p>${c.publicRepos} public · ${c.archived} archived · ${c.privateUnavailable} private UNAVAILABLE</p></article>
      <article class="plane-card"><span>Hub bake</span><b>${c.hub.models}/${c.hub.datasets}/${c.hub.spaces}</b><p>models / datasets / spaces. ${c.hub.kernelsMisplaced} KERNEL cards still in model namespace.</p></article>
      <article class="plane-card"><span>Open queue</span><b>${c.openQueue}</b><p>${c.p0} P0 still open or held. No merge from this origin.</p></article>
      <article class="plane-card"><span>Frontiers</span><b>${DATA.frontiers.length}</b><p>Λ gate LOCKED. Promotion is withhold-only.</p></article>
    </div>
    <p class="note">Bake ${esc(DATA.capturedAt)} · scope ${esc(DATA.scope)}. Later keep-7 counts stay in estate.json and are not overwritten. Catalog hologram remains /estate/os/.</p>`;
}

function filterList(items, haystack) {
  const query = q.trim().toLowerCase();
  if (!query) return items;
  return items.filter((item) => haystack(item).toLowerCase().includes(query));
}

function searchBox(placeholder) {
  return `<p><input id="q" value="${esc(q)}" placeholder="${esc(placeholder)}" style="width:min(420px,100%);background:#080c14;color:#e8edf5;border:1px solid #5b8dee55;padding:.45rem .55rem" /></p>`;
}

function renderGithub() {
  const rows = filterList(DATA.repos, (r) => `${r.name} ${r.description} ${r.language || ""}`);
  return searchBox("Filter observed public repos") + `
    <p class="note">${rows.length} / ${DATA.repos.length} OBSERVED public records. 5 private remain UNAVAILABLE unnamed.</p>
    <table class="plane-table"><thead><tr><th>Repo</th><th>Truth</th><th>Lang</th><th>State</th></tr></thead><tbody>
    ${rows.map((r) => `<tr><td><a href="${esc(r.href)}">${esc(r.name)}</a><div class="note">${esc(r.description)}</div></td><td>${truth(r.truth)}</td><td>${esc(r.language || "—")}</td><td>${r.archived ? "ARCHIVED" : "public"}</td></tr>`).join("")}
    </tbody></table>`;
}

function renderHub() {
  const rows = filterList(DATA.hub, (h) => `${h.id} ${h.title} ${h.kind} ${h.artifactClass || ""}`);
  return searchBox("Filter Hub cards") + `
    <p class="note">${rows.length} / ${DATA.hub.length} Hub cards in the 16:49Z bake. Runtime UNAVAILABLE.</p>
    <table class="plane-table"><thead><tr><th>Card</th><th>Kind</th><th>Class</th><th>Truth</th></tr></thead><tbody>
    ${rows.map((h) => `<tr><td><a href="${esc(h.href)}">${esc(h.id)}</a>${h.misplaced ? ' <span class="locked-warn">KERNEL-IN-MODEL-NS</span>' : ""}</td><td>${esc(h.kind)}</td><td>${esc(h.artifactClass || "—")}</td><td>${truth(h.truth)}</td></tr>`).join("")}
    </tbody></table>`;
}

function renderQueue() {
  return `<table class="plane-table"><thead><tr><th>Item</th><th>Sev</th><th>State</th><th>Truth</th></tr></thead><tbody>
    ${DATA.queue.map((item) => `<tr><td><b>${esc(item.title)}</b><div class="note">${esc(item.repo)} — ${esc(item.reason)}</div></td><td>${esc(item.severity)}</td><td>${esc(item.state)}</td><td>${truth(item.truth)}</td></tr>`).join("")}
    </tbody></table>
    <p class="note">Queue is MODELED work. This hologram cannot merge, archive, or rename.</p>`;
}

function renderFabric() {
  const by = {};
  for (const c of DATA.controls) (by[c.lane] ||= []).push(c);
  return DATA.lanes.map((lane) => `
    <section class="plane-panel" style="margin-bottom:.85rem">
      <span>${esc(lane.id)}</span>
      <h2 style="margin:.2rem 0 .4rem;font-size:1.05rem">${esc(lane.title)}</h2>
      <p class="note">${esc(lane.brief)}</p>
      <table class="plane-table"><tbody>
        ${(by[lane.id] || []).map((c) => `<tr><td>${esc(c.title)}</td><td>${esc(c.state)}</td><td>${truth(c.truth)}</td><td class="note">${esc(c.evidence)}</td></tr>`).join("")}
      </tbody></table>
    </section>`).join("");
}

function renderPassports() {
  const list = passports();
  const selected = list.find((p) => p.passport_id === selectedPassport) || list[0];
  let selectedHtml = '<p class="note">No passport selected.</p>';
  if (selected) {
    selectedHtml =
      '<h2 style="margin:.2rem 0;font-size:1.05rem">' + esc(selected.passport_id) + "</h2>" +
      "<p>" + truth(selected.policy_decision) + " " + truth(selected.action && selected.action.state) + " " + truth(selected.signature && selected.signature.state) + "</p>" +
      '<p class="note">Resource ' + esc((selected.authority && selected.authority.resource) || (selected.action && selected.action.target) || "") + "</p>" +
      "<p><b>If acted.</b> " + esc((selected.expected_if_acted && selected.expected_if_acted.statement) || "") + "</p>" +
      "<p><b>If withheld.</b> " + esc((selected.expected_if_withheld && selected.expected_if_withheld.statement) || "") + "</p>" +
      (selected.local_only ? '<p class="locked-warn">Local-only. Lost on reload. Not a receipt.</p>' : "");
  }
  return `
    <div class="plane-grid">
      <section class="plane-panel">
        <span>Mint PROPOSE_ONLY</span>
        <p class="note">Writes a passport in this tab. Does not call GitHub, Hub, or DNS. Lambda cannot be a target.</p>
        <form class="plane-form" id="mint">
          <label>Resource<input name="resource" required placeholder="github:repo:szl-holdings/example" /></label>
          <label>If acted<textarea name="acted" required rows="2">A mutation would fire without EXACT_RUNTIME_HEAD.</textarea></label>
          <label>If withheld<textarea name="withheld" required rows="2">The estate stays fail-closed. No merge is attempted.</textarea></label>
          <label>Decision
            <select name="decision">
              <option value="ALLOW">ALLOW (still propose-only)</option>
              <option value="REQUIRE_APPROVAL">REQUIRE_APPROVAL</option>
            </select>
          </label>
          <button type="submit">Mint passport</button>
        </form>
      </section>
      <section class="plane-panel">
        <span>Selected</span>
        ${selectedHtml}
      </section>
    </div>
    <table class="plane-table"><thead><tr><th>Passport</th><th>Decision</th><th>Action</th><th>Sig</th></tr></thead><tbody>
      ${list.map((p) => `<tr><td><a href="#/passports/${esc(p.passport_id)}">${esc(p.passport_id)}</a></td><td>${truth(p.policy_decision)}</td><td>${esc(p.action && p.action.state)}</td><td>${esc(p.signature && p.signature.state)}</td></tr>`).join("")}
    </tbody></table>`;
}

function renderFrontiers() {
  const selected = DATA.frontiers.find((f) => f.id === selectedFrontier) || DATA.frontiers.find((f) => f.id === "lambda") || DATA.frontiers[0];
  const locked = selected.gate === "LOCKED" || selected.id === "lambda";
  return `
    <div class="plane-grid">
      <section class="plane-panel">
        <span>${esc(selected.ring)}</span>
        <h2 style="margin:.2rem 0">${esc(selected.name)}</h2>
        <p>${truth(selected.truth)} ${truth(selected.gate)} distance ${esc(selected.modeledDistance)}</p>
        <p>${esc(selected.role)}</p>
        <p><b>If promoted.</b> ${esc(selected.ifPromoted)}</p>
        <p><b>If withheld.</b> ${esc(selected.ifWithheld)}</p>
        <p class="note">Blocker: ${esc(selected.blocker)}</p>
        <p class="note">${locked ? "Λ / LOCKED targets are withhold-only. This hologram will not mint a promotion passport." : "Promotion mint is PROPOSE_ONLY and stays in this tab."}</p>
        ${locked ? "" : `<button id="promote" type="button">Propose withhold passport</button>`}
      </section>
    </div>
    <table class="plane-table"><thead><tr><th>Frontier</th><th>Ring</th><th>Gate</th><th>Truth</th></tr></thead><tbody>
      ${DATA.frontiers.map((f) => `<tr><td><a href="#/frontiers/${esc(f.id)}">${esc(f.name)}</a></td><td>${esc(f.ring)}</td><td>${esc(f.gate)}</td><td>${truth(f.truth)}</td></tr>`).join("")}
    </tbody></table>`;
}

function render() {
  route();
  const app = $("#app");
  const body = {
    overview: renderOverview,
    github: renderGithub,
    hub: renderHub,
    queue: renderQueue,
    fabric: renderFabric,
    passports: renderPassports,
    frontiers: renderFrontiers,
  }[view]();
  app.innerHTML = body;
  document.querySelectorAll("[data-nav]").forEach((a) => {
    a.classList.toggle("is-on", a.getAttribute("data-nav") === view);
    a.setAttribute("aria-current", a.getAttribute("data-nav") === view ? "page" : "false");
  });
  const box = $("#q");
  if (box) box.addEventListener("input", (e) => { q = e.target.value; render(); });
  const form = $("#mint");
  if (form) form.addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const resource = String(fd.get("resource") || "").trim();
    if (/lambda|conjecture|Λ/i.test(resource)) {
      alert("Λ remains Conjecture 1. Promotion is withheld.");
      return;
    }
    const next = mintProposal({
      resource,
      acted: String(fd.get("acted") || ""),
      withheld: String(fd.get("withheld") || ""),
      decision: String(fd.get("decision") || "ALLOW"),
    });
    minted = [next, ...minted];
    selectedPassport = next.passport_id;
    setHash("passports", next.passport_id);
    render();
  });
  const promote = $("#promote");
  if (promote) promote.addEventListener("click", () => {
    const f = DATA.frontiers.find((x) => x.id === selectedFrontier) || DATA.frontiers[0];
    if (f.gate === "LOCKED" || f.id === "lambda") return;
    const next = mintProposal({
      resource: "frontier:" + f.id,
      acted: f.ifPromoted,
      withheld: f.ifWithheld,
      decision: "REQUIRE_APPROVAL",
    });
    minted = [next, ...minted];
    selectedPassport = next.passport_id;
    setHash("passports", next.passport_id);
    render();
  });
}

fetch("./data.json")
  .then((r) => {
    if (!r.ok) throw new Error("UNAVAILABLE");
    return r.json();
  })
  .then((d) => {
    DATA = d;
    selectedPassport = (d.passports && d.passports[0] && d.passports[0].passport_id) || null;
    window.addEventListener("hashchange", render);
    render();
  })
  .catch(() => {
    $("#app").innerHTML = '<p class="note">Bake UNAVAILABLE. Fail closed. Catalog remains at /estate/os/.</p>';
  });
