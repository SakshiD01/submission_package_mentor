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
    label: "Transport Time — Outbound",
    unit: "hrs",
    category: "agri",
    icon: "⏱",
    theme: "teal",
    tooltip:
      "Average total transport time for agri-food products travelling outbound from Ireland to GB. Includes port waiting and ferry crossing time.",
  },
  wt_ob_a_gb_dub: {
    label: "Wait Time Outbound — Dublin (GB side)",
    unit: "hrs",
    category: "agri",
    icon: "🕐",
    theme: "amber",
    tooltip:
      "Average waiting time for agri export trucks at the GB-side of Dublin departures — time spent queuing for customs and SPS checks before boarding.",
  },
  wt_ob_a_gb_ross: {
    label: "Wait Time Outbound — Rosslare (GB side)",
    unit: "hrs",
    category: "agri",
    icon: "🕐",
    theme: "amber",
    tooltip: "Average waiting time for agri export trucks at the GB-side of Rosslare departures.",
  },
  tt_ib_agri: {
    label: "Transport Time — Inbound",
    unit: "hrs",
    category: "agri",
    icon: "⏱",
    theme: "teal",
    tooltip:
      "Average total transport time for agri-food products arriving inbound into Ireland from GB. Higher border check rates increase this significantly.",
  },
  wt_ib_a_dub: {
    label: "Wait Time Inbound — Dublin",
    unit: "hrs",
    category: "agri",
    icon: "🕐",
    theme: "amber",
    tooltip:
      "Average waiting time for agri import trucks at Dublin port — includes SPS physical inspection queue. This is the primary DAFM utilisation driver.",
  },
  wt_ib_a_ross: {
    label: "Wait Time Inbound — Rosslare",
    unit: "hrs",
    category: "agri",
    icon: "🕐",
    theme: "amber",
    tooltip: "Average waiting time for agri import trucks at Rosslare port.",
  },
  wt_ib_na_dub: {
    label: "Wait Time Inbound — Dublin",
    unit: "hrs",
    category: "non_agri",
    icon: "🏭",
    theme: "blue",
    tooltip:
      "Average waiting time for non-agri import trucks at Dublin port. Non-agri products go through customs checks only — no SPS inspection.",
  },
  wt_ob_na_gb_dub: {
    label: "Wait Time Outbound — Dublin (GB side)",
    unit: "hrs",
    category: "non_agri",
    icon: "🏭",
    theme: "blue",
    tooltip:
      "Average waiting time for non-agri export trucks at the GB-side port — customs clearance queue on departure from Ireland.",
  },
  wt_ib_na_ross: {
    label: "Wait Time Inbound — Rosslare",
    unit: "hrs",
    category: "non_agri",
    icon: "🏭",
    theme: "blue",
    tooltip: "Average waiting time for non-agri import trucks at Rosslare port.",
  },
  wt_ob_na_gb_ross: {
    label: "Wait Time Outbound — Rosslare (GB side)",
    unit: "hrs",
    category: "non_agri",
    icon: "🏭",
    theme: "blue",
    tooltip: "Average waiting time for non-agri export trucks at the GB-side of Rosslare departures.",
  },
  tt_ob_lb: {
    label: "Landbridge TT — Outbound",
    unit: "hrs",
    category: "routes",
    icon: "🛤",
    theme: "violet",
    tooltip:
      "Average total transit time for trucks travelling outbound via the GB Landbridge route (Ireland → GB → EU through Dover/Calais). Includes UK transit time.",
  },
  wt_ob_lb: {
    label: "Landbridge WT — Outbound",
    unit: "hrs",
    category: "routes",
    icon: "🕐",
    theme: "violet",
    tooltip:
      "Average waiting time at Landbridge transit points for outbound trucks — includes Dover/Calais check delays.",
  },
  tt_ib_lb: {
    label: "Landbridge TT — Inbound",
    unit: "hrs",
    category: "routes",
    icon: "🛤",
    theme: "violet",
    tooltip:
      "Average total transit time for trucks arriving inbound via the Landbridge (EU → GB → Ireland). Sensitive to UK border check intensity.",
  },
  wt_ib_lb: {
    label: "Landbridge WT — Inbound",
    unit: "hrs",
    category: "routes",
    icon: "🕐",
    theme: "violet",
    tooltip: "Average waiting time at Landbridge transit points for inbound trucks.",
  },
  tt_ob_dr: {
    label: "Direct Route TT — Outbound",
    unit: "hrs",
    category: "routes",
    icon: "🚢",
    theme: "teal",
    tooltip:
      "Average transport time for trucks using Direct EU routes outbound (Ireland → Cherbourg / Rotterdam / Zeebrugge). Bypasses UK checks entirely.",
  },
  tt_ib_dr: {
    label: "Direct Route TT — Inbound",
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
