/**
 * Single source of truth: allowed ranges, ports, and long descriptions for modals.
 * Keys match API / TRAINING_COLUMN_ORDER (31 parameters).
 */

/** @typedef {{ min: number; max: number; step?: number; unit: string; ports: string[] | null; group: 1|2|3|4; detail: string }} ParameterMetaEntry */

/** Display order (matches simulation form). */
export const PARAMETER_ORDER = [
  "NA_Im",
  "NA_Ex",
  "A_Im",
  "A_Ex",
  "NA_Im_LB",
  "NA_Im_DR",
  "NA_Ex_LB",
  "NA_Ex_DR",
  "A_Im_LB",
  "A_Im_DR",
  "A_Ex_LB",
  "A_Ex_DR",
  "VCap_Dub_Hey",
  "VCap_Dub_Holy",
  "VCap_Dub_Liv",
  "VCap_Ross_Fish",
  "VCap_Ross_Pem",
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
];

const T_MIN = 1;
const T_MAX = 15_000_000;
const SUB_VOL_MAX = 10_000_000;
const VC_MIN = 1;
const VC_MAX = 500;
const CHK_MIN = 0.1;
const CHK_MAX = 600;
const SHED_MIN = 1;
const SHED_MAX = 200;

/** @type {Record<string, ParameterMetaEntry>} */
export const PARAMETER_META = {
  NA_Im: {
    group: 1,
    min: T_MIN,
    max: T_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Dublin", "Rosslare", "GB maritime corridors"],
    detail:
      "Non-agri import volume from GB to Ireland (tonnes per year). Higher demand increases pressure on Irish port customs and inspection resources. Typical observed band in training data is roughly 4.7M–7.6M tonnes.",
  },
  NA_Ex: {
    group: 1,
    min: T_MIN,
    max: T_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Dublin", "Rosslare", "UK-side queues"],
    detail:
      "Non-agri export volume from Ireland to GB (tonnes). Affects outbound waiting times at UK-side ports.",
  },
  A_Im: {
    group: 1,
    min: T_MIN,
    max: T_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Dublin", "Rosslare", "DAFM bays"],
    detail:
      "Agri-food import volume from GB to Ireland. Agri flows use SPS checks — higher volumes increase DAFM bay utilisation and inbound delays.",
  },
  A_Ex: {
    group: 1,
    min: T_MIN,
    max: T_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Dublin", "Rosslare"],
    detail:
      "Agri-food export volume from Ireland to GB. Drives outbound SPS queues at Irish ports.",
  },
  NA_Im_LB: {
    group: 2,
    min: 0,
    max: SUB_VOL_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Dover", "Calais", "Landbridge"],
    detail:
      "Volume of non-agri imports routed via the GB Landbridge (e.g. through Dover/Calais). Reducing Landbridge share shifts freight toward direct EU sailings.",
  },
  NA_Im_DR: {
    group: 2,
    min: 0,
    max: SUB_VOL_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Cherbourg", "Rotterdam", "Zeebrugge"],
    detail:
      "Volume of non-agri imports arriving on direct EU routes (bypasses UK land border).",
  },
  NA_Ex_LB: {
    group: 2,
    min: 0,
    max: SUB_VOL_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Landbridge"],
    detail: "Non-agri exports routed via the GB Landbridge.",
  },
  NA_Ex_DR: {
    group: 2,
    min: 0,
    max: SUB_VOL_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Direct EU"],
    detail: "Non-agri exports using direct EU sailings from Ireland.",
  },
  A_Im_LB: {
    group: 2,
    min: 0,
    max: SUB_VOL_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Landbridge", "UK border"],
    detail:
      "Agri imports via Landbridge face additional UK border checks compared with direct EU routes.",
  },
  A_Im_DR: {
    group: 2,
    min: 0,
    max: SUB_VOL_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Cherbourg", "Rotterdam", "Zeebrugge"],
    detail: "Agri imports on direct EU routes — avoids UK checks on that leg.",
  },
  A_Ex_LB: {
    group: 2,
    min: 0,
    max: SUB_VOL_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Landbridge"],
    detail: "Agri exports via the Landbridge corridor.",
  },
  A_Ex_DR: {
    group: 2,
    min: 0,
    max: SUB_VOL_MAX,
    step: 1,
    unit: "tonnes",
    ports: ["Direct EU"],
    detail: "Agri exports via direct EU routes.",
  },
  VCap_Dub_Hey: {
    group: 2,
    min: VC_MIN,
    max: VC_MAX,
    step: 1,
    unit: "trailers",
    ports: ["Dublin", "Heysham"],
    detail:
      "Average trailer slots per sailing on Dublin–Heysham. Lower capacity increases queuing when demand is high.",
  },
  VCap_Dub_Holy: {
    group: 2,
    min: VC_MIN,
    max: VC_MAX,
    step: 1,
    unit: "trailers",
    ports: ["Dublin", "Holyhead"],
    detail: "Average trailer capacity on the Dublin–Holyhead ferry (typically high volume).",
  },
  VCap_Dub_Liv: {
    group: 2,
    min: VC_MIN,
    max: VC_MAX,
    step: 1,
    unit: "trailers",
    ports: ["Dublin", "Liverpool"],
    detail: "Average trailer capacity on Dublin–Liverpool.",
  },
  VCap_Ross_Fish: {
    group: 2,
    min: VC_MIN,
    max: VC_MAX,
    step: 1,
    unit: "trailers",
    ports: ["Rosslare", "Fishguard"],
    detail: "Average trailer capacity on Rosslare–Fishguard.",
  },
  VCap_Ross_Pem: {
    group: 2,
    min: VC_MIN,
    max: VC_MAX,
    step: 1,
    unit: "trailers",
    ports: ["Rosslare", "Pembroke"],
    detail: "Average trailer capacity on Rosslare–Pembroke.",
  },
  ChkTime_Doc: {
    group: 3,
    min: CHK_MIN,
    max: CHK_MAX,
    step: 0.01,
    unit: "minutes",
    ports: ["Dublin", "Rosslare"],
    detail:
      "Average minutes per truck for documentary and seal-identity checks (customs and DAFM documentation).",
  },
  ChkTime_Phy: {
    group: 3,
    min: CHK_MIN,
    max: CHK_MAX,
    step: 0.01,
    unit: "minutes",
    ports: ["Dublin", "Rosslare"],
    detail:
      "Average minutes for a full physical inspection (red-route / SPS-selected trucks).",
  },
  NumCusShed_D: {
    group: 3,
    min: SHED_MIN,
    max: SHED_MAX,
    step: 1,
    unit: "count",
    ports: ["Dublin"],
    detail: "Number of Revenue (customs) check depots at Dublin port.",
  },
  NumDAFM_D: {
    group: 3,
    min: SHED_MIN,
    max: SHED_MAX,
    step: 1,
    unit: "count",
    ports: ["Dublin"],
    detail: "Number of SPS (DAFM) inspection bays at Dublin.",
  },
  NumCusShed_R: {
    group: 3,
    min: SHED_MIN,
    max: SHED_MAX,
    step: 1,
    unit: "count",
    ports: ["Rosslare"],
    detail: "Number of Revenue check depots at Rosslare.",
  },
  NumDAFM_R: {
    group: 3,
    min: SHED_MIN,
    max: SHED_MAX,
    step: 1,
    unit: "count",
    ports: ["Rosslare"],
    detail: "Number of SPS inspection bays at Rosslare.",
  },
  Pct_NA_OB_Green: {
    group: 4,
    min: 0,
    max: 1,
    step: 0.01,
    unit: "fraction (0–1)",
    ports: ["UK outbound ports"],
    detail:
      "Share of non-agri export trucks on the green (low-friction) lane at UK ports. Stored internally as a fraction (0–1); the form shows 0–100%.",
  },
  Pct_NA_OB_Red: {
    group: 4,
    min: 0,
    max: 1,
    step: 0.01,
    unit: "fraction (0–1)",
    ports: ["UK outbound ports"],
    detail: "Share of non-agri export trucks directed to full physical checks at UK ports.",
  },
  Pct_A_OB_Red: {
    group: 4,
    min: 0,
    max: 1,
    step: 0.01,
    unit: "fraction (0–1)",
    ports: ["UK outbound ports"],
    detail: "Share of agri export trucks selected for SPS inspection at UK ports.",
  },
  Pct_NA_IB_Green: {
    group: 4,
    min: 0,
    max: 1,
    step: 0.01,
    unit: "fraction (0–1)",
    ports: ["Dublin", "Rosslare"],
    detail: "Share of non-agri import trucks on the green lane at Irish ports.",
  },
  Pct_NA_IB_Red: {
    group: 4,
    min: 0,
    max: 1,
    step: 0.01,
    unit: "fraction (0–1)",
    ports: ["Dublin", "Rosslare"],
    detail: "Share of non-agri import trucks sent to red-route physical checks in Ireland.",
  },
  Pct_A_IB_Red: {
    group: 4,
    min: 0,
    max: 1,
    step: 0.01,
    unit: "fraction (0–1)",
    ports: ["Dublin", "Rosslare"],
    detail: "Share of agri import trucks selected for SPS inspection in Ireland.",
  },
  Pct_IB_PreBoard: {
    group: 4,
    min: 0,
    max: 1,
    step: 0.01,
    unit: "fraction (0–1)",
    ports: ["UK pre-boarding"],
    detail: "Share of inbound trucks stopped for pre-boarding verification before departure from UK ports.",
  },
  Pct_OB_PreBoard: {
    group: 4,
    min: 0,
    max: 1,
    step: 0.01,
    unit: "fraction (0–1)",
    ports: ["Dublin", "Rosslare"],
    detail: "Share of outbound trucks stopped for pre-boarding checks at Irish ports.",
  },
};

/**
 * Human-readable range for labels and settings table.
 * @param {string} apiKey
 * @param {boolean} [isPercent]
 */
export function formatRangeLabel(apiKey, isPercent = false) {
  const m = PARAMETER_META[apiKey];
  if (!m) return "";
  if (isPercent) {
    return `Allowed: ${(m.min * 100).toFixed(0)}% – ${(m.max * 100).toFixed(0)}%`;
  }
  const { min, max, unit } = m;
  const a = Number.isInteger(min) ? min : min;
  const b = Number.isInteger(max) ? max : max;
  return `Allowed: ${a.toLocaleString()} – ${b.toLocaleString()} ${unit}`;
}

export const CONFIG_STORAGE_KEY = "nolhc_ui_config_v1";

/** @returns {Record<string, number> | null} */
export function loadSavedConfig() {
  try {
    const raw = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!raw) return null;
    const o = JSON.parse(raw);
    if (o && typeof o === "object") return o;
    return null;
  } catch {
    return null;
  }
}

/** @param {Record<string, number>} config */
export function saveConfigToStorage(config) {
  localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
}

/** Display labels aligned with main simulator form (percent params omit “ (%)” here). */
export const PARAMETER_LABELS = {
  NA_Im: "Non-Agri Import Volume",
  NA_Ex: "Non-Agri Export Volume",
  A_Im: "Agri Import Volume",
  A_Ex: "Agri Export Volume",
  NA_Im_LB: "Non-Agri Import — Landbridge share",
  NA_Im_DR: "Non-Agri Import — Direct Route share",
  NA_Ex_LB: "Non-Agri Export — Landbridge share",
  NA_Ex_DR: "Non-Agri Export — Direct Route share",
  A_Im_LB: "Agri Import — Landbridge share",
  A_Im_DR: "Agri Import — Direct Route share",
  A_Ex_LB: "Agri Export — Landbridge share",
  A_Ex_DR: "Agri Export — Direct Route share",
  VCap_Dub_Hey: "Vessel Cap — Dublin → Heysham",
  VCap_Dub_Holy: "Vessel Cap — Dublin → Holyhead",
  VCap_Dub_Liv: "Vessel Cap — Dublin → Liverpool",
  VCap_Ross_Fish: "Vessel Cap — Rosslare → Fishguard",
  VCap_Ross_Pem: "Vessel Cap — Rosslare → Pembroke",
  ChkTime_Doc: "Documentary Check Duration",
  ChkTime_Phy: "Physical Check Duration",
  NumCusShed_D: "Revenue Sheds — Dublin",
  NumDAFM_D: "SPS Check Depots — Dublin",
  NumCusShed_R: "Revenue Sheds — Rosslare",
  NumDAFM_R: "SPS Check Depots — Rosslare",
  Pct_NA_OB_Green: "Non-Agri Export → Green Route (UK)",
  Pct_NA_OB_Red: "Non-Agri Export → Red Route (UK)",
  Pct_A_OB_Red: "Agri Export → SPS Check (UK)",
  Pct_NA_IB_Green: "Non-Agri Import → Green Route (IRE)",
  Pct_NA_IB_Red: "Non-Agri Import → Red Route (IRE)",
  Pct_A_IB_Red: "Agri Import → SPS Check (IRE)",
  Pct_IB_PreBoard: "Import Trucks — Pre-Boarding Check (UK)",
  Pct_OB_PreBoard: "Export Trucks — Pre-Boarding Check (IRE)",
};

export const SETTINGS_GROUPS = [
  {
    id: 1,
    title: "📦 Shifts in Trade Volume",
    badge: "4 params",
    headerDetail:
      "Import and export volumes of Agri and Non-Agri products between GB and Ireland",
  },
  {
    id: 2,
    title: "🚢 Direct Routes to Mainland Europe",
    badge: "17 params",
    headerDetail:
      "Volume shifts between Landbridge and Direct routes, plus vessel capacities on each GB and EU route",
  },
  {
    id: 3,
    title: "👮 Customs Expertise & Resources",
    badge: "6 params",
    headerDetail: "Check durations and staffing levels at Dublin and Rosslare ports",
  },
  {
    id: 4,
    title: "🛂 Border Checks Intervention",
    badge: "8 params",
    headerDetail: "Percentage of trucks in each routing category at Irish and UK ports",
  },
];
