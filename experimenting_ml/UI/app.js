/**
 * NOLHC ML UI — app glue (NOLHC_ML_UI_Spec.md).
 * Vanilla ES modules: data.js + components.js + this file.
 */

import {
  PORT_COORDS,
  MAP_ROUTES,
  APP_CONFIG,
  KPI_META,
  KPI_CATEGORIES,
  NOLHC_MEDIANS,
  OUTPUT_API_TARGETS,
  colToSlug,
} from "./data/data.js";

import {
  CONFIG_STORAGE_KEY,
  PARAMETER_META,
  PARAMETER_LABELS,
  formatRangeLabel,
  loadSavedConfig,
  saveConfigToStorage,
} from "./data/parameter_meta.js";
import { getParameterModalSections } from "./data/parameter_help.js";
import { SCENARIO_FAMILIES } from "./data/scenario_sheets.js";

import {
  el,
  InfoIconButton,
  UtilBar,
  KpiCard,
  NumberField,
  SectionCard,
  IndRow,
  EmptyState,
} from "./components/components.js";

const API_ML_BASE =
  (typeof window !== "undefined" && window.__ML_API_BASE__) ||
  (typeof window !== "undefined" &&
  window.location &&
  /^https?:$/i.test(window.location.protocol || "")
    ? window.location.origin
    : "http://localhost:8000");

const CATEGORY_ORDER = ["agri", "non_agri", "routes", "staff"];

/** @type {typeof NOLHC_MEDIANS} */
const state = {
  config: { ...NOLHC_MEDIANS },
  hasRun: false,
  loading: false,
  lastResult: null,
  /** Raw `/api/predict` `predictions` map (API target keys → `{ model, prediction, … }`) for SHAP lookup. */
  lastPredictions: null,
  /** Last `focus_target` sent to `/api/predict` (default for SHAP dropdown). */
  lastShapFocusTarget: null,
  /** Selected API output column for SHAP panel (e.g. `TT_OB_Agri`); synced from `focus_target` after each run. */
  shapSelectedApiTarget: null,
  apiError: null,
  activeView: "results",
  modelAvgR2: null,
  modelVersion: "v1",
  /** `/api/predict` `reliability` block: novelty + per-KPI interval width + accept/verify decision (technical report §13.3). */
  reliability: null,
};

let mapInstance = null;
let debouncedPredictTimer = null;
let runHintEl = null;
const scenarioUiState = {
  familyId: SCENARIO_FAMILIES[0]?.id || null,
  levelId: "as_is",
  values: {},
};

/**
 * Excel scenario keys -> live simulator config keys.
 * This is a best-effort bridge between scenario workbook naming and NOLHC API schema.
 */
const SCENARIO_TO_CONFIG_MAP = {
  PerGreenTrucksAPImIR: "Pct_NA_IB_Green",
  PerFullIdnChkAPImIR: "Pct_NA_IB_Red",
  PerPhyChkAPImIR: "Pct_NA_IB_Red",
  PerGreenTrucksAgriImIR: "Pct_A_IB_Red",
  PerFullIdnChkAgriImIR: "Pct_A_IB_Red",
  PerPhyChkAgriImIR: "Pct_A_IB_Red",
  DocChkTimeAPImIR: "ChkTime_Doc",
  DocChkTimeAgriImIR: "ChkTime_Doc",
  PhyChkTimeAPImIR: "ChkTime_Phy",
  PhyChkTimeAgriImIR: "ChkTime_Phy",
  PerGreenTrucksAPImUKW: "Pct_NA_OB_Green",
  PerFullIdnChkAPImUKW: "Pct_NA_OB_Red",
  PerPhyChkAPImUKW: "Pct_NA_OB_Red",
  PerGreenTrucksAgriImUKW: "Pct_A_OB_Red",
  PerFullIdnChkAgriImUKW: "Pct_A_OB_Red",
  PerPhyChkAgriImUKW: "Pct_A_OB_Red",
  DocChkTimeAPImUKW: "ChkTime_Doc",
  DocChkTimeAgriImUKW: "ChkTime_Doc",
  PhyChkTimeAPImUKW: "ChkTime_Phy",
  PhyChkTimeAgriImUKW: "ChkTime_Phy",
};

/** Field-type icons: non-agri commodity, agri (plant), vessel, officer roles, border. */
const IC = {
  nonAgri: "📦",
  agri: "🌾",
  ship: "🚢",
  docOfficer: "📋",
  inspectOfficer: "🔍",
  customs: "👮",
  spsOfficer: "🏥",
  border: "🛂",
};

const DIRECT_ROUTE_EDITABLE_KEYS = new Set([
  "NA_Im_LB",
  "NA_Im_DR",
  "NA_Ex_LB",
  "NA_Ex_DR",
  "A_Im_LB",
  "A_Im_DR",
  "A_Ex_LB",
  "A_Ex_DR",
  "ChkTime_Doc",
  "ChkTime_Phy",
  "NumCusShed_D",
  "NumDAFM_D",
  "NumCusShed_R",
  "NumDAFM_R",
  "Pct_NA_OB_Green",
  "Pct_NA_OB_Red",
  "Pct_A_OB_Red",
  "Pct_NA_IB_Green",
  "Pct_NA_IB_Red",
  "Pct_A_IB_Red",
  "Pct_IB_PreBoard",
  "Pct_OB_PreBoard",
]);

const NON_TARIFF_EDITABLE_KEYS = new Set([
  "NA_Im_LB",
  "NA_Ex_LB",
  "A_Im_LB",
  "A_Ex_LB",
  "ChkTime_Doc",
  "ChkTime_Phy",
  "NumCusShed_D",
  "NumDAFM_D",
  "NumCusShed_R",
  "NumDAFM_R",
  "Pct_NA_OB_Green",
  "Pct_NA_OB_Red",
  "Pct_A_OB_Red",
  "Pct_NA_IB_Green",
  "Pct_NA_IB_Red",
  "Pct_A_IB_Red",
  "Pct_IB_PreBoard",
  "Pct_OB_PreBoard",
]);

const SCENARIO_EDITABLE_KEYS = {
  direct_route: DIRECT_ROUTE_EDITABLE_KEYS,
  non_tariff: NON_TARIFF_EDITABLE_KEYS,
};

function isEditableByScenarioPolicy(apiKey, familyId = scenarioUiState.familyId) {
  const allow = SCENARIO_EDITABLE_KEYS[familyId];
  if (!allow) return true;
  return allow.has(apiKey);
}

function lockedReasonForScenarioPolicy(familyId = scenarioUiState.familyId) {
  if (familyId === "direct_route") {
    return "Locked in Direct Route scenario policy (mentor mapping).";
  }
  if (familyId === "non_tariff") {
    return "Locked in Non-Tariff scenario policy (mentor mapping).";
  }
  return "Locked by current scenario policy.";
}

let formFieldStagger = 0;

let persistTimer = null;
function schedulePersistConfig() {
  clearTimeout(persistTimer);
  persistTimer = setTimeout(() => {
    saveConfigToStorage(state.config);
  }, 400);
}

function hoursFromPred(pr) {
  if (!pr || pr.value == null || pr.value === undefined) return null;
  const v = Number(pr.value);
  return Number.isFinite(v) ? v : null;
}

function timelineSep(dashed = false) {
  return el("div", { class: dashed ? "timeline-sep timeline-sep--dash" : "timeline-sep" });
}

function timelinePort(emojiLabel, pr) {
  const stop = el("div", { class: "timeline-stop" });
  stop.append(el("div", { class: "timeline-dot" }));
  stop.append(el("div", { class: "timeline-name" }, emojiLabel));
  const w = hoursFromPred(pr);
  if (w != null && w > 0) stop.append(el("div", { class: "timeline-wait" }, `${w.toFixed(1)}h wait`));
  return stop;
}

function timelineFerry(ttPr, sublabel) {
  const f = el("div", { class: "timeline-ferry" });
  f.append(el("span", { class: "timeline-ship" }, "🚢"));
  const h = hoursFromPred(ttPr);
  if (h != null) f.append(el("span", { class: "timeline-ferry-hours" }, `${h.toFixed(1)}h`));
  if (sublabel) f.append(el("span", { class: "timeline-ferry-sub" }, sublabel));
  return f;
}

/** Multi-leg journey: agri / non-agri / landbridge / direct — uses NOLHC API slugs. */
function renderNolhcJourneyTimeline(lr) {
  if (!lr || typeof lr !== "object") return null;

  const box = el("div", { class: "timeline-box timeline-box--nolhc" });
  box.append(el("div", { class: "timeline-label" }, "Journey breakdown"));

  const row1 = el("div", { class: "timeline-row" });
  row1.append(timelinePort("🌾 Agri · IRE inbound", lr.wt_ib_a_dub));
  row1.append(timelineSep());
  row1.append(timelineFerry(lr.tt_ib_agri, "sea leg"));
  row1.append(timelineSep());
  row1.append(timelinePort("GB · Agri (Dub)", lr.wt_ob_a_gb_dub));
  row1.append(timelineSep());
  row1.append(timelineFerry(lr.tt_ob_agri, "return"));
  row1.append(timelineSep());
  row1.append(timelinePort("📦 Non-agri · IRE", lr.wt_ib_na_dub));
  row1.append(timelineSep());
  row1.append(timelinePort("GB · Non-agri", lr.wt_ob_na_gb_dub));
  box.append(row1);

  const row2 = el("div", { class: "timeline-row timeline-row--secondary" });
  row2.append(el("div", { class: "timeline-row-tag" }, "🛤 Landbridge"));
  row2.append(timelineFerry(lr.tt_ib_lb, "TT in"));
  row2.append(timelineSep(true));
  row2.append(timelinePort("Wait / mid", lr.wt_ib_lb));
  row2.append(timelineSep(true));
  row2.append(timelineFerry(lr.tt_ob_lb, "TT out"));
  box.append(row2);

  const row3 = el("div", { class: "timeline-row timeline-row--secondary" });
  row3.append(el("div", { class: "timeline-row-tag" }, "⛴ Direct EU"));
  row3.append(timelineFerry(lr.tt_ib_dr, "in"));
  row3.append(timelineSep());
  row3.append(timelineFerry(lr.tt_ob_dr, "out"));
  box.append(row3);

  const samples = [
    hoursFromPred(lr.tt_ib_agri),
    hoursFromPred(lr.tt_ob_agri),
    hoursFromPred(lr.tt_ib_lb),
    hoursFromPred(lr.tt_ob_lb),
    hoursFromPred(lr.tt_ib_dr),
    hoursFromPred(lr.tt_ob_dr),
  ].filter((x) => x != null);
  const avg = samples.length ? samples.reduce((a, b) => a + b, 0) / samples.length : null;

  const total = el("div", { class: "timeline-total" });
  total.append(
    el("span", {}, "Average total transport time (agri + landbridge + direct; in/out)"),
    el("span", {}, avg != null ? `${avg.toFixed(1)} hrs` : "—"),
  );
  box.append(total);

  return box;
}

function fieldIdForApiKey(apiKey) {
  return `f-${apiKey.replace(/_/g, "-").toLowerCase()}`;
}

function truckHint(tonnes) {
  const t = Number(tonnes) || 0;
  return `≈ ${Math.round(t / APP_CONFIG.tonnesPerTruck).toLocaleString()} trucks`;
}

function refreshVolumeHints() {
  for (const key of ["NA_Im", "NA_Ex", "A_Im", "A_Ex"]) {
    const hint = document.getElementById(`${fieldIdForApiKey(key)}-hint`);
    if (hint) hint.textContent = truckHint(state.config[key]);
  }
}

/** Aligns with run_ui_inference_api._scenario_vector: shift columns track direct-route share (tonnes). */
const ROUTE_VOLUME_PAIRS = [
  ["NA_Im", "NA_Im_LB", "NA_Im_DR", "Shift_NA_Im_LB_to_Cher"],
  ["NA_Ex", "NA_Ex_LB", "NA_Ex_DR", "Shift_NA_Ex_LB_to_Cher"],
  ["A_Im", "A_Im_LB", "A_Im_DR", "Shift_A_Im_LB_to_Cher"],
  ["A_Ex", "A_Ex_LB", "A_Ex_DR", "Shift_A_Ex_LB_to_Cher"],
];

/** As-Is: 100% LB / 0% DR; Scenario 1: 60% LB / 40% DR; Scenario 2: 15% LB / 85% DR (of ideal corridor tonnes). */
function landbridgeDirectFractionForScenarioLevel(levelId) {
  if (levelId === "as_is") return { lb: 1, dr: 0 };
  if (levelId === "scenario_1") return { lb: 0.6, dr: 0.4 };
  if (levelId === "scenario_2") return { lb: 0.15, dr: 0.85 };
  return { lb: 1, dr: 0 };
}

function applyDirectRouteCorridorTonnes(family) {
  if (!family || family.id !== "direct_route") return;
  const { lb, dr } = landbridgeDirectFractionForScenarioLevel(scenarioUiState.levelId);
  const c = { ...state.config };
  for (const [total, lbk, drk, shk] of ROUTE_VOLUME_PAIRS) {
    const t = Number(c[total]) || 0;
    c[lbk] = t * lb;
    c[drk] = t * dr;
    c[shk] = t * dr;
  }
  state.config = c;
  saveConfigToStorage(state.config);
}

/** Maps UI scenario ids to run_ui_inference_api /api/infer scenario_family. */
function scenarioFamilyToInferApi() {
  if (scenarioUiState.familyId === "non_tariff") return "border";
  return "routes";
}

/** Maps UI level ids to infer scenario_level (baseline / moderate / significant). */
function scenarioLevelToInferApi() {
  if (scenarioUiState.levelId === "scenario_1") return "moderate";
  if (scenarioUiState.levelId === "scenario_2") return "significant";
  return "baseline";
}

/** Physical-domain guards for displayed KPIs (hours ≥ 0, utilisation in [0, 1]). */
function clipKpiRow(slug, row) {
  if (!row || row.value == null) return row;
  let v = Number(row.value);
  if (!Number.isFinite(v)) return row;
  const meta = KPI_META[slug];
  const unitStr = (row.unit || "").toLowerCase();
  const isFrac = Boolean(meta?.fraction || row.unit === "fraction" || unitStr === "fraction");
  const isHours =
    (meta && !meta.fraction) ||
    (!meta && /^(tt_|wt_)/.test(slug)) ||
    unitStr.includes("hour");
  let clipped = false;
  if (isFrac) {
    const c = Math.max(0, Math.min(1, v));
    if (c !== v) clipped = true;
    v = c;
  } else if (isHours) {
    const c = Math.max(0, v);
    if (c !== v) clipped = true;
    v = c;
  }
  const wasFlagged = row.status === "clipped_to_domain";
  return {
    ...row,
    value: v,
    status: clipped || wasFlagged ? "clipped_to_domain" : row.status,
  };
}

function clipSimulatorResult(lr) {
  const out = {};
  for (const [slug, pr] of Object.entries(lr || {})) {
    out[slug] = clipKpiRow(slug, pr);
  }
  return out;
}

/** Converts /api/infer predictions object to the shape renderResults expects (slug keys). */
function normalizeInferToSimulatorResult(preds) {
  const out = {};
  for (const [target, row] of Object.entries(preds || {})) {
    const slug = String(target).toLowerCase().replace(/-/g, "_");
    if (!KPI_META[slug]) continue;
    const meta = KPI_META[slug];
    const val = Number(row.prediction);
    if (!Number.isFinite(val)) continue;
    out[slug] = {
      value: val,
      unit: meta.fraction ? "fraction" : "hours",
      status: row.clipped_to_domain ? "clipped_to_domain" : "ok",
      r2: null,
      registered_as: String(row.model || ""),
      mae: 0,
    };
  }
  return out;
}

function safeShapFilenamePart(s) {
  return String(s).replace(/[^a-zA-Z0-9_.-]+/g, "_");
}

/** Parse `feature,mean_abs_shap` CSV from step4_shap. */
function parseShapImportanceCsv(text) {
  const lines = text.trim().split(/\r?\n/).filter((l) => l.length);
  if (lines.length < 2) return [];
  const header = lines[0].split(",").map((h) => h.trim().toLowerCase());
  const fi = header.indexOf("feature");
  const vi = header.indexOf("mean_abs_shap");
  if (fi < 0 || vi < 0) return [];
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(",");
    const feature = (cols[fi] || "").trim();
    const mean = parseFloat(String(cols[vi] || "").trim());
    if (feature && Number.isFinite(mean)) rows.push({ feature, mean_abs_shap: mean });
  }
  return rows;
}

async function loadShapIntoHost(host, noteEl, apiTarget) {
  const target = String(apiTarget || "").trim();
  host.innerHTML = "";
  host.append(el("div", { class: "scenario-llm-item" }, "Loading input importance…"));

  const preds = state.lastPredictions;
  if (!preds || typeof preds !== "object" || !Object.keys(preds).length) {
    host.innerHTML = "";
    host.append(
      el("div", { class: "scenario-llm-item" }, "Run a prediction to load input-importance (SHAP) drivers."),
    );
    if (noteEl) noteEl.innerHTML = "";
    return;
  }

  const model = preds[target]?.model ? String(preds[target].model) : "";
  const slug = colToSlug(target);
  const kpiLabel = KPI_META[slug]?.label || target;

  if (!model) {
    host.innerHTML = "";
    host.append(
      el(
        "div",
        { class: "scenario-llm-item" },
        `No model metadata for “${kpiLabel}” in the last run. Run simulation again.`,
      ),
    );
    if (noteEl) {
      noteEl.innerHTML = "";
      noteEl.append(
        el("div", { class: "scenario-llm-item" },
          el("strong", {}, "Model: "),
          "—",
        ),
        el("div", { class: "scenario-llm-item" },
          el("strong", {}, "Note: "),
          `SHAP files are named per target and registered model. After a full /api/predict, the model for ${kpiLabel} should appear here.`,
        ),
      );
    }
    return;
  }

  const base = API_ML_BASE.replace(/\/$/, "");
  const url = `${base}/outputs/step4_shap/${safeShapFilenamePart(target)}__${safeShapFilenamePart(model)}__importance.csv`;
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const rows = parseShapImportanceCsv(await r.text()).slice(0, 10);
    if (!rows.length) throw new Error("Empty or invalid SHAP CSV");
    const maxS = Math.max(...rows.map((x) => x.mean_abs_shap), 1e-12);
    host.innerHTML = "";
    for (const row of rows) {
      const label = PARAMETER_LABELS[row.feature] || row.feature;
      const pct = Math.round((row.mean_abs_shap / maxS) * 100);
      host.append(
        el("div", { class: "scenario-xai-row" },
          el("div", { class: "scenario-xai-label" }, label),
          el("div", { class: "scenario-xai-bar-bg" }, el("div", { class: "scenario-xai-bar-fill", style: { width: `${Math.max(4, pct)}%` } })),
          el("div", { class: "scenario-xai-val" }, row.mean_abs_shap.toFixed(3)),
        ),
      );
    }
    if (noteEl) {
      noteEl.innerHTML = "";
      noteEl.append(
        el("div", { class: "scenario-llm-item" },
          el("strong", {}, "Model: "),
          model,
        ),
        el("div", { class: "scenario-llm-item" },
          el("strong", {}, "Note: "),
          `Mean |SHAP| for “${kpiLabel}” (${target}) using ${model} — global importance from the offline CV pipeline for this output, not the delta from your last slider change.`,
        ),
      );
    }
  } catch (e) {
    host.innerHTML = "";
    host.append(
      el("div", { class: "scenario-llm-item" },
        `Could not load SHAP for ${kpiLabel} (${String(e.message || e)}). Ensure outputs/step4_shap is served next to /api/predict.`,
      ),
    );
    if (noteEl) {
      noteEl.innerHTML = "";
      noteEl.append(
        el("div", { class: "scenario-llm-item" },
          el("strong", {}, "Model: "),
          model,
        ),
      );
    }
  }
}

function appendShapAttributionPanel(right) {
  const host = el("div", { class: "scenario-xai-list" });
  const note = el("div", { class: "scenario-llm-panel" });

  const defaultApi =
    state.shapSelectedApiTarget ||
    state.lastShapFocusTarget ||
    OUTPUT_API_TARGETS[0] ||
    "TT_OB_Agri";
  const initial = OUTPUT_API_TARGETS.includes(defaultApi) ? defaultApi : OUTPUT_API_TARGETS[0];

  const select = el("select", {
    class: "scenario-select shap-kpi-select",
    id: "shap-kpi-select",
    "aria-label": "Focus KPI for SHAP importance",
    onchange: (e) => {
      const v = e.target?.value;
      if (!v) return;
      state.shapSelectedApiTarget = v;
      void loadShapIntoHost(host, note, v);
    },
  });
  for (const api of OUTPUT_API_TARGETS) {
    const slug = colToSlug(api);
    const optLabel = KPI_META[slug]?.label || api;
    select.append(el("option", { value: api }, optLabel));
  }
  select.value = initial;

  const toolbar = el("div", { class: "shap-kpi-toolbar" },
    el("label", { class: "scenario-select-label", htmlFor: "shap-kpi-select" }, "Focus KPI"),
    select,
  );

  right.append(
    SectionCard(
      "Explanatory drivers (SHAP)",
      "blue",
      el(
        "div",
        { class: "scenario-llm-item", style: { opacity: 0.9, marginBottom: "10px" } },
        "Pick an output (KPI) below. Bars show which NOLHC inputs matter most for that target (mean |SHAP| from the trained model).",
      ),
      toolbar,
      host,
      note,
    ),
  );
  void loadShapIntoHost(host, note, initial);
}

function inputRealismSummary() {
  const outOfRange = [];
  const nearEdge = [];
  for (const [k, m] of Object.entries(PARAMETER_META)) {
    const v = Number(state.config[k]);
    if (!Number.isFinite(v)) continue;
    if (v < m.min || v > m.max) {
      outOfRange.push(`${k} (${v.toFixed(2)})`);
      continue;
    }
    const span = m.max - m.min;
    if (span <= 0) continue;
    const edgePct = Math.min((v - m.min) / span, (m.max - v) / span);
    if (edgePct < 0.05) nearEdge.push(k);
  }
  const risk = outOfRange.length ? "high" : nearEdge.length > 6 ? "medium" : "low";
  return { outOfRange, nearEdge, risk };
}

function realismPanel() {
  const s = inputRealismSummary();
  const tone = s.risk === "high" ? "amber" : "teal";
  const lines = [
    `Calibrated range check: ${s.outOfRange.length ? "Out-of-range inputs detected" : "All inputs in allowed bounds"}`,
    `Near-edge inputs (<= 5% from min/max): ${s.nearEdge.length}`,
  ];
  if (s.outOfRange.length) lines.push(`Out-of-range keys: ${s.outOfRange.slice(0, 6).join(", ")}`);
  return SectionCard(
    "Input realism checks",
    tone,
    el("div", { class: "scenario-llm-panel" }, ...lines.map((t) => el("div", { class: "scenario-llm-item" }, t))),
  );
}

function buildPredictBody() {
  return {
    NA_Im: state.config.NA_Im,
    NA_Ex: state.config.NA_Ex,
    A_Im: state.config.A_Im,
    A_Ex: state.config.A_Ex,
    NA_Im_LB: state.config.NA_Im_LB,
    NA_Im_DR: state.config.NA_Im_DR,
    NA_Ex_LB: state.config.NA_Ex_LB,
    NA_Ex_DR: state.config.NA_Ex_DR,
    A_Im_LB: state.config.A_Im_LB,
    A_Im_DR: state.config.A_Im_DR,
    A_Ex_LB: state.config.A_Ex_LB,
    A_Ex_DR: state.config.A_Ex_DR,
    Shift_NA_Im_LB_to_Cher: state.config.Shift_NA_Im_LB_to_Cher,
    Shift_NA_Ex_LB_to_Cher: state.config.Shift_NA_Ex_LB_to_Cher,
    Shift_A_Im_LB_to_Cher: state.config.Shift_A_Im_LB_to_Cher,
    Shift_A_Ex_LB_to_Cher: state.config.Shift_A_Ex_LB_to_Cher,
    VCap_Dub_Hey: state.config.VCap_Dub_Hey,
    VCap_Dub_Holy: state.config.VCap_Dub_Holy,
    VCap_Dub_Liv: state.config.VCap_Dub_Liv,
    VCap_Ross_Fish: state.config.VCap_Ross_Fish,
    VCap_Ross_Pem: state.config.VCap_Ross_Pem,
    ChkTime_Doc: state.config.ChkTime_Doc,
    ChkTime_Phy: state.config.ChkTime_Phy,
    NumCusShed_D: state.config.NumCusShed_D,
    NumDAFM_D: state.config.NumDAFM_D,
    NumCusShed_R: state.config.NumCusShed_R,
    NumDAFM_R: state.config.NumDAFM_R,
    Pct_NA_OB_Green: state.config.Pct_NA_OB_Green,
    Pct_NA_OB_Red: state.config.Pct_NA_OB_Red,
    Pct_A_OB_Red: state.config.Pct_A_OB_Red,
    Pct_NA_IB_Green: state.config.Pct_NA_IB_Green,
    Pct_NA_IB_Red: state.config.Pct_NA_IB_Red,
    Pct_A_IB_Red: state.config.Pct_A_IB_Red,
    Pct_IB_PreBoard: state.config.Pct_IB_PreBoard,
    Pct_OB_PreBoard: state.config.Pct_OB_PreBoard,
  };
}

function validateRun() {
  const c = state.config;
  const issues = [];
  if (!(c.NA_Im > 0 && c.NA_Ex > 0 && c.A_Im > 0 && c.A_Ex > 0)) {
    issues.push("📦 Shifts in Trade Volume");
  }
  const anyVcap =
    c.VCap_Dub_Hey > 0 ||
    c.VCap_Dub_Holy > 0 ||
    c.VCap_Dub_Liv > 0 ||
    c.VCap_Ross_Fish > 0 ||
    c.VCap_Ross_Pem > 0;
  if (!anyVcap) issues.push("🚢 Direct Routes to Mainland Europe");
  if (!(c.ChkTime_Doc > 0 && c.ChkTime_Phy > 0)) issues.push("👮 Customs Expertise & Resources");
  if (!(c.NumCusShed_D >= 1 && c.NumDAFM_D >= 1)) issues.push("👮 Customs Expertise & Resources");
  return issues;
}

function runButtonEnabled() {
  return validateRun().length === 0;
}

function updateRunButtonState() {
  const btn = document.getElementById("btn-run-predict");
  if (!btn) return;
  const ok = runButtonEnabled();
  btn.disabled = !ok;
  btn.classList.remove("btn-run-simulation--ready", "btn-run-simulation--loading");
  if (ok) btn.classList.add("btn-run-simulation--ready");
  if (runHintEl) {
    runHintEl.textContent = ok ? "" : `Missing required values in: ${validateRun().join(", ")}`;
  }
}

function maybeAutoPredict() {
  if (!state.hasRun) return;
  if (debouncedPredictTimer) clearTimeout(debouncedPredictTimer);
  debouncedPredictTimer = setTimeout(() => {
    debouncedPredictTimer = null;
    if (runButtonEnabled()) void runPrediction();
  }, 300);
}

function bindNumber(apiKey, opts) {
  const id = fieldIdForApiKey(apiKey);
  const {
    label,
    required = false,
    min: optMin,
    max: optMax,
    step: optStep,
    tooltip,
    usePlainText = false,
    isPercent = false,
    fieldIcon = null,
  } = opts;
  const lockedByPolicy = !isEditableByScenarioPolicy(apiKey);
  const lockReason = lockedByPolicy ? lockedReasonForScenarioPolicy() : null;

  const m = PARAMETER_META[apiKey];
  const min = m != null ? (isPercent ? m.min * 100 : m.min) : optMin ?? 0;
  const max = m != null ? (isPercent ? m.max * 100 : m.max) : optMax;
  const step =
    m?.step != null && !isPercent ? m.step : isPercent ? 1 : optStep;

  const displayValue = isPercent ? Math.round(state.config[apiKey] * 10000) / 100 : state.config[apiKey];
  const staggerMs = (formFieldStagger++) * 38;

  const detail = m?.detail ?? tooltip ?? null;
  const { wrap } = NumberField({
    id,
    label,
    required,
    value: displayValue,
    min,
    max,
    step,
    tooltip: m ? null : tooltip,
    infoSections: m ? getParameterModalSections(apiKey, isPercent) : undefined,
    infoDetail: m ? null : detail,
    infoPorts: m?.ports ?? null,
    rangeLabel: m ? formatRangeLabel(apiKey, isPercent) : undefined,
    usePlainText,
    fieldIcon,
    staggerMs,
    disabled: lockedByPolicy,
    slider: true,
    onChange: (v) => {
      if (lockedByPolicy) return;
      state.config[apiKey] = isPercent ? v / 100 : v;
      if (["NA_Im", "NA_Ex", "A_Im", "A_Ex"].includes(apiKey)) {
        refreshVolumeHints();
        applyDirectRouteCorridorTonnes(activeScenarioFamily());
      }
      updateRunButtonState();
      maybeAutoPredict();
      schedulePersistConfig();
    },
  });
  if (lockReason) {
    wrap.append(el("div", { class: "field-lock-note" }, `🔒 ${lockReason}`));
  }
  return wrap;
}

function factorGroupHeaderRow(title, badge, headerTooltip) {
  const left = el("div", { class: "factor-group-title-row" },
    el("span", { class: "factor-group-chevron" }, "▼"),
    el("span", {}, title),
  );
  if (headerTooltip) left.append(InfoIconButton(title, headerTooltip, null));
  return el(
    "div",
    {
      style: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        width: "100%",
        gap: "10px",
      },
    },
    left,
    el("span", { class: "factor-group-badge" }, badge),
  );
}

function createFactorGroup(open, title, badge, headerTooltip, bodyNodes) {
  const grp = el("div", { class: `factor-group${open ? " open" : ""}` });
  const hdr = el("div", { class: "factor-group-header" });
  hdr.append(factorGroupHeaderRow(title, badge, headerTooltip));
  hdr.addEventListener("click", () => grp.classList.toggle("open"));
  const body = el("div", { class: "factor-group-body" });
  body.append(...bodyNodes);
  grp.append(hdr, body);
  return grp;
}

function buildInputForm() {
  const formBody = document.getElementById("form-body");
  const formFooter = document.getElementById("form-footer");
  if (!formBody || !formFooter) return;

  formBody.innerHTML = "";
  formFieldStagger = 0;
  const family = activeScenarioFamily();
  if (!scenarioUiState.values || Object.keys(scenarioUiState.values).length === 0) {
    scenarioUiState.values = defaultScenarioValues(family, scenarioUiState.levelId);
    applyScenarioValuesToConfig(family);
  }

  const familySelect = el("select", {
    class: "scenario-select",
    onchange: (e) => {
      scenarioUiState.familyId = e.target.value;
      const selected = activeScenarioFamily();
      scenarioUiState.values = defaultScenarioValues(selected, scenarioUiState.levelId);
      applyScenarioValuesToConfig(selected);
      buildInputForm();
    },
  });
  SCENARIO_FAMILIES.forEach((f) => familySelect.append(el("option", { value: f.id }, f.title)));
  familySelect.value = family.id;

  const levelRow = el("div", { class: "scenario-level-row" });
  family.levels.forEach((lvl) => {
    levelRow.append(
      el(
        "button",
        {
          type: "button",
          class: `scenario-level-btn${scenarioUiState.levelId === lvl.id ? " active" : ""}`,
          onclick: () => {
            scenarioUiState.levelId = lvl.id;
            scenarioUiState.values = defaultScenarioValues(family, lvl.id);
            applyScenarioValuesToConfig(family);
            buildInputForm();
          },
        },
        lvl.label,
      ),
    );
  });

  const mainCfgChildren = [
    el("div", { class: "scenario-config-head" },
      el("label", { class: "scenario-select-label" }, "Scenario family"),
      familySelect,
    ),
    levelRow,
    el("p", { class: "scenario-family-desc" }, family.description),
  ];
  if (family.id === "direct_route") {
    mainCfgChildren.push(
      el(
        "p",
        { class: "scenario-tonne-note" },
        "Route volumes (tonnes): As-Is = 100% landbridge / 0% direct; Scenario 1 = 60% / 40%; Scenario 2 = 15% / 85% of corridor totals (NA_Im, NA_Ex, A_Im, A_Ex). Same logic as Decision Intelligence.",
      ),
    );
  }
  formBody.append(el("div", { class: "scenario-config-block" }, ...mainCfgChildren));
  const editableKeys = SCENARIO_EDITABLE_KEYS[family.id];
  if (editableKeys) {
    formBody.append(
      el(
        "div",
        { class: "scenario-policy-note" },
        `Scenario policy: ${editableKeys.size} / ${Object.keys(PARAMETER_META).length} parameters are editable in this family.`,
      ),
    );
  }

  const g1 = createFactorGroup(
    true,
    "📦 Shifts in Trade Volume",
    "4 params",
    "Import and export volumes of Agri and Non-Agri products between GB and Ireland",
    [
      bindNumber("NA_Im", {
        label: "Non-Agri Import Volume",
        required: true,
        min: 1,
        fieldIcon: IC.nonAgri,
        tooltip:
          "Demand of inbound non-agri products arriving from GB to Ireland. Increasing this raises pressure on Irish port customs and DAFM resources.",
        hint: truckHint(state.config.NA_Im),
      }),
      bindNumber("NA_Ex", {
        label: "Non-Agri Export Volume",
        required: true,
        min: 1,
        fieldIcon: IC.nonAgri,
        tooltip:
          "Demand of outbound non-agri products leaving Ireland to GB. Affects waiting times at UK-side ports.",
        hint: truckHint(state.config.NA_Ex),
      }),
      bindNumber("A_Im", {
        label: "Agri Import Volume",
        required: true,
        min: 1,
        fieldIcon: IC.agri,
        tooltip:
          "Demand of inbound agri-food products from GB to Ireland. Agri products face SPS checks — higher volumes increase DAFM bay utilisation significantly.",
        hint: truckHint(state.config.A_Im),
      }),
      bindNumber("A_Ex", {
        label: "Agri Export Volume",
        required: true,
        min: 1,
        fieldIcon: IC.agri,
        tooltip:
          "Demand of outbound agri-food products from Ireland to GB. Affects outbound SPS check queues at Irish ports.",
        hint: truckHint(state.config.A_Ex),
      }),
    ],
  );

  const g2body = [
    el("div", { class: "form-subheading" }, "Volume shifts (tonnes)"),
    bindNumber("NA_Im_LB", {
      label: "Non-Agri Import — Landbridge share",
      min: 0,
      fieldIcon: IC.nonAgri,
      tooltip:
        "Volume of non-agri imports routed via GB Landbridge (through Dover/Calais). Reducing this shifts freight to Direct routes.",
    }),
    bindNumber("NA_Im_DR", {
      label: "Non-Agri Import — Direct Route share",
      min: 0,
      fieldIcon: IC.nonAgri,
      tooltip: "Volume of non-agri imports arriving via Direct EU routes (Cherbourg, Rotterdam, Zeebrugge).",
    }),
    bindNumber("NA_Ex_LB", {
      label: "Non-Agri Export — Landbridge share",
      min: 0,
      fieldIcon: IC.nonAgri,
      tooltip: "Volume of non-agri exports routed via GB Landbridge.",
    }),
    bindNumber("NA_Ex_DR", {
      label: "Non-Agri Export — Direct Route share",
      min: 0,
      fieldIcon: IC.nonAgri,
      tooltip: "Volume of non-agri exports via Direct EU routes.",
    }),
    bindNumber("A_Im_LB", {
      label: "Agri Import — Landbridge share",
      min: 0,
      fieldIcon: IC.agri,
      tooltip:
        "Volume of agri imports via GB Landbridge. Agri products on the Landbridge face additional UK border checks.",
    }),
    bindNumber("A_Im_DR", {
      label: "Agri Import — Direct Route share",
      min: 0,
      fieldIcon: IC.agri,
      tooltip: "Volume of agri imports via Direct EU routes (bypasses UK checks).",
    }),
    bindNumber("A_Ex_LB", {
      label: "Agri Export — Landbridge share",
      min: 0,
      fieldIcon: IC.agri,
      tooltip: "Volume of agri exports via Landbridge.",
    }),
    bindNumber("A_Ex_DR", {
      label: "Agri Export — Direct Route share",
      min: 0,
      fieldIcon: IC.agri,
      tooltip: "Volume of agri exports via Direct EU routes.",
    }),
    el("div", { class: "form-subheading" }, "Vessel capacities (trailers)"),
    bindNumber("VCap_Dub_Hey", {
      label: "Vessel Cap — Dublin → Heysham",
      required: true,
      min: 1,
      fieldIcon: IC.ship,
      tooltip: "Average number of trailer slots per sailing on the Dublin–Heysham route.",
    }),
    bindNumber("VCap_Dub_Holy", {
      label: "Vessel Cap — Dublin → Holyhead",
      required: true,
      min: 1,
      fieldIcon: IC.ship,
      tooltip: "Average trailer capacity on the Dublin–Holyhead ferry.",
    }),
    bindNumber("VCap_Dub_Liv", {
      label: "Vessel Cap — Dublin → Liverpool",
      required: true,
      min: 1,
      fieldIcon: IC.ship,
      tooltip: "Average trailer capacity on the Dublin–Liverpool route.",
    }),
    bindNumber("VCap_Ross_Fish", {
      label: "Vessel Cap — Rosslare → Fishguard",
      required: true,
      min: 1,
      fieldIcon: IC.ship,
      tooltip: "Average trailer capacity on the Rosslare–Fishguard route.",
    }),
    bindNumber("VCap_Ross_Pem", {
      label: "Vessel Cap — Rosslare → Pembroke",
      required: true,
      min: 1,
      fieldIcon: IC.ship,
      tooltip: "Average trailer capacity on the Rosslare–Pembroke route.",
    }),
  ];
  const g2 = createFactorGroup(
    false,
    "🚢 Direct Routes to Mainland Europe",
    "17 params",
    "Volume shifts between Landbridge and Direct routes, plus vessel capacities on each GB and EU route",
    g2body,
  );

  const g3 = createFactorGroup(
    false,
    "👮 Customs Expertise & Resources",
    "6 params",
    "Check durations and staffing levels at Dublin and Rosslare ports",
    [
      bindNumber("ChkTime_Doc", {
        label: "Documentary Check Duration",
        required: true,
        min: 0.1,
        fieldIcon: IC.docOfficer,
        tooltip:
          "Average time in minutes for documentary and seal identity checks per truck. Applies to customs and DAFM documentary checks at Irish ports.",
      }),
      bindNumber("ChkTime_Phy", {
        label: "Physical Check Duration",
        required: true,
        min: 0.1,
        fieldIcon: IC.inspectOfficer,
        tooltip:
          "Average time in minutes for a full physical inspection per truck. Applies to red-route and SPS-selected trucks.",
      }),
      bindNumber("NumCusShed_D", {
        label: "Revenue Sheds — Dublin",
        required: true,
        min: 1,
        fieldIcon: IC.customs,
        tooltip: "Number of Revenue (customs) check depots at Dublin port.",
      }),
      bindNumber("NumDAFM_D", {
        label: "SPS Check Depots — Dublin",
        required: true,
        min: 1,
        fieldIcon: IC.spsOfficer,
        tooltip: "Number of SPS (DAFM) inspection bays at Dublin port.",
      }),
      bindNumber("NumCusShed_R", {
        label: "Revenue Sheds — Rosslare",
        required: true,
        min: 1,
        fieldIcon: IC.customs,
        tooltip: "Number of Revenue check depots at Rosslare port.",
      }),
      bindNumber("NumDAFM_R", {
        label: "SPS Check Depots — Rosslare",
        required: true,
        min: 1,
        fieldIcon: IC.spsOfficer,
        tooltip: "Number of SPS inspection bays at Rosslare port.",
      }),
    ],
  );

  const pct = (apiKey, label, tooltip, fieldIcon = IC.border) =>
    bindNumber(apiKey, {
      label: `${label} (%)`,
      required: false,
      min: 0,
      max: 100,
      step: 1,
      isPercent: true,
      fieldIcon,
      tooltip,
    });

  const g4 = createFactorGroup(
    false,
    "🛂 Border Checks Intervention",
    "8 params",
    "Percentage of trucks in each routing category at Irish and UK ports",
    [
      pct(
        "Pct_NA_OB_Green",
        "Non-Agri Export → Green Route (UK)",
        "Percentage of non-agri export trucks directed to the green lane at UK ports.",
        IC.nonAgri,
      ),
      pct(
        "Pct_NA_OB_Red",
        "Non-Agri Export → Red Route (UK)",
        "Percentage of non-agri export trucks directed to the red lane at UK ports.",
        IC.nonAgri,
      ),
      pct(
        "Pct_A_OB_Red",
        "Agri Export → SPS Check (UK)",
        "Percentage of agri export trucks selected for full SPS physical inspection at UK ports.",
        IC.agri,
      ),
      pct(
        "Pct_NA_IB_Green",
        "Non-Agri Import → Green Route (IRE)",
        "Percentage of non-agri import trucks directed to the green lane at Irish ports.",
        IC.nonAgri,
      ),
      pct(
        "Pct_NA_IB_Red",
        "Non-Agri Import → Red Route (IRE)",
        "Percentage of non-agri import trucks directed to full physical checks at Irish ports.",
        IC.nonAgri,
      ),
      pct(
        "Pct_A_IB_Red",
        "Agri Import → SPS Check (IRE)",
        "Percentage of agri import trucks selected for SPS physical inspection at Irish ports.",
        IC.agri,
      ),
      pct(
        "Pct_IB_PreBoard",
        "Import Trucks — Pre-Boarding Check (UK)",
        "Percentage of inbound trucks stopped at UK ports for pre-boarding verification.",
        IC.border,
      ),
      pct(
        "Pct_OB_PreBoard",
        "Export Trucks — Pre-Boarding Check (IRE)",
        "Percentage of outbound trucks stopped at Irish ports for pre-boarding verification.",
        IC.border,
      ),
    ],
  );

  formBody.append(g1, g2, g3, g4);

  formFooter.innerHTML = "";
  const runRow = el("div", { class: "form-actions form-actions--run-reset" });
  const runBtn = el("button", {
    type: "button",
    class: "btn-run-simulation",
    id: "btn-run-predict",
    onclick: () => void runPrediction(),
  });
  runBtn.append(
    el("span", { class: "btn-run-simulation__icon" }, "🚢"),
    el("span", { class: "btn-run-simulation__text" }, "Run simulation"),
    el("span", { class: "btn-run-simulation__shine" }),
  );
  const resetBtn = el("button", {
    type: "button",
    class: "btn-reset-simulation",
    onclick: () => resetForm(),
  });
  resetBtn.append(el("span", { class: "btn-reset-simulation__ico" }, "↺"), " Reset to defaults");
  runRow.append(runBtn, resetBtn);
  runHintEl = el("div", { class: "hint-text", style: { minHeight: "16px" } });
  formFooter.append(runRow, runHintEl);

  refreshVolumeHints();
  updateRunButtonState();
}

function resetForm() {
  try {
    localStorage.removeItem(CONFIG_STORAGE_KEY);
  } catch {
    /* ignore */
  }
  Object.assign(state.config, NOLHC_MEDIANS);
  state.hasRun = false;
  state.lastResult = null;
  state.lastPredictions = null;
  state.lastShapFocusTarget = null;
  state.shapSelectedApiTarget = null;
  state.apiError = null;
  buildInputForm();
  state.activeView = "results";
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", tabViewFromEl(b) === "results");
  });
  const filterBarReset = document.getElementById("ind-filter-bar");
  if (filterBarReset) filterBarReset.style.display = "none";
  renderResults();
  const mapSection = document.getElementById("results-map-section");
  if (mapSection) mapSection.style.display = "none";
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
  }
}

async function fetchHealth() {
  const base = API_ML_BASE.replace(/\/$/, "");
  for (const path of ["/api/health", "/health"]) {
    try {
      const res = await fetch(`${base}${path}`);
      if (res.ok) return res.json();
    } catch {
      /* try next path */
    }
  }
  throw new Error("Health check failed");
}

async function runPrediction() {
  const runBtn = document.getElementById("btn-run-predict");
  if (runBtn) {
    runBtn.classList.add("btn-run-simulation--loading");
    runBtn.classList.remove("btn-run-simulation--ready");
  }
  state.loading = true;
  state.apiError = null;
  state.activeView = "results";
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", tabViewFromEl(b) === "results");
  });
  const filterBarRun = document.getElementById("ind-filter-bar");
  if (filterBarRun) filterBarRun.style.display = "none";
  renderResults();
  try {
    const base = API_ML_BASE.replace(/\/$/, "");
    const payload = buildPredictBody();
    const inferBody = {
      scenario_family: scenarioFamilyToInferApi(),
      scenario_level: scenarioLevelToInferApi(),
      inputs: {},
      model_features: payload,
      focus_target: "TT_OB_Agri",
      light: true,
      include_trend: false,
      include_target_corr: false,
      mc_samples: 128,
    };
    const stackRes = await fetch(`${base}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(inferBody),
    });
    const stackData = await stackRes.json().catch(() => ({}));
    if (stackRes.ok && stackData && stackData.ok !== false) {
      state.lastShapFocusTarget = String(inferBody.focus_target || "TT_OB_Agri");
      state.shapSelectedApiTarget = state.lastShapFocusTarget;
      state.lastPredictions =
        stackData.predictions && typeof stackData.predictions === "object" ? stackData.predictions : {};
      const rawSim =
        stackData.simulator && typeof stackData.simulator === "object"
          ? stackData.simulator
          : normalizeInferToSimulatorResult(stackData.predictions || {});
      state.lastResult = clipSimulatorResult(rawSim);
      state.reliability =
        stackData.reliability && typeof stackData.reliability === "object" ? stackData.reliability : null;
      state.hasRun = true;
      return;
    }
    throw new Error(stackData.error || stackData.detail || `HTTP ${stackRes.status}: /api/predict failed`);
  } catch (e) {
    state.apiError = { title: "Prediction failed", message: String(e.message || e) };
  } finally {
    state.loading = false;
    if (runBtn) runBtn.classList.remove("btn-run-simulation--loading");
    updateRunButtonState();
    renderResults();
  }
}

function confidenceBadgeEl() {
  const r2 = state.modelAvgR2;
  if (r2 == null || Number.isNaN(r2)) return null;
  let cls = "low";
  let label = "🔴 Low Confidence";
  if (r2 >= 0.9) {
    cls = "high";
    label = "🟢 High Confidence";
  } else if (r2 >= 0.75) {
    cls = "good";
    label = "🟡 Good Confidence";
  }
  return el("div", { class: `confidence-badge ${cls}` }, label, el("span", { style: { fontWeight: "400", opacity: 0.85 } }, ` (avg R² ${r2.toFixed(2)})`));
}

function formatKpiValue(slug, pr) {
  if (pr.value == null || pr.value === undefined) return "—";
  const meta = KPI_META[slug];
  const v = pr.value;
  if (typeof v !== "number" || !Number.isFinite(v)) return String(v);
  if (meta?.fraction || pr.unit === "fraction") {
    return `${(v * 100).toFixed(1)}`;
  }
  if ((pr.unit || "").toLowerCase().includes("hour")) return v.toFixed(1);
  return v.toFixed(2);
}

function kpiUnitDisplay(slug, pr) {
  const meta = KPI_META[slug];
  if (meta?.fraction || pr.unit === "fraction") return "%";
  if ((pr.unit || "").toLowerCase().includes("hour")) return "hrs";
  return pr.unit || "";
}

function themeForStaffUtil(v) {
  if (v == null || !Number.isFinite(v)) return "violet";
  const pct = v <= 1 ? v * 100 : v;
  if (pct > 80) return "rose";
  if (pct >= 60) return "amber";
  return "violet";
}

/** Per-KPI conformal interval + reliability chip for a card (technical report §13.3). */
function uncertaintyForCard(slug, pr) {
  const iv = pr && pr.interval;
  if (!iv || iv.lower == null || iv.upper == null) return null;
  const meta = KPI_META[slug];
  const frac = meta?.fraction || pr.unit === "fraction";
  const fmt = (x) => (frac ? `${(Number(x) * 100).toFixed(1)}%` : Number(x).toFixed(1));
  const cov = pr.coverage_level != null ? Math.round(Number(pr.coverage_level) * 100) : 90;
  const rel = state.reliability?.per_kpi?.[slug];
  return {
    intervalText: `${fmt(iv.lower)} – ${fmt(iv.upper)}`,
    coverageText: `${cov}% interval`,
    lowConfidence: Boolean(rel?.low_confidence),
  };
}

/** Trust strip shown above the KPI grid: overall accept/verify + novelty (technical report §13.3). */
function reliabilityStripEl() {
  const r = state.reliability;
  if (!r || r.available === false) return null;
  const verify = r.decision === "verify";
  const strip = el("div", { class: `reliability-strip ${verify ? "reliability-strip--verify" : "reliability-strip--ok"}` });
  strip.append(
    el("div", { class: "reliability-strip-head" },
      el("span", { class: "reliability-strip-icon" }, verify ? "⚠" : "✓"),
      el("span", { class: "reliability-strip-title" },
        verify ? "Verify this scenario against AnyLogic" : "Predictions within the calibrated operating range"),
    ),
  );
  if (r.reason) strip.append(el("div", { class: "reliability-strip-reason" }, r.reason));
  const nov = r.novelty || {};
  if (nov.available) {
    const novTxt = nov.is_novel
      ? "Input sits outside the training hull (novelty above the calibrated threshold)"
      : `Input inside the training hull (novelty ${Number(nov.score).toFixed(3)} vs threshold ${Number(nov.threshold).toFixed(3)})`;
    strip.append(el("div", { class: "reliability-strip-novelty" }, `🎯 ${novTxt}`));
  }
  return strip;
}

function renderResults() {
  const right = document.getElementById("right-content");
  if (!right) return;
  right.innerHTML = "";

  if (state.apiError) {
    right.append(
      el("div", { class: "api-error-banner" },
        el("div", { class: "api-error-title" }, state.apiError.title),
        el("div", { class: "api-error-message" }, state.apiError.message),
      ),
    );
  }

  if (state.loading) {
    right.append(
      el("div", { class: "api-loading" },
        el("div", { class: "api-loading-spinner" }),
        el("div", { class: "api-loading-text" }, "Running prediction…"),
        el("div", { class: "api-loading-sub" }, "Benchmarked ML models on NOLHC parameters."),
      ),
    );
    return;
  }

  const mapSection = document.getElementById("results-map-section");
  if (state.hasRun && mapSection) {
    mapSection.style.display = "";
    buildMapNolhc();
  } else if (mapSection) {
    mapSection.style.display = "none";
  }

  if (!state.hasRun || !state.lastResult) {
    right.append(
      EmptyState(
        "📊",
        "No results yet",
        "Configure parameters on the left and click Run simulation.",
        "Run simulation",
      ),
    );
    return;
  }

  const badge = confidenceBadgeEl();
  if (badge) right.append(badge);
  const relStrip = reliabilityStripEl();
  if (relStrip) right.append(relStrip);
  right.append(realismPanel());

  const journey = renderNolhcJourneyTimeline(state.lastResult);
  if (journey) right.append(journey);

  let delay = 0;
  for (const cat of CATEGORY_ORDER) {
    const catCfg = KPI_CATEGORIES[cat];
    const slugs = Object.keys(KPI_META).filter((s) => KPI_META[s].category === cat);
    if (!slugs.length) continue;
    const cards = [];
    for (const slug of slugs) {
      const pr = state.lastResult[slug];
      if (!pr || pr.value == null) continue;
      const meta = KPI_META[slug];
      let theme = meta.theme;
      if (meta.fraction) theme = themeForStaffUtil(pr.value);
      const warn = pr.status === "low_confidence" ? " ⚠" : "";
      const clippedWarn = pr.status === "clipped_to_domain" ? " (clipped)" : "";
      const subParts = [];
      if (pr.registered_as) subParts.push(`model: ${pr.registered_as}`);
      if (clippedWarn) subParts.push(clippedWarn);
      if (pr.r2 != null) subParts.push(`R² ${Number(pr.r2).toFixed(2)}`);
      cards.push(
        KpiCard({
          icon: meta.icon,
          label: meta.label,
          value: `${formatKpiValue(slug, pr)}${warn}`,
          unit: kpiUnitDisplay(slug, pr),
          sub: subParts.join(" · "),
          theme,
          delay: delay * 0.05,
          tooltip: meta.tooltip,
          uncertainty: uncertaintyForCard(slug, pr),
        }),
      );
      delay += 1;
    }
    if (!cards.length) continue;
    const grid = el("div", { class: "kpi-grid" });
    cards.forEach((c) => grid.append(c));
    right.append(SectionCard(catCfg.title, catCfg.border, grid));
  }

  appendShapAttributionPanel(right);

  if (state.hasRun && mapSection) {
    const legend = el("div", { class: "map-legend" },
      el("div", { class: "map-legend-item" },
        el("div", { class: "map-legend-dot", style: { background: "#1a1a2e" } }),
        el("span", {}, "GB Maritime"),
      ),
      el("div", { class: "map-legend-item" },
        el("div", { class: "map-legend-dash" }),
        el("span", {}, "Landbridge"),
      ),
      el("div", { class: "map-legend-item" },
        el("div", { class: "map-legend-dot", style: { background: "#1a3a5c" } }),
        el("span", {}, "Direct EU"),
      ),
    );
    right.append(legend);
  }
}

function buildMapNolhc() {
  const container = document.getElementById("results-map");
  if (!container) return;
  if (typeof L === "undefined") return;

  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
  }

  mapInstance = L.map(container, { zoomControl: true, scrollWheelZoom: false }).setView([52.5, -2.0], 5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap",
    opacity: 0.6,
  }).addTo(mapInstance);

  const activePorts = new Set();
  MAP_ROUTES.forEach((r) => {
    activePorts.add(r.from);
    activePorts.add(r.to);
    L.polyline([PORT_COORDS[r.from], PORT_COORDS[r.to]], {
      color: r.color,
      weight: 2,
      opacity: 0.85,
      dashArray: r.dash || undefined,
    }).addTo(mapInstance);
  });

  const sz = 8;
  Object.entries(PORT_COORDS).forEach(([name, pos]) => {
    const icon = L.divIcon({
      html: `<svg width="${sz + 4}" height="${sz + 4}" viewBox="0 0 ${sz + 4} ${sz + 4}">
        <circle cx="${(sz + 4) / 2}" cy="${(sz + 4) / 2}" r="${sz / 2}" fill="#cc2936" stroke="white" stroke-width="1.5"/>
      </svg>`,
      className: "",
      iconSize: [sz + 4, sz + 4],
      iconAnchor: [(sz + 4) / 2, (sz + 4) / 2],
    });
    L.marker(pos, { icon }).addTo(mapInstance).bindPopup(`<b>${name}</b>`);
    const lbl = L.divIcon({
      html: `<div style="font-size:10px;font-weight:600;color:#1a1a2e;white-space:nowrap;text-shadow:1px 1px 2px rgba(255,255,255,.9)">${name}</div>`,
      className: "",
      iconSize: [0, 0],
      iconAnchor: [-9, 7],
    });
    L.marker(pos, { icon: lbl, interactive: false }).addTo(mapInstance);
  });

  const allPos = Object.entries(PORT_COORDS)
    .filter(([n]) => activePorts.has(n))
    .map(([, p]) => p);
  if (allPos.length > 1) mapInstance.fitBounds(L.latLngBounds(allPos), { padding: [40, 40] });
}

function indDirectionFilter() {
  const sel = document.getElementById("ind-direction");
  return sel ? sel.value : "";
}

function indRouteFilter() {
  const sel = document.getElementById("ind-route");
  return sel ? sel.value : "";
}

function buildIndicatorFilters() {
  const bar = document.getElementById("ind-filter-bar");
  if (!bar) return;
  bar.innerHTML = "";
  bar.append(el("label", {}, "🔍 Filters"));
  const dirSel = el("select", { id: "ind-direction" });
  dirSel.append(
    el("option", { value: "" }, "All Flows"),
    el("option", { value: "agri" }, "Agri Products"),
    el("option", { value: "non_agri" }, "Non-Agri Products"),
  );
  dirSel.addEventListener("change", () => renderIndicators());
  bar.append(dirSel);

  const routeSel = el("select", { id: "ind-route" });
  routeSel.append(
    el("option", { value: "" }, "All Routes"),
    el("option", { value: "gb" }, "GB Maritime"),
    el("option", { value: "lb" }, "Landbridge"),
    el("option", { value: "direct" }, "Direct EU"),
  );
  routeSel.addEventListener("change", () => renderIndicators());
  bar.append(routeSel);

  const dateInp = el("input", {
    id: "ind-date",
    type: "date",
    value: new Date().toISOString().split("T")[0],
    max: new Date().toISOString().split("T")[0],
  });
  dateInp.addEventListener("change", () => renderIndicators());
  bar.append(dateInp);
}

function showSectionForFilters(sectionKind) {
  const d = indDirectionFilter();
  const r = indRouteFilter();
  if (sectionKind === "volume") {
    if (!d) return true;
    return true;
  }
  if (sectionKind === "port") return true;
  if (sectionKind === "border") {
    if (d === "agri" || d === "non_agri") return true;
    return !d;
  }
  if (sectionKind === "route_perf") {
    if (r === "gb" || r === "lb" || r === "direct") return true;
    return !r;
  }
  return true;
}

function renderIndicators() {
  const right = document.getElementById("right-content");
  if (!right) return;
  right.innerHTML = "";

  const c = state.config;
  const naIm = Number(c.NA_Im) || 0;
  const aImLb = Number(c.A_Im_LB) || 0;
  const naImLb = Number(c.NA_Im_LB) || 0;
  const lbShare =
    naIm > 0 ? (((naImLb + aImLb) / (naIm + (Number(c.A_Im) || 0))) * 100).toFixed(1) : "0";

  if (showSectionForFilters("volume")) {
    right.append(
      SectionCard(
        "1 — Trade Volume Overview",
        "teal",
        IndRow("Non-Agri Imports (GB→IRE)", naIm.toLocaleString(), `≈ ${Math.round(naIm / APP_CONFIG.tonnesPerTruck).toLocaleString()} trucks`),
        IndRow("Non-Agri Exports (IRE→GB)", Number(c.NA_Ex).toLocaleString(), `≈ ${Math.round(c.NA_Ex / APP_CONFIG.tonnesPerTruck).toLocaleString()} trucks`),
        IndRow("Agri-Food Imports (GB→IRE)", Number(c.A_Im).toLocaleString(), `≈ ${Math.round(c.A_Im / APP_CONFIG.tonnesPerTruck).toLocaleString()} trucks`),
        IndRow("Agri-Food Exports (IRE→GB)", Number(c.A_Ex).toLocaleString(), `≈ ${Math.round(c.A_Ex / APP_CONFIG.tonnesPerTruck).toLocaleString()} trucks`),
        UtilBar(Number(lbShare), "Landbridge share (imports, approx.)"),
      ),
    );
  }

  if (showSectionForFilters("port")) {
    const dublin = el("div", { class: "ind-section", style: { flex: 1 } },
      el("div", { class: "ind-section-title" }, "Dublin Port"),
      IndRow("Revenue Sheds", String(c.NumCusShed_D)),
      IndRow("SPS Depots", String(c.NumDAFM_D)),
    );
    const rossl = el("div", { class: "ind-section", style: { flex: 1 } },
      el("div", { class: "ind-section-title" }, "Rosslare Port"),
      IndRow("Revenue Sheds", String(c.NumCusShed_R)),
      IndRow("SPS Depots", String(c.NumDAFM_R)),
    );
    const row = el("div", { style: { display: "flex", gap: "12px" } }, dublin, rossl);
    const lr = state.lastResult;
    const extras = [];
    if (lr) {
      if (lr.uti_cus_d?.value != null) extras.push(UtilBar(lr.uti_cus_d.value * 100, "Dublin — Customs util"));
      if (lr.uti_dafm_d?.value != null) extras.push(UtilBar(lr.uti_dafm_d.value * 100, "Dublin — DAFM util"));
      if (lr.uti_cus_r?.value != null) extras.push(UtilBar(lr.uti_cus_r.value * 100, "Rosslare — Customs util"));
      if (lr.uti_dafm_r?.value != null) extras.push(UtilBar(lr.uti_dafm_r.value * 100, "Rosslare — DAFM util"));
    }
    right.append(SectionCard("2 — Port Resources & Capacity", "blue", row, ...extras));
  }

  if (showSectionForFilters("border")) {
    right.append(
      SectionCard(
        "3 — Border Check Intensity",
        "amber",
        IndRow("Agri Import → SPS (IRE)", `${(c.Pct_A_IB_Red * 100).toFixed(0)}%`),
        IndRow("Agri Export → SPS (UK)", `${(c.Pct_A_OB_Red * 100).toFixed(0)}%`),
        IndRow("Non-Agri Import → Red", `${(c.Pct_NA_IB_Red * 100).toFixed(0)}%`),
        IndRow("Non-Agri Export → Red", `${(c.Pct_NA_OB_Red * 100).toFixed(0)}%`),
        IndRow("Inbound Pre-Boarding", `${(c.Pct_IB_PreBoard * 100).toFixed(0)}%`),
        IndRow("Outbound Pre-Boarding", `${(c.Pct_OB_PreBoard * 100).toFixed(0)}%`),
        UtilBar(Math.min(100, (c.ChkTime_Doc / 60) * 100), `Documentary check: ${c.ChkTime_Doc} min/truck`),
        UtilBar(Math.min(100, (c.ChkTime_Phy / 120) * 100), `Physical check: ${c.ChkTime_Phy} min/truck`),
      ),
    );
  }

  const rf = indRouteFilter();
  if (showSectionForFilters("route_perf")) {
    if (!state.hasRun || !state.lastResult) {
      right.append(
        SectionCard(
          "4 — Route Performance",
          "",
          EmptyState("📊", "No results yet", "Run a prediction to see route performance summary."),
        ),
      );
    } else {
      const lr = state.lastResult;
      const blocks = [];
      if (!rf || rf === "gb") {
        blocks.push(
          el("div", { class: "ind-section" },
            el("div", { class: "ind-section-title" }, "GB Maritime"),
            IndRow("Agri TT outbound", formatKpiValue("tt_ob_agri", lr.tt_ob_agri), lr.tt_ob_agri?.unit),
            IndRow("Agri TT inbound", formatKpiValue("tt_ib_agri", lr.tt_ib_agri), lr.tt_ib_agri?.unit),
          ),
        );
      }
      if (!rf || rf === "lb") {
        blocks.push(
          el("div", { class: "ind-section" },
            el("div", { class: "ind-section-title" }, "Landbridge"),
            IndRow("TT outbound", formatKpiValue("tt_ob_lb", lr.tt_ob_lb)),
            IndRow("TT inbound", formatKpiValue("tt_ib_lb", lr.tt_ib_lb)),
          ),
        );
      }
      if (!rf || rf === "direct") {
        blocks.push(
          el("div", { class: "ind-section" },
            el("div", { class: "ind-section-title" }, "Direct EU"),
            IndRow("TT outbound", formatKpiValue("tt_ob_dr", lr.tt_ob_dr)),
            IndRow("TT inbound", formatKpiValue("tt_ib_dr", lr.tt_ib_dr)),
          ),
        );
      }
      right.append(SectionCard("4 — Route Performance", "", ...blocks));
    }
  }
}

function activeScenarioFamily() {
  return SCENARIO_FAMILIES.find((f) => f.id === scenarioUiState.familyId) || SCENARIO_FAMILIES[0];
}

function formatScenarioValue(v, unit) {
  if (!Number.isFinite(v)) return "—";
  if (unit === "ratio") return `${(v * 100).toFixed(0)}%`;
  if (Math.abs(v) >= 1000) return v.toLocaleString();
  if (Math.abs(v) < 10 && !Number.isInteger(v)) return v.toFixed(2);
  return String(Math.round(v * 100) / 100);
}

function scenarioSliderBounds(param) {
  const values = Object.values(param.values).filter((v) => Number.isFinite(v));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  if (minValue === maxValue) {
    const pad = Math.max(Math.abs(minValue) * 0.2, param.step || 1);
    return { min: minValue - pad, max: maxValue + pad };
  }
  const span = maxValue - minValue;
  return { min: minValue - span * 0.1, max: maxValue + span * 0.1 };
}

function defaultScenarioValues(family, levelId) {
  const next = {};
  family.parameters.forEach((p) => {
    const fallback = p.values.as_is;
    next[p.key] = Number.isFinite(p.values[levelId]) ? p.values[levelId] : fallback;
  });
  return next;
}

function scenarioImpactSummary(family) {
  let changed = 0;
  let sumPct = 0;
  let borderPressure = 0;
  family.parameters.forEach((p) => {
    const baseline = p.values.as_is;
    const current = scenarioUiState.values[p.key];
    if (!Number.isFinite(current) || !Number.isFinite(baseline)) return;
    if (current !== baseline) changed += 1;
    const denom = baseline === 0 ? 1 : Math.abs(baseline);
    sumPct += Math.abs((current - baseline) / denom) * 100;
    if (/ChkTime|PerFullIdnChk|PerPhyChk|PerSecurityChk/i.test(p.key)) {
      borderPressure += Math.abs(current - baseline);
    }
  });
  const avgDelta = family.parameters.length ? sumPct / family.parameters.length : 0;
  return {
    changed,
    avgDelta,
    borderPressure,
  };
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function applyScenarioValuesToConfig(family) {
  const next = { ...state.config };
  family.parameters.forEach((p) => {
    const apiKey = SCENARIO_TO_CONFIG_MAP[p.key];
    if (!apiKey || !(apiKey in next)) return;
    const raw = scenarioUiState.values[p.key];
    if (!Number.isFinite(raw)) return;

    let mapped = raw;
    if (apiKey.startsWith("Pct_")) {
      // Workbook percentages are often ratio-like (0-1), while config stores 0-1.
      mapped = raw > 1 ? raw / 100 : raw;
      mapped = clamp(mapped, 0, 1);
    }
    const meta = PARAMETER_META[apiKey];
    if (meta) mapped = clamp(mapped, meta.min, meta.max);
    next[apiKey] = mapped;
  });
  state.config = next;
  saveConfigToStorage(state.config);
  applyDirectRouteCorridorTonnes(family);
}

/** Right panel: scenario-first controls sourced from scenario_mapping.xlsx. */
function renderSettingsTab() {
  const right = document.getElementById("right-content");
  if (!right) return;
  right.innerHTML = "";

  const family = activeScenarioFamily();
  if (!scenarioUiState.values || Object.keys(scenarioUiState.values).length === 0) {
    scenarioUiState.values = defaultScenarioValues(family, scenarioUiState.levelId);
    applyScenarioValuesToConfig(family);
  }
  right.append(
    el("div", { class: "settings-tab-intro" },
      el(
        "p",
        { class: "settings-tab-lead" },
        "Scenario-based settings from the Excel mapping. Select a scenario family, choose a preset, then tune sliders. Impact cards update live as you edit.",
      ),
      el("a", { href: "settings.html", class: "settings-tab-full-link" }, "Open full parameter editor →"),
    ),
  );

  const familySelect = el("select", {
    class: "scenario-select",
    onchange: (e) => {
      scenarioUiState.familyId = e.target.value;
      const selected = activeScenarioFamily();
      scenarioUiState.values = defaultScenarioValues(selected, scenarioUiState.levelId);
      applyScenarioValuesToConfig(selected);
      if (state.hasRun) maybeAutoPredict();
      renderSettingsTab();
    },
  });
  SCENARIO_FAMILIES.forEach((f) => {
    familySelect.append(el("option", { value: f.id }, f.title));
  });
  familySelect.value = family.id;

  const levelRow = el("div", { class: "scenario-level-row" });
  family.levels.forEach((lvl) => {
    const btn = el(
      "button",
      {
        type: "button",
        class: `scenario-level-btn${scenarioUiState.levelId === lvl.id ? " active" : ""}`,
        onclick: () => {
          scenarioUiState.levelId = lvl.id;
          scenarioUiState.values = defaultScenarioValues(family, lvl.id);
          applyScenarioValuesToConfig(family);
          if (state.hasRun) maybeAutoPredict();
          renderSettingsTab();
        },
      },
      lvl.label,
    );
    levelRow.append(btn);
  });

  const settingsCfgChildren = [
    el("div", { class: "scenario-config-head" },
      el("label", { class: "scenario-select-label" }, "Scenario family"),
      familySelect,
    ),
    levelRow,
    el("p", { class: "scenario-family-desc" }, family.description),
  ];
  if (family.id === "direct_route") {
    settingsCfgChildren.push(
      el(
        "p",
        { class: "scenario-tonne-note" },
        "Route volumes (tonnes): As-Is = 100% landbridge / 0% direct; Scenario 1 = 60% / 40%; Scenario 2 = 15% / 85% of corridor totals.",
      ),
    );
  }
  right.append(el("div", { class: "scenario-config-block" }, ...settingsCfgChildren));

  const sliders = el("div", { class: "scenario-slider-list" });
  family.parameters.forEach((p) => {
    const current = Number.isFinite(scenarioUiState.values[p.key]) ? scenarioUiState.values[p.key] : p.values.as_is;
    const bounds = scenarioSliderBounds(p);
    const field = el("div", { class: "scenario-slider-item" });
    field.append(
      el("div", { class: "scenario-slider-head" },
        el("div", {},
          el("div", { class: "scenario-slider-label" }, p.label),
          el("div", { class: "scenario-slider-desc" }, p.description),
        ),
        el("div", { class: "scenario-slider-value" }, formatScenarioValue(current, p.unit)),
      ),
      el("input", {
        type: "range",
        min: String(bounds.min),
        max: String(bounds.max),
        step: String(p.step || 1),
        value: String(current),
        oninput: (e) => {
          scenarioUiState.values[p.key] = Number(e.target.value);
          applyScenarioValuesToConfig(family);
          if (state.hasRun) maybeAutoPredict();
          renderSettingsTab();
        },
      }),
      el(
        "div",
        { class: "scenario-slider-foot" },
        `Baseline: ${formatScenarioValue(p.values.as_is, p.unit)} | Scenario 1: ${formatScenarioValue(p.values.scenario_1, p.unit)} | Scenario 2: ${formatScenarioValue(p.values.scenario_2, p.unit)}`,
      ),
    );
    sliders.append(field);
  });

  right.append(SectionCard("Scenario input controls", "teal", sliders));
}

function tabViewFromEl(btn) {
  const v = btn?.getAttribute?.("data-view");
  return v != null && String(v).trim() !== "" ? String(v).trim() : null;
}

function setActiveTab(view) {
  const v = typeof view === "string" ? view.trim() : "";
  if (v !== "results" && v !== "indicators") return;

  state.activeView = v;
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", tabViewFromEl(b) === v);
  });
  const filterBar = document.getElementById("ind-filter-bar");
  const mapSection = document.getElementById("results-map-section");
  if (v === "results") {
    if (filterBar) filterBar.style.display = "none";
    if (mapSection && state.hasRun) mapSection.style.display = "";
    renderResults();
  } else {
    if (filterBar) filterBar.style.display = "";
    if (mapSection) mapSection.style.display = "none";
    renderIndicators();
  }
}

const CHAT_NOLHC = {
  agri: "Agri-food products face **SPS (sanitary/phytosanitary)** checks. **DAFM** bays at Dublin and Rosslare handle inspections; high **DAFM utilisation** drives inbound wait times.",
  food: "Agri-food products face **SPS (sanitary/phytosanitary)** checks. **DAFM** bays at Dublin and Rosslare handle inspections; high **DAFM utilisation** drives inbound wait times.",
  sps: "**SPS checks** apply to agri-food. They take longer than standard customs checks and use **DAFM inspection bays**.",
  landbridge: "The **Landbridge** runs Ireland → GB → EU (e.g. via Dover/Calais). **UK border checks** add time compared with direct EU sailings.",
  gb: "The **Landbridge** runs Ireland → GB → EU (e.g. via Dover/Calais). **UK border checks** add time compared with direct EU sailings.",
  dover: "The **Landbridge** runs Ireland → GB → EU (e.g. via Dover/Calais). **UK border checks** add time compared with direct EU sailings.",
  direct: "**Direct EU routes** (Cherbourg, Rotterdam, Zeebrugge) **bypass the UK**. Longer sailings but no UK border friction.",
  cherbourg: "**Direct EU routes** (Cherbourg, Rotterdam, Zeebrugge) **bypass the UK**. Longer sailings but no UK border friction.",
  rotterdam: "**Direct EU routes** (Cherbourg, Rotterdam, Zeebrugge) **bypass the UK**. Longer sailings but no UK border friction.",
  zeebrugge: "**Direct EU routes** (Cherbourg, Rotterdam, Zeebrugge) **bypass the UK**. Longer sailings but no UK border friction.",
  wait: "**Waiting times** depend on check percentages, **capacities**, and **staff utilisation**. Use the KPI cards after running a prediction.",
  queue: "**Waiting times** depend on check percentages, **capacities**, and **staff utilisation**. Use the KPI cards after running a prediction.",
  delay: "**Waiting times** depend on check percentages, **capacities**, and **staff utilisation**. Use the KPI cards after running a prediction.",
  customs: "**Revenue (customs) sheds** process non-agri checks. More sheds reduce customs queues at Dublin and Rosslare.",
  revenue: "**Revenue (customs) sheds** process non-agri checks. More sheds reduce customs queues at Dublin and Rosslare.",
  shed: "**Revenue (customs) sheds** process non-agri checks. More sheds reduce customs queues at Dublin and Rosslare.",
  dafm: "**DAFM** runs **SPS** inspections on agri-food. **DAFM utilisation** above **80%** is a critical bottleneck.",
  inspection: "**DAFM** runs **SPS** inspections on agri-food. **DAFM utilisation** above **80%** is a critical bottleneck.",
  bay: "**DAFM** runs **SPS** inspections on agri-food. **DAFM utilisation** above **80%** is a critical bottleneck.",
  utilisation: "**Utilisation** KPIs show how busy customs and DAFM resources are (as a fraction of capacity).",
  capacity: "**Vessel capacities** (trailer slots per sailing) affect queuing and transport times when demand is high.",
  staff: "**Utilisation** KPIs show how busy customs and DAFM resources are (as a fraction of capacity).",
  vessel: "**Vessel capacities** (trailer slots per sailing) affect queuing and transport times when demand is high.",
  ferry: "**Vessel capacities** (trailer slots per sailing) affect queuing and transport times when demand is high.",
  preboard: "**Pre-boarding checks** stop a share of trucks before boarding — set via the Border Checks parameters.",
  green: "**Green vs red** routes control what share of trucks get full inspections — higher red shares increase waits.",
  red: "**Green vs red** routes control what share of trucks get full inspections — higher red shares increase waits.",
  route: "**Green vs red** routes control what share of trucks get full inspections — higher red shares increase waits.",
};

let chatOpen = false;

function addBotMessage(container, text) {
  const wrap = el("div", { class: "chat-msg" });
  const ico = el("div", { class: "chat-bot-icon" }, "🤖");
  const bbl = el("div", { class: "chat-bubble bot" });
  bbl.innerHTML = text
    .split("\n")
    .map((l) => `<p>${l.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\*(.*?)\*/g, "<em>$1</em>")}</p>`)
    .join("");
  wrap.append(ico, bbl);
  container.append(wrap);
  container.scrollTop = container.scrollHeight;
}

function sendChat(messages, inp) {
  const text = inp.value.trim();
  if (!text) return;
  inp.value = "";
  const userWrap = el("div", { class: "chat-msg user" });
  userWrap.append(el("div", { class: "chat-bubble user" }, text));
  messages.append(userWrap);
  const typingWrap = el("div", { class: "chat-msg" });
  typingWrap.append(
    el("div", { class: "chat-bot-icon" }, "🤖"),
    el("div", { class: "chat-bubble bot" }, el("div", { class: "typing-dots" }, el("span"), el("span"), el("span"))),
  );
  messages.append(typingWrap);
  messages.scrollTop = messages.scrollHeight;
  setTimeout(() => {
    messages.removeChild(typingWrap);
    const lower = text.toLowerCase();
    const key = Object.keys(CHAT_NOLHC).find((k) => lower.includes(k));
    const reply = key
      ? CHAT_NOLHC[key]
      : "I can explain **NOLHC parameters** (trade volumes, routes, customs, border checks) and **KPIs** after you run a prediction. Try: **landbridge**, **direct route**, **DAFM**, or **utilisation**.";
    addBotMessage(messages, reply);
  }, 500);
}

function toggleChat() {
  chatOpen = !chatOpen;
  const p = document.getElementById("chat-panel");
  if (p) p.style.display = chatOpen ? "flex" : "none";
}

function buildChatbot() {
  let panel = document.getElementById("chat-panel");
  if (!panel) {
    panel = el("div", { class: "chat-panel", id: "chat-panel", style: { display: "none" } });
    document.getElementById("app")?.append(panel);
  }
  panel.innerHTML = "";
  panel.className = "chat-panel";
  panel.style.display = "none";
  chatOpen = false;

  const header = el("div", { class: "chat-header" });
  header.append(
    el("div", { class: "chat-avatar" }, "🤖"),
    el("div", {},
      el("div", { class: "chat-header-name" }, "NOLHC Assistant"),
      el("div", { class: "chat-header-sub" }, "Ask about NOLHC simulation parameters & results"),
    ),
  );
  const messages = el("div", { class: "chat-messages", id: "chat-messages" });
  addBotMessage(
    messages,
    "Hello! I can explain the **simulation parameters** and **predicted KPIs** for the NOLHC Ireland trade model. Ask me anything.",
  );
  const inp = el("input", { type: "text", placeholder: "Ask about NOLHC…", id: "chat-input" });
  inp.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendChat(messages, inp);
  });
  const inputRow = el("div", { class: "chat-input-row" },
    inp,
    el("button", { class: "chat-send", id: "chat-send", onclick: () => sendChat(messages, inp) }, "➤"),
  );
  panel.append(header, messages, inputRow);

  let toggle = document.querySelector(".chat-toggle");
  if (!toggle) {
    toggle = el("button", { class: "chat-toggle", onclick: toggleChat }, "💬");
    document.body.append(toggle);
  } else {
    toggle.onclick = toggleChat;
  }
}

function showAppBootError(err) {
  const msg = err && err.message ? err.message : String(err);
  const stack = err && err.stack ? err.stack : "";
  console.error("NOLHC UI boot error:", err);
  const box = el("div", {
    class: "app-boot-error",
    style: {
      margin: "16px",
      padding: "16px 20px",
      borderRadius: "10px",
      border: "1px solid rgba(248, 113, 113, 0.5)",
      background: "rgba(127, 29, 29, 0.35)",
      color: "#fecaca",
      font: "14px/1.5 system-ui, sans-serif",
      maxWidth: "720px",
    },
  });
  box.append(
    el("strong", { style: { display: "block", marginBottom: "8px" } }, "Could not start the NOLHC UI"),
    el("div", {}, msg),
  );
  if (stack) {
    box.append(
      el(
        "pre",
        {
          style: {
            marginTop: "12px",
            padding: "10px",
            overflow: "auto",
            fontSize: "11px",
            background: "rgba(0,0,0,0.35)",
            borderRadius: "6px",
            color: "#e2e8f0",
          },
        },
        stack,
      ),
    );
  }
  const right = document.getElementById("right-content");
  if (right) {
    right.innerHTML = "";
    right.append(box);
  } else {
    document.body.prepend(box);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  try {
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const t = e.currentTarget;
        const view = tabViewFromEl(t);
        if (view) setActiveTab(view);
      });
    });

    const saved = loadSavedConfig();
    if (saved) {
      for (const k of Object.keys(NOLHC_MEDIANS)) {
        if (typeof saved[k] === "number" && Number.isFinite(saved[k])) {
          state.config[k] = saved[k];
        }
      }
    }

    void (async () => {
      try {
        try {
          const h = await fetchHealth();
          state.modelAvgR2 = typeof h.avg_r2 === "number" ? h.avg_r2 : null;
          state.modelVersion = h.model_version || "v1";
        } catch {
          state.modelAvgR2 = null;
        }
        buildInputForm();
        buildIndicatorFilters();
        buildChatbot();
        renderResults();
      } catch (e) {
        showAppBootError(e);
      }
    })();
  } catch (e) {
    showAppBootError(e);
  }
});
