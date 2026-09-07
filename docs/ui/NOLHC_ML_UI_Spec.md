# NOLHC ML Engine — UI Development Specification

**Version:** 1.0  
**Predecessor UI:** `Brexit_ML_UI_Spec.md` (superseded for input/output layer — design system and layout unchanged)  
**API base URL:** `http://localhost:8000`  
**Primary endpoint:** `POST /predict`  
**UI architecture:** Vanilla JS ES Modules — `index.html` + `app.js` + `components/components.js` + `styles/styles.css` + `data/data.js`  
**Map library:** Leaflet.js 1.9.4 (OpenStreetMap tiles)  
**Scope:** NOLHC dataset — 35 input parameters → 20 KPI outputs across 4 output categories

---

## Table of Contents

1. [What Changes vs the Brexit UI](#1-what-changes-vs-the-brexit-ui)
2. [Design System — Unchanged](#2-design-system--unchanged)
3. [Left Panel — Input Form Rebuild](#3-left-panel--input-form-rebuild)
4. [Tooltip System — New Requirement](#4-tooltip-system--new-requirement)
5. [Right Panel — Output KPI Cards Rebuild](#5-right-panel--output-kpi-cards-rebuild)
6. [Journey Map — Simplified](#6-journey-map--simplified)
7. [Indicators Tab — Updated Sections](#7-indicators-tab--updated-sections)
8. [API Integration Changes](#8-api-integration-changes)
9. [Application State Changes](#9-application-state-changes)
10. [data.js Changes](#10-datajs-changes)
11. [Chatbot Updates](#11-chatbot-updates)
12. [Cursor Implementation Checklist](#12-cursor-implementation-checklist)

---

## 1. What Changes vs the Brexit UI

This section is the quick-reference diff. Read it first before the detailed sections.

### What stays exactly the same

| Element | Status |
|---|---|
| Design system (colours, typography, CSS variables) | ✅ Unchanged |
| Overall layout: header + left panel + right panel | ✅ Unchanged |
| Tab bar: Results ↔ Indicators | ✅ Unchanged |
| KPI card component, UtilBar, DeltaBadge, SectionCard, IndRow | ✅ Unchanged |
| Chatbot panel structure (FAB, panel, header, bubbles) | ✅ Unchanged — keywords updated only |
| Animations, scrollbar styling, responsive breakpoint | ✅ Unchanged |
| Leaflet map with port markers and route lines | ✅ Unchanged structure — routes simplified |
| All HTML IDs in `index.html` | ✅ Unchanged |

### What changes

| Element | Change |
|---|---|
| Left panel header subtitle | New text |
| All form fields | Completely replaced — 4 collapsible factor groups replace the route/port/regime selects |
| Tooltip on every field | **New requirement** — info icon + hover tooltip on all inputs and all output KPIs |
| API endpoint | Changed from `POST /scenario/predict` to `POST /predict` |
| Request body | 35 numeric parameters instead of semantic fields |
| Response body | 20 flat KPI slugs instead of grouped semantic response |
| Output KPI cards | Reorganised into 4 categories with new labels, units, and API key mapping |
| Results panel section structure | 4 category sections instead of mixed groups |
| `data.js` | Replace scenario data with NOLHC parameter definitions and KPI metadata |
| Indicators tab sections 1–4 | Content updated to match NOLHC factors and KPIs |
| Chatbot keyword map | Updated to NOLHC terminology |

---

## 2. Design System — Unchanged

All CSS variables, typography, spacing, radii, colour themes, and animation keyframes from the Brexit UI spec (Section 1) remain **identical**. Do not change `styles/styles.css` for any design token.

The only CSS changes permitted are:
- Adding `.tooltip-wrap`, `.tooltip-icon`, `.tooltip-popup` classes (Section 4)
- Adding `.factor-group`, `.factor-group-header`, `.factor-group-body` for collapsible sections (Section 3.2)

---

## 3. Left Panel — Input Form Rebuild

### 3.1 Panel Header

| Element | New value |
|---|---|
| `h2` | `Simulation Parameters` |
| `p` subtitle | `Configure the 4 factor groups for prediction` |

### 3.2 Form Structure — 4 Collapsible Factor Groups

The Brexit form's cascading select fields are **replaced** with 4 collapsible accordion groups, one per NOLHC experimental factor. All 35 input parameters are distributed across these groups.

Each group renders as:

```
┌─────────────────────────────────────────────────┐
│  ▼  Factor Name                     [N params]  │  ← .factor-group-header (click to toggle)
├─────────────────────────────────────────────────┤
│  [field]  label  [ℹ]   [_________ input ______] │
│  [field]  label  [ℹ]   [_________ input ______] │
│  ...                                            │
└─────────────────────────────────────────────────┘
```

#### Collapsible group CSS

```css
.factor-group {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  margin-bottom: 10px;
  overflow: hidden;
}
.factor-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(30,41,59,0.5);
  cursor: pointer;
  user-select: none;
  font: 600 12px #E2E8F0;
}
.factor-group-header:hover {
  background: rgba(51,65,85,0.5);
}
.factor-group-chevron {
  font-size: 10px;
  color: #64748B;
  transition: transform 0.2s;
}
.factor-group.open .factor-group-chevron {
  transform: rotate(180deg);
}
.factor-group-badge {
  font: 400 10px #64748B;
  background: rgba(51,65,85,0.6);
  padding: 2px 7px;
  border-radius: 999px;
}
.factor-group-body {
  padding: 10px 14px 14px;
  display: none;
  flex-direction: column;
  gap: 10px;
  background: rgba(15,23,42,0.3);
}
.factor-group.open .factor-group-body {
  display: flex;
}
```

Default state: **Group 1 open**, Groups 2–4 collapsed.

### 3.3 Factor Group 1 — Shifts in Trade Volume

**Header:** `📦 Shifts in Trade Volume` · badge: `4 params`  
**Description tooltip on header:** `Import and export volumes of Agri and Non-Agri products between GB and Ireland`

| # | Field ID | Label | Tooltip description | Unit | Min | Default |
|---|---|---|---|---|---|---|
| 1 | `f-na-im` | Non-Agri Import Volume | Demand of inbound non-agri products arriving from GB to Ireland. Increasing this raises pressure on Irish port customs and DAFM resources. | tonnes | 1 | 6,140,333 |
| 2 | `f-na-ex` | Non-Agri Export Volume | Demand of outbound non-agri products leaving Ireland to GB. Affects waiting times at UK-side ports. | tonnes | 1 | 5,387,458 |
| 3 | `f-a-im` | Agri Import Volume | Demand of inbound agri-food products from GB to Ireland. Agri products face SPS checks — higher volumes increase DAFM bay utilisation significantly. | tonnes | 1 | 2,826,920 |
| 4 | `f-a-ex` | Agri Export Volume | Demand of outbound agri-food products from Ireland to GB. Affects outbound SPS check queues at Irish ports. | tonnes | 1 | 2,111,499 |

All 4 fields: `NumberField`, required, comma-formatted hint showing approx truck count (`≈ ${Math.round(value/25).toLocaleString()} trucks`).

### 3.4 Factor Group 2 — Direct Routes to Mainland Europe

**Header:** `🚢 Direct Routes to Mainland Europe` · badge: `17 params`  
**Description tooltip on header:** `Volume shifts between Landbridge and Direct routes, plus vessel capacities on each GB and EU route`

#### Sub-section A: Volume shifts (8 fields)

| # | Field ID | Label | Tooltip description | Unit |
|---|---|---|---|---|
| 5 | `f-naim-lb` | Non-Agri Import — Landbridge share | Volume of non-agri imports routed via GB Landbridge (through Dover/Calais). Reducing this shifts freight to Direct routes. | tonnes |
| 6 | `f-naim-dr` | Non-Agri Import — Direct Route share | Volume of non-agri imports arriving via Direct EU routes (Cherbourg, Rotterdam, Zeebrugge). | tonnes |
| 7 | `f-naex-lb` | Non-Agri Export — Landbridge share | Volume of non-agri exports routed via GB Landbridge. | tonnes |
| 8 | `f-naex-dr` | Non-Agri Export — Direct Route share | Volume of non-agri exports via Direct EU routes. | tonnes |
| 9 | `f-aim-lb` | Agri Import — Landbridge share | Volume of agri imports via GB Landbridge. Agri products on the Landbridge face additional UK border checks. | tonnes |
| 10 | `f-aim-dr` | Agri Import — Direct Route share | Volume of agri imports via Direct EU routes (bypasses UK checks). | tonnes |
| 11 | `f-aex-lb` | Agri Export — Landbridge share | Volume of agri exports via Landbridge. | tonnes |
| 12 | `f-aex-dr` | Agri Export — Direct Route share | Volume of agri exports via Direct EU routes. | tonnes |

#### Sub-section B: Vessel capacities (5 fields)

| # | Field ID | Label | Tooltip description | Unit | Default |
|---|---|---|---|---|---|
| 13 | `f-vcap-dub-hey` | Vessel Cap — Dublin → Heysham | Average number of trailer slots per sailing on the Dublin–Heysham route. Reducing this increases vessel queuing. | trailers | 63 |
| 14 | `f-vcap-dub-holy` | Vessel Cap — Dublin → Holyhead | Average trailer capacity on the Dublin–Holyhead ferry. Holyhead is the highest-volume route. | trailers | 109 |
| 15 | `f-vcap-dub-liv` | Vessel Cap — Dublin → Liverpool | Average trailer capacity on the Dublin–Liverpool route. | trailers | 64 |
| 16 | `f-vcap-ross-fish` | Vessel Cap — Rosslare → Fishguard | Average trailer capacity on the Rosslare–Fishguard route. | trailers | 52 |
| 17 | `f-vcap-ross-pem` | Vessel Cap — Rosslare → Pembroke | Average trailer capacity on the Rosslare–Pembroke route. | trailers | 84 |

All volume fields: `NumberField`, min=0, no required asterisk (0 is valid — means route not used). Vessel capacity fields: `NumberField`, min=1, required.

### 3.5 Factor Group 3 — Customs Expertise & Resources

**Header:** `👮 Customs Expertise & Resources` · badge: `6 params`  
**Description tooltip on header:** `Check durations and staffing levels at Dublin and Rosslare ports`

| # | Field ID | Label | Tooltip description | Unit | Min | Default |
|---|---|---|---|---|---|---|
| 18 | `f-chktime-doc` | Documentary Check Duration | Average time in minutes for documentary and seal identity checks per truck. This applies to both customs and DAFM documentary checks at Irish ports. | minutes | 0.1 | 4.3 |
| 19 | `f-chktime-phy` | Physical Check Duration | Average time in minutes for a full physical inspection per truck. Physical checks are significantly longer than documentary — applies to red-route and SPS-selected trucks. | minutes | 0.1 | 34.0 |
| 20 | `f-cushed-d` | Revenue Sheds — Dublin | Number of Revenue (customs) check depots available at Dublin port for processing trucks. More sheds reduce queue waiting times. | count | 1 | 2 |
| 21 | `f-dafm-d` | SPS Check Depots — Dublin | Number of SPS (DAFM) inspection bays at Dublin port. DAFM bays process agri-food trucks for sanitary and phytosanitary checks. | count | 1 | 15 |
| 22 | `f-cushed-r` | Revenue Sheds — Rosslare | Number of Revenue check depots at Rosslare port. | count | 1 | 1 |
| 23 | `f-dafm-r` | SPS Check Depots — Rosslare | Number of SPS inspection bays at Rosslare port. | count | 1 | 1 |

All fields: `NumberField`, required.

### 3.6 Factor Group 4 — Border Checks Intervention

**Header:** `🛂 Border Checks Intervention` · badge: `8 params`  
**Description tooltip on header:** `Percentage of trucks in each routing category at Irish and UK ports`

All 8 fields are fractions displayed as percentages (0.0–1.0 stored, shown as 0–100% in UI). Use `NumberField` with `min=0`, `max=100`, `step=1`. Store as `value / 100` in state. Show `%` as suffix in label.

| # | Field ID | Label | Tooltip description | Default (%) |
|---|---|---|---|---|
| 24 | `f-pct-na-ob-green` | Non-Agri Export → Green Route (UK) | Percentage of non-agri export trucks directed to the green (no-check) lane at UK ports. Higher values mean faster throughput for non-agri exports. | 27% |
| 25 | `f-pct-na-ob-red` | Non-Agri Export → Red Route (UK) | Percentage of non-agri export trucks directed to the red (full physical check) lane at UK ports. | 38% |
| 26 | `f-pct-a-ob-red` | Agri Export → SPS Check (UK) | Percentage of agri/food export trucks selected for full SPS physical inspection at UK ports. SPS checks take significantly longer than standard checks. | 83% |
| 27 | `f-pct-na-ib-green` | Non-Agri Import → Green Route (IRE) | Percentage of non-agri import trucks directed to the green lane at Irish ports — no documentary or physical check required. | 33% |
| 28 | `f-pct-na-ib-red` | Non-Agri Import → Red Route (IRE) | Percentage of non-agri import trucks directed to full physical checks at Irish ports. | 28% |
| 29 | `f-pct-a-ib-red` | Agri Import → SPS Check (IRE) | Percentage of agri/food import trucks selected for SPS physical inspection at Irish ports. This is a key driver of DAFM bay utilisation. | 30% |
| 30 | `f-pct-ib-preboard` | Import Trucks — Pre-Boarding Check (UK) | Percentage of inbound trucks stopped at UK ports for pre-boarding status verification before departure. | 29% |
| 31 | `f-pct-ob-preboard` | Export Trucks — Pre-Boarding Check (IRE) | Percentage of outbound trucks stopped at Irish ports for pre-boarding status verification. | 29% |

### 3.7 Form Footer — Run & Reset Buttons

**Run button validation:** button is enabled when ALL of the following are non-zero / non-null:
- `NA_Im`, `NA_Ex`, `A_Im`, `A_Ex` (must be > 0)
- At least one vessel capacity > 0
- `ChkTime_Doc`, `ChkTime_Phy` > 0
- `NumCusShed_D`, `NumDAFM_D` ≥ 1

Run button label: `▶  Run Prediction`  
Error hint: `Missing required values in: [Factor Group Name]`

---

## 4. Tooltip System — New Requirement

Every input field and every output KPI card must have an info icon that shows a brief description on hover. This is a **new feature** not present in the Brexit UI.

### 4.1 Tooltip component

Add to `components.js`:

```javascript
/**
 * TooltipIcon — renders an ℹ icon that shows a popup on hover.
 * @param {string} text - The description to show in the tooltip.
 * @returns {HTMLElement}
 */
export function TooltipIcon(text) {
  const wrap = el("span", { class: "tooltip-wrap" });
  const icon = el("span", { class: "tooltip-icon" }, "ℹ");
  const popup = el("div", { class: "tooltip-popup" }, text);
  wrap.append(icon, popup);
  return wrap;
}
```

### 4.2 Tooltip CSS

Add to `styles.css`:

```css
/* ── Tooltip system ───────────────────────────────────────── */
.tooltip-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  margin-left: 5px;
  cursor: help;
}
.tooltip-icon {
  font-size: 10px;
  font-style: normal;
  color: #475569;
  background: rgba(51,65,85,0.5);
  border-radius: 50%;
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: color 0.15s, background 0.15s;
}
.tooltip-wrap:hover .tooltip-icon {
  color: #2DD4BF;
  background: rgba(13,148,136,0.2);
}
.tooltip-popup {
  display: none;
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: #1E293B;
  border: 1px solid rgba(51,65,85,0.8);
  border-radius: 8px;
  padding: 8px 10px;
  font: 400 11px/1.5 -apple-system, sans-serif;
  color: #CBD5E1;
  width: 220px;
  z-index: 200;
  pointer-events: none;
  box-shadow: 0 8px 16px rgba(0,0,0,0.4);
}
.tooltip-wrap:hover .tooltip-popup {
  display: block;
}
/* Prevent popup from clipping at left edge */
.tooltip-popup.right-align {
  left: auto;
  right: 0;
  transform: none;
}
```

### 4.3 How to attach tooltips

**On form fields** — update `SelectField` and `NumberField` in `components.js` to accept an optional `tooltip` prop:

```javascript
// In SelectField and NumberField — add tooltip prop
export function NumberField({ id, label, required, tooltip, ... }) {
  const lbl = el("label", { class: "form-label", for: id }, label);
  if (required) lbl.append(el("span", { class: "required" }, " *"));
  if (tooltip)  lbl.append(TooltipIcon(tooltip));          // ← add this line
  // ... rest unchanged
}
```

The `tooltip` string for each field is defined in Sections 3.3–3.6 above.

**On output KPI cards** — update `KpiCard` in `components.js` to accept an optional `tooltip` prop:

```javascript
export function KpiCard({ icon, label, value, unit, sub, theme, delay, tooltip }) {
  // ... existing card build ...
  const lbl = el("div", { class: "kpi-label" }, label);
  if (tooltip) lbl.append(TooltipIcon(tooltip));           // ← add this line
  // ... rest unchanged
}
```

The `tooltip` string for each KPI card is defined in Section 5 below.

### 4.4 Tooltip on factor group headers

Each `.factor-group-header` also gets a tooltip. Attach as a small `ℹ` next to the factor name (not the badge). Tooltip text is defined in Sections 3.3–3.6 above.

---

## 5. Right Panel — Output KPI Cards Rebuild

The NOLHC model returns 20 KPIs grouped into 4 categories. Each category renders as a collapsible `SectionCard` (same component as before) containing a `.kpi-grid`.

### 5.1 Overall structure

```
[Section: 🌾 Agri Products]          — teal border
  [Transport Time — Outbound]   [Transport Time — Inbound]
  [Wait Time — Outbound Dublin] [Wait Time — Outbound Rosslare]
  [Wait Time — Inbound Dublin]  [Wait Time — Inbound Rosslare]

[Section: 🏭 Non-Agri Products]      — blue border
  [Wait Time — Inbound Dublin]  [Wait Time — Outbound Dublin]
  [Wait Time — Inbound Rosslare][Wait Time — Outbound Rosslare]

[Section: 🛳 Routes]                 — violet border
  [TT Landbridge Outbound]  [TT Landbridge Inbound]
  [WT Landbridge Outbound]  [WT Landbridge Inbound]
  [TT Direct Route Outbound][TT Direct Route Inbound]

[Section: 👷 Staff Utilisation]      — amber border
  [Customs — Dublin]    [DAFM — Dublin]
  [Customs — Rosslare]  [DAFM — Rosslare]
```

### 5.2 Complete KPI card definitions

Each row below defines one KPI card. `api_slug` is the key in the API response dict.

#### Category 1 — Agri Products (6 cards)

| Card label | api_slug | Icon | Theme | Unit | Tooltip description |
|---|---|---|---|---|---|
| Transport Time — Outbound | `tt_ob_agri` | ⏱ | `teal` | hrs | Average total transport time for agri-food products travelling outbound from Ireland to GB. Includes port waiting and ferry crossing time. |
| Wait Time Outbound — Dublin (GB side) | `wt_ob_a_gb_dub` | 🕐 | `amber` | hrs | Average waiting time for agri export trucks at the GB-side of Dublin departures — time spent queuing for customs and SPS checks before boarding. |
| Wait Time Outbound — Rosslare (GB side) | `wt_ob_a_gb_ross` | 🕐 | `amber` | hrs | Average waiting time for agri export trucks at the GB-side of Rosslare departures. |
| Transport Time — Inbound | `tt_ib_agri` | ⏱ | `teal` | hrs | Average total transport time for agri-food products arriving inbound into Ireland from GB. Higher border check rates increase this significantly. |
| Wait Time Inbound — Dublin | `wt_ib_a_dub` | 🕐 | `amber` | hrs | Average waiting time for agri import trucks at Dublin port — includes SPS physical inspection queue. This is the primary DAFM utilisation driver. |
| Wait Time Inbound — Rosslare | `wt_ib_a_ross` | 🕐 | `amber` | hrs | Average waiting time for agri import trucks at Rosslare port. |

#### Category 2 — Non-Agri Products (4 cards)

| Card label | api_slug | Icon | Theme | Unit | Tooltip description |
|---|---|---|---|---|---|
| Wait Time Inbound — Dublin | `wt_ib_na_dub` | 🏭 | `blue` | hrs | Average waiting time for non-agri import trucks at Dublin port. Non-agri products go through customs checks only — no SPS inspection. |
| Wait Time Outbound — Dublin (GB side) | `wt_ob_na_gb_dub` | 🏭 | `blue` | hrs | Average waiting time for non-agri export trucks at the GB-side port — customs clearance queue on departure from Ireland. |
| Wait Time Inbound — Rosslare | `wt_ib_na_ross` | 🏭 | `blue` | hrs | Average waiting time for non-agri import trucks at Rosslare port. |
| Wait Time Outbound — Rosslare (GB side) | `wt_ob_na_gb_ross` | 🏭 | `blue` | hrs | Average waiting time for non-agri export trucks at the GB-side of Rosslare departures. |

#### Category 3 — Routes (6 cards)

| Card label | api_slug | Icon | Theme | Unit | Tooltip description |
|---|---|---|---|---|---|
| Landbridge Transport Time — Outbound | `tt_ob_lb` | 🛤 | `violet` | hrs | Average total transit time for trucks travelling outbound via the GB Landbridge route (Ireland → GB → EU through Dover/Calais). Includes UK transit time. |
| Landbridge Wait Time — Outbound | `wt_ob_lb` | 🕐 | `violet` | hrs | Average waiting time at Landbridge transit points for outbound trucks — includes Dover/Calais check delays. |
| Landbridge Transport Time — Inbound | `tt_ib_lb` | 🛤 | `violet` | hrs | Average total transit time for trucks arriving inbound via the Landbridge (EU → GB → Ireland). Sensitive to UK border check intensity. |
| Landbridge Wait Time — Inbound | `wt_ib_lb` | 🕐 | `violet` | hrs | Average waiting time at Landbridge transit points for inbound trucks. |
| Direct Route Transport Time — Outbound | `tt_ob_dr` | 🚢 | `teal` | hrs | Average transport time for trucks using Direct EU routes outbound (Ireland → Cherbourg / Rotterdam / Zeebrugge). Bypasses UK checks entirely. |
| Direct Route Transport Time — Inbound | `tt_ib_dr` | 🚢 | `teal` | hrs | Average transport time for trucks arriving via Direct EU routes inbound into Ireland. |

#### Category 4 — Staff Utilisation (4 cards)

All utilisation values from the API are fractions (0.0–1.0). Multiply by 100 before displaying. Apply conditional colouring: `violet` < 60%, `amber` 60–80%, `rose` > 80%.

| Card label | api_slug | Icon | Unit | Tooltip description |
|---|---|---|---|---|
| Customs Utilisation — Dublin | `uti_cus_d` | 👮 | % | Utilisation rate of Revenue (customs) check depots at Dublin port. Values above 80% indicate a bottleneck — trucks are queuing for customs processing. |
| DAFM Utilisation — Dublin | `uti_dafm_d` | 🏥 | % | Utilisation rate of SPS (DAFM) inspection bays at Dublin. High utilisation here is the primary driver of agri-food inbound waiting times. Values above 80% are critical. |
| Customs Utilisation — Rosslare | `uti_cus_r` | 👮 | % | Utilisation rate of Revenue check depots at Rosslare port. |
| DAFM Utilisation — Rosslare | `uti_dafm_r` | 🏥 | % | Utilisation rate of SPS inspection bays at Rosslare port. |

### 5.3 Status handling (same rules as Brexit UI, simplified)

Since the NOLHC dataset has no zero-inflation and all outputs are trained, the only statuses are:

| `status` | Display |
|---|---|
| `ok` | Show value normally |
| `low_confidence` | Show value with `⚠` badge appended to value |
| `value: null` | Do not render card |

No `not_trained` or `zero_predicted` states exist in this dataset.

### 5.4 Model confidence badge

Show above the KPI grid. Source from `registry.json` overall R² (fetched from `GET /health`):

| avg_r2 | Badge |
|---|---|
| ≥ 0.90 | 🟢 High Confidence |
| 0.75–0.89 | 🟡 Good Confidence |
| < 0.75 | 🔴 Low Confidence |

---

## 6. Journey Map — Simplified

The NOLHC model covers both GB and EU routes simultaneously (all routes active in all runs). The map stays the same structurally but route filtering is simplified.

### 6.1 Route display logic

There is no longer a `route_type` selector. Show **all three corridor types** simultaneously on the map at all times:

| Corridor | Lines | Style |
|---|---|---|
| GB East/West Maritime | Dublin→Heysham, Dublin→Liverpool, Dublin→Holyhead, Rosslare→Fishguard, Rosslare→Pembroke | Solid dark `#1a1a2e`, 2px |
| Landbridge | Dublin→Liverpool, Dover→Calais | Dashed `#1a1a2e` `6 4`, 2px |
| Direct EU | Dublin→Cherbourg, Rosslare→Cherbourg, Dublin→Rotterdam, Dublin→Zeebrugge | Solid `#1a3a5c`, 2px |

All ports shown at the same 8px marker size (no active/inactive distinction — all routes are always active).

### 6.2 Map caption

Below the map, add a small legend row (replace the journey breakdown timeline — no per-run timeline is needed since inputs are parameter values not a single journey):

```
● GB Maritime  ┄ Landbridge  ● Direct EU
```

```css
.map-legend {
  display: flex;
  gap: 16px;
  justify-content: center;
  font: 400 10px #64748B;
  padding: 6px 0 10px;
}
.map-legend-item { display: flex; align-items: center; gap: 5px; }
.map-legend-dot  { width: 8px; height: 8px; border-radius: 50%; }
```

---

## 7. Indicators Tab — Updated Sections

The Indicators tab keeps the same layout and filter bar. Update content to match NOLHC factors.

### 7.1 Filter bar — updated options

| Filter | Options |
|---|---|
| `#ind-direction` | All Flows · Agri Products · Non-Agri Products |
| `#ind-route` | All Routes · GB Maritime · Landbridge · Direct EU |
| `#ind-date` | Date picker (unchanged) |

### 7.2 Section 1 — Trade Volume Overview

`SectionCard('1 — Trade Volume Overview')` — teal border

Show 4 `IndRow` items sourced from the current state values:

| Row label | Value source | Sub-label |
|---|---|---|
| Non-Agri Imports (GB→IRE) | `state.config.NA_Im` formatted | `≈ N trucks` |
| Non-Agri Exports (IRE→GB) | `state.config.NA_Ex` formatted | `≈ N trucks` |
| Agri-Food Imports (GB→IRE) | `state.config.A_Im` formatted | `≈ N trucks` |
| Agri-Food Exports (IRE→GB) | `state.config.A_Ex` formatted | `≈ N trucks` |

Below the rows, show a `UtilBar` for Landbridge vs Direct split:
- `LB share %` = `(NA_Im_LB + A_Im_LB) / (NA_Im + A_Im) * 100`

### 7.3 Section 2 — Port Resources & Capacity

`SectionCard('2 — Port Resources & Capacity', 'blue')` — blue border

Two port cards side-by-side (Dublin and Rosslare):

```
┌──────────────────────┐  ┌──────────────────────┐
│ Dublin Port          │  │ Rosslare Port        │
│ Revenue Sheds:  N    │  │ Revenue Sheds:  N    │
│ SPS Depots:     N    │  │ SPS Depots:     N    │
└──────────────────────┘  └──────────────────────┘
```

Values sourced from `state.config.NumCusShed_D`, `NumDAFM_D`, `NumCusShed_R`, `NumDAFM_R`.

Below each card, show a `UtilBar` using the corresponding utilisation from `state.lastResult` (if available):
- `Customs util` → `uti_cus_d` / `uti_cus_r` × 100
- `DAFM util` → `uti_dafm_d` / `uti_dafm_r` × 100

### 7.4 Section 3 — Border Check Intensity

`SectionCard('3 — Border Check Intensity', 'amber')` — amber border

Show check percentages as a grid of `IndRow` items:

| Row | Value source |
|---|---|
| Agri Import → SPS Check (Irish ports) | `state.config.Pct_A_IB_Red * 100` % |
| Agri Export → SPS Check (UK ports) | `state.config.Pct_A_OB_Red * 100` % |
| Non-Agri Import → Red Route | `state.config.Pct_NA_IB_Red * 100` % |
| Non-Agri Export → Red Route | `state.config.Pct_NA_OB_Red * 100` % |
| Inbound Pre-Boarding Checks | `state.config.Pct_IB_PreBoard * 100` % |
| Outbound Pre-Boarding Checks | `state.config.Pct_OB_PreBoard * 100` % |

Add two `UtilBar` components:
- `Documentary check time: ${ChkTime_Doc} min/truck`
- `Physical check time: ${ChkTime_Phy} min/truck`

### 7.5 Section 4 — Route Performance Summary

`SectionCard('4 — Route Performance')` — default teal border

Only shown when `state.hasRun === true`. If no run yet, show a small `EmptyState('📊', 'No results yet', 'Run a prediction to see route performance summary.')`.

When results available, show 3 route cards:

| Route | KPIs displayed |
|---|---|
| GB Maritime | `tt_ob_agri` + `tt_ib_agri` (agri transport times) |
| Landbridge | `tt_ob_lb` + `tt_ib_lb` |
| Direct EU | `tt_ob_dr` + `tt_ib_dr` |

Each route card uses `.ind-section` with `IndRow` items for each KPI.

---

## 8. API Integration Changes

### 8.1 Endpoint

| Property | Old (Brexit) | New (NOLHC) |
|---|---|---|
| Method | `POST` | `POST` |
| URL | `/scenario/predict` | `/predict` |
| Options endpoint | `GET /scenario/options` (called on load) | Not needed — no dynamic option lists |
| Health endpoint | `GET /health` | `GET /health` — call on load to get avg R² for confidence badge |

### 8.2 Request construction

```javascript
// Build the 35-parameter request body from state.config
// All percentage fields stored as fractions (0–1) — divide UI % by 100 before sending
const requestBody = {
  NA_Im:           state.config.NA_Im,
  NA_Ex:           state.config.NA_Ex,
  A_Im:            state.config.A_Im,
  A_Ex:            state.config.A_Ex,
  NA_Im_LB:        state.config.NA_Im_LB,
  NA_Im_DR:        state.config.NA_Im_DR,
  NA_Ex_LB:        state.config.NA_Ex_LB,
  NA_Ex_DR:        state.config.NA_Ex_DR,
  A_Im_LB:         state.config.A_Im_LB,
  A_Im_DR:         state.config.A_Im_DR,
  A_Ex_LB:         state.config.A_Ex_LB,
  A_Ex_DR:         state.config.A_Ex_DR,
  VCap_Dub_Hey:    state.config.VCap_Dub_Hey,
  VCap_Dub_Holy:   state.config.VCap_Dub_Holy,
  VCap_Dub_Liv:    state.config.VCap_Dub_Liv,
  VCap_Ross_Fish:  state.config.VCap_Ross_Fish,
  VCap_Ross_Pem:   state.config.VCap_Ross_Pem,
  ChkTime_Doc:     state.config.ChkTime_Doc,
  ChkTime_Phy:     state.config.ChkTime_Phy,
  NumCusShed_D:    state.config.NumCusShed_D,
  NumDAFM_D:       state.config.NumDAFM_D,
  NumCusShed_R:    state.config.NumCusShed_R,
  NumDAFM_R:       state.config.NumDAFM_R,
  Pct_NA_OB_Green: state.config.Pct_NA_OB_Green,
  Pct_NA_OB_Red:   state.config.Pct_NA_OB_Red,
  Pct_A_OB_Red:    state.config.Pct_A_OB_Red,
  Pct_NA_IB_Green: state.config.Pct_NA_IB_Green,
  Pct_NA_IB_Red:   state.config.Pct_NA_IB_Red,
  Pct_A_IB_Red:    state.config.Pct_A_IB_Red,
  Pct_IB_PreBoard: state.config.Pct_IB_PreBoard,
  Pct_OB_PreBoard: state.config.Pct_OB_PreBoard,
};

const response = await fetch('http://localhost:8000/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(requestBody),
});

if (!response.ok) {
  const err = await response.json();
  throw new Error(`${response.status}: ${err.detail}`);
}

const data = await response.json();
state.lastResult = data;
```

### 8.3 Response structure

```json
{
  "tt_ob_agri":       { "value": 22.5, "unit": "hours",    "status": "ok", "r2": 0.91, "registered_as": "stacking", "mae": 1.1 },
  "wt_ob_a_gb_dub":   { "value": 0.92, "unit": "hours",    "status": "ok", "r2": 0.87, "registered_as": "gpr_rbf",  "mae": 0.08 },
  "wt_ob_a_gb_ross":  { "value": 0.01, "unit": "hours",    "status": "ok", "r2": 0.83, "registered_as": "xgboost",  "mae": 0.01 },
  "tt_ib_agri":       { "value": 22.3, "unit": "hours",    "status": "ok", "r2": 0.92, "registered_as": "stacking", "mae": 1.2 },
  "wt_ib_a_dub":      { "value": 0.40, "unit": "hours",    "status": "ok", "r2": 0.89, "registered_as": "gpr_rbf",  "mae": 0.05 },
  "wt_ib_a_ross":     { "value": 0.03, "unit": "hours",    "status": "ok", "r2": 0.84, "registered_as": "svr_rbf",  "mae": 0.02 },
  "wt_ib_na_dub":     { "value": 33.9, "unit": "hours",    "status": "ok", "r2": 0.91, "registered_as": "stacking", "mae": 2.1 },
  "wt_ob_na_gb_dub":  { "value": 0.98, "unit": "hours",    "status": "ok", "r2": 0.88, "registered_as": "xgboost",  "mae": 0.09 },
  "wt_ib_na_ross":    { "value": 2.59, "unit": "hours",    "status": "ok", "r2": 0.86, "registered_as": "gpr_rbf",  "mae": 0.21 },
  "wt_ob_na_gb_ross": { "value": 1.82, "unit": "hours",    "status": "ok", "r2": 0.85, "registered_as": "lightgbm", "mae": 0.18 },
  "tt_ob_lb":         { "value": 26.0, "unit": "hours",    "status": "ok", "r2": 0.93, "registered_as": "stacking", "mae": 0.8 },
  "wt_ob_lb":         { "value": 1.96, "unit": "hours",    "status": "ok", "r2": 0.87, "registered_as": "gpr_rbf",  "mae": 0.15 },
  "tt_ib_lb":         { "value": 47.9, "unit": "hours",    "status": "ok", "r2": 0.90, "registered_as": "stacking", "mae": 1.5 },
  "wt_ib_lb":         { "value": 29.0, "unit": "hours",    "status": "ok", "r2": 0.88, "registered_as": "xgboost",  "mae": 1.2 },
  "tt_ob_dr":         { "value": 35.5, "unit": "hours",    "status": "ok", "r2": 0.94, "registered_as": "stacking", "mae": 0.6 },
  "tt_ib_dr":         { "value": 30.7, "unit": "hours",    "status": "ok", "r2": 0.93, "registered_as": "stacking", "mae": 0.7 },
  "uti_cus_d":        { "value": 0.97, "unit": "fraction", "status": "ok", "r2": 0.95, "registered_as": "gpr_rbf",  "mae": 0.02 },
  "uti_dafm_d":       { "value": 0.24, "unit": "fraction", "status": "ok", "r2": 0.91, "registered_as": "stacking", "mae": 0.03 },
  "uti_cus_r":        { "value": 0.57, "unit": "fraction", "status": "ok", "r2": 0.88, "registered_as": "xgboost",  "mae": 0.04 },
  "uti_dafm_r":       { "value": 0.13, "unit": "fraction", "status": "ok", "r2": 0.86, "registered_as": "gpr_rbf",  "mae": 0.02 }
}
```

> The response is a **flat dict of 20 slugs** — no nested `results.transit` / `results.border_delay` grouping. Grouping into the 4 categories is done entirely in the UI render layer.

### 8.4 Health endpoint — call on load

```javascript
// On DOMContentLoaded — fetch health to get model confidence
const health = await fetch('http://localhost:8000/health').then(r => r.json());
state.modelAvgR2 = health.avg_r2;   // used for confidence badge
state.modelVersion = health.model_version;
```

---

## 9. Application State Changes

### 9.1 Updated state object

```javascript
const state = {
  config: {
    // Factor 1 — Trade Volumes
    NA_Im:           6140333,
    NA_Ex:           5387458,
    A_Im:            2826920,
    A_Ex:            2111499,

    // Factor 2 — Direct Routes
    NA_Im_LB:        747571,
    NA_Im_DR:        681189,
    NA_Ex_LB:        835757,
    NA_Ex_DR:        480163,
    A_Im_LB:         427438,
    A_Im_DR:         301281,
    A_Ex_LB:         344142,
    A_Ex_DR:         119462,
    VCap_Dub_Hey:    63,
    VCap_Dub_Holy:   109,
    VCap_Dub_Liv:    64,
    VCap_Ross_Fish:  52,
    VCap_Ross_Pem:   84,

    // Factor 3 — Customs Resources
    ChkTime_Doc:     4.28,
    ChkTime_Phy:     33.99,
    NumCusShed_D:    2,
    NumDAFM_D:       15,
    NumCusShed_R:    1,
    NumDAFM_R:       1,

    // Factor 4 — Border Checks (stored as fractions 0–1)
    Pct_NA_OB_Green: 0.27,
    Pct_NA_OB_Red:   0.38,
    Pct_A_OB_Red:    0.83,
    Pct_NA_IB_Green: 0.33,
    Pct_NA_IB_Red:   0.28,
    Pct_A_IB_Red:    0.30,
    Pct_IB_PreBoard: 0.29,
    Pct_OB_PreBoard: 0.29,
  },

  // UI state
  hasRun:         false,
  isLoading:      false,
  lastResult:     null,    // flat dict of 20 KPI slugs → PredictionResult
  apiError:       null,
  activeView:     "results",
  modelAvgR2:     null,    // fetched from GET /health on load
  modelVersion:   "v1",
};
```

### 9.2 No cascade resets needed

Unlike the Brexit UI, there are no dependent dropdowns. All 35 fields are independent. Changing any field does not reset any other field. If `state.hasRun === true`, debounce any field change by 300ms and auto-re-call the API.

---

## 10. data.js Changes

Replace the entire content of `data.js` with the NOLHC-specific constants. The Brexit scenario data (ROUTES, FERRY_TIMES, CHECK_PARAMS, etc.) is no longer needed.

### What to keep

```javascript
// Keep unchanged:
export const PORT_COORDS   = { ... }  // all 12 ports — same as before
export const MAP_ROUTES    = [ ... ]  // all 11 routes — same as before
export const APP_CONFIG    = { ... }  // tonnesPerTruck: 25, etc.
```

### What to replace

```javascript
// ── NOLHC KPI METADATA ────────────────────────────────────────
// One entry per output slug — used to drive KPI card rendering.
export const KPI_META = {
  tt_ob_agri:       { label: "Transport Time — Outbound",           unit: "hrs",  category: "agri",       icon: "⏱", theme: "teal" },
  wt_ob_a_gb_dub:   { label: "Wait Time Outbound — Dublin (GB)",    unit: "hrs",  category: "agri",       icon: "🕐", theme: "amber" },
  wt_ob_a_gb_ross:  { label: "Wait Time Outbound — Rosslare (GB)",  unit: "hrs",  category: "agri",       icon: "🕐", theme: "amber" },
  tt_ib_agri:       { label: "Transport Time — Inbound",            unit: "hrs",  category: "agri",       icon: "⏱", theme: "teal" },
  wt_ib_a_dub:      { label: "Wait Time Inbound — Dublin",          unit: "hrs",  category: "agri",       icon: "🕐", theme: "amber" },
  wt_ib_a_ross:     { label: "Wait Time Inbound — Rosslare",        unit: "hrs",  category: "agri",       icon: "🕐", theme: "amber" },
  wt_ib_na_dub:     { label: "Wait Time Inbound — Dublin",          unit: "hrs",  category: "non_agri",   icon: "🏭", theme: "blue" },
  wt_ob_na_gb_dub:  { label: "Wait Time Outbound — Dublin (GB)",    unit: "hrs",  category: "non_agri",   icon: "🏭", theme: "blue" },
  wt_ib_na_ross:    { label: "Wait Time Inbound — Rosslare",        unit: "hrs",  category: "non_agri",   icon: "🏭", theme: "blue" },
  wt_ob_na_gb_ross: { label: "Wait Time Outbound — Rosslare (GB)",  unit: "hrs",  category: "non_agri",   icon: "🏭", theme: "blue" },
  tt_ob_lb:         { label: "Landbridge TT — Outbound",            unit: "hrs",  category: "routes",     icon: "🛤", theme: "violet" },
  wt_ob_lb:         { label: "Landbridge WT — Outbound",            unit: "hrs",  category: "routes",     icon: "🕐", theme: "violet" },
  tt_ib_lb:         { label: "Landbridge TT — Inbound",             unit: "hrs",  category: "routes",     icon: "🛤", theme: "violet" },
  wt_ib_lb:         { label: "Landbridge WT — Inbound",             unit: "hrs",  category: "routes",     icon: "🕐", theme: "violet" },
  tt_ob_dr:         { label: "Direct Route TT — Outbound",          unit: "hrs",  category: "routes",     icon: "🚢", theme: "teal" },
  tt_ib_dr:         { label: "Direct Route TT — Inbound",           unit: "hrs",  category: "routes",     icon: "🚢", theme: "teal" },
  uti_cus_d:        { label: "Customs Utilisation — Dublin",        unit: "%",    category: "staff",      icon: "👮", theme: "violet" },
  uti_dafm_d:       { label: "DAFM Utilisation — Dublin",           unit: "%",    category: "staff",      icon: "🏥", theme: "violet" },
  uti_cus_r:        { label: "Customs Utilisation — Rosslare",      unit: "%",    category: "staff",      icon: "👮", theme: "violet" },
  uti_dafm_r:       { label: "DAFM Utilisation — Rosslare",         unit: "%",    category: "staff",      icon: "🏥", theme: "violet" },
};

// Category display config
export const KPI_CATEGORIES = {
  agri:     { title: "🌾 Agri Products",    border: "teal" },
  non_agri: { title: "🏭 Non-Agri Products", border: "blue" },
  routes:   { title: "🛳 Routes",            border: "violet" },
  staff:    { title: "👷 Staff Utilisation", border: "amber" },
};

// NOLHC training medians (used as default field values — already in state.config)
export const NOLHC_MEDIANS = {
  NA_Im: 6140333, NA_Ex: 5387458, A_Im: 2826920, A_Ex: 2111499,
  NA_Im_LB: 747571, NA_Im_DR: 681189, NA_Ex_LB: 835757, NA_Ex_DR: 480163,
  A_Im_LB: 427438, A_Im_DR: 301281, A_Ex_LB: 344142, A_Ex_DR: 119462,
  VCap_Dub_Hey: 63, VCap_Dub_Holy: 109, VCap_Dub_Liv: 64,
  VCap_Ross_Fish: 52, VCap_Ross_Pem: 84,
  ChkTime_Doc: 4.28, ChkTime_Phy: 33.99,
  NumCusShed_D: 2, NumDAFM_D: 15, NumCusShed_R: 1, NumDAFM_R: 1,
  Pct_NA_OB_Green: 0.27, Pct_NA_OB_Red: 0.38, Pct_A_OB_Red: 0.83,
  Pct_NA_IB_Green: 0.33, Pct_NA_IB_Red: 0.28, Pct_A_IB_Red: 0.30,
  Pct_IB_PreBoard: 0.29, Pct_OB_PreBoard: 0.29,
};
```

---

## 11. Chatbot Updates

No structural changes — only update the keyword response map to NOLHC terminology.

### Updated keyword response map

| Keywords | Topic | Response summary |
|---|---|---|
| `agri`, `food`, `sps` | Agri-food SPS checks | Explain SPS (sanitary/phytosanitary) checks — DAFM inspection process, why agri products face longer delays, role of DAFM bays |
| `landbridge`, `gb`, `dover` | Landbridge route | Explain GB Landbridge — Ireland→Liverpool→Dover→Calais→EU, UK border checks add time, post-Brexit friction |
| `direct`, `cherbourg`, `rotterdam`, `zeebrugge` | Direct EU routes | Direct sailings bypassing GB — faster for EU-bound freight, no UK checks, longer sea crossing |
| `wait`, `queue`, `delay` | Waiting times | Explain WT outputs — driven by check percentages and resource capacity; DAFM utilisation above 80% is critical |
| `customs`, `revenue`, `shed` | Customs resources | Revenue sheds at Dublin/Rosslare — more sheds reduce customs waiting times for non-agri products |
| `dafm`, `inspection`, `bay` | DAFM resources | DAFM inspection bays — handle SPS checks on agri food; key bottleneck when utilisation exceeds 80% |
| `utilisation`, `capacity`, `staff` | Staff utilisation | Explain Uti_Cus and Uti_DAFM outputs — fraction of working time staff/facilities are occupied |
| `vessel`, `capacity`, `ferry` | Vessel capacity | Vessel trailer slots — reducing capacity increases vessel queue lengths and transport time |
| `preboarding`, `pre-boarding` | Pre-boarding checks | Percentage of trucks checked before boarding — adds to outbound/inbound waiting times |
| `green`, `red`, `route` | Routing lanes | Green route = no check; red route = full physical inspection; percentage setting drives wait times |

---

## 12. Cursor Implementation Checklist

> Keep `uvicorn main:app --port 8000 --reload` running throughout.  
> Work through phases in order — each is independently testable.

### Phase A — Project Setup

- [ ] Copy existing `ui/` folder into `nolhc_ml/` project directory
- [ ] Confirm `index.html` has all required IDs unchanged from Brexit version
- [ ] Call `GET /health` on load — verify it returns `{ avg_r2, model_version, ... }`
- [ ] Confirm `POST /predict` with the 35-param body returns 20 KPI slugs
- [ ] Confirm Leaflet 1.9.4 CDN links are intact in `<head>`

### Phase B — data.js Replacement

- [ ] Remove all Brexit-specific exports: `ROUTES`, `ROUTE_DISPLAY`, `CORRIDOR_ROUTES`, `FERRY_TIMES`, `FERRY_CAPACITY`, `SAILINGS_PER_DAY`, `LAND_TRANSIT`, `GOODS_TYPES`, `GOODS_ICONS`, `SHELF_LIFE_DAYS`, `AGRI_PCT`, `TRUCK_TYPES`, `CHECK_PARAMS`, `OFFICERS`, `CHECK_COSTS_BY_PORT`, `CHECK_COST_BASE`, `ANNUAL_VOLUMES`, `TRUCK_MIX`
- [ ] Add `KPI_META` with all 20 entries per Section 10
- [ ] Add `KPI_CATEGORIES` per Section 10
- [ ] Add `NOLHC_MEDIANS` per Section 10
- [ ] Keep `PORT_COORDS` (all 12 ports unchanged)
- [ ] Keep `MAP_ROUTES` (all 11 routes unchanged)
- [ ] Keep `APP_CONFIG` (update `tonnesPerTruck: 25` if needed)

### Phase C — State & API Wiring

- [ ] Replace `state.config` with NOLHC 35-parameter object per Section 9.1
- [ ] Add `state.modelAvgR2` and `state.modelVersion` fields
- [ ] On `DOMContentLoaded`: call `GET /health`, store `avg_r2` and `model_version`
- [ ] Implement `async runSim()`: build 35-param `requestBody` per Section 8.2
  - [ ] Convert percentage fields: store ÷ 100 before sending
  - [ ] `POST` to `/predict`
  - [ ] On success: store flat dict in `state.lastResult`
  - [ ] On error: show error banner per Section 8.4

### Phase D — Tooltip System

- [ ] Add `TooltipIcon(text)` to `components.js` per Section 4.1
- [ ] Add all tooltip CSS classes to `styles.css` per Section 4.2
- [ ] Update `NumberField` to accept and render optional `tooltip` prop
- [ ] Update `SelectField` to accept and render optional `tooltip` prop (for future use)
- [ ] Update `KpiCard` to accept and render optional `tooltip` prop per Section 4.3
- [ ] Test: hover on a field → popup appears; hover on KPI card → popup appears

### Phase E — Left Panel Form Rebuild

- [ ] Update panel header: `h2 = 'Simulation Parameters'`, subtitle = `'Configure the 4 factor groups for prediction'`
- [ ] Add `.factor-group`, `.factor-group-header`, `.factor-group-body` CSS per Section 3.2
- [ ] Build Group 1 (Trade Volumes): 4 `NumberField`s with tonnage defaults and truck-count hints
- [ ] Build Group 2 (Direct Routes): 8 volume `NumberField`s + 5 vessel capacity `NumberField`s
- [ ] Build Group 3 (Customs Resources): 6 `NumberField`s with correct defaults
- [ ] Build Group 4 (Border Checks): 8 `NumberField`s with 0–100% display (stored ÷ 100)
- [ ] Each group header has a tooltip showing the factor description
- [ ] Each individual field has its tooltip string from Sections 3.3–3.6
- [ ] Default state: Group 1 open, Groups 2–4 collapsed
- [ ] Click group header toggles `.open` class and chevron rotation
- [ ] Run button: validate required fields (Group 1 volumes > 0, vessel caps > 0, check times > 0)
- [ ] Run button label: `▶  Run Prediction`
- [ ] Error hint: shows which group has missing/invalid values

### Phase F — Map Update

- [ ] Remove route filtering logic — show ALL routes at all times
- [ ] All port markers: uniform 8px size
- [ ] Add `.map-legend` below map per Section 6.2
- [ ] Remove journey breakdown timeline — replace with map legend

### Phase G — Results KPI Cards Rebuild

- [ ] On `renderResults()`: group `state.lastResult` by `KPI_META[slug].category`
- [ ] Render 4 `SectionCard` sections in order: `agri`, `non_agri`, `routes`, `staff`
- [ ] Inside each section: render `kpi-grid` with cards from that category
- [ ] Each `KpiCard` receives `tooltip` from the tooltip descriptions in Section 5.2
- [ ] Utilisation cards: multiply value by 100; apply conditional theme (violet/amber/rose)
- [ ] Show `registered_as` model name as sub-text on each card: e.g. `model: stacking`
- [ ] Render model confidence badge above first section using `state.modelAvgR2`
- [ ] Handle `status: 'low_confidence'` → append `⚠` to value
- [ ] Apply staggered `fadeUp` animation (0.05s per card)

### Phase H — Indicators Tab Update

- [ ] Update filter bar options: direction (All/Agri/Non-Agri), route (All/GB/LB/Direct)
- [ ] Section 1: Trade Volume Overview — 4 `IndRow`s from `state.config` + LB share util bar
- [ ] Section 2: Port Resources — Dublin and Rosslare cards from `state.config` + utilisation bars from `state.lastResult`
- [ ] Section 3: Border Check Intensity — 6 `IndRow`s from `state.config` + 2 util bars for check times
- [ ] Section 4: Route Performance — show only if `state.hasRun`; 3 route cards with relevant KPIs

### Phase I — Chatbot Keyword Update

- [ ] Replace all Brexit keyword entries with NOLHC entries from Section 11
- [ ] Update chatbot header sub-text: `'Ask about NOLHC simulation parameters & results'`
- [ ] Update initial greeting: `'Hello! I can explain the simulation parameters and predicted KPIs for the NOLHC Ireland trade model. Ask me anything.'`

### Phase J — Polish & Verification

- [ ] All 35 fields have working tooltips (hover shows description)
- [ ] All 20 KPI cards have working tooltips
- [ ] Factor group accordions open/close correctly; Group 1 open by default
- [ ] Full round trip: set values → Run Prediction → 4 sections populate with cards
- [ ] Confidence badge appears and reflects `GET /health` avg_r2
- [ ] `registered_as` model name appears in each KPI card sub-text
- [ ] Map shows all routes simultaneously with legend
- [ ] Indicators tab sections 1–4 all render correctly
- [ ] Error states: 400, 503, network failure all show appropriate banners
- [ ] Reset button clears all fields to median defaults and clears results
- [ ] Responsive: 640px breakpoint — single column, accordion groups still work

---

*End of specification. Design system, animations, and HTML shell are inherited unchanged from `Brexit_ML_UI_Spec.md`. Only input parameters, output KPIs, API contract, and data.js are replaced for the NOLHC dataset.*
