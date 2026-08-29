/* Estate catalog hologram. READ-ONLY. No mutations. Not a live dashboard. */
const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const esc = (s) =>
  String(s ?? "")
    .replaceAll("&", "&")
    .replaceAll("<", "<")
    .replaceAll(">", ">")
    .replaceAll('"', """);

const VIEWS = ["lattice", "catalog", "ledger"];
const LANES = ["all", "github", "space", "gated", "model", "dataset", "collection"];
const RINGS = ["all", "flagship", "organ", "kernel", "holographic", "vertical", "docs", "archive"];
const LANE_LABEL = {
  all: "ALL",
  github: "GITHUB",
  space: "SPACE",
  gated: "GATED",
  model: "MODEL",
  dataset: "CORPUS",
  collection: "COLLECT",
};
const RING_LABEL = {
  all: "ALL",
  flagship: "FLAGSHIP",
  organ: "ORGAN",
  kernel: "KERNEL",
  holographic: "HOLO",
  vertical: "VERTICAL",
  docs: "DOCS",
  archive: "ARCHIVE",
};

let DATA = null;
let view = "lattice";
let q = "";
let lane = "all";
let ring = "all";
let selectedId = null;

function truth(t) {
  const k = String(t || "UNAVAILABLE").replace(/\s+/g, "-");
  return `<span class="truth t-${esc(k)}">${esc(t)}</span>`;
}

function firstUrl(a) {
  return a.urls?.github || a.urls?.huggingface || a.urls?.homepage || a.urls?.canonical || "";
}

function rel(iso) {
  if (!iso) return "UNAVAILABLE";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "UNAVAILABLE";
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  if (s < 86400 * 40) return `${Math.floor(s / 86400)}d`;
  return iso.slice(0, 10);
}

function visible() {
  const query = q.trim().toLowerCase();
  return DATA.assets.filter((a) => {
    if (lane === "gated") {
      if (!a.gated) return false;
    } else if (lane !== "all" && a.lane !== lane) return false;
    if (ring !== "all" && a.ring !== ring) return false;
    if (!query) return true;
    const hay = `${a.name} ${a.title} ${a.description} ${(a.topics || []).join(" ")}`.toLowerCase();
    return hay.includes(query);
  });
}

function selected() {
  return DATA.assets.find((a) => a.id === selectedId) || null;
}

function route() {
  const h = (location.hash || "#/lattice").replace(/^#\/?/, "");
  const parts = h.split("/").filter(Boolean);
  view = VIEWS.includes(parts[0]) ? parts[0] : "lattice";
  if (parts[1]) selectedId = decodeURIComponent(parts[1]);
  render();
}

function go(hash) {
  if (location.hash === hash) route();
  else location.hash = hash;
}

function controls() {
  return `
    <input class="os-search" id="q" type="search" value="${esc(q)}" placeholder="Search the public estate" aria-label="Search the public estate" />
    <div class="os-row" id="lanes">
      ${LANES.map((l) => `<button type="button" class="os-chip ${lane === l ? "on" : ""}" data-lane="${esc(l)}">${esc(LANE_LABEL[l])}</button>`).join("")}
    </div>
    <div class="os-row" id="rings">
      ${RINGS.map((r) => `<button type="button" class="os-chip ${ring === r ? "on" : ""}" data-ring="${esc(r)}">${esc(RING_LABEL[r])}</button>`).join("")}
    </div>
    <p class="muted mono">${visible().length} shown · READ-ONLY · not a live dashboard</p>
  `;
}

function flagships() {
  const rows = DATA.assets.filter((a) => a.ring === "flagship" && (a.lane === "github" || a.lane === "space"));
  if (!rows.length) return "";
  return `
    <p class="os-kicker">Flagship rail · DERIVED</p>
    <div class="os-grid flag">
      ${rows.map((a) => `
        <button type="button" class="os-card ${a.id === selectedId ? "on" : ""}" data-id="${esc(a.id)}">
          <p class="os-kicker">${esc(a.lane)} · ${esc(a.ring)}</p>
          <h3>${esc(a.title)}</h3>
          <p>${esc(a.description)}</p>
          <div class="os-meta">${truth(a.catalogHonesty)}${a.gated ? `<span class="os-chip warn">GATED</span>` : ""}</div>
        </button>`).join("")}
    </div>`;
}

function renderLattice() {
  const rows = visible();
  const groups = {};
  for (const r of RINGS.slice(1)) groups[r] = [];
  for (const a of rows) (groups[a.ring] || (groups[a.ring] = [])).push(a);
  return `
    <p class="os-kicker">Lattice · ${esc(DATA.scope)} · ${esc(DATA.capturedAt)}</p>
    <h2 class="os-h2">${DATA.counts.assets} public catalog rows. Runtime stays UNAVAILABLE.</h2>
    <p class="os-lede">Unauthenticated bake. Later keep-7 recapture is labeled in /estate.json and is not overwritten. Private GitHub names are withheld. Λ remains Conjecture 1.</p>
    ${controls()}
    ${flagships()}
    ${RINGS.slice(1).map((r) => {
      const list = groups[r] || [];
      if (!list.length) return "";
      return `
        <div class="os-ring-head"><span>${esc(RING_LABEL[r])}</span><b>${list.length}</b></div>
        <div class="os-grid flag">
          ${list.slice(0, 48).map((a) => `
            <button type="button" class="os-card ${a.id === selectedId ? "on" : ""}" data-id="${esc(a.id)}">
              <p class="os-kicker">${esc(a.lane)}${a.gated ? " · gated" : ""} · ${esc(rel(a.updatedAt))}</p>
              <h3>${esc(a.title)}</h3>
              <p>${esc(a.description)}</p>
            </button>`).join("")}
        </div>
        ${list.length > 48 ? `<p class="muted">Showing 48 of ${list.length}. Switch to Catalog for the rest.</p>` : ""}`;
    }).join("")}
    <div class="handoff-line"><span class="os-kicker">Later recapture · do not overwrite</span>${esc(DATA.laterRecapture.bound)}</div>
  `;
}

function renderCatalog() {
  const rows = visible().slice().sort((a, b) => String(b.updatedAt || "").localeCompare(String(a.updatedAt || "")));
  return `
    <p class="os-kicker">Catalog · MEASURED where labelled</p>
    <h2 class="os-h2">Every public row. Counts are not quality.</h2>
    <p class="os-lede">Gated Spaces are HTTP 401, not deletions. Host 200 is reachability, not LIVE.</p>
    ${controls()}
    <div class="os-table-wrap">
      <table class="os-table">
        <thead><tr><th>Name</th><th>Lane</th><th>Ring</th><th>Honesty</th><th>Updated</th><th>Location</th></tr></thead>
        <tbody>
          ${rows.map((a) => {
            const href = firstUrl(a);
            return `<tr class="${a.id === selectedId ? "on" : ""}">
              <td><button type="button" class="link" data-id="${esc(a.id)}">${esc(a.title)}</button>${a.gated ? " · gated" : ""}</td>
              <td class="mono">${esc(a.lane)}</td>
              <td class="ring">${esc(a.ring)}</td>
              <td>${truth(a.catalogHonesty)}</td>
              <td class="mono">${esc(rel(a.updatedAt))}</td>
              <td>${href ? `<a href="${esc(href)}" target="_blank" rel="noopener">open</a>` : "—"}</td>
            </tr>`;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderLedger() {
  const src = DATA.sources || [];
  return `
    <p class="os-kicker">Ledger · sources for this bake</p>
    <h2 class="os-h2">A figure without method is omitted.</h2>
    <p class="os-lede">This hologram does not probe live APIs. connect-src is self. Fail closed.</p>
    <div class="os-table-wrap">
      <table class="os-table">
        <thead><tr><th>Source</th><th>Class</th><th>Count</th><th>Bound</th></tr></thead>
        <tbody>
          ${src.map((s) => `<tr>
            <td class="mono">${esc(s.id)}</td>
            <td>${truth(s.honesty)}</td>
            <td class="mono">${esc(s.itemCount ?? s.totalCount ?? "—")}</td>
            <td>${esc(s.note || s.reason || s.url || "—")}</td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>
    <div class="handoff-line">Product honesty remains <a href="https://a-11-oy.com/api/a11oy/v1/honest" target="_blank" rel="noopener">a-11-oy.com/api/a11oy/v1/honest</a>. This origin does not clone /verify. Λ = Conjecture 1.</div>
  `;
}

function renderInspector() {
  const box = $("#inspector");
  const a = selected();
  if (!a || view === "ledger") {
    box.hidden = true;
    box.innerHTML = "";
    return;
  }
  const urls = Object.entries(a.urls || {}).filter(([, v]) => v);
  box.hidden = false;
  box.innerHTML = `
    <p class="os-kicker">${esc(a.lane)} · ${esc(a.ring)}</p>
    <h3>${esc(a.title)}</h3>
    <p>${esc(a.description)}</p>
    <div class="os-meta">${truth(a.catalogHonesty)}${truth(a.runtimeHonesty)}${a.gated ? `<span class="os-chip warn">GATED</span>` : ""}${a.archived ? `<span class="os-chip down">ARCHIVED</span>` : ""}</div>
    <dl>
      <dt>Updated</dt><dd class="mono">${esc(a.updatedAt || "UNAVAILABLE")}</dd>
      <dt>Language</dt><dd>${esc(a.language || "—")}</dd>
      <dt>License</dt><dd>${esc(a.license || "—")}</dd>
      <dt>SHA</dt><dd class="mono">${esc(a.sha ? String(a.sha).slice(0, 12) : "—")}</dd>
      <dt>Runtime</dt><dd>${esc(a.runtimeNote || "UNAVAILABLE")}</dd>
    </dl>
    <div class="os-row">
      ${urls.map(([k, v]) => `<a class="os-chip" href="${esc(v)}" target="_blank" rel="noopener">${esc(k)}</a>`).join("")}
    </div>
  `;
}

function render() {
  $$(".os-subnav a").forEach((a) => a.classList.toggle("on", a.dataset.nav === view));
  const app = $("#app");
  if (view === "catalog") app.innerHTML = renderCatalog();
  else if (view === "ledger") app.innerHTML = renderLedger();
  else app.innerHTML = renderLattice();
  renderInspector();
  bind();
}

function bind() {
  const input = $("#q");
  if (input) {
    input.addEventListener("input", () => {
      q = input.value;
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        render();
      }
    });
    input.addEventListener("search", () => render());
  }
  $$("[data-lane]").forEach((b) =>
    b.addEventListener("click", () => {
      lane = b.dataset.lane;
      render();
    }),
  );
  $$("[data-ring]").forEach((b) =>
    b.addEventListener("click", () => {
      ring = b.dataset.ring;
      render();
    }),
  );
  $$("[data-id]").forEach((b) =>
    b.addEventListener("click", () => {
      selectedId = b.dataset.id;
      go(`#/${view}/${encodeURIComponent(selectedId)}`);
    }),
  );
}

async function boot() {
  const app = $("#app");
  try {
    const res = await fetch("./data.json", { redirect: "error" });
    if (!res.ok) throw new Error(String(res.status));
    DATA = await res.json();
  } catch {
    app.innerHTML = `<div class="empty-panel" data-kind="error"><span class="empty-kicker">UNAVAILABLE</span><b>data.json did not load. This is not an observed-empty inventory.</b></div>`;
    return;
  }
  window.addEventListener("hashchange", route);
  route();
}

boot();
