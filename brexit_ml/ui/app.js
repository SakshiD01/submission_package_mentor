/**
 * ============================================================
 *  MAIN APP — app.js
 *  This file is the "glue". It:
 *  1. Imports data from data.js
 *  2. Imports UI pieces from components.js
 *  3. Builds every panel and connects them together
 *
 *  You should NOT need to edit this file to change data or styling.
 *  - Change data?   → data/data.js
 *  - Change look?   → styles/styles.css
 *  - Change layout? → index.html
 * ============================================================
 */

import {
  ROUTES,
  ROUTE_DISPLAY,
  ANNUAL_VOLUMES,
  PORT_CAPACITY,
  CORRIDOR_PORTS,
  TRUCK_MIX,
  CHECK_COSTS_BY_PORT,
  PORT_COORDS,
  MAP_ROUTES,
  OFFICERS,
  FERRY_CAPACITY,
  SAILINGS_PER_DAY,
} from "./data/data.js";

/** Indicator tab corridor labels (static dashboard; not tied to API route_type). */
const INDICATOR_CORRIDORS = ["East/West Maritime Corridor", "Land-bridge Route", "Direct Route"];

import {
  el, UtilBar, DeltaBadge, KpiCard, SelectField, NumberField,
  DateField, SectionCard, IndRow, EmptyState, GoodsBadge,
} from "./components/components.js";

/**
 * ML API base URL. When the UI is served by ``uvicorn main:app`` (same host/port as the API),
 * use the page origin so ``fetch`` stays same-origin. Override with ``window.__ML_API_BASE__``.
 */
const API_ML_BASE =
  (typeof window !== "undefined" && window.__ML_API_BASE__) ||
  (typeof window !== "undefined" &&
    window.location &&
    /^https?:$/i.test(window.location.protocol || "")
    ? window.location.origin
    : "http://localhost:8000");

/** Mirrors `schemas.VALID_OPTIONS` when GET /scenario/options fails (offline / CORS). */
const FALLBACK_VALID_OPTIONS = {
  supplier_region: ["ireland", "great_britain", "eu"],
  origin_port: {
    ireland: ["dublin", "rosslare"],
    great_britain: ["liverpool", "holyhead", "heysham", "fishguard", "pembroke"],
    eu: ["cherbourg", "rotterdam", "zeebrugge", "bilbao"],
  },
  destination_region: ["ireland", "great_britain", "eu"],
  destination_port: {
    ireland: ["dublin", "rosslare"],
    great_britain: ["liverpool", "holyhead", "heysham", "fishguard", "pembroke"],
    eu: ["cherbourg", "rotterdam", "zeebrugge", "bilbao"],
  },
  commodity_type: ["all_products", "agri", "category"],
  direction: ["export", "import"],
  route_type: {
    great_britain: ["direct_gb"],
    eu: ["landbridge", "direct_cherbourg", "direct_rotterdam", "direct_zeebrugge", "direct_bilbao"],
  },
  check_regime: ["none", "light", "standard", "hard"],
};

/**
 * Populated on load from GET /scenario/options (same shape as backend VALID_OPTIONS).
 * @type {Record<string, unknown> | null}
 */
let VALID_OPTIONS = null;

async function loadScenarioOptions() {
  const url = `${API_ML_BASE.replace(/\/$/, "")}/scenario/options`;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(res.statusText || String(res.status));
    VALID_OPTIONS = await res.json();
  } catch (e) {
    console.warn("GET /scenario/options failed; using bundled fallback", e);
    VALID_OPTIONS = { ...FALLBACK_VALID_OPTIONS };
  }
  if (typeof window !== "undefined") window.VALID_OPTIONS = VALID_OPTIONS;
}

function effectiveValidOptions() {
  return VALID_OPTIONS || FALLBACK_VALID_OPTIONS;
}

function supplierRegionLabel(slug) {
  const labels = { ireland: "Ireland", great_britain: "Great Britain", eu: "European Union" };
  return labels[slug] || String(slug).replace(/_/g, " ");
}

function portSlugLabel(slug) {
  if (!slug) return "";
  return slug.charAt(0).toUpperCase() + slug.slice(1);
}

const COMMODITY_ICONS = {
  all_products: "📦",
  agri: "🌾",
  category: "⚠️",
};

function commodityLabel(slug) {
  const labels = {
    all_products: "All products",
    agri: "Agri-food",
    category: "Category / risk commodities",
  };
  return labels[slug] || String(slug).replace(/_/g, " ");
}

function checkRegimeLabel(slug) {
  const labels = { none: "None", light: "Light", standard: "Standard", hard: "Hard" };
  return labels[slug] || String(slug);
}

function directionSelectOptionsApi(vo) {
  const raw = Array.isArray(vo.direction) ? vo.direction : ["import", "export"];
  const labels = {
    import: "Import — goods arriving in Ireland",
    export: "Export — goods leaving Ireland",
  };
  return raw.map((api) => ({
    value: api,
    label: labels[api] || api,
  }));
}

/** Phase 1 (semantic_api): Ireland → GB port pairs for export. */
const PHASE1_EXPORT_DEST_BY_ORIGIN = {
  dublin: ["liverpool", "holyhead", "heysham"],
  rosslare: ["fishguard", "pembroke"],
};

/** GB origin → Irish destination for import (same physical legs as export). */
const PHASE1_IMPORT_DEST_BY_ORIGIN = {
  liverpool: ["dublin"],
  holyhead: ["dublin"],
  heysham: ["dublin"],
  fishguard: ["rosslare"],
  pembroke: ["rosslare"],
};

function destinationRegionLabel(slug) {
  const labels = { ireland: "Ireland", great_britain: "Great Britain", eu: "European Union" };
  return labels[slug] || String(slug).replace(/_/g, " ");
}

function routeTypeLabel(slug) {
  const labels = {
    direct_gb: "Direct (East/West Maritime Corridor)",
    landbridge: "Via GB Land-bridge",
    direct_cherbourg: "Direct to Cherbourg",
    direct_rotterdam: "Direct to Rotterdam",
    direct_zeebrugge: "Direct to Zeebrugge",
    direct_bilbao: "Direct to Bilbao",
  };
  return labels[slug] || String(slug).replace(/_/g, " ");
}

function directionOptionsForSupplier(vo, supplier) {
  const base = directionSelectOptionsApi(vo);
  if (!supplier) return base;
  if (supplier === "ireland") return base.filter((o) => o.value === "export");
  if (supplier === "great_britain") return base.filter((o) => o.value === "import");
  return [];
}

function destinationRegionSlugsForPhase1(cfg) {
  const { supplier_region: sr, direction: d } = cfg;
  if (!d) return [];
  const vo = effectiveValidOptions();
  const all = Array.isArray(vo.destination_region)
    ? vo.destination_region
    : FALLBACK_VALID_OPTIONS.destination_region;
  if (sr === "ireland" && d === "export") return all.filter((x) => x === "great_britain");
  if (sr === "great_britain" && d === "import") return all.filter((x) => x === "ireland");
  return [];
}

function destinationPortSlugsForPhase1(cfg) {
  const vo = effectiveValidOptions();
  const byRegion =
    vo.destination_port && typeof vo.destination_port === "object"
      ? vo.destination_port
      : FALLBACK_VALID_OPTIONS.destination_port;
  const dr = cfg.destination_region;
  if (!dr) return [];
  const pool = Array.isArray(byRegion[dr]) ? byRegion[dr] : [];
  if (cfg.supplier_region === "ireland" && cfg.direction === "export" && cfg.origin_port) {
    const allow = new Set(PHASE1_EXPORT_DEST_BY_ORIGIN[cfg.origin_port] || []);
    return pool.filter((p) => allow.has(p));
  }
  if (cfg.supplier_region === "great_britain" && cfg.direction === "import" && cfg.origin_port) {
    const allow = new Set(PHASE1_IMPORT_DEST_BY_ORIGIN[cfg.origin_port] || []);
    return pool.filter((p) => allow.has(p));
  }
  return pool;
}

/**
 * Route type select: Phase 1 only `direct_gb` is valid; other slugs shown disabled (Phase 2).
 */
function routeTypeSelectOptions(vo, destinationRegion) {
  const rt = vo?.route_type;
  if (!rt || typeof rt !== "object") {
    return [{ value: "direct_gb", label: routeTypeLabel("direct_gb") }];
  }
  const gb = Array.isArray(rt.great_britain) ? rt.great_britain : [];
  const eu = Array.isArray(rt.eu) ? rt.eu : [];
  const out = [];
  if (destinationRegion === "great_britain" || destinationRegion === "ireland") {
    gb.forEach((slug) => {
      out.push({
        value: slug,
        label: routeTypeLabel(slug),
        disabled: slug !== "direct_gb",
      });
    });
    eu.forEach((slug) => {
      out.push({
        value: slug,
        label: `${routeTypeLabel(slug)} (Phase 2)`,
        disabled: true,
      });
    });
  } else if (destinationRegion === "eu") {
    eu.forEach((slug) => {
      out.push({
        value: slug,
        label: `${routeTypeLabel(slug)} (Phase 2)`,
        disabled: true,
      });
    });
    gb.forEach((slug) => {
      out.push({
        value: slug,
        label: `${routeTypeLabel(slug)} (Phase 2)`,
        disabled: true,
      });
    });
  } else {
    [...gb, ...eu].forEach((slug) => {
      out.push({
        value: slug,
        label: slug === "direct_gb" ? routeTypeLabel(slug) : `${routeTypeLabel(slug)} (Phase 2)`,
        disabled: slug !== "direct_gb",
      });
    });
  }
  return out.length ? out : [{ value: "direct_gb", label: routeTypeLabel("direct_gb") }];
}

// ── APP STATE ─────────────────────────────────────────────────
const state = {
  config: {
    supplier_region: "",
    origin_port: "",
    destination_region: "",
    destination_port: "",
    commodity_type: "",
    direction: "",
    product_volume_tonnes: 0,
    route_type: "",
    check_regime: "standard",
    shelf_life_days: 0,
    customs_officers: null,
    dafm_officers: null,
    security_officers: null,
    tractors: null,
    unaccompanied_pct: null,
    shipmentDate: new Date().toISOString().split("T")[0],
    notes: "",
  },
  advancedOpen: false,
  hasRun: false,
  activeView: "results",
  loading: false,
  lastResult: null,
  /** @type {{ kind: string, title: string, message: string } | null} */
  apiError: null,
};

let debouncedPredictTimer = null;

const IRISH_PORTS = new Set(["dublin", "rosslare"]);
const GB_PORTS = new Set(["liverpool", "holyhead", "heysham", "fishguard", "pembroke"]);

/**
 * Build POST /scenario/predict body (ScenarioRequest) from UI config.
 */
function buildScenarioRequest(cfg) {
  const irishPortSlug =
    cfg.supplier_region === "ireland" ? cfg.origin_port : cfg.destination_port;
  const irishPortTitle =
    irishPortSlug && irishPortSlug.length
      ? irishPortSlug.charAt(0).toUpperCase() + irishPortSlug.slice(1)
      : "Dublin";

  /** @type {Record<string, unknown>} */
  const requestBody = {
    supplier_region: cfg.supplier_region,
    origin_port: cfg.origin_port,
    destination_region: cfg.destination_region,
    destination_port: cfg.destination_port,
    commodity_type: cfg.commodity_type || "all_products",
    direction: cfg.direction,
    product_volume_tonnes: Math.max(1, Number(cfg.product_volume_tonnes) || 1),
    route_type: cfg.route_type || "direct_gb",
    check_regime: cfg.check_regime || "standard",
  };

  const shelf = cfg.shelf_life_days > 0 ? cfg.shelf_life_days : undefined;
  if (shelf != null && shelf > 0) requestBody.shelf_life_days = shelf;

  if (cfg.customs_officers != null) requestBody.customs_officers = cfg.customs_officers;
  if (cfg.dafm_officers != null) requestBody.dafm_officers = cfg.dafm_officers;
  if (cfg.security_officers != null) requestBody.security_officers = cfg.security_officers;
  if (cfg.tractors != null) requestBody.tractors = cfg.tractors;
  if (cfg.unaccompanied_pct != null) requestBody.unaccompanied_pct = cfg.unaccompanied_pct;

  if (
    requestBody.customs_officers == null &&
    requestBody.dafm_officers == null &&
    requestBody.security_officers == null &&
    requestBody.tractors == null
  ) {
    requestBody.customs_officers = OFFICERS.irish_customs;
    requestBody.dafm_officers = OFFICERS.irish_dafm;
    requestBody.security_officers = OFFICERS.irish_security;
    requestBody.tractors = PORT_CAPACITY[irishPortTitle]?.tractors ?? 20;
  }
  if (requestBody.unaccompanied_pct == null) requestBody.unaccompanied_pct = 0.5;

  return requestBody;
}

const RESULT_GROUP_LABELS = {
  transit: "Transit",
  border_delay: "Border & waiting",
  shelf_life: "Shelf life",
  resource_utilisation: "Resource utilisation",
  vessel_queues: "Vessel queues",
  costs: "Costs",
};

function themeForStatus(status) {
  if (status === "low_coverage" || status === "zero_predicted") return "amber";
  if (status === "not_trained") return "grey";
  return "teal";
}

function iconForGroup(group) {
  if (group === "transit") return "⏱";
  if (group === "costs") return "💶";
  if (group === "shelf_life") return "⏳";
  if (group === "vessel_queues") return "🚛";
  if (group === "resource_utilisation") return "👥";
  return "📌";
}

const RESULT_GROUP_ORDER = [
  "transit",
  "border_delay",
  "shelf_life",
  "resource_utilisation",
  "vessel_queues",
  "costs",
];

function formatPredictionValue(pr, groupId) {
  if (pr.value == null || pr.value === undefined) return "—";
  const u = (pr.unit || "").toLowerCase();
  const v = pr.value;
  if (typeof v !== "number" || !Number.isFinite(v)) return String(v);
  if (
    groupId === "resource_utilisation" &&
    v >= 0 &&
    v <= 1
  ) {
    return `${(v * 100).toFixed(1)}%`;
  }
  if (u === "eur" || u === "€") return `€${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  if (u === "fraction") return `${(v * 100).toFixed(0)}%`;
  if (u === "minutes" || u === "minute") return `${v.toFixed(0)}`;
  if (u === "hours" || u === "hour" || u === "hrs") return `${v.toFixed(1)}`;
  if (u === "days" || u === "day") return `${v.toFixed(1)}`;
  if (Number.isInteger(v)) return String(v);
  return v.toFixed(2);
}

function displayUnitForPrediction(pr, groupId) {
  if (pr.value == null || pr.value === undefined) return "";
  const u = (pr.unit || "").toLowerCase();
  const v = pr.value;
  if (
    groupId === "resource_utilisation" &&
    typeof v === "number" &&
    Number.isFinite(v) &&
    v >= 0 &&
    v <= 1
  ) {
    return "";
  }
  if (!u || u === "mixed" || u === "fraction" || u === "eur" || u === "€") return "";
  if (u === "minutes" || u === "minute") return "min";
  if (u === "hours" || u === "hour") return "hrs";
  return pr.unit || "";
}

function predictionSub(pr) {
  const parts = [];
  if (pr.phase != null) parts.push(`Phase ${pr.phase}`);
  if (pr.coverage_pct != null) parts.push(`${pr.coverage_pct}% coverage`);
  if (pr.r2 != null && !Number.isNaN(pr.r2)) parts.push(`R² ${Number(pr.r2).toFixed(2)}`);
  if (pr.status && pr.status !== "ok") parts.push(String(pr.status).replace(/_/g, " "));
  return parts.join(" · ");
}

// ── VALIDATION ────────────────────────────────────────────────
function getMissingFields(config) {
  const missing = [];
  if (!config.supplier_region) missing.push("Supplier Region");
  else if (config.supplier_region === "eu") missing.push("EU supplier (Phase 2 — not supported yet)");
  if (config.supplier_region && config.supplier_region !== "eu" && !config.origin_port) {
    missing.push("Origin Port");
  }
  if (config.supplier_region && config.origin_port && !config.direction) missing.push("Direction");
  const drOpts = destinationRegionSlugsForPhase1(config);
  if (config.direction && !drOpts.length && config.supplier_region && config.supplier_region !== "eu") {
    missing.push("Destination Region");
  }
  if (config.direction && drOpts.length && !config.destination_region) missing.push("Destination Region");
  const dpSlugs = destinationPortSlugsForPhase1(config);
  if (config.destination_region && dpSlugs.length && !config.destination_port) {
    missing.push("Destination Port");
  }
  if (!config.commodity_type) missing.push("Commodity Type");
  if (config.destination_region && !config.route_type) missing.push("Route Type");
  if (!config.check_regime) missing.push("Check Regime");
  if (!config.product_volume_tonnes || config.product_volume_tonnes < 1) {
    missing.push("Product Volume (tonnes)");
  }
  return missing;
}

// ── LEAFLET MAP ───────────────────────────────────────────────
let mapInstance = null;

/** Same `route_type` slug as POST /scenario/predict (direct_gb | landbridge | direct_*). */
function scenarioRouteType(cfg) {
  return cfg.route_type || null;
}

function mapRoutesForScenarioRouteType(routeType) {
  if (!routeType) return MAP_ROUTES;
  if (routeType === "direct_gb") {
    return MAP_ROUTES.filter((r) => r.corridor === "East/West Maritime Corridor");
  }
  if (routeType === "landbridge") {
    return MAP_ROUTES.filter((r) => r.corridor === "Land-bridge Route");
  }
  if (String(routeType).startsWith("direct_")) {
    return MAP_ROUTES.filter((r) => r.corridor === "Direct Route");
  }
  return MAP_ROUTES;
}

function buildMap(containerId, cfg) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (mapInstance) { mapInstance.remove(); mapInstance = null; }

  mapInstance = L.map(container, { zoomControl: true, scrollWheelZoom: false }).setView([52.5, -2.0], 5);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap", opacity: 0.6,
  }).addTo(mapInstance);

  const routeType = cfg ? scenarioRouteType(cfg) : null;
  const visibleRoutes = mapRoutesForScenarioRouteType(routeType);
  const activePorts   = new Set();
  visibleRoutes.forEach(r => { activePorts.add(r.from); activePorts.add(r.to); });

  visibleRoutes.forEach(r => {
    L.polyline([PORT_COORDS[r.from], PORT_COORDS[r.to]], {
      color: r.color, weight: 2, opacity: 0.85, dashArray: r.dash || undefined,
    }).addTo(mapInstance);
  });

  Object.entries(PORT_COORDS).forEach(([name, pos]) => {
    const active = activePorts.size === 0 || activePorts.has(name);
    const sz = active ? 10 : 7;
    const icon = L.divIcon({
      html: `<svg width="${sz+4}" height="${sz+4}" viewBox="0 0 ${sz+4} ${sz+4}">
               <circle cx="${(sz+4)/2}" cy="${(sz+4)/2}" r="${sz/2}" fill="#cc2936" stroke="white" stroke-width="1.5"/>
             </svg>`,
      className: "", iconSize: [sz+4, sz+4], iconAnchor: [(sz+4)/2, (sz+4)/2],
    });
    L.marker(pos, { icon }).addTo(mapInstance).bindPopup(`<b>${name}</b>`);
    const lbl = L.divIcon({
      html: `<div style="font-size:10px;font-weight:600;color:#1a1a2e;white-space:nowrap;text-shadow:1px 1px 2px rgba(255,255,255,.9),-1px -1px 2px rgba(255,255,255,.9)">${name}</div>`,
      className: "", iconSize: [0,0], iconAnchor: [-9, 7],
    });
    L.marker(pos, { icon: lbl, interactive: false }).addTo(mapInstance);
  });

  const allPos = Object.entries(PORT_COORDS)
    .filter(([n]) => activePorts.size === 0 || activePorts.has(n))
    .map(([, p]) => p);
  if (allPos.length > 1) mapInstance.fitBounds(L.latLngBounds(allPos), { padding: [40, 40] });
}

// ── JOURNEY TIMELINE (spec stop-order + OUTPUT border_delay keys) ──
/** KPI groups rendered only in the timeline (not repeated as cards below). */
const TIMELINE_KPI_GROUPS = new Set(["transit", "border_delay"]);

/**
 * Border/wait API keys (`results.border_delay`) — display names from OUTPUT_COLUMN_ORDER
 * (spec §14 semantic outputs; column inventory §6.x in engine spec).
 *
 * Stop → keys (commodity prefix P = AP | Agri | Cat):
 * - Irish Port import: `{P} avg WT on im at D` or `... at R` (Dublin / Rosslare)
 * - Irish Port export: `{P} avg WT on ex at D` or `... at R`
 * - GB West port import (arrival at GB): `{P} avg waiting time on im at {liv|holy|hey|fish|pem}`
 * - GB West port export (departure from GB): `{P} avg waiting time on ex at {short}`
 * - GB East: `Avg waiting time on im at dov` | `Avg waiting time on ex at dov`
 * - EU Port (landbridge): `Avg waiting time on im at cal` | `Avg waiting time on ex at cal`
 */

function commodityForApi(cfg) {
  return cfg.commodity_type || "all_products";
}

function commodityPrefix(commodity) {
  if (commodity === "agri") return "Agri";
  if (commodity === "category") return "Cat";
  return "AP";
}

function directionApiFromPayload(payload, cfg) {
  const d = payload?.direction;
  if (d === "import" || d === "export") return d;
  if (cfg.direction === "import" || cfg.direction === "export") return cfg.direction;
  return "import";
}

function irishPortLetter(irishSlug) {
  return irishSlug === "rosslare" ? "R" : "D";
}

function gbShortFromSlug(slug) {
  const m = { liverpool: "liv", holyhead: "holy", heysham: "hey", fishguard: "fish", pembroke: "pem" };
  return m[slug] || "liv";
}

/** Irish sea leg: Irish slug + GB slug from explicit origin/destination ports. */
function irishAndGbSlugs(cfg) {
  const o = cfg.origin_port;
  const d = cfg.destination_port;
  const irish = IRISH_PORTS.has(o) ? o : IRISH_PORTS.has(d) ? d : "dublin";
  const gbSlug = GB_PORTS.has(o) ? o : GB_PORTS.has(d) ? d : "liverpool";
  return { irishSlug: irish, gbSlug };
}

function transitTimeKey(commodity, direction, routeType) {
  const d = direction;
  const rt = routeType;
  if (rt === "landbridge") {
    return d === "import" ? "Transportation time import from EULB" : "Transportation time exportto EULB";
  }
  if (rt === "direct_cherbourg") {
    return d === "import" ? "Transportation time import from EU che" : "Transportation time exportto EU che";
  }
  if (rt === "direct_rotterdam" || rt === "direct_zeebrugge") {
    return d === "import" ? "Transportation time import from EU ro ze" : "Transportation time exportto EU ro ze";
  }
  if (rt === "direct_bilbao") {
    return d === "import" ? "Transportation time import from EU bil" : "Transportation time exportto EU bil";
  }
  if (commodity === "all_products") {
    return d === "import" ? "Transportation time all P import from GB" : "Transportation time all P exportto GB";
  }
  if (commodity === "agri") {
    return d === "import" ? "Transportation time agri import from GB" : "Transportation time agri exportto GB";
  }
  return d === "import" ? "Transportation time cat import from GB" : "Transportation time cat exportto GB";
}

function pickPrediction(groupObj, keys) {
  if (!groupObj || typeof groupObj !== "object") return null;
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    const pr = groupObj[k];
    if (pr != null && typeof pr === "object") return pr;
  }
  return null;
}

function hoursFromPrediction(pr) {
  if (!pr || pr.value == null || pr.value === undefined) return null;
  const u = (pr.unit || "").toLowerCase();
  let v = Number(pr.value);
  if (Number.isNaN(v)) return null;
  if (u === "minutes" || u === "minute") return v / 60;
  return v;
}

function buildJourneyStops(cfg, payload) {
  const routeType = scenarioRouteType(cfg);
  if (!routeType) return [];

  const dir = directionApiFromPayload(payload, cfg);
  const commodity = commodityForApi(cfg);
  const p = commodityPrefix(commodity);
  const { irishSlug, gbSlug } = irishAndGbSlugs(cfg);
  const ilet = irishPortLetter(irishSlug);
  const gshort = gbShortFromSlug(gbSlug);

  const borderG = payload.results?.border_delay || {};
  const transitG = payload.results?.transit || {};
  const ttKey = transitTimeKey(commodity, dir, routeType);
  const transitHrs = hoursFromPrediction(pickPrediction(transitG, [ttKey]));

  const irishIm = [`${p} avg WT on im at ${ilet}`];
  const irishEx = [`${p} avg WT on ex at ${ilet}`];
  const gbIm = [`${p} avg waiting time on im at ${gshort}`];
  const gbEx = [`${p} avg waiting time on ex at ${gshort}`];
  const euImCal = ["Avg waiting time on im at cal"];
  const euExCal = ["Avg waiting time on ex at cal"];
  const gbEastImDov = ["Avg waiting time on im at dov"];
  const gbEastExDov = ["Avg waiting time on ex at dov"];

  const stops = [];

  if (routeType === "direct_gb") {
    if (dir === "import") {
      stops.push({ kind: "port", label: "GB West port", waitHrs: hoursFromPrediction(pickPrediction(borderG, gbIm)) });
      stops.push({ kind: "ferry", transitHrs, showTransitHours: true });
      stops.push({ kind: "port", label: "Irish Port", waitHrs: hoursFromPrediction(pickPrediction(borderG, irishIm)) });
    } else {
      stops.push({ kind: "port", label: "Irish Port", waitHrs: hoursFromPrediction(pickPrediction(borderG, irishEx)) });
      stops.push({ kind: "ferry", transitHrs, showTransitHours: true });
      stops.push({ kind: "port", label: "GB West port", waitHrs: hoursFromPrediction(pickPrediction(borderG, gbEx)) });
    }
  } else if (routeType === "landbridge") {
    if (dir === "import") {
      stops.push({ kind: "port", label: "EU Port", waitHrs: hoursFromPrediction(pickPrediction(borderG, euImCal)) });
      stops.push({ kind: "port", label: "GB East", waitHrs: hoursFromPrediction(pickPrediction(borderG, gbEastImDov)) });
      stops.push({ kind: "port", label: "GB West", waitHrs: hoursFromPrediction(pickPrediction(borderG, gbIm)) });
      stops.push({ kind: "ferry", transitHrs, showTransitHours: false });
      stops.push({ kind: "port", label: "Irish Port", waitHrs: hoursFromPrediction(pickPrediction(borderG, irishIm)) });
    } else {
      stops.push({ kind: "port", label: "Irish Port", waitHrs: hoursFromPrediction(pickPrediction(borderG, irishEx)) });
      stops.push({ kind: "ferry", transitHrs, showTransitHours: false });
      stops.push({ kind: "port", label: "GB West", waitHrs: hoursFromPrediction(pickPrediction(borderG, gbIm)) });
      stops.push({ kind: "port", label: "GB East", waitHrs: hoursFromPrediction(pickPrediction(borderG, gbEastExDov)) });
      stops.push({ kind: "port", label: "EU Port", waitHrs: hoursFromPrediction(pickPrediction(borderG, euExCal)) });
    }
  } else if (String(routeType).startsWith("direct_")) {
    // EU-side border waits: no separate avg-WT outputs in Phase 1 OUTPUT_COLUMN_ORDER for Cherbourg/Rotterdam/etc.
    if (dir === "import") {
      stops.push({ kind: "port", label: "EU Port", waitHrs: null });
      stops.push({ kind: "ferry", transitHrs, showTransitHours: true });
      stops.push({ kind: "port", label: "Irish Port", waitHrs: hoursFromPrediction(pickPrediction(borderG, irishIm)) });
    } else {
      stops.push({ kind: "port", label: "Irish Port", waitHrs: hoursFromPrediction(pickPrediction(borderG, irishEx)) });
      stops.push({ kind: "ferry", transitHrs, showTransitHours: true });
      stops.push({ kind: "port", label: "EU Port", waitHrs: null });
    }
  }

  return stops;
}

function renderJourneyTimeline(cfg, payload) {
  const stops = buildJourneyStops(cfg, payload);
  if (!stops.length) return null;

  const timelineBox = el("div", { class: "timeline-box" });
  timelineBox.append(el("div", { class: "timeline-label" }, "Journey breakdown"));

  const timelineRow = el("div", { class: "timeline-row" });
  stops.forEach((s, i) => {
    if (i > 0) timelineRow.append(el("div", { class: "timeline-sep" }));
    if (s.kind === "ferry") {
      const f = el("div", { class: "timeline-ferry" });
      f.append(el("span", {}, "🚢"));
      if (s.showTransitHours && s.transitHrs != null) {
        f.append(
          el(
            "span",
            { style: { fontSize: "10px", color: "#2dd4bf", fontWeight: "600" } },
            `${s.transitHrs.toFixed(1)}h`
          )
        );
      }
      timelineRow.append(f);
    } else {
      const stop = el("div", { class: "timeline-stop" });
      stop.append(el("div", { class: "timeline-dot" }));
      stop.append(el("div", { class: "timeline-name" }, s.label));
      if (s.waitHrs != null && s.waitHrs > 0) {
        stop.append(el("div", { class: "timeline-wait" }, `${s.waitHrs.toFixed(1)}h wait`));
      }
      timelineRow.append(stop);
    }
  });
  timelineBox.append(timelineRow);

  const routeType = scenarioRouteType(cfg);
  const dir = directionApiFromPayload(payload, cfg);
  const commodity = commodityForApi(cfg);
  const ttKey = transitTimeKey(commodity, dir, routeType);
  const transitPr = pickPrediction(payload.results?.transit || {}, [ttKey]);
  const totalHrs = hoursFromPrediction(transitPr);

  const timelineTotal = el("div", { class: "timeline-total" });
  timelineTotal.append(
    el("span", {}, "Transportation time (API)"),
    el("span", {}, totalHrs != null ? `${totalHrs.toFixed(1)} hrs` : "—")
  );
  timelineBox.append(timelineTotal);

  return timelineBox;
}

// ── RESULTS PANEL ─────────────────────────────────────────────
function renderResults() {
  const container = document.getElementById("right-content");
  const mapSection = document.getElementById("results-map-section");
  if (mapSection) mapSection.style.display = "none";

  container.innerHTML = "";

  if (!state.hasRun) {
    container.append(EmptyState("📊", "Ready to simulate",
      "Configure your shipment and press Run Simulation to view results.",
      "Run Simulation"
    ));
    return;
  }

  if (state.loading) {
    container.append(
      el("div", { class: "api-loading" },
        el("div", { class: "api-loading-spinner" }),
        el("div", { class: "api-loading-text" }, "Running ML prediction…"),
        el("div", { class: "api-loading-sub" }, "Calling the Brexit ML engine at " + API_ML_BASE)
      )
    );
    return;
  }

  if (state.apiError) {
    const { title, message, kind } = state.apiError;
    const banner = el("div", { class: `api-error-banner api-error-${kind}` });
    banner.append(el("div", { class: "api-error-title" }, title));
    banner.append(el("div", { class: "api-error-message" }, message));
    container.append(banner);
    container.append(EmptyState(
      "⚠️",
      "No results yet",
      "Fix the issue above and run again, or adjust your scenario (Phase 1 supports IRE ↔ GB direct routes).",
      null
    ));
    return;
  }

  const payload = state.lastResult;
  if (!payload || !payload.results) {
    container.append(EmptyState("📊", "No prediction data",
      "Run a simulation to load API results.", null));
    return;
  }

  if (mapSection) mapSection.style.display = "";
  setTimeout(() => buildMap("results-map", state.config), 50);

  const meta = el("div", { class: "api-result-meta" });
  if (payload.corridor) meta.append(el("div", { class: "api-meta-line" }, payload.corridor));
  const bits = [];
  if (payload.model_version) bits.push(`Model ${payload.model_version}`);
  if (payload.overall_confidence) bits.push(`Confidence: ${payload.overall_confidence}`);
  if (bits.length) meta.append(el("div", { class: "api-meta-sub" }, bits.join(" · ")));
  container.append(meta);

  const timelineEl = renderJourneyTimeline(state.config, payload);
  if (timelineEl) container.append(timelineEl);

  let delay = 0.05;
  RESULT_GROUP_ORDER.forEach((groupId) => {
    if (TIMELINE_KPI_GROUPS.has(groupId)) return;
    const groupObj = payload.results[groupId];
    if (!groupObj || typeof groupObj !== "object" || Object.keys(groupObj).length === 0) return;

    const title = RESULT_GROUP_LABELS[groupId] || groupId;
    container.append(el("div", { class: "kpi-section-title" }, title));

    const grid = el("div", { class: "kpi-grid" });
    Object.entries(groupObj).forEach(([kpiName, pr]) => {
      if (!pr || typeof pr !== "object") return;
      grid.append(
        KpiCard({
          icon: iconForGroup(groupId),
          label: kpiName,
          value: formatPredictionValue(pr, groupId),
          unit: displayUnitForPrediction(pr, groupId),
          sub: predictionSub(pr),
          theme: themeForStatus(pr.status),
          delay,
        })
      );
      delay += 0.04;
    });
    container.append(grid);
  });
}

// ── INDICATORS PANEL ──────────────────────────────────────────
function renderIndicators() {
  const container = document.getElementById("right-content");
  container.innerHTML = "";

  const direction = document.getElementById("ind-direction")?.value || "";
  const corridor  = document.getElementById("ind-corridor")?.value || "";
  const dateVal   = document.getElementById("ind-date")?.value || new Date().toISOString().split("T")[0];

  if (!direction) {
    container.append(EmptyState("📈", "Select a direction",
      "Choose Inbound or Outbound above to load the indicators dashboard.", null
    ));
    return;
  }

  const today   = new Date(dateVal + "T12:00:00");
  const dow     = today.getDay();
  const dayFact = [0.55, 0.92, 0.95, 0.90, 0.93, 0.88, 0.60][dow];
  const util    = Math.round(dayFact * 100);

  const corridors = corridor
    ? [corridor]
    : ["East/West Maritime Corridor", "Land-bridge Route", "Direct Route"];

  // ── Section 1: Trade Volumes ──
  const volSection = SectionCard("1 — RoRo Trade Volumes");
  corridors.forEach(c => {
    const ann   = ANNUAL_VOLUMES[c];
    const imp   = Math.round(ann.import  / 365 * dayFact);
    const exp   = Math.round(ann.export  / 365 * dayFact);
    const agriI = Math.round(ann.agriImport / 365 * dayFact);
    const agriE = Math.round(ann.agriExport / 365 * dayFact);
    const labels = {
      "East/West Maritime Corridor":"Ireland ↔ GB",
      "Land-bridge Route":"Ireland ↔ EU (via GB)",
      "Direct Route":"Ireland ↔ EU (Direct)",
    };
    const lbl = el("div", { class: "ind-corridor-label" }, labels[c]);
    volSection.append(lbl);
    volSection.append(UtilBar(util, "Daily traffic vs annual average"));
    if (direction === "import" || direction === "Inbound to Ireland") {
      volSection.append(IndRow("Imports → Ireland", `${imp.toLocaleString()} t`, `of which agri-food: ${agriI.toLocaleString()} t`));
    } else {
      volSection.append(IndRow("Exports from Ireland", `${exp.toLocaleString()} t`, `of which agri-food: ${agriE.toLocaleString()} t`));
    }
  });
  container.append(volSection);

  // ── Section 2: Port Capacities ──
  const capSection = SectionCard("2 — Port Capacities", "blue");
  const ferryRoutes = corridor === "East/West Maritime Corridor"
    ? [ROUTES.HEYSHAM_DUBLIN, ROUTES.HOLYHEAD_DUBLIN, ROUTES.LIVERPOOL_DUBLIN, ROUTES.FISHGUARD_ROSSLARE, ROUTES.PEMBROKE_ROSSLARE]
    : corridor === "Direct Route"
    ? [ROUTES.CHERBOURG_DUBLIN, ROUTES.CHERBOURG_ROSSLARE, ROUTES.ROTTERDAM_DUBLIN, ROUTES.ZEEBRUGGE_DUBLIN]
    : [ROUTES.HOLYHEAD_DUBLIN, ROUTES.CHERBOURG_DUBLIN, ROUTES.ROTTERDAM_DUBLIN];

  const ferryLbl = el("div", { class: "ind-section-title", style:{color:"#93c5fd"} }, "Ferry Daily Capacity");
  capSection.append(ferryLbl);

  ferryRoutes.forEach((r) => {
    const cap = FERRY_CAPACITY[r];
    const sail = SAILINGS_PER_DAY[r];
    if (cap == null || sail == null) return;
    const loadFactor = Math.min(Math.round(dayFact * 0.7 * 100), 99);
    capSection.append(
      IndRow(ROUTE_DISPLAY[r] || r, `${(cap * sail).toLocaleString()} trailers/day`, `${sail} sailing${sail > 1 ? "s" : ""} × ${cap} trailers`),
      UtilBar(loadFactor, "Estimated load factor")
    );
  });

  const portsToShow = corridor ? (CORRIDOR_PORTS[corridor] || []) : [];
  portsToShow.slice(0, 4).forEach(port => {
    const cap  = PORT_CAPACITY[port]; if (!cap) return;
    const util2 = Math.min(Math.round(dayFact * 85), 99);
    const card  = el("div", { class: "port-card" });
    card.append(el("div", { class: "port-card-name" }, `${port} Port`));
    const grid2 = el("div", { class: "port-grid" });
    grid2.innerHTML = `<span>Customs: <strong>${cap.customs} officers</strong></span>
      <span>DAFM: <strong>${cap.dafm} officers</strong></span>
      <span>Security: <strong>${cap.security} officers</strong></span>
      <span>Tractors: <strong>${cap.tractors}</strong></span>`;
    card.append(grid2, UtilBar(util2, "Est. officer utilisation"));
    capSection.append(card);
  });
  container.append(capSection);

  // ── Section 3: Check Costs ──
  if (portsToShow.length > 0) {
    const costSection = SectionCard("3 — Cost for Official Checks", "amber");
    portsToShow.slice(0, 3).forEach(port => {
      const costs = CHECK_COSTS_BY_PORT[port] || { documentary:50, physical:500 };
      const trucks = Math.round(
        (ANNUAL_VOLUMES[corridor || "East/West Maritime Corridor"]?.import || 6330240)
        / 365 * dayFact / (CORRIDOR_PORTS[corridor || "East/West Maritime Corridor"]?.length || 4) / 25
      );
      const total = Math.round(trucks * costs.documentary + trucks * 0.15 * costs.physical);
      const card = el("div", { class: "cost-card" });
      const hdr  = el("div", { class: "cost-header" });
      hdr.append(
        el("div", { class: "cost-port" }, `${port} Port`),
        el("div", { class: "cost-total" }, `€${total.toLocaleString()} `, el("span", {}, "est. today"))
      );
      const cgrid = el("div", { class: "cost-grid" });
      [["Documentary", costs.documentary], ["Physical", costs.physical]].forEach(([lbl, val]) => {
        const item = el("div", { class: "cost-item" });
        item.innerHTML = `<div class="cost-item-label">${lbl}</div><div class="cost-item-val">€${val}</div><div class="cost-item-sub">/truck</div>`;
        cgrid.append(item);
      });
      card.append(hdr, cgrid);
      costSection.append(card);
    });
    container.append(costSection);
  }

  // ── Section 4: Truck Mix ──
  if (corridor) {
    const mix     = TRUCK_MIX[corridor] || { unaccompanied: 47, accompanied: 53 };
    const mixSec  = SectionCard("4 — Type of Trucks");
    const mixGrid = el("div", { class: "mix-grid" });
    const unacc   = el("div", { class: "mix-card" });
    unacc.innerHTML = `<div class="mix-pct">${mix.unaccompanied}%</div><div class="mix-label">Unaccompanied</div>`;
    const acc = el("div", { class: "mix-card" });
    acc.innerHTML = `<div class="mix-pct grey">${mix.accompanied}%</div><div class="mix-label">Accompanied</div>`;
    mixGrid.append(unacc, acc);
    mixSec.append(mixGrid, UtilBar(mix.unaccompanied, "Unaccompanied share"), UtilBar(mix.accompanied, "Accompanied share"));
    container.append(mixSec);
  }
}

function syncConfigWithOptions() {
  const cfg = state.config;
  const vo = effectiveValidOptions();

  const supplierSlugs = Array.isArray(vo.supplier_region)
    ? vo.supplier_region
    : FALLBACK_VALID_OPTIONS.supplier_region;
  if (cfg.supplier_region && !supplierSlugs.includes(cfg.supplier_region)) {
    cfg.supplier_region = "";
    cfg.origin_port = "";
    cfg.destination_port = "";
    cfg.route_type = "";
  }

  const originByRegion =
    vo.origin_port && typeof vo.origin_port === "object"
      ? vo.origin_port
      : FALLBACK_VALID_OPTIONS.origin_port;
  const originPortSlugs =
    cfg.supplier_region && Array.isArray(originByRegion[cfg.supplier_region])
      ? originByRegion[cfg.supplier_region]
      : [];
  if (cfg.origin_port && !originPortSlugs.includes(cfg.origin_port)) {
    cfg.origin_port = "";
    cfg.destination_port = "";
    cfg.route_type = "";
  }

  const dirOpts = directionOptionsForSupplier(vo, cfg.supplier_region);
  const allowedDir = new Set(dirOpts.map((o) => o.value));
  if (cfg.direction && !allowedDir.has(cfg.direction)) {
    cfg.direction = "";
    cfg.destination_region = "";
    cfg.destination_port = "";
    cfg.route_type = "";
  }

  const drOpts = destinationRegionSlugsForPhase1(cfg);
  if (cfg.destination_region && !drOpts.includes(cfg.destination_region)) {
    cfg.destination_region = "";
    cfg.destination_port = "";
    cfg.route_type = "";
  }
  if (drOpts.length === 1) cfg.destination_region = drOpts[0];

  const dpSlugs = destinationPortSlugsForPhase1(cfg);
  if (cfg.destination_port && !dpSlugs.includes(cfg.destination_port)) {
    cfg.destination_port = "";
    cfg.route_type = "";
  }

  const rtOpts = routeTypeSelectOptions(vo, cfg.destination_region).filter((o) => !o.disabled);
  const rtAllowed = new Set(rtOpts.map((o) => o.value));
  if (cfg.route_type && !rtAllowed.has(cfg.route_type)) cfg.route_type = "";
  if (cfg.destination_region && !cfg.route_type) {
    if (rtOpts.length === 1) cfg.route_type = rtOpts[0].value;
    else cfg.route_type = "direct_gb";
  }

  const commoditySlugs = Array.isArray(vo.commodity_type)
    ? vo.commodity_type
    : FALLBACK_VALID_OPTIONS.commodity_type;
  if (cfg.commodity_type && !commoditySlugs.includes(cfg.commodity_type)) {
    cfg.commodity_type = "";
  }

  const regimeSlugs = Array.isArray(vo.check_regime)
    ? vo.check_regime
    : FALLBACK_VALID_OPTIONS.check_regime;
  if (!regimeSlugs.includes(cfg.check_regime)) {
    cfg.check_regime = regimeSlugs.includes("standard")
      ? "standard"
      : regimeSlugs[0] || "standard";
  }
}

function scheduleDebouncedPredict() {
  if (!state.hasRun || state.loading) return;
  clearTimeout(debouncedPredictTimer);
  debouncedPredictTimer = setTimeout(() => {
    debouncedPredictTimer = null;
    if (!state.hasRun || state.loading) return;
    if (getMissingFields(state.config).length > 0) return;
    void runSim();
  }, 300);
}

/** Fields that only need footer / hint updates — not a full form rebuild (preserves focus while typing). */
const LAZY_FORM_FIELDS = new Set([
  "notes",
  "product_volume_tonnes",
  "shelf_life_days",
  "customs_officers",
  "dafm_officers",
  "security_officers",
  "tractors",
  "unaccompanied_pct",
]);

function updateVolumeHintFromState() {
  const hintEl = document.getElementById("f-volume-hint");
  if (!hintEl) return;
  const t = Number(state.config.product_volume_tonnes);
  hintEl.textContent =
    Number.isFinite(t) && t >= 1 ? `≈ ${Math.round(t / 25).toLocaleString()} trucks` : "";
}

function renderFormFooter() {
  const cfg = state.config;
  const missing = getMissingFields(cfg);
  const canRun = missing.length === 0 && !state.loading;
  const footer = document.getElementById("form-footer");
  if (!footer) return;
  footer.innerHTML = "";
  const runAttrs = {
    class: `btn-run ${canRun ? "ready" : "disabled"}`,
    disabled: !canRun,
  };
  if (canRun) runAttrs.onclick = () => { void runSim(); };
  const runBtn = el("button", runAttrs, state.loading ? "⏳  Running…" : "▶  Run Simulation");
  footer.append(runBtn);
  if (!canRun) footer.append(el("div", { class: "error-hint" }, `Missing: ${missing.join(", ")}`));
  if (state.hasRun) {
    footer.append(el("button", { class: "btn-reset", onclick: resetSim }, "↺  Reset"));
  }
}

function applyLazyFormField(field, value) {
  state.config[field] = value;
  updateVolumeHintFromState();
  renderFormFooter();
  if (!state.hasRun || field === "notes") return;
  if (getMissingFields(state.config).length === 0) scheduleDebouncedPredict();
  else renderResults();
}

// ── PRODUCT INPUT FORM ────────────────────────────────────────
function buildInputForm() {
  const form = document.getElementById("form-body");
  form.innerHTML = "";

  syncConfigWithOptions();
  const cfg = state.config;
  const vo = effectiveValidOptions();

  const supplierSlugs = Array.isArray(vo.supplier_region)
    ? vo.supplier_region
    : FALLBACK_VALID_OPTIONS.supplier_region;
  const originByRegion =
    vo.origin_port && typeof vo.origin_port === "object"
      ? vo.origin_port
      : FALLBACK_VALID_OPTIONS.origin_port;
  const originPortSlugs =
    cfg.supplier_region && Array.isArray(originByRegion[cfg.supplier_region])
      ? originByRegion[cfg.supplier_region]
      : [];
  const dirOpts = directionOptionsForSupplier(vo, cfg.supplier_region);
  const drOpts = destinationRegionSlugsForPhase1(cfg);
  const dpSlugs = destinationPortSlugsForPhase1(cfg);
  const commoditySlugs = Array.isArray(vo.commodity_type)
    ? vo.commodity_type
    : FALLBACK_VALID_OPTIONS.commodity_type;
  const regimeSlugs = Array.isArray(vo.check_regime)
    ? vo.check_regime
    : FALLBACK_VALID_OPTIONS.check_regime;
  const rtSelectOpts = routeTypeSelectOptions(vo, cfg.destination_region);

  form.append(
    DateField({
      id: "f-date",
      label: "📅 Shipment Date",
      value: cfg.shipmentDate,
      max: new Date().toISOString().split("T")[0],
      onChange: (v) => update("shipmentDate", v),
    })
  );

  form.append(
    SelectField({
      id: "f-supplier-region",
      label: "🌍 Supplier Region",
      required: true,
      options: supplierSlugs.map((slug) => ({
        value: slug,
        label: `${supplierRegionLabel(slug)}${slug === "eu" ? " (Phase 2)" : ""}`,
        disabled: slug === "eu",
      })),
      value: cfg.supplier_region,
      placeholder: "Select region",
      onChange: (v) => {
        applyFormChange("supplier_region", v);
      },
    })
  );

  if (cfg.supplier_region && cfg.supplier_region !== "eu") {
    form.append(
      SelectField({
        id: "f-origin-port",
        label: "⚓ Origin Port",
        required: true,
        options: originPortSlugs.map((slug) => ({ value: slug, label: portSlugLabel(slug) })),
        value: cfg.origin_port,
        placeholder: "Select origin port",
        onChange: (v) => applyFormChange("origin_port", v),
      })
    );
  }

  if (cfg.supplier_region && cfg.origin_port) {
    form.append(
      SelectField({
        id: "f-direction",
        label: "↔ Direction",
        required: true,
        options: dirOpts,
        value: cfg.direction,
        placeholder: "Select direction",
        onChange: (v) => applyFormChange("direction", v),
      })
    );
  }

  if (cfg.direction && drOpts.length) {
    form.append(
      SelectField({
        id: "f-destination-region",
        label: "🎯 Destination Region",
        required: true,
        options: drOpts.map((slug) => ({ value: slug, label: destinationRegionLabel(slug) })),
        value: cfg.destination_region,
        placeholder: "Select destination region",
        onChange: (v) => applyFormChange("destination_region", v),
      })
    );
  }

  if (cfg.destination_region && dpSlugs.length) {
    form.append(
      SelectField({
        id: "f-destination-port",
        label: "🏁 Destination Port",
        required: true,
        options: dpSlugs.map((slug) => ({ value: slug, label: portSlugLabel(slug) })),
        value: cfg.destination_port,
        placeholder: "Select destination port",
        onChange: (v) => applyFormChange("destination_port", v),
      })
    );
  }

  form.append(
    SelectField({
      id: "f-commodity",
      label: "📦 Commodity Type",
      required: true,
      options: commoditySlugs.map((slug) => ({
        value: slug,
        label: `${COMMODITY_ICONS[slug] || "📦"} ${commodityLabel(slug)}`,
      })),
      value: cfg.commodity_type,
      placeholder: "Select commodity type",
      onChange: (v) => applyFormChange("commodity_type", v),
    })
  );

  if (cfg.destination_region) {
    form.append(
      SelectField({
        id: "f-route-type",
        label: "🗺 Route Type",
        required: true,
        options: rtSelectOpts,
        value: cfg.route_type,
        placeholder: "Select route type",
        onChange: (v) => applyFormChange("route_type", v),
      })
    );
  }

  form.append(
    SelectField({
      id: "f-check-regime",
      label: "🛂 Border Check Regime",
      required: true,
      options: regimeSlugs.map((slug) => ({ value: slug, label: checkRegimeLabel(slug) })),
      value: cfg.check_regime,
      placeholder: "Select regime",
      onChange: (v) => applyFormChange("check_regime", v),
    })
  );

  const vol = cfg.product_volume_tonnes > 0 ? cfg.product_volume_tonnes : "";
  const volHint =
    vol !== "" && vol >= 1 ? `≈ ${Math.round(Number(vol) / 25).toLocaleString()} trucks` : null;
  const { wrap: volWrap } = NumberField({
    id: "f-volume",
    label: "📦 Product Volume (tonnes)",
    required: true,
    value: vol,
    placeholder: "e.g. 100",
    min: 1,
    usePlainText: true,
    onChange: (v) => applyFormChange("product_volume_tonnes", v),
    hint: volHint,
  });
  form.append(volWrap);

  const { wrap: shelfWrap } = NumberField({
    id: "f-shelf",
    label: "⏳ Shelf Life (Days)",
    value: cfg.shelf_life_days > 0 ? cfg.shelf_life_days : "",
    placeholder: "Optional — default 14 days in API",
    min: 0,
    nullable: true,
    onChange: (v) => applyFormChange("shelf_life_days", v == null || v === 0 ? 0 : v),
  });
  form.append(shelfWrap);

  const advHead = el("div", { class: "form-field" });
  const advBtn = el(
    "button",
    {
      type: "button",
      class: "btn-reset",
      style: { width: "100%" },
      onclick: () => {
        state.advancedOpen = !state.advancedOpen;
        buildInputForm();
        if (state.hasRun) scheduleDebouncedPredict();
      },
    },
    state.advancedOpen ? "▼ Hide advanced options" : "▶ Advanced options"
  );
  advHead.append(advBtn);
  form.append(advHead);

  if (state.advancedOpen) {
    const uPct =
      cfg.unaccompanied_pct != null ? Math.round(cfg.unaccompanied_pct * 100) : "";
    form.append(
      NumberField({
        id: "f-customs",
        label: "👮 Customs Officers",
        value: cfg.customs_officers != null ? cfg.customs_officers : "",
        placeholder: "Default: 10",
        min: 0,
        nullable: true,
        onChange: (v) => applyFormChange("customs_officers", v),
      }).wrap
    );
    form.append(
      NumberField({
        id: "f-dafm",
        label: "🏥 DAFM Officers",
        value: cfg.dafm_officers != null ? cfg.dafm_officers : "",
        placeholder: "Default: 10",
        min: 0,
        nullable: true,
        onChange: (v) => applyFormChange("dafm_officers", v),
      }).wrap
    );
    form.append(
      NumberField({
        id: "f-security",
        label: "🔒 Security Officers",
        value: cfg.security_officers != null ? cfg.security_officers : "",
        placeholder: "Default: 10",
        min: 0,
        nullable: true,
        onChange: (v) => applyFormChange("security_officers", v),
      }).wrap
    );
    form.append(
      NumberField({
        id: "f-tractors",
        label: "🚜 Tractors",
        value: cfg.tractors != null ? cfg.tractors : "",
        placeholder: "Default: 20",
        min: 0,
        nullable: true,
        onChange: (v) => applyFormChange("tractors", v),
      }).wrap
    );
    form.append(
      NumberField({
        id: "f-unacc",
        label: "% Unaccompanied",
        value: uPct,
        placeholder: "Default: 50%",
        min: 0,
        max: 100,
        nullable: true,
        onChange: (v) =>
          applyFormChange(
            "unaccompanied_pct",
            v == null ? null : Math.min(100, Math.max(0, v)) / 100
          ),
      }).wrap
    );
  }

  const notesWrap = el("div", { class: "form-field" });
  notesWrap.append(el("label", { class: "form-label", for: "f-notes" }, "📝 Additional Notes"));
  const textarea = el("textarea", { id: "f-notes", placeholder: "Special handling requirements..." });
  textarea.value = cfg.notes || "";
  textarea.addEventListener("input", () => applyFormChange("notes", textarea.value));
  notesWrap.append(textarea);
  form.append(notesWrap);

  renderFormFooter();
}

function applyFormChange(field, value) {
  const c = state.config;
  if (LAZY_FORM_FIELDS.has(field)) {
    applyLazyFormField(field, value);
    return;
  }
  if (field === "supplier_region") {
    c.supplier_region = value;
    c.origin_port = "";
    c.destination_port = "";
    c.route_type = "";
  } else if (field === "direction") {
    c.direction = value;
    c.destination_region = "";
    c.destination_port = "";
    c.route_type = "";
  } else if (field === "destination_region") {
    c.destination_region = value;
    c.destination_port = "";
    c.route_type = "";
  } else if (field === "destination_port") {
    c.destination_port = value;
    c.route_type = "";
  } else if (field === "origin_port") {
    c.origin_port = value;
    c.destination_port = "";
    c.route_type = "";
  } else {
    c[field] = value;
  }
  buildInputForm();
  if (state.hasRun) {
    if (getMissingFields(state.config).length === 0) scheduleDebouncedPredict();
    else renderResults();
  }
}

// ── STATE UPDATES ─────────────────────────────────────────────
function update(field, value) {
  state.config[field] = value;
  buildInputForm();
  if (state.hasRun) {
    if (getMissingFields(state.config).length === 0) scheduleDebouncedPredict();
    else renderResults();
  }
}

async function runSim() {
  clearTimeout(debouncedPredictTimer);
  debouncedPredictTimer = null;
  state.hasRun = true;
  state.loading = true;
  state.apiError = null;
  state.lastResult = null;
  state.activeView = "results";

  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === "results");
  });
  buildInputForm();
  renderResults();

  const url = `${API_ML_BASE.replace(/\/$/, "")}/scenario/predict`;
  const requestBody = buildScenarioRequest(state.config);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });

    let data = {};
    try {
      data = await response.json();
    } catch {
      data = {};
    }

    if (!response.ok) {
      const rawDetail = data.detail;
      const detailStr =
        (typeof rawDetail === "string" && rawDetail) ||
        (Array.isArray(rawDetail) && rawDetail.map((e) => (typeof e === "string" ? e : JSON.stringify(e))).join("; ")) ||
        (rawDetail != null && typeof rawDetail === "object" ? JSON.stringify(rawDetail) : "") ||
        (Array.isArray(data.errors) && data.errors.join("; ")) ||
        (typeof data.error === "string" && data.error) ||
        response.statusText ||
        "Request failed";

      if (response.status === 400) {
        state.apiError = {
          kind: "400",
          title: "Invalid scenario (400)",
          message: detailStr,
        };
      } else if (response.status === 503) {
        state.apiError = {
          kind: "503",
          title: "Models not ready (503)",
          message: detailStr,
        };
      } else {
        state.apiError = {
          kind: "http",
          title: `Error ${response.status}`,
          message: detailStr,
        };
      }
      state.lastResult = null;
    } else {
      state.lastResult = data;
      state.apiError = null;
    }
  } catch {
    state.apiError = {
      kind: "network",
      title: "Cannot reach the ML API",
      message:
        "The browser could not complete the request. Start the API (for example uvicorn on port 8000), check the URL, and if this page is opened as a file or on another host, enable CORS or serve the UI through a proxy.",
    };
    state.lastResult = null;
  } finally {
    state.loading = false;
    buildInputForm();
    renderResults();
  }
}

function resetSim() {
  clearTimeout(debouncedPredictTimer);
  debouncedPredictTimer = null;
  state.config = {
    supplier_region: "",
    origin_port: "",
    destination_region: "",
    destination_port: "",
    commodity_type: "",
    direction: "",
    product_volume_tonnes: 0,
    route_type: "",
    check_regime: "standard",
    shelf_life_days: 0,
    customs_officers: null,
    dafm_officers: null,
    security_officers: null,
    tractors: null,
    unaccompanied_pct: null,
    shipmentDate: new Date().toISOString().split("T")[0],
    notes: "",
  };
  state.advancedOpen = false;
  state.hasRun = false;
  state.loading = false;
  state.lastResult = null;
  state.apiError = null;
  buildInputForm();
  renderResults();
}

// ── TABS ──────────────────────────────────────────────────────
function setActiveTab(view) {
  state.activeView = view;
  document.querySelectorAll(".tab-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.view === view);
  });

  if (view === "results") {
    renderResults();
  } else {
    renderIndicatorsWithFilters();
  }
}

function renderIndicatorsWithFilters() {
  const mapSection = document.getElementById("results-map-section");
  if (mapSection) mapSection.style.display = "none";

  const right = document.getElementById("right-content");
  right.innerHTML = "";

  renderIndicators();
}

// ── CHATBOT ───────────────────────────────────────────────────
const CHAT_ANSWERS = {
  east:     "The **East/West Maritime Corridor** connects Ireland and Great Britain. Key routes: Holyhead–Dublin (3.25h, 4 sailings/day), Heysham–Dublin (3.5h), Liverpool–Dublin (8h). These are the most frequent services.",
  land:     "The **Land-bridge Route** transits through Great Britain (~18 hours total). Since Brexit it faces additional UK customs checks at both entry and exit points, adding significant delays especially for agri-food.",
  direct:   "**Direct Routes** to EU ports (Cherbourg, Rotterdam, Zeebrugge) bypass the UK entirely. Crossings range from 17–28 hours but avoid UK border friction post-Brexit.",
  shelf:    "**Shelf life** matters most for perishables. Fish (3 days), fresh meat (5 days), and plants (7 days) are most sensitive. A Rotterdam–Dublin crossing (28h) uses over a full day before customs even begins.",
  cost:     "**Official check costs** range from ~€150/truck (East/West) to ~€320/truck (Land-bridge). Agri-food products face a ~40% surcharge due to mandatory SPS inspections.",
  sps:      "**SPS (Sanitary & Phytosanitary) checks** apply to agri-food goods and multiply check times by 2.5×. This means a 5-minute customs check becomes 12+ minutes for animals or fish.",
  queue:    "**Queue lengths** depend on truck arrival rate versus officer capacity. The simulator uses a Pollaczek-Khinchine queuing formula. Adding more officers (in data.js) directly reduces queue estimates.",
  officer:  "**Officer numbers** are set in data.js under OFFICERS. Currently 10 customs and 10 DAFM officers per port. Increasing these values will reduce simulated wait times.",
};

let chatOpen = false;

function buildChatbot() {
  const toggle = el("button", { class: "chat-toggle", onclick: toggleChat }, "💬");
  let panel = document.getElementById("chat-panel");
  if (!panel) {
    panel = el("div", { class: "chat-panel", id: "chat-panel", style: { display: "none" } });
    document.body.append(panel);
  } else {
    panel.innerHTML = "";
    panel.className = "chat-panel";
    panel.style.display = "none";
  }

  const header = el("div", { class: "chat-header" });
  header.append(
    el("div", { class: "chat-avatar" }, "🤖"),
    el("div", {},
      el("div", { class: "chat-header-name" }, "Route Advisor"),
      el("div", { class: "chat-header-sub" }, "Ask about RoRo routes & logistics")
    )
  );

  const messages = el("div", { class: "chat-messages", id: "chat-messages" });
  addBotMessage(messages, "Hello! I'm your RoRo route advisor. Ask me about routes, costs, SPS checks, shelf life, or queues.\n\n*Try: 'Tell me about the direct route' or 'What are SPS checks?'*");

  const inputRow = el("div", { class: "chat-input-row" });
  const inp      = el("input", { type: "text", placeholder: "Ask about routes...", id: "chat-input" });
  const sendBtn  = el("button", { class: "chat-send", id: "chat-send", onclick: () => sendChat(messages, inp) }, "➤");
  inp.addEventListener("keydown", e => { if (e.key === "Enter") sendChat(messages, inp); });
  inputRow.append(inp, sendBtn);

  panel.append(header, messages, inputRow);
  document.body.append(toggle);
  if (!document.body.contains(panel)) document.body.append(panel);
}

function toggleChat() {
  chatOpen = !chatOpen;
  document.getElementById("chat-panel").style.display = chatOpen ? "flex" : "none";
}

function addBotMessage(container, text) {
  const wrap = el("div", { class: "chat-msg" });
  const ico  = el("div", { class: "chat-bot-icon" }, "🤖");
  const bbl  = el("div", { class: "chat-bubble bot" });
  // Simple markdown: **bold** and *italic*
  bbl.innerHTML = text
    .split("\n")
    .map(l => `<p>${l.replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>").replace(/\*(.*?)\*/g,"<em>$1</em>")}</p>`)
    .join("");
  wrap.append(ico, bbl);
  container.append(wrap);
  container.scrollTop = container.scrollHeight;
}

function sendChat(messages, inp) {
  const text = inp.value.trim(); if (!text) return;
  inp.value = "";

  // User bubble
  const userWrap = el("div", { class: "chat-msg user" });
  const userBbl  = el("div", { class: "chat-bubble user" }, text);
  userWrap.append(userBbl);
  messages.append(userWrap);

  // Typing indicator
  const typingWrap = el("div", { class: "chat-msg" });
  const typingIco  = el("div", { class: "chat-bot-icon" }, "🤖");
  const typingBbl  = el("div", { class: "chat-bubble bot" });
  typingBbl.innerHTML = `<div class="typing-dots"><span></span><span></span><span></span></div>`;
  typingWrap.append(typingIco, typingBbl);
  messages.append(typingWrap);
  messages.scrollTop = messages.scrollHeight;

  setTimeout(() => {
    messages.removeChild(typingWrap);
    const lower = text.toLowerCase();
    const key   = Object.keys(CHAT_ANSWERS).find(k => lower.includes(k));
    const reply = key
      ? CHAT_ANSWERS[key]
      : `I can help with: **East/West routes**, **Land-bridge**, **Direct routes**, **shelf life**, **costs**, **SPS checks**, **queues**, and **officers**.\n\nWhat would you like to know?`;
    addBotMessage(messages, reply);
  }, 700);
}

// ── INDICATORS FILTER BAR ─────────────────────────────────────
function buildIndicatorFilters() {
  const bar = document.getElementById("ind-filter-bar");
  bar.innerHTML = "";

  bar.append(el("label", {}, "🔍 Filters"));

  const vo = effectiveValidOptions();
  const dirOpts = directionSelectOptionsApi(vo);

  const dirSel = el("select", { id: "ind-direction" });
  dirSel.append(el("option", { value: "" }, "All Directions"));
  dirOpts.forEach((o) => {
    const short = o.value === "import" ? "Inbound" : o.value === "export" ? "Outbound" : o.label;
    dirSel.append(el("option", { value: o.value }, short));
  });
  dirSel.addEventListener("change", () => renderIndicators());
  bar.append(dirSel);

  const corrSel = el("select", { id: "ind-corridor" });
  corrSel.append(el("option", { value: "" }, "All Corridors"));
  const corridorShort = {
    "East/West Maritime Corridor": "East/West",
    "Land-bridge Route": "Land-bridge",
    "Direct Route": "Direct",
  };
  INDICATOR_CORRIDORS.forEach((c) => {
    corrSel.append(el("option", { value: c }, corridorShort[c] || c));
  });
  corrSel.addEventListener("change", () => renderIndicators());
  bar.append(corrSel);

  const dateInp = el("input", { id:"ind-date", type:"date",
    value: new Date().toISOString().split("T")[0],
    max:   new Date().toISOString().split("T")[0],
  });
  dateInp.addEventListener("change", () => renderIndicators());
  bar.append(dateInp);
}

// ── BOOT ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => setActiveTab(btn.dataset.view));
  });

  void (async () => {
    await loadScenarioOptions();
    buildInputForm();
    renderResults();
    buildIndicatorFilters();
    buildChatbot();
  })();
});
