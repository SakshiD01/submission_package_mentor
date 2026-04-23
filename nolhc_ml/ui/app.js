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
} from "./data/data.js";

import {
  el,
  TooltipIcon,
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
  apiError: null,
  activeView: "results",
  modelAvgR2: null,
  modelVersion: "v1",
};

let mapInstance = null;
let debouncedPredictTimer = null;
let runHintEl = null;

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

let formFieldStagger = 0;

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
    el("span", {}, "Mean transport-time KPIs (sample)"),
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
    min = 0,
    max,
    step,
    tooltip,
    usePlainText = false,
    isPercent = false,
    fieldIcon = null,
  } = opts;
  const displayValue = isPercent ? Math.round(state.config[apiKey] * 10000) / 100 : state.config[apiKey];
  const staggerMs = (formFieldStagger++) * 38;
  const { wrap, inp } = NumberField({
    id,
    label,
    required,
    value: displayValue,
    min,
    max,
    step,
    tooltip,
    usePlainText,
    fieldIcon,
    staggerMs,
    onChange: (v) => {
      state.config[apiKey] = isPercent ? v / 100 : v;
      if (["NA_Im", "NA_Ex", "A_Im", "A_Ex"].includes(apiKey)) refreshVolumeHints();
      updateRunButtonState();
      maybeAutoPredict();
    },
  });
  return wrap;
}

function factorGroupHeaderRow(title, badge, headerTooltip) {
  const left = el("div", { class: "factor-group-title-row" },
    el("span", { class: "factor-group-chevron" }, "▼"),
    el("span", {}, title),
  );
  if (headerTooltip) left.append(TooltipIcon(headerTooltip));
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
  Object.assign(state.config, NOLHC_MEDIANS);
  state.hasRun = false;
  state.lastResult = null;
  state.apiError = null;
  buildInputForm();
  renderResults();
  const mapSection = document.getElementById("results-map-section");
  if (mapSection) mapSection.style.display = "none";
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
  }
}

async function fetchHealth() {
  const url = `${API_ML_BASE.replace(/\/$/, "")}/health`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Health ${res.status}`);
  return res.json();
}

async function runPrediction() {
  const runBtn = document.getElementById("btn-run-predict");
  if (runBtn) {
    runBtn.classList.add("btn-run-simulation--loading");
    runBtn.classList.remove("btn-run-simulation--ready");
  }
  state.loading = true;
  state.apiError = null;
  renderResults();
  try {
    const url = `${API_ML_BASE.replace(/\/$/, "")}/predict`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPredictBody()),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.error || res.statusText || String(res.status));
    }
    state.lastResult = data;
    state.hasRun = true;
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
      const subParts = [];
      if (pr.registered_as) subParts.push(`model: ${pr.registered_as}`);
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
        }),
      );
      delay += 1;
    }
    if (!cards.length) continue;
    const grid = el("div", { class: "kpi-grid" });
    cards.forEach((c) => grid.append(c));
    right.append(SectionCard(catCfg.title, catCfg.border, grid));
  }

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

function setActiveTab(view) {
  state.activeView = view;
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === view);
  });
  const filterBar = document.getElementById("ind-filter-bar");
  const mapSection = document.getElementById("results-map-section");
  if (view === "results") {
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

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => setActiveTab(btn.dataset.view));
  });

  void (async () => {
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
  })();
});
