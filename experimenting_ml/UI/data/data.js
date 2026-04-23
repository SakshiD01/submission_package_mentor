/**
 * NOLHC ML UI — static data (NOLHC_ML_UI_Spec.md §10).
 * Map + app config inherited from Brexit data shape; KPI + medians are NOLHC-specific.
 */

export const GOODS_ICONS = {};

export const PORT_COORDS = {
  Dublin: [53.3478, -6.2297],
  Rosslare: [52.2537, -6.3389],
  Heysham: [54.0333, -2.9167],
  Liverpool: [53.4084, -2.9916],
  Holyhead: [53.3094, -4.6331],
  Fishguard: [52.0092, -4.9906],
  Pembroke: [51.6833, -4.95],
  Dover: [51.1279, 1.3134],
  Calais: [50.9513, 1.8587],
  Cherbourg: [49.6333, -1.6167],
  Rotterdam: [51.9225, 4.4792],
  Zeebrugge: [51.3333, 3.1833],
};

/** Ferry / corridor polylines — same geometry as Brexit; NOLHC map shows all routes always. */
export const MAP_ROUTES = [
  { from: "Dublin", to: "Heysham", corridor: "East/West Maritime Corridor", color: "#1a1a2e", dash: null },
  { from: "Dublin", to: "Liverpool", corridor: "East/West Maritime Corridor", color: "#1a1a2e", dash: null },
  { from: "Dublin", to: "Holyhead", corridor: "East/West Maritime Corridor", color: "#1a1a2e", dash: null },
  { from: "Rosslare", to: "Fishguard", corridor: "East/West Maritime Corridor", color: "#1a1a2e", dash: null },
  { from: "Rosslare", to: "Pembroke", corridor: "East/West Maritime Corridor", color: "#1a1a2e", dash: null },
  { from: "Dublin", to: "Liverpool", corridor: "Land-bridge Route", color: "#1a1a2e", dash: "6 4" },
  { from: "Dover", to: "Calais", corridor: "Land-bridge Route", color: "#1a1a2e", dash: "6 4" },
  { from: "Dublin", to: "Cherbourg", corridor: "Direct Route", color: "#1a3a5c", dash: null },
  { from: "Rosslare", to: "Cherbourg", corridor: "Direct Route", color: "#1a3a5c", dash: null },
  { from: "Dublin", to: "Rotterdam", corridor: "Direct Route", color: "#1a3a5c", dash: null },
  { from: "Dublin", to: "Zeebrugge", corridor: "Direct Route", color: "#1a3a5c", dash: null },
];

export const APP_CONFIG = {
  tonnesPerTruck: 25,
};

/** One entry per API output slug (20 targets incl. Uti_DAFM_R). */
export const KPI_META = {
  tt_ob_agri: {
    label: "Agri Export Transport Time — Outbound (IRE→GB)",
    unit: "hrs",
    category: "agri",
    icon: "⏱",
    theme: "teal",
    tooltip:
      "Average total transport time for agri-food products travelling outbound from Ireland to GB. Includes port waiting and ferry crossing time.",
  },
  wt_ob_a_gb_dub: {
    label: "Agri Export Waiting Time — Outbound, Dublin (GB-side)",
    unit: "hrs",
    category: "agri",
    icon: "🕐",
    theme: "amber",
    tooltip:
      "Average waiting time for agri export trucks at the GB-side of Dublin departures — time spent queuing for customs and SPS checks before boarding.",
  },
  wt_ob_a_gb_ross: {
    label: "Agri Export Waiting Time — Outbound, Rosslare (GB-side)",
    unit: "hrs",
    category: "agri",
    icon: "🕐",
    theme: "amber",
    tooltip: "Average waiting time for agri export trucks at the GB-side of Rosslare departures.",
  },
  tt_ib_agri: {
    label: "Agri Import Transport Time — Inbound (GB→IRE)",
    unit: "hrs",
    category: "agri",
    icon: "⏱",
    theme: "teal",
    tooltip:
      "Average total transport time for agri-food products arriving inbound into Ireland from GB. Higher border check rates increase this significantly.",
  },
  wt_ib_a_dub: {
    label: "Agri Import Waiting Time — Inbound, Dublin",
    unit: "hrs",
    category: "agri",
    icon: "🕐",
    theme: "amber",
    tooltip:
      "Average waiting time for agri import trucks at Dublin port — includes SPS physical inspection queue. This is the primary DAFM utilisation driver.",
  },
  wt_ib_a_ross: {
    label: "Agri Import Waiting Time — Inbound, Rosslare",
    unit: "hrs",
    category: "agri",
    icon: "🕐",
    theme: "amber",
    tooltip: "Average waiting time for agri import trucks at Rosslare port.",
  },
  wt_ib_na_dub: {
    label: "Non-Agri Import Waiting Time — Inbound, Dublin",
    unit: "hrs",
    category: "non_agri",
    icon: "🏭",
    theme: "blue",
    tooltip:
      "Average waiting time for non-agri import trucks at Dublin port. Non-agri products go through customs checks only — no SPS inspection.",
  },
  wt_ob_na_gb_dub: {
    label: "Non-Agri Export Waiting Time — Outbound, Dublin (GB-side)",
    unit: "hrs",
    category: "non_agri",
    icon: "🏭",
    theme: "blue",
    tooltip:
      "Average waiting time for non-agri export trucks at the GB-side port — customs clearance queue on departure from Ireland.",
  },
  wt_ib_na_ross: {
    label: "Non-Agri Import Waiting Time — Inbound, Rosslare",
    unit: "hrs",
    category: "non_agri",
    icon: "🏭",
    theme: "blue",
    tooltip: "Average waiting time for non-agri import trucks at Rosslare port.",
  },
  wt_ob_na_gb_ross: {
    label: "Non-Agri Export Waiting Time — Outbound, Rosslare (GB-side)",
    unit: "hrs",
    category: "non_agri",
    icon: "🏭",
    theme: "blue",
    tooltip: "Average waiting time for non-agri export trucks at the GB-side of Rosslare departures.",
  },
  tt_ob_lb: {
    label: "Landbridge Transport Time — Outbound Export (IRE→EU via GB)",
    unit: "hrs",
    category: "routes",
    icon: "🛤",
    theme: "violet",
    tooltip:
      "Average total transit time for trucks travelling outbound via the GB Landbridge route (Ireland → GB → EU through Dover/Calais). Includes UK transit time.",
  },
  wt_ob_lb: {
    label: "Landbridge Waiting Time — Outbound Export",
    unit: "hrs",
    category: "routes",
    icon: "🕐",
    theme: "violet",
    tooltip:
      "Average waiting time at Landbridge transit points for outbound trucks — includes Dover/Calais check delays.",
  },
  tt_ib_lb: {
    label: "Landbridge Transport Time — Inbound Import (EU→IRE via GB)",
    unit: "hrs",
    category: "routes",
    icon: "🛤",
    theme: "violet",
    tooltip:
      "Average total transit time for trucks arriving inbound via the Landbridge (EU → GB → Ireland). Sensitive to UK border check intensity.",
  },
  wt_ib_lb: {
    label: "Landbridge Waiting Time — Inbound Import",
    unit: "hrs",
    category: "routes",
    icon: "🕐",
    theme: "violet",
    tooltip: "Average waiting time at Landbridge transit points for inbound trucks.",
  },
  tt_ob_dr: {
    label: "Direct Route Transport Time — Outbound Export (IRE→EU)",
    unit: "hrs",
    category: "routes",
    icon: "🚢",
    theme: "teal",
    tooltip:
      "Average transport time for trucks using Direct EU routes outbound (Ireland → Cherbourg / Rotterdam / Zeebrugge). Bypasses UK checks entirely.",
  },
  tt_ib_dr: {
    label: "Direct Route Transport Time — Inbound Import (EU→IRE)",
    unit: "hrs",
    category: "routes",
    icon: "🚢",
    theme: "teal",
    tooltip: "Average transport time for trucks arriving via Direct EU routes inbound into Ireland.",
  },
  uti_cus_d: {
    label: "Customs Utilisation — Dublin",
    unit: "%",
    category: "staff",
    icon: "👮",
    theme: "violet",
    tooltip:
      "Utilisation rate of Revenue (customs) check depots at Dublin port. Values above 80% indicate a bottleneck — trucks are queuing for customs processing.",
    fraction: true,
  },
  uti_dafm_d: {
    label: "DAFM Utilisation — Dublin",
    unit: "%",
    category: "staff",
    icon: "🏥",
    theme: "violet",
    tooltip:
      "Utilisation rate of SPS (DAFM) inspection bays at Dublin. High utilisation here is the primary driver of agri-food inbound waiting times. Values above 80% are critical.",
    fraction: true,
  },
  uti_cus_r: {
    label: "Customs Utilisation — Rosslare",
    unit: "%",
    category: "staff",
    icon: "👮",
    theme: "violet",
    tooltip: "Utilisation rate of Revenue check depots at Rosslare port.",
    fraction: true,
  },
  uti_dafm_r: {
    label: "DAFM Utilisation — Rosslare",
    unit: "%",
    category: "staff",
    icon: "🏥",
    theme: "violet",
    tooltip:
      "Utilisation rate of SPS (DAFM) inspection bays at Rosslare port. High values indicate agri-food inspection pressure.",
    fraction: true,
  },
};

/**
 * Matches `nolhc_ml.training_columns.col_to_slug` — maps API output column names to `KPI_META` keys.
 * @param {string} name
 */
export function colToSlug(name) {
  return String(name)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80);
}

/** Same order as `OUTPUT_COLUMN_ORDER` in `nolhc_ml/src/training_columns.py` (20 targets). */
export const OUTPUT_API_TARGETS = [
  "TT_OB_Agri",
  "WT_OB_A_GB-Dub",
  "WT_OB_A_GB-Ross",
  "TT_IB_Agri",
  "WT_IB_A_Dub",
  "WT_IB_A_Ross",
  "WT_IB_NA_Dub",
  "WT_OB_NA_GB-Dub",
  "WT_IB_NA_Ross",
  "WT_OB_NA_GB-Ross",
  "TT_OB_LB",
  "WT_OB_LB",
  "TT_IB_LB",
  "WT_IB_LB",
  "TT_OB_DR",
  "TT_IB_DR",
  "Uti_Cus_D",
  "Uti_DAFM_D",
  "Uti_Cus_R",
  "Uti_DAFM_R",
];

export const KPI_CATEGORIES = {
  agri: { title: "🌾 Agri Products", border: "teal" },
  non_agri: { title: "🏭 Non-Agri Products", border: "blue" },
  routes: { title: "🛳 Routes", border: "violet" },
  staff: { title: "👷 Staff Utilisation", border: "amber" },
};

/** Default `state.config` — matches spec §9.1 / training medians. */
export const NOLHC_MEDIANS = {
  NA_Im: 6140333,
  NA_Ex: 5387458,
  A_Im: 2826920,
  A_Ex: 2111499,
  NA_Im_LB: 747571,
  NA_Im_DR: 681189,
  NA_Ex_LB: 835757,
  NA_Ex_DR: 480163,
  A_Im_LB: 427438,
  A_Im_DR: 301281,
  A_Ex_LB: 344142,
  A_Ex_DR: 119462,
  Shift_NA_Im_LB_to_Cher: 681189,
  Shift_NA_Ex_LB_to_Cher: 480163,
  Shift_A_Im_LB_to_Cher: 301281,
  Shift_A_Ex_LB_to_Cher: 119462,
  VCap_Dub_Hey: 63,
  VCap_Dub_Holy: 109,
  VCap_Dub_Liv: 64,
  VCap_Ross_Fish: 52,
  VCap_Ross_Pem: 84,
  ChkTime_Doc: 4.28,
  ChkTime_Phy: 33.99,
  NumCusShed_D: 2,
  NumDAFM_D: 15,
  NumCusShed_R: 1,
  NumDAFM_R: 1,
  Pct_NA_OB_Green: 0.27,
  Pct_NA_OB_Red: 0.38,
  Pct_A_OB_Red: 0.83,
  Pct_NA_IB_Green: 0.33,
  Pct_NA_IB_Red: 0.28,
  Pct_A_IB_Red: 0.3,
  Pct_IB_PreBoard: 0.29,
  Pct_OB_PreBoard: 0.29,
};
