// SPDX-License-Identifier: Apache-2.0
// Real-data registry cards for the a11oy.net proof registry front door.
//
// Every value rendered here is read at request time from JSON this origin
// already publishes:
//   /public-inventory.json  (szl.public-hf-inventory/v3 — dated unauthenticated
//                            public Hugging Face API snapshot)
//   /models.json            (dated MEASURED classification of the public model
//                            cards)
// Nothing is hand-typed, interpolated, or estimated. If a document, a field, or
// a whole fetch is missing, the card or count renders the honest label
// (UNAVAILABLE / STRUCTURAL-ONLY) instead of a number. Killinchu-named
// resources are withheld from this front door by standing policy.
(function () {
  "use strict";

  var root = document.getElementById("inventory-cards");
  if (!root) return;

  var COUNT_IDS = {
    total: "invTotal",
    models: "invModels",
    datasets: "invDatasets",
    spaces: "invSpaces",
    collections: "invCollections",
    buckets: "invBuckets"
  };
  var PREVIEW = 9;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function setText(id, value) {
    var node = document.getElementById(id);
    if (!node) return;
    node.textContent = (typeof value === "number" && isFinite(value))
      ? String(value)
      : "—";
  }

  function shortName(id) {
    var parts = String(id || "").split("/");
    return parts[parts.length - 1] || String(id || "");
  }

  function isWithheld(id) {
    return /killinchu/i.test(String(id || ""));
  }

  function shortSha(sha) {
    return /^[0-9a-f]{7,}$/i.test(String(sha || ""))
      ? String(sha).slice(0, 7)
      : null;
  }

  function isoDay(value) {
    var text = String(value || "");
    return /^\d{4}-\d{2}-\d{2}/.test(text) ? text.slice(0, 10) : null;
  }

  function hubUrl(kind, id) {
    var base = "https://huggingface.co/";
    if (kind === "DATASET") base += "datasets/";
    if (kind === "SPACE") base += "spaces/";
    if (kind === "COLLECTION") return "https://huggingface.co/collections/" + id;
    if (kind === "BUCKET") return "https://huggingface.co/" + id;
    return base + id;
  }

  function fetchJson(url) {
    return fetch(url, {
      credentials: "omit",
      redirect: "error",
      cache: "no-store",
      headers: { "Accept": "application/json" }
    }).then(function (response) {
      if (!response || !response.ok) throw new Error("REQUEST_FAILED");
      return response.json();
    });
  }

  // ---- the one shared card component (SZL monochrome design system v1) ----
  function card(spec) {
    var node = document.createElement(spec.href ? "a" : "div");
    node.className = "inv-card";
    if (spec.href) {
      node.href = spec.href;
      node.target = "_blank";
      node.rel = "noopener";
    }
    node.appendChild(el("span", "inv-eyebrow", spec.eyebrow));
    node.appendChild(el("b", null, spec.title));
    node.appendChild(el("p", null, spec.description));
    if (spec.metrics && spec.metrics.length) {
      var metrics = el("span", "inv-metrics", spec.metrics.join("  ·  "));
      node.appendChild(metrics);
    }
    var foot = el("span", "inv-foot");
    foot.appendChild(el("span", "inv-label", spec.label));
    if (spec.href) foot.appendChild(el("span", "inv-open", "Open Hub card ↗"));
    node.appendChild(foot);
    return node;
  }

  function emptyPanel(message) {
    var panel = el("div", "empty-panel");
    panel.setAttribute("data-kind", "unavailable");
    panel.appendChild(el("span", "empty-kicker", "UNAVAILABLE"));
    panel.appendChild(el("b", null, message));
    panel.appendChild(el(
      "small",
      null,
      "No count, hash, or date is invented to fill this panel. Read the committed JSON directly at /public-inventory.json and /models.json."
    ));
    return panel;
  }

  function group(title, note, cards) {
    var section = el("div", "inv-group");
    var head = el("div", "inv-group-head");
    head.appendChild(el("h3", null, title));
    head.appendChild(el("p", null, note));
    section.appendChild(head);
    var grid = el("div", "inv-grid");
    section.appendChild(grid);
    if (!cards.length) {
      grid.appendChild(emptyPanel(title + " could not be read from the committed snapshot."));
      return section;
    }
    cards.forEach(function (item, index) {
      if (index >= PREVIEW) item.setAttribute("data-inv-more", "true");
      grid.appendChild(item);
    });
    if (cards.length > PREVIEW) {
      var more = el("button", "inv-more", "Show all " + cards.length + " ↓");
      more.type = "button";
      more.addEventListener("click", function () {
        var hidden = grid.querySelectorAll("[data-inv-more]");
        Array.prototype.forEach.call(hidden, function (node) {
          node.removeAttribute("data-inv-more");
        });
        more.remove();
      });
      section.appendChild(more);
    }
    return section;
  }

  function modelCards(inventory, contract) {
    var classes = (contract && contract.classes) || {};
    var byId = {};
    var listed = (contract && contract.models) || [];
    listed.forEach(function (item) { byId[item.id] = item; });
    return (inventory.resources.models || [])
      .filter(function (item) { return !isWithheld(item.id); })
      .map(function (item) {
        var classified = byId[item.id];
        var klass = classified && classified.class ? classified.class : null;
        var metrics = [];
        if (item.license) metrics.push("license " + item.license);
        if (classified && typeof classified.files === "number") {
          metrics.push(classified.files + " files");
        }
        if (shortSha(item.repository_sha)) metrics.push("sha " + shortSha(item.repository_sha));
        if (isoDay(item.last_modified)) metrics.push("updated " + isoDay(item.last_modified));
        return card({
          eyebrow: ["MODEL", item.pipeline_tag || null, klass]
            .filter(Boolean).join(" · "),
          title: shortName(item.id),
          description: klass && classes[klass]
            ? classes[klass]
            : "Public Hub model card; class not stated in the committed classification.",
          metrics: metrics,
          label: klass || "UNAVAILABLE",
          href: hubUrl("MODEL", item.id)
        });
      });
  }

  function datasetCards(inventory) {
    return (inventory.resources.datasets || [])
      .filter(function (item) { return !isWithheld(item.id); })
      .map(function (item) {
        var metrics = [];
        if (item.license) metrics.push("license " + item.license);
        if (shortSha(item.repository_sha)) metrics.push("sha " + shortSha(item.repository_sha));
        if (isoDay(item.last_modified)) metrics.push("updated " + isoDay(item.last_modified));
        return card({
          eyebrow: "DATASET",
          title: shortName(item.id),
          description: "Public Hub dataset listing. Payload, data rights, and quality are not inspected on this origin.",
          metrics: metrics,
          label: item.source_observation === "PUBLIC_HF_REPOSITORY_OBSERVED"
            ? "REPORTED"
            : "UNAVAILABLE",
          href: hubUrl("DATASET", item.id)
        });
      });
  }

  function spaceCards(inventory) {
    return (inventory.resources.spaces || [])
      .filter(function (item) { return !isWithheld(item.id); })
      .map(function (item) {
        var runtime = item.runtime || {};
        var reach = item.root_observation || {};
        var metrics = [];
        if (runtime.stage) metrics.push("stage " + runtime.stage);
        if (reach.state) {
          metrics.push("root " + reach.state + (reach.http_status ? " " + reach.http_status : ""));
        }
        if (shortSha(item.repository_sha)) metrics.push("sha " + shortSha(item.repository_sha));
        if (isoDay(item.last_modified)) metrics.push("updated " + isoDay(item.last_modified));
        return card({
          eyebrow: ["SPACE", item.sdk || null].filter(Boolean).join(" · "),
          title: shortName(item.id),
          description: runtime.interpretation
            ? "Provider-reported stage in the dated snapshot: reachability only, never quality or freshness."
            : "Public Hub Space listing. No runtime stage was captured for this row in the snapshot.",
          metrics: metrics,
          label: runtime.stage ? "REPORTED" : "UNAVAILABLE",
          href: hubUrl("SPACE", item.id)
        });
      });
  }

  function bucketCards(inventory) {
    return (inventory.resources.buckets || [])
      .filter(function (item) { return !isWithheld(item.id); })
      .map(function (item) {
        var metrics = [];
        if (typeof item.observed_object_count === "number") {
          metrics.push(item.observed_object_count + " objects observed");
        }
        if (typeof item.observed_size_bytes === "number") {
          metrics.push(item.observed_size_bytes + " bytes observed");
        }
        if (isoDay(item.updated_at)) metrics.push("updated " + isoDay(item.updated_at));
        return card({
          eyebrow: ["BUCKET", item.visibility || null].filter(Boolean).join(" · "),
          title: shortName(item.id),
          description: "Object counts and byte totals were walked from the public bucket tree endpoint in this snapshot.",
          metrics: metrics,
          label: typeof item.observed_object_count === "number" ? "MEASURED" : "UNAVAILABLE",
          href: hubUrl("BUCKET", item.id)
        });
      });
  }

  function renderProvenance(inventory, contract) {
    var line = document.getElementById("invProvenance");
    if (!line) return;
    var observed = inventory && inventory.observed_at ? inventory.observed_at : null;
    var mode = inventory && inventory.observation_mode ? inventory.observation_mode : null;
    var parts = [];
    parts.push("source /public-inventory.json");
    parts.push(inventory && inventory.schema ? inventory.schema : "schema UNAVAILABLE");
    parts.push(observed ? "observed " + observed : "observed_at UNAVAILABLE");
    parts.push(mode || "observation_mode UNAVAILABLE");
    if (contract && contract.captured_at) {
      parts.push("classification /models.json captured " + contract.captured_at);
    } else {
      parts.push("classification /models.json UNAVAILABLE");
    }
    if (contract && contract.energy) parts.push("energy " + contract.energy);
    line.textContent = parts.join(" · ");
  }

  function render(inventory, contract) {
    var counts = (inventory && inventory.counts) || {};
    setText(COUNT_IDS.total, counts.public_resources_total);
    setText(COUNT_IDS.models, counts.models);
    setText(COUNT_IDS.datasets, counts.datasets);
    setText(COUNT_IDS.spaces, counts.spaces);
    setText(COUNT_IDS.collections, counts.collections);
    setText(COUNT_IDS.buckets, counts.buckets);

    root.textContent = "";
    root.appendChild(group(
      "Models",
      "Class and file counts come from the committed MEASURED classification; a card with no stated class renders UNAVAILABLE.",
      modelCards(inventory, contract)
    ));
    root.appendChild(group(
      "Datasets",
      "Listing metadata only. A listed URL is location; it is never quality, safety, or data rights.",
      datasetCards(inventory)
    ));
    root.appendChild(group(
      "Spaces",
      "Provider-reported stage captured in the dated snapshot, not a live probe from this document. The browser atlas below stays models, datasets, collections, and buckets.",
      spaceCards(inventory)
    ));
    root.appendChild(group(
      "Buckets",
      "Object and byte totals walked from the public bucket tree endpoint in the same capture.",
      bucketCards(inventory)
    ));
    renderProvenance(inventory, contract);
  }

  function fail(message) {
    Object.keys(COUNT_IDS).forEach(function (key) { setText(COUNT_IDS[key], null); });
    root.textContent = "";
    root.appendChild(emptyPanel(message));
    var line = document.getElementById("invProvenance");
    if (line) {
      line.textContent = "Committed inventory documents could not be read in this browser session · UNAVAILABLE · no count is substituted.";
    }
  }

  Promise.all([
    fetchJson("/public-inventory.json"),
    fetchJson("/models.json").catch(function () { return null; })
  ]).then(function (results) {
    var inventory = results[0];
    if (!inventory || !inventory.resources) {
      fail("The published inventory document did not contain a resources block.");
      return;
    }
    render(inventory, results[1]);
  }).catch(function () {
    fail("The published inventory document could not be read in this browser session.");
  });
}());
