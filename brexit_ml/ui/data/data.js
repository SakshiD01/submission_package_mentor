/**
 * ============================================================
 *  DATA LAYER — data.js
 *  All static data lives HERE and ONLY HERE.
 *  To change any value (e.g. ferry times, officer counts,
 *  check costs), edit this file. Nothing else needs changing.
 * ============================================================
 */

// ── 1. ROUTE KEYS ────────────────────────────────────────────
// Single source of truth for route string identifiers.
// Using en-dash (–) consistently everywhere.
export const ROUTES = {
  HEYSHAM_DUBLIN:     "Heysham – Dublin",
  HOLYHEAD_DUBLIN:    "Holyhead – Dublin",
  LIVERPOOL_DUBLIN:   "Liverpool – Dublin",
  FISHGUARD_ROSSLARE: "Fishguard – Rosslare",
  PEMBROKE_ROSSLARE:  "Pembroke – Rosslare",
  LANDBRIDGE:         "Ireland – EU (via GB Land-bridge)",
  CHERBOURG_DUBLIN:   "Cherbourg – Dublin",
  CHERBOURG_ROSSLARE: "Cherbourg – Rosslare",
  ROTTERDAM_DUBLIN:   "Rotterdam – Dublin",
  ZEEBRUGGE_DUBLIN:   "Zeebrugge – Dublin",
};

// ── 2. DISPLAY LABELS ────────────────────────────────────────
// Human-friendly labels shown in dropdowns (arrows for inbound).
// The key is the route ID from ROUTES above.
export const ROUTE_DISPLAY = {
  [ROUTES.HEYSHAM_DUBLIN]:     "Heysham → Dublin",
  [ROUTES.HOLYHEAD_DUBLIN]:    "Holyhead → Dublin",
  [ROUTES.LIVERPOOL_DUBLIN]:   "Liverpool → Dublin",
  [ROUTES.FISHGUARD_ROSSLARE]: "Fishguard → Rosslare",
  [ROUTES.PEMBROKE_ROSSLARE]:  "Pembroke → Rosslare",
  [ROUTES.LANDBRIDGE]:         "Ireland → / ← EU (via GB Land-bridge)",
  [ROUTES.CHERBOURG_DUBLIN]:   "Cherbourg → Dublin",
  [ROUTES.CHERBOURG_ROSSLARE]: "Cherbourg → Rosslare",
  [ROUTES.ROTTERDAM_DUBLIN]:   "Rotterdam → Dublin",
  [ROUTES.ZEEBRUGGE_DUBLIN]:   "Zeebrugge → Dublin",
};

// ── 3. CORRIDOR → ROUTES MAP ─────────────────────────────────
// Which routes belong to which corridor.
export const CORRIDOR_ROUTES = {
  "East/West Maritime Corridor": [
    ROUTES.HEYSHAM_DUBLIN, ROUTES.HOLYHEAD_DUBLIN, ROUTES.LIVERPOOL_DUBLIN,
    ROUTES.FISHGUARD_ROSSLARE, ROUTES.PEMBROKE_ROSSLARE,
  ],
  "Land-bridge Route": [ROUTES.LANDBRIDGE],
  "Direct Route": [
    ROUTES.CHERBOURG_DUBLIN, ROUTES.CHERBOURG_ROSSLARE,
    ROUTES.ROTTERDAM_DUBLIN, ROUTES.ZEEBRUGGE_DUBLIN,
  ],
};

// ── 4. FERRY CROSSING TIMES (hours) ──────────────────────────
// How many hours the ferry crossing itself takes (not including waits).
export const FERRY_TIMES = {
  [ROUTES.HEYSHAM_DUBLIN]:     3.5,
  [ROUTES.HOLYHEAD_DUBLIN]:    3.25,
  [ROUTES.LIVERPOOL_DUBLIN]:   8.0,
  [ROUTES.FISHGUARD_ROSSLARE]: 3.5,
  [ROUTES.PEMBROKE_ROSSLARE]:  4.0,
  [ROUTES.LANDBRIDGE]:         18.0,
  [ROUTES.CHERBOURG_DUBLIN]:   18.5,
  [ROUTES.CHERBOURG_ROSSLARE]: 17.0,
  [ROUTES.ROTTERDAM_DUBLIN]:   28.0,
  [ROUTES.ZEEBRUGGE_DUBLIN]:   24.0,
};

// ── 5. FERRY CAPACITY (trailers per sailing) ──────────────────
export const FERRY_CAPACITY = {
  [ROUTES.HEYSHAM_DUBLIN]:     122,
  [ROUTES.HOLYHEAD_DUBLIN]:    209,
  [ROUTES.LIVERPOOL_DUBLIN]:   123,
  [ROUTES.FISHGUARD_ROSSLARE]: 75,
  [ROUTES.PEMBROKE_ROSSLARE]:  122,
  [ROUTES.LANDBRIDGE]:         123,
  [ROUTES.CHERBOURG_DUBLIN]:   170,
  [ROUTES.CHERBOURG_ROSSLARE]: 150,
  [ROUTES.ROTTERDAM_DUBLIN]:   530,
  [ROUTES.ZEEBRUGGE_DUBLIN]:   530,
};

// ── 6. FERRY SAILINGS PER DAY ─────────────────────────────────
export const SAILINGS_PER_DAY = {
  [ROUTES.HEYSHAM_DUBLIN]:     2,
  [ROUTES.HOLYHEAD_DUBLIN]:    4,
  [ROUTES.LIVERPOOL_DUBLIN]:   2,
  [ROUTES.FISHGUARD_ROSSLARE]: 2,
  [ROUTES.PEMBROKE_ROSSLARE]:  2,
  [ROUTES.LANDBRIDGE]:         3,
  [ROUTES.CHERBOURG_DUBLIN]:   1,
  [ROUTES.CHERBOURG_ROSSLARE]: 1,
  [ROUTES.ROTTERDAM_DUBLIN]:   1,
  [ROUTES.ZEEBRUGGE_DUBLIN]:   1,
};

// ── 7. LAND TRANSIT ADDITIONS (hours) ────────────────────────
// Extra driving time on top of ferry crossing (Land-bridge crosses GB).
export const LAND_TRANSIT = {
  "East/West Maritime Corridor": 0,
  "Land-bridge Route":           8,
  "Direct Route":                0,
};

// ── 8. GOODS TYPES & PROPERTIES ─────────────────────────────
export const GOODS_TYPES = [
  "Animals & Animal Products",
  "Plants & Plant Products",
  "Timber & Timber Products",
  "Fishery Products",
  "Animal Feed",
  "Fertilizers",
  "Food of Non-Animal Origin",
];

export const GOODS_ICONS = {
  "Animals & Animal Products": "🐄",
  "Plants & Plant Products":   "🌿",
  "Timber & Timber Products":  "🪵",
  "Fishery Products":          "🐟",
  "Animal Feed":               "🌾",
  "Fertilizers":               "🧪",
  "Food of Non-Animal Origin": "🥫",
};

// Default shelf life in days per goods type.
// Override with user input in the form.
export const SHELF_LIFE_DAYS = {
  "Animals & Animal Products": 5,
  "Plants & Plant Products":   7,
  "Timber & Timber Products":  365,
  "Fishery Products":          3,
  "Animal Feed":               90,
  "Fertilizers":               180,
  "Food of Non-Animal Origin": 14,
};

// What % of trucks carrying this goods type are classified as agri/SPS.
export const AGRI_PCT = {
  "Animals & Animal Products": 1.00,
  "Plants & Plant Products":   1.00,
  "Timber & Timber Products":  0.10,
  "Fishery Products":          1.00,
  "Animal Feed":               1.00,
  "Fertilizers":               0.60,
  "Food of Non-Animal Origin": 1.00,
};

// ── 9. TRUCK TYPES & CAPACITIES ─────────────────────────────
export const TRUCK_TYPES = [
  { value: "unaccompanied", label: "Unaccompanied (25t)",      capacity: 25 },
  { value: "accompanied",   label: "Accompanied (25t)",        capacity: 25 },
  { value: "refrigerated",  label: "Refrigerated / Reefer (22t)", capacity: 22 },
  { value: "tanker",        label: "Tanker (30t)",             capacity: 30 },
  { value: "flatbed",       label: "Flatbed (28t)",            capacity: 28 },
];

// ── 10. PORT CHECK PARAMETERS ────────────────────────────────
// All times in MINUTES. Percentages as decimals (1.00 = 100%).
export const CHECK_PARAMS = {
  // --- Irish port outbound (trucks leaving Ireland) ---
  irish_out_customs_pct: 1.00,   // 100% trucks get customs check
  irish_out_customs_min: 5,      // 5 min per truck

  // --- Irish port inbound (trucks arriving into Ireland) ---
  irish_in_green_pct:    0.85,   // 85% go straight through (green lane)
  irish_in_orange_min:   10,     // orange lane: documentary check (10 min)
  irish_in_red_pct:      0.15,   // 15% get physical inspection (red lane)
  irish_in_red_min:      30,     // red lane: physical check (30 min)
  irish_in_sec_pct:      0.05,   // 5% get security check
  irish_in_sec_min:      20,     // security check (20 min)

  // --- West GB ports (Holyhead, Liverpool etc.) outbound ---
  gbw_out_customs_pct:   1.00,
  gbw_out_customs_min:   5,

  // --- West GB ports inbound ---
  gbw_in_green_pct:      0.80,
  gbw_in_orange_min:     12,
  gbw_in_red_pct:        0.20,
  gbw_in_red_min:        35,
  gbw_in_sec_pct:        0.05,
  gbw_in_sec_min:        20,

  // --- East GB port (Dover) outbound ---
  gbe_out_customs_pct:   1.00,
  gbe_out_customs_min:   5,

  // --- East GB port (Dover) inbound ---
  gbe_in_green_pct:      0.90,
  gbe_in_orange_min:     8,
  gbe_in_red_pct:        0.10,
  gbe_in_red_min:        25,
  gbe_in_sec_pct:        0.03,
  gbe_in_sec_min:        15,

  // --- EU ports (Cherbourg, Rotterdam, Zeebrugge) outbound ---
  eu_out_customs_pct:    1.00,
  eu_out_customs_min:    5,

  // --- EU ports inbound ---
  eu_in_green_pct:       0.90,
  eu_in_orange_min:      10,
  eu_in_red_pct:         0.10,
  eu_in_red_min:         30,
  eu_in_sec_pct:         0.03,
  eu_in_sec_min:         15,

  // SPS multiplier: agri-food checks take 2.5× longer
  sps_time_multiplier:   2.5,
};

// ── 11. OFFICER COUNTS PER PORT ───────────────────────────────
// Increase these numbers to model more staff → shorter queues.
export const OFFICERS = {
  irish_customs:  10,
  irish_dafm:     10,
  irish_security: 10,
  gbw_customs:    10,
  gbw_dafm:       10,
  gbe_customs:    10,
  eu_customs:     10,
  eu_dafm:        10,
};

// ── 12. OFFICIAL CHECK COSTS (€ per truck) ───────────────────
export const CHECK_COSTS_BY_PORT = {
  Dublin:    { documentary: 55, physical: 520, security: 500 },
  Rosslare:  { documentary: 50, physical: 500, security: 480 },
  Heysham:   { documentary: 40, physical: 420, security: 400 },
  Liverpool: { documentary: 45, physical: 450, security: 420 },
  Holyhead:  { documentary: 42, physical: 430, security: 410 },
  Fishguard: { documentary: 38, physical: 400, security: 390 },
  Pembroke:  { documentary: 38, physical: 400, security: 390 },
  Dover:     { documentary: 45, physical: 460, security: 430 },
  Calais:    { documentary: 42, physical: 440, security: 420 },
  Cherbourg: { documentary: 48, physical: 480, security: 460 },
  Rotterdam: { documentary: 50, physical: 490, security: 470 },
  Zeebrugge: { documentary: 48, physical: 470, security: 450 },
};

// Base check cost per corridor (used in KPI summary)
export const CHECK_COST_BASE = {
  "East/West Maritime Corridor": 150,
  "Land-bridge Route":           320,
  "Direct Route":                220,
};

// ── 13. ANNUAL TRADE VOLUMES (tonnes, 2018 data) ─────────────
export const ANNUAL_VOLUMES = {
  "East/West Maritime Corridor": {
    import:     6330240,
    export:     5554080,
    agriImport: 1643898,
    agriExport: 1340611,
  },
  "Land-bridge Route": {
    import:     1205760,
    export:     1057920,
    agriImport: 313123,
    agriExport: 255354,
  },
  "Direct Route": {
    import:     1357000,
    export:     800000,
    agriImport: 501694,
    agriExport: 110256,
  },
};

// ── 14. PORT STAFF CAPACITIES (for Indicators panel) ─────────
export const PORT_CAPACITY = {
  Dublin:    { customs: 10, dafm: 10, security: 10, tractors: 20 },
  Rosslare:  { customs: 10, dafm: 10, security: 10, tractors: 20 },
  Heysham:   { customs: 10, dafm: 10, security: 10, tractors: 20 },
  Liverpool: { customs: 10, dafm: 10, security: 10, tractors: 20 },
  Holyhead:  { customs: 10, dafm: 10, security: 10, tractors: 20 },
  Fishguard: { customs: 10, dafm: 10, security: 10, tractors: 20 },
  Pembroke:  { customs: 10, dafm: 10, security: 10, tractors: 20 },
  Dover:     { customs: 10, dafm: 10, security: 10, tractors: 20 },
  Calais:    { customs: 10, dafm: 10, security: 10, tractors: 20 },
  Cherbourg: { customs: 10, dafm: 10, security: 10, tractors: 20 },
  Rotterdam: { customs: 10, dafm: 10, security: 10, tractors: 20 },
  Zeebrugge: { customs: 10, dafm: 10, security: 10, tractors: 20 },
};

// ── 15. PORTS PER CORRIDOR (for Indicators filter) ───────────
export const CORRIDOR_PORTS = {
  "East/West Maritime Corridor": ["Dublin","Rosslare","Heysham","Liverpool","Holyhead","Fishguard","Pembroke"],
  "Land-bridge Route":           ["Dublin","Rosslare","Heysham","Liverpool","Dover","Calais"],
  "Direct Route":                ["Dublin","Rosslare","Cherbourg","Rotterdam","Zeebrugge"],
};

// ── 16. TRUCK MIX PER CORRIDOR (% unaccompanied) ─────────────
export const TRUCK_MIX = {
  "East/West Maritime Corridor": { unaccompanied: 50, accompanied: 50 },
  "Land-bridge Route":           { unaccompanied: 35, accompanied: 65 },
  "Direct Route":                { unaccompanied: 45, accompanied: 55 },
};

// ── 17. MAP — PORT COORDINATES (spec §4.3) ───────────────────
// All twelve ports — lat, lng to four decimal places.
export const PORT_COORDS = {
  Dublin:      [53.3478, -6.2297],
  Rosslare:    [52.2537, -6.3389],
  Heysham:     [54.0333, -2.9167],
  Liverpool:   [53.4084, -2.9916],
  Holyhead:    [53.3094, -4.6331],
  Fishguard:   [52.0092, -4.9906],
  Pembroke:    [51.6833, -4.9500],
  Dover:       [51.1279,  1.3134],
  Calais:      [50.9513,  1.8587],
  Cherbourg:   [49.6333, -1.6167],
  Rotterdam:   [51.9225,  4.4792],
  Zeebrugge:   [51.3333,  3.1833],
};

// ── 18. MAP — FERRY ROUTE LINES ───────────────────────────────
export const MAP_ROUTES = [
  // East/West Maritime Corridor — solid dark lines
  { from: "Dublin",   to: "Heysham",   corridor: "East/West Maritime Corridor", color: "#1a1a2e", dash: null },
  { from: "Dublin",   to: "Liverpool",  corridor: "East/West Maritime Corridor", color: "#1a1a2e", dash: null },
  { from: "Dublin",   to: "Holyhead",   corridor: "East/West Maritime Corridor", color: "#1a1a2e", dash: null },
  { from: "Rosslare", to: "Fishguard",  corridor: "East/West Maritime Corridor", color: "#1a1a2e", dash: null },
  { from: "Rosslare", to: "Pembroke",   corridor: "East/West Maritime Corridor", color: "#1a1a2e", dash: null },
  // Land-bridge — dashed dark lines
  { from: "Dublin",   to: "Liverpool",  corridor: "Land-bridge Route",            color: "#1a1a2e", dash: "6 4" },
  { from: "Dover",    to: "Calais",     corridor: "Land-bridge Route",            color: "#1a1a2e", dash: "6 4" },
  // Direct — solid blue lines
  { from: "Dublin",   to: "Cherbourg",  corridor: "Direct Route",                 color: "#1a3a5c", dash: null },
  { from: "Rosslare", to: "Cherbourg",  corridor: "Direct Route",                 color: "#1a3a5c", dash: null },
  { from: "Dublin",   to: "Rotterdam",  corridor: "Direct Route",                 color: "#1a3a5c", dash: null },
  { from: "Dublin",   to: "Zeebrugge",  corridor: "Direct Route",                 color: "#1a3a5c", dash: null },
];

// ── 19. APP CONFIG ────────────────────────────────────────────
// General settings you might want to tweak.
export const APP_CONFIG = {
  portWorkingHoursPerDay: 16,    // How many hours ports operate daily
  tonnesPerTruck:         25,    // Default tonnes capacity per truck
  shelfLifeCriticalPct:   30,    // Below this % remaining shelf life = critical (shown in red)
  queueSaturationFactor:  2,     // Queue multiplier when port is at capacity
};
