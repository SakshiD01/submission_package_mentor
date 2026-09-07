/**
 * Operator console (technical report §13) — a screen over the batch-sequential
 * loop. Additive: it does not touch the simulator. All logic is server-side
 * (loop/operator_api.py); this file is fetch + render only.
 */

const API =
  (typeof window !== "undefined" && window.__ML_API_BASE__) ||
  (window.location && /^https?:$/i.test(window.location.protocol)
    ? window.location.origin
    : "http://localhost:8000");

const $ = (sel, root = document) => root.querySelector(sel);
const selectedPending = new Set();

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k === "html") e.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2), v);
    else if (v != null) e.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid == null) continue;
    e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return e;
}

async function api(path, opts) {
  const res = await fetch(`${API}${path}`, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data;
}

const fmtDate = (s) => (s ? new Date(s).toLocaleString() : "—");

// ── 1 · Dataset status ────────────────────────────────────────────────
async function loadStatus() {
  const body = $("#op-status .op-status-body");
  try {
    const d = await api("/api/operator/status");
    body.innerHTML = "";
    body.append(
      h("div", { class: "op-stat-row" },
        h("div", { class: "op-stat" }, h("div", { class: "op-stat-num" }, d.n_training_rows), h("div", { class: "op-stat-lbl" }, "training rows")),
        h("div", { class: "op-stat" }, h("div", { class: "op-stat-num" }, d.n_original_rows), h("div", { class: "op-stat-lbl" }, "original NOLHC")),
        h("div", { class: "op-stat" }, h("div", { class: "op-stat-num" }, d.n_training_rows - d.n_original_rows), h("div", { class: "op-stat-lbl" }, "added by rounds")),
        h("div", { class: "op-stat" }, h("div", { class: "op-stat-num" }, d.pending_open), h("div", { class: "op-stat-lbl" }, "pending review")),
      ),
    );

    const perKpi = h("table", { class: "op-table op-table--compact" },
      h("thead", {}, h("tr", {}, h("th", {}, "KPI"), h("th", {}, "rows"))),
      h("tbody", {}, ...Object.entries(d.per_kpi_rows).map(([k, n]) =>
        h("tr", {}, h("td", {}, k), h("td", { class: n < d.n_training_rows ? "op-warn" : "" }, n)))),
    );
    body.append(h("details", { class: "op-details" }, h("summary", {}, "Per-KPI row counts (uneven — see §15.3)"), perKpi));

    const rounds = h("table", { class: "op-table" },
      h("thead", {}, h("tr", {}, h("th", {}, "Round"), h("th", {}, "Scope"), h("th", {}, "Status"), h("th", {}, "Rows added"), h("th", {}, "Total after"), h("th", {}, "When"))),
      h("tbody", {}, ...d.rounds.map((r) =>
        h("tr", {},
          h("td", {}, r.round_id),
          h("td", {}, r.kpi_scope || "—"),
          h("td", {}, h("span", { class: `op-badge op-badge--${r.status === "ingested" ? "ok" : "wait"}` }, r.status)),
          h("td", {}, r.n_rows_added ?? "—"),
          h("td", {}, r.n_training_rows_after ?? "—"),
          h("td", {}, fmtDate(r.ingested_at || r.exported_at)),
        ))),
    );
    body.append(h("h3", {}, "Round history"), rounds);
  } catch (e) {
    body.innerHTML = `<div class="op-error">${e.message}</div>`;
  }
}

// ── 2 · Pending review ────────────────────────────────────────────────
async function loadPending() {
  const body = $("#op-pending .op-pending-body");
  try {
    const d = await api("/api/operator/pending");
    $("#op-pending-count").textContent = d.entries.length ? `(${d.entries.length})` : "";
    if (!d.entries.length) {
      body.innerHTML = `<div class="op-empty">No pending points. Scenarios that the trust screen flags as "verify" land here automatically.</div>`;
      return;
    }
    body.innerHTML = "";
    d.entries.forEach((e) => {
      const row = h("div", { class: "op-pend-row" },
        h("input", { type: "checkbox", "data-id": e.id, checked: selectedPending.has(e.id) ? "checked" : null,
          onchange: (ev) => { ev.target.checked ? selectedPending.add(e.id) : selectedPending.delete(e.id); } }),
        h("div", { class: "op-pend-main" },
          h("div", { class: "op-pend-reason" }, e.reason || "low trust"),
          h("div", { class: "op-pend-meta" }, `${e.source} · seen ${e.seen_count}× · ${fmtDate(e.created_at)}`),
        ),
        h("button", { class: "op-btn op-btn--sm", onclick: async () => {
          await api("/api/operator/pending/dismiss", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ entry_id: e.id }) });
          selectedPending.delete(e.id); loadPending(); loadStatus();
        } }, "Dismiss"),
      );
      body.append(row);
    });
  } catch (e) {
    body.innerHTML = `<div class="op-error">${e.message}</div>`;
  }
}

// ── 3 · Build a round ─────────────────────────────────────────────────
async function buildRound() {
  const out = $("#op-build .op-build-result");
  const btn = $("#op-build-btn");
  btn.disabled = true;
  out.innerHTML = `<div class="op-running">Proposing, scoring, flagging…</div>`;
  try {
    const payload = {
      // Fixed to all20 (operator.html) -- PROVEN_6 is a one-off, mentor-benchmarked
      // exercise, not a repeatable scope choice; DEMO_4 is strictly narrower than
      // all20 for the same generic mechanism, so there's no reason to pick it here.
      kpi_scope: "all20",
      n_candidates: Number($("#op-ncand").value),
      quantile: Number($("#op-quantile").value),
      max_batch_size: Number($("#op-batch").value),
      n_replications: Number($("#op-reps").value),
      seed: $("#op-seed").value === "" ? null : Number($("#op-seed").value),
    };
    if ($("#op-usepending").checked) payload.candidate_ids = [...selectedPending];
    const d = await api("/api/operator/round/export", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!d.round_id || d.flagged_count === 0) {
      out.innerHTML = `<div class="op-warnbox">${d.message || "Nothing flagged — try a lower quantile or more candidates."}</div>`;
      return;
    }
    out.innerHTML = "";
    out.append(
      h("div", { class: "op-okbox" },
        h("div", {}, h("strong", {}, `Round ${d.round_id}`), ` — ${d.flagged_count} candidate(s) flagged on ${d.kpi_scope}.`),
        h("a", { class: "op-btn op-btn--primary", href: `${API}/api/operator/worklist?round_id=${encodeURIComponent(d.round_id)}` }, "⬇ Download worklist (.xlsx)"),
        h("div", { class: "op-pend-meta" }, "Run these in AnyLogic Cloud by hand, then bring the results CSV back to panel 4."),
      ),
    );
    loadStatus(); loadPending(); refreshIngestRounds();
  } catch (e) {
    out.innerHTML = `<div class="op-error">${e.message}</div>`;
  } finally {
    btn.disabled = false;
  }
}

// ── 4 · Ingest results ────────────────────────────────────────────────
async function refreshIngestRounds() {
  try {
    const d = await api("/api/operator/status");
    const sel = $("#op-ingest-round");
    const cur = sel.value;
    sel.innerHTML = `<option value="">—</option>`;
    d.rounds.filter((r) => r.status !== "ingested").forEach((r) => {
      sel.append(h("option", { value: r.round_id }, `${r.round_id} (${r.kpi_scope})`));
    });
    if ([...sel.options].some((o) => o.value === cur)) sel.value = cur;
  } catch { /* ignore */ }
}

function _bufferToBase64(buf) {
  let binary = "";
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

async function ingestResults() {
  const out = $("#op-ingest .op-ingest-result");
  const btn = $("#op-ingest-btn");
  const roundId = $("#op-ingest-round").value;
  const text = $("#op-ingest-text").value.trim();
  const file = $("#op-ingest-file").files[0];
  if (!roundId) { out.innerHTML = `<div class="op-error">Pick a round.</div>`; return; }
  if (!file && !text) { out.innerHTML = `<div class="op-error">Paste CSV text, or upload a results file (.csv/.xlsx).</div>`; return; }
  btn.disabled = true;
  out.innerHTML = `<div class="op-running">Validating &amp; ingesting…</div>`;
  try {
    // A real result export is normally a binary .xlsx, not plain text --
    // read it as bytes and base64-encode for the JSON transport (6-Sep
    // fix) rather than file.text(), which corrupts anything non-CSV.
    // Pasted textarea content stays plain text -- it genuinely is text.
    const payload = { round_id: roundId };
    if (file) {
      payload.results_content_b64 = _bufferToBase64(await file.arrayBuffer());
      payload.filename = file.name;
    } else {
      payload.results_csv = text;
    }
    const d = await api("/api/operator/round/ingest", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    out.innerHTML = "";
    out.append(
      h("div", { class: "op-okbox" },
        h("div", {}, h("strong", {}, `+${d.rows_added} rows`), ` → ${d.n_training_rows_after} total.`),
        h("div", { class: "op-pend-meta" }, `Ingested KPI columns: ${d.ingested_kpi_columns.join(", ") || "—"}`),
      ),
    );
    if (d.warnings && d.warnings.length) {
      out.append(h("div", { class: "op-warnbox" },
        h("strong", {}, `${d.warnings.length} validation warning(s) — reviewed, not blocking:`),
        h("ul", {}, ...d.warnings.map((w) => h("li", {}, w))),
      ));
    }
    $("#op-ingest-text").value = "";
    loadStatus(); refreshIngestRounds();
  } catch (e) {
    out.innerHTML = `<div class="op-error">${e.message}</div>`;
  } finally {
    btn.disabled = false;
  }
}

// ── 5 · Recalibration check ───────────────────────────────────────────
async function runRecal() {
  const out = $("#op-recal .op-recal-result");
  const btn = $("#op-recal-btn");
  btn.disabled = true;
  out.innerHTML = `<div class="op-running">Re-benchmarking each PROVEN_6 family on the current data…</div>`;
  try {
    const d = await api("/api/operator/recalibrate");
    out.innerHTML = "";
    out.append(h("div", { class: d.review_count ? "op-warnbox" : "op-okbox" },
      d.review_count ? `${d.review_count} KPI(s) would recommend a different method — review before touching proven6.py.` : "All PROVEN_6 methods still confirm their fixed choice."));
    out.append(h("table", { class: "op-table" },
      h("thead", {}, h("tr", {}, h("th", {}, "KPI"), h("th", {}, "Family"), h("th", {}, "n"), h("th", {}, "Fixed method"), h("th", {}, "Best now"), h("th", {}, ""))),
      h("tbody", {}, ...d.checks.map((c) =>
        h("tr", { class: c.review_needed ? "op-row-review" : "" },
          h("td", {}, c.kpi_slug),
          h("td", {}, c.family),
          h("td", {}, `${c.n_train}/${c.n_test}`),
          h("td", {}, c.fixed_method),
          h("td", {}, c.best_method),
          h("td", {}, c.review_needed ? h("span", { class: "op-badge op-badge--wait" }, "REVIEW") : "✓"),
        ))),
    ));
  } catch (e) {
    out.innerHTML = `<div class="op-error">${e.message}</div>`;
  } finally {
    btn.disabled = false;
  }
}

// ── wire ─────────────────────────────────────────────────────────────
$("#op-build-btn").addEventListener("click", buildRound);
$("#op-ingest-btn").addEventListener("click", ingestResults);
$("#op-recal-btn").addEventListener("click", runRecal);
loadStatus();
loadPending();
refreshIngestRounds();
