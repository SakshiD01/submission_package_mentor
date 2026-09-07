# Brexit ML Engine — UI Development Specification

**Prototype reference:** https://roro-route-flow.base44.app/Dashboard  
**API base URL:** `http://localhost:8000`  
**Primary endpoint:** `POST /scenario/predict`  
**UI architecture:** Vanilla JS ES Modules — `index.html` + `app.js` + `components/components.js` + `styles/styles.css` + `data/data.js`  
**Map library:** Leaflet.js 1.9.4 (OpenStreetMap tiles)  
**Phase 1 scope:** IRE ↔ GB East/West Corridor only

---

## Table of Contents

1. [UI Overview & Design System](#1-ui-overview--design-system)
2. [App Header](#2-app-header)
3. [Left Panel — Input Form](#3-left-panel--input-form)
4. [Right Panel — Results View](#4-right-panel--results-view)
5. [Right Panel — Indicators Tab](#5-right-panel--indicators-tab)
6. [Reusable Components](#6-reusable-components)
7. [Chatbot (Route Advisor)](#7-chatbot-route-advisor)
8. [API Integration](#8-api-integration)
9. [Application State](#9-application-state)
10. [File Structure & Animations](#10-file-structure--animations)
11. [Cursor Implementation Checklist](#11-cursor-implementation-checklist)

---

## 1. UI Overview & Design System

### 1.1 Visual Theme

| Token | CSS Variable | Hex | Used For |
|---|---|---|---|
| Background | — | `#020817` | `<body>` base |
| Surface 900 | `--slate-900` | `#0F172A` | Deepest panels, chatbot bg |
| Surface 800 | `--slate-800` | `#1E293B` | Form inputs, code blocks |
| Surface 700 | `--slate-700` | `#334155` | Active tab bg, hover states |
| Border | `--border` | `rgba(51,65,85,0.5)` | All panel dividers |
| Primary | `--teal` | `#0D9488` | Run button, active accents |
| Primary Light | `--teal-light` | `#2DD4BF` | Values, highlights, totals |
| Primary Dim | `--teal-dim` | `rgba(13,148,136,0.2)` | Card backgrounds |
| Text Primary | — | `#F8FAFC` | Body text, headings |
| Text Muted | `--slate-400` | `#94A3B8` | Labels, subtitles |
| Text Faint | `--slate-500` | `#64748B` | Hints, section titles |
| Radius SM | `--radius-sm` | `6px` | Inputs, small elements |
| Radius MD | `--radius-md` | `10px` | Buttons, KPI cards |
| Radius LG | `--radius-lg` | `14px` | Map wrapper, ind-sections |

### 1.2 Typography

| Element | Size | Weight | Colour |
|---|---|---|---|
| Body base | 14px | 400 | `#F8FAFC` |
| Form label | 11px | 500 | `#94A3B8` — UPPERCASE, letter-spacing 0.05em |
| Form input | 13px | 400 | white |
| KPI value | 19px | 700 | theme colour |
| KPI label | 10px | 500 | `#64748B` — UPPERCASE |
| KPI unit | 11px | 400 | `#94A3B8` |
| Timeline name | 10px | 400 | `#94A3B8` |
| Section title | 10px | 600 | `#64748B` — UPPERCASE |
| Tab button | 11px | 500 active / 400 inactive | white / `#64748B` |
| App title | 13px | 600 | white |
| App subtitle | 10px | 400 | `#64748B` |

Font stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`

### 1.3 Full Viewport Layout

The app occupies 100% viewport height with `overflow:hidden`. No scroll bars on the outer shell — only inner panels scroll.

```
┌────────────────────────────────────────────────────────────────┐
│  APP HEADER — 56px fixed                                       │
│  [SC logo] [Supply Chain Simulator] .......... [Tab bar]       │
├──────────────────────────┬─────────────────────────────────────┤
│  LEFT PANEL — 320px      │  RIGHT PANEL — flex:1               │
│  flex-shrink: 0          │                                     │
│                          │  [ind-filter-bar]  ← hidden/shown   │
│  [panel-header]          │  padding:12px 16px; border-bottom   │
│   h2 + subtitle          │                                     │
│                          │  [right-content — scrollable]       │
│  [form-body — scrollable]│  padding: 16px                      │
│  padding: 20px 24px      │                                     │
│                          │                                     │
│  [form-footer — fixed]   │                                     │
│  padding: 16px 24px      │                                     │
│  border-top              │                                     │
└──────────────────────────┴─────────────────────────────────────┘
                  [💬 Chatbot FAB — fixed, bottom-right]
```

| Region | CSS class | Dimensions / behaviour |
|---|---|---|
| Outer shell | `#app` | `display:flex; flex-direction:column; height:100vh; overflow:hidden` |
| Header | `.app-header` | `height:56px; flex-shrink:0; border-bottom:1px solid var(--border); padding:0 24px` |
| Body row | `.app-body` | `flex:1; display:flex; overflow:hidden` |
| Left panel | `.left-panel` | `width:320px; flex-shrink:0; border-right:1px solid var(--border); background:rgba(15,23,42,0.5); display:flex; flex-direction:column; overflow:hidden` |
| Right panel | `.right-panel` | `flex:1; overflow:hidden; display:flex; flex-direction:column` |
| Indicator filter bar | `.ind-filters` (id `ind-filter-bar`) | `display:none` by default; `display:flex` when Indicators tab active |
| Right scrollable content | `.panel-scroll` (id `right-content`) | `flex:1; overflow-y:auto; padding:16px` |
| Panel header | `.panel-header` | `padding:20px 24px; border-bottom:1px solid var(--border); flex-shrink:0` |
| Form body | `.form-body` (id `form-body`) | `flex:1; overflow-y:auto; padding:20px 24px` |
| Form footer | `.form-footer` (id `form-footer`) | `padding:16px 24px; border-top:1px solid var(--border); flex-shrink:0` |

---

## 2. App Header

```
┌────────────────────────────────────────────────────────────────┐
│ [SC]  Supply Chain Simulator          [📊 Results] [📈 Indics] │
│       RoRo Truck Logistics — Ireland ↔ GB ↔ EU                 │
└────────────────────────────────────────────────────────────────┘
```

### 2.1 Logo Block (left side)

| Element | Spec |
|---|---|
| Logo square `.logo` | `32×32px; border-radius:8px; background:linear-gradient(135deg,#14B8A6,#0D9488); font:700 13px white; text:'SC'` |
| App title `.app-title` | `font:600 13px white; text:'Supply Chain Simulator'` |
| App subtitle `.app-subtitle` | `font:400 10px #64748B; text:'RoRo Truck Logistics — Ireland ↔ GB ↔ EU'` |
| Wrapper | `display:flex; align-items:center; gap:12px` |

### 2.2 Tab Bar (right side)

| Element | Spec |
|---|---|
| Wrapper `.tab-bar` | `display:flex; gap:3px; background:rgba(30,41,59,0.5); border:1px solid var(--border); border-radius:8px; padding:3px` |
| Tab button `.tab-btn` | `padding:4px 12px; border-radius:6px; border:none; font:11px; background:transparent; color:#64748B; cursor:pointer; transition:all 0.15s` |
| Active `.tab-btn.active` | `background:#334155; color:white; font-weight:500` |
| Results tab | `data-view="results"` — icon 📊, label "Results" |
| Indicators tab | `data-view="indicators"` — icon 📈, label "Indicators" |

**Tab switching behaviour:**
- Click Results → `setActiveTab('results')` → show `right-content`, hide `ind-filter-bar` → call `renderResults()`
- Click Indicators → `setActiveTab('indicators')` → show `ind-filter-bar` → call `renderIndicatorsWithFilters()`
- Only one tab has `.active` at a time

---

## 3. Left Panel — Input Form

### 3.1 Panel Header

| Element | Spec |
|---|---|
| Container `.panel-header` | `padding:20px 24px; border-bottom:1px solid var(--border); flex-shrink:0` |
| `h2` | `font:600 17px white; text:'Product Specification'` |
| `p` subtitle | `font:400 12px #94A3B8; margin-top:2px; text:'Configure your RoRo shipment'` |

### 3.2 Form Fields — Complete Ordered List

> **IMPORTANT:** Fields 3, 5, 6, and 8 are conditional — they only render when the preceding field has a value. This cascading behaviour is critical.

#### Field 1: Shipment Date (always shown)

| Property | Value |
|---|---|
| Component | `DateField` |
| ID | `f-date` |
| Label | `📅 Shipment Date` |
| Default | `new Date().toISOString().split('T')[0]` (today) |
| Max | today (no future dates) |
| Required | No |
| State key | `config.shipmentDate` |

---

#### Field 2: Supplier Region

| Property | Value |
|---|---|
| Component | `SelectField` |
| ID | `f-supplier-region` |
| Label | `🌍 Supplier Region` |
| Placeholder | `Select region` |
| Required | Yes — red `*` |
| Options | `ireland` \| `great_britain` \| `eu` |
| State key | `config.supplier_region` |
| On change | Reset `origin_port`, `destination_port`, `route_type` |
| API field | `supplier_region` |

---

#### Field 3: Origin Port *(shown only when supplier_region is set)*

| Property | Value |
|---|---|
| Component | `SelectField` |
| ID | `f-origin-port` |
| Label | `⚓ Origin Port` |
| Required | Yes |
| Options if `ireland` | `dublin` \| `rosslare` |
| Options if `great_britain` | `liverpool` \| `holyhead` \| `heysham` \| `fishguard` \| `pembroke` |
| Options if `eu` | `cherbourg` \| `rotterdam` \| `zeebrugge` \| `bilbao` |
| State key | `config.origin_port` |
| API field | `origin_port` |

---

#### Field 4: Direction

| Property | Value |
|---|---|
| Component | `SelectField` |
| ID | `f-direction` |
| Label | `↔ Direction` |
| Required | Yes |
| Options | `export` (Ireland sending goods out) \| `import` (Ireland receiving goods) |
| State key | `config.direction` |
| On change | Reset `destination_region`, `destination_port` |
| API field | `direction` |

---

#### Field 5: Destination Region *(shown only when direction is set)*

| Property | Value |
|---|---|
| Component | `SelectField` |
| ID | `f-destination-region` |
| Label | `🎯 Destination Region` |
| Required | Yes |
| Options | `great_britain` \| `eu` |
| State key | `config.destination_region` |
| On change | Reset `destination_port`, `route_type` |
| API field | `destination_region` |

---

#### Field 6: Destination Port *(shown only when destination_region is set)*

| Property | Value |
|---|---|
| Component | `SelectField` |
| ID | `f-destination-port` |
| Label | `🏁 Destination Port` |
| Required | Yes |
| Options if `great_britain` | `liverpool` \| `holyhead` \| `heysham` \| `fishguard` \| `pembroke` |
| Options if `eu` | `cherbourg` \| `rotterdam` \| `zeebrugge` \| `bilbao` |
| State key | `config.destination_port` |
| API field | `destination_port` |

---

#### Field 7: Commodity Type

| Property | Value |
|---|---|
| Component | `SelectField` |
| ID | `f-commodity` |
| Label | `📦 Commodity Type` |
| Required | Yes |
| Options | `all_products` — All Products \| `agri` — Agri-Food / SPS \| `category` — Specific Category |
| State key | `config.commodity_type` |
| API field | `commodity_type` |
| Note | Determines which output KPIs are returned — agri gets SPS-specific outputs |

---

#### Field 8: Route Type *(shown only when destination_region is set)*

| Property | Value |
|---|---|
| Component | `SelectField` |
| ID | `f-route-type` |
| Label | `🗺 Route Type` |
| Required | Yes |
| Options if `great_britain` | `direct_gb` — Direct (East/West Maritime Corridor) |
| Options if `eu` | `landbridge` — Via GB Land-bridge *(Phase 2)* \| `direct_cherbourg` — Direct to Cherbourg *(Phase 2)* \| `direct_rotterdam` — Direct to Rotterdam *(Phase 2)* \| `direct_zeebrugge` — Direct to Zeebrugge *(Phase 2)* \| `direct_bilbao` — Direct to Bilbao *(Phase 2)* |
| Phase 2 note | Show Phase 2 options as disabled / greyed with `(Phase 2)` badge |
| State key | `config.route_type` |
| API field | `route_type` |

---

#### Field 9: Border Check Regime

| Property | Value |
|---|---|
| Component | `SelectField` |
| ID | `f-check-regime` |
| Label | `🛂 Border Check Regime` |
| Required | Yes |
| Options | `none` — No checks (Pre-Brexit baseline) \| `light` — Light checks (Customs export only) \| `standard` — Standard (10% physical) \| `hard` — Hard Brexit (30% SPS physical) |
| State key | `config.check_regime` |
| API field | `check_regime` |

---

#### Field 10: Product Volume (tonnes)

| Property | Value |
|---|---|
| Component | `NumberField` |
| ID | `f-volume` |
| Label | `📦 Product Volume (tonnes)` |
| Required | Yes |
| Min | 1 |
| Hint text | After entry: show approx truck count — `≈ ${Math.round(value/25).toLocaleString()} trucks` |
| State key | `config.product_volume_tonnes` |
| API field | `product_volume_tonnes` |

---

#### Field 11: Shelf Life (optional)

| Property | Value |
|---|---|
| Component | `NumberField` |
| ID | `f-shelf` |
| Label | `⏳ Shelf Life (Days)` |
| Placeholder | `Enter shelf life in days (optional)` |
| Required | No |
| State key | `config.shelf_life_days` |
| API field | `shelf_life_days` |
| Default | 14 days if omitted |

---

#### Fields 12–16: Advanced Options *(collapsible, collapsed by default)*

| # | Label | ID | API field | Default | Constraint |
|---|---|---|---|---|---|
| 12 | `👮 Customs Officers` | `f-customs` | `customs_officers` | 10 | int ≥ 0 |
| 13 | `🏥 DAFM Officers` | `f-dafm` | `dafm_officers` | 10 | int ≥ 0 |
| 14 | `🔒 Security Officers` | `f-security` | `security_officers` | 10 | int ≥ 0 |
| 15 | `🚜 Tractors` | `f-tractors` | `tractors` | 20 | int ≥ 0 |
| 16 | `% Unaccompanied` | `f-unacc` | `unaccompanied_pct` | 0.5 | 0.0–1.0, display as % |

### 3.3 Form Field Component Specs

#### SelectField props

| Prop | Type | Description |
|---|---|---|
| `id` | string | HTML id for the `<select>` |
| `label` | string | Shown as uppercase 11px label above input |
| `required` | boolean | Appends red `*` to label |
| `options` | array | `{value, label}` objects |
| `value` | string | Currently selected value |
| `placeholder` | string | First `<option value="">` |
| `onChange` | function | Called with new value string |
| `disabled` | boolean | Greys out field (opacity:0.4) |

#### NumberField props

| Prop | Type | Description |
|---|---|---|
| `id` | string | HTML id |
| `label` | string | Label text |
| `required` | boolean | Red asterisk |
| `value` | number | Current value |
| `placeholder` | string | Input placeholder |
| `min` | number | Minimum value (default: 0) |
| `onChange` | function | Called with `parseFloat(input.value) \|\| 0` |
| `hint` | string\|null | Shown below input in `#2DD4BF` |

#### Common input styling

```css
input[type="number"], select {
  width: 100%;
  padding: 9px 12px;
  border-radius: var(--radius-sm);          /* 6px */
  background: rgba(30,41,59,0.5);
  border: 1px solid var(--slate-700);       /* #334155 */
  color: white;
  font-size: 13px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s;
}
input:focus, select:focus {
  border-color: var(--teal);               /* #0D9488 */
}
```

### 3.4 Form Footer — Run & Reset Buttons

| Element | Class | Spec |
|---|---|---|
| Run button (active) | `.btn-run.ready` | `width:100%; padding:12px 16px; border-radius:10px; background:#0D9488; color:white; font:600 14px; hover→#14B8A6` |
| Run button (disabled) | `.btn-run.disabled` | Same dimensions; `background:#1E293B; color:#64748B; cursor:not-allowed; border:1px solid #334155` |
| Run label | — | `▶  Run Simulation` |
| Reset button | `.btn-reset` | `width:100%; padding:8px 16px; border-radius:10px; background:#1E293B; color:#94A3B8; font:500 12px` — only shown after first run |
| Reset label | — | `↺  Reset` |
| Error hint | `.error-hint` | `font:400 10px #64748B; text-align:center; margin-top:4px` — lists missing required fields |

**Validation logic:**
- Button is `.btn-run.disabled` until ALL required fields are populated
- Required: `supplier_region`, `origin_port`, `destination_region`, `destination_port`, `commodity_type`, `direction`, `route_type`, `check_regime`, `product_volume_tonnes` (> 0)
- Missing fields shown: `Missing: Direction, Route Type`
- On click → `state.isLoading = true` → POST to API → render results

---

## 4. Right Panel — Results View

### 4.1 Empty State (before first run)

| Element | Spec |
|---|---|
| Container `.empty-state` | `height:100%; display:flex; align-items:center; justify-content:center; flex-direction:column; text-align:center; gap:12px` |
| Icon `.empty-icon` | `64×64px; border-radius:16px; background:rgba(30,41,59,0.5); font-size:26px; icon:📊` |
| Heading | `font:500 15px #94A3B8; text:'Ready to simulate'` |
| Body | `font:400 13px #64748B; max-width:280px; text:'Configure your shipment and press Run Simulation to view results.'` |
| Highlight span | `color:#2DD4BF; font-weight:600; text:'Run Simulation'` |

### 4.2 Loading State (during API call)

- While `POST /scenario/predict` is in flight, replace `right-content` with a loading indicator
- Do NOT clear the left panel form during loading
- Suggested: centred spinner or pulsing skeleton matching the map + timeline + card layout

### 4.3 Map — Leaflet.js

#### Map container

| Property | Value |
|---|---|
| CSS class | `.map-wrapper` |
| Dimensions | `100% width × 200px height` |
| Margin | `margin-bottom:12px` |
| Border | `1px solid rgba(51,65,85,0.4)` |
| Border radius | `14px` |
| Overflow | `hidden` |
| Inner div | `id="results-map"; width:100%; height:100%` |
| Ocean background | `.leaflet-container { background: #A8C8E8 !important }` |

#### Map initialisation

```javascript
mapInstance = L.map('results-map', {
  zoomControl: true,
  scrollWheelZoom: false
}).setView([52.5, -2.0], 5);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap',
  opacity: 0.6
}).addTo(mapInstance);
```

#### Port coordinates (exact — do not change)

| Port | Latitude | Longitude |
|---|---|---|
| Dublin | 53.3478 | -6.2297 |
| Rosslare | 52.2537 | -6.3389 |
| Heysham | 54.0333 | -2.9167 |
| Liverpool | 53.4084 | -2.9916 |
| Holyhead | 53.3094 | -4.6331 |
| Fishguard | 52.0092 | -4.9906 |
| Pembroke | 51.6833 | -4.9500 |
| Dover | 51.1279 | 1.3134 |
| Calais | 50.9513 | 1.8587 |
| Cherbourg | 49.6333 | -1.6167 |
| Rotterdam | 51.9225 | 4.4792 |
| Zeebrugge | 51.3333 | 3.1833 |

#### Port markers

| Property | Spec |
|---|---|
| Active marker size | 10px circle |
| Inactive marker size | 7px circle |
| Fill colour | `#CC2936` (red) |
| Stroke | white, 1.5px |
| Marker type | `L.divIcon` with inline SVG `<circle>` |
| Port label | `L.divIcon` — 10px bold, white text-shadow, anchor offset `[-9, 7]` |
| Label interaction | `interactive: false` |
| Port popup | `L.marker.bindPopup('<b>PortName</b>')` |

#### Route lines

| Corridor | From → To | Colour | Dash | Weight |
|---|---|---|---|---|
| East/West Maritime | Dublin → Heysham | `#1A1A2E` | none | 2px |
| East/West Maritime | Dublin → Liverpool | `#1A1A2E` | none | 2px |
| East/West Maritime | Dublin → Holyhead | `#1A1A2E` | none | 2px |
| East/West Maritime | Rosslare → Fishguard | `#1A1A2E` | none | 2px |
| East/West Maritime | Rosslare → Pembroke | `#1A1A2E` | none | 2px |
| Land-bridge | Dublin → Liverpool | `#1A1A2E` | `6 4` | 2px |
| Land-bridge | Dover → Calais | `#1A1A2E` | `6 4` | 2px |
| Direct Route | Dublin → Cherbourg | `#1A3A5C` | none | 2px |
| Direct Route | Rosslare → Cherbourg | `#1A3A5C` | none | 2px |
| Direct Route | Dublin → Rotterdam | `#1A3A5C` | none | 2px |
| Direct Route | Dublin → Zeebrugge | `#1A3A5C` | none | 2px |

#### Map corridor filtering

- `direct_gb` → show East/West Maritime lines only
- `landbridge` → show Land-bridge lines only
- `direct_cherbourg` / `direct_rotterdam` / `direct_zeebrugge` → show Direct Route lines only
- Active ports = union of all port names appearing in visible route lines
- Active ports get 10px markers; all others get 7px
- Call `mapInstance.fitBounds(activePorts, { padding: [40, 40] })` after rendering
- Always destroy previous map instance first: `mapInstance.remove()`
- Initialise inside `setTimeout(..., 50)` to allow DOM to paint

### 4.4 Journey Breakdown Timeline

#### Container `.timeline-box`

```css
.timeline-box {
  background: rgba(30,41,59,0.5);
  border-radius: 8px;
  border: 1px solid rgba(51,65,85,0.3);
  padding: 10px 12px;
  margin-bottom: 16px;
}
```

#### Timeline structure

```
┌──────────────────────────────────────────────────────────────┐
│ JOURNEY BREAKDOWN                                            │
│                                                              │
│  [●]  ─────  [🚢]  ─────  [●]  ─────  [●]                  │
│ Irish Port  18.5h  GB Port       GB East (landbridge only)   │
│  0.5h wait         0.3h wait                                 │
│                                                              │
│ Total transit time ................................ 22.4 hrs  │
└──────────────────────────────────────────────────────────────┘
```

#### Stop types

| Type | CSS | Render |
|---|---|---|
| Port stop | `.timeline-stop` | Vertical flex column: 8px circle dot + port name + wait time (if > 0) |
| Ferry segment | `.timeline-ferry` | Vertical flex: 🚢 emoji + duration e.g. `18.5h` in `#2DD4BF`, font:10px 600 |
| Separator | `.timeline-sep` | `16px × 1px; background:#475569` |

#### Stop order by route and direction

| Route | Direction | Stop order (left → right) |
|---|---|---|
| `direct_gb` | import (GB → IRE) | GB Port → 🚢 (transit hrs) → Irish Port |
| `direct_gb` | export (IRE → GB) | Irish Port → 🚢 (transit hrs) → GB Port |
| `landbridge` | import | EU Port → GB West → 🚢 → GB East → Irish Port |
| `landbridge` | export | Irish Port → 🚢 → GB West → GB East → EU Port |
| `direct_*` | import | EU Port → 🚢 (transit hrs) → Irish Port |
| `direct_*` | export | Irish Port → 🚢 (transit hrs) → EU Port |

#### Port display labels

| `destination_port` value | Display label |
|---|---|
| `dublin` | Dublin Port |
| `rosslare` | Rosslare Port |
| `liverpool` | Liverpool Port |
| `holyhead` | Holyhead Port |
| `heysham` | Heysham Port |
| `fishguard` | Fishguard Port |
| `pembroke` | Pembroke Port |
| `cherbourg` | Cherbourg Port |
| `rotterdam` | Rotterdam Port |
| `zeebrugge` | Zeebrugge Port |

#### Wait time display rules

| Condition | Display |
|---|---|
| Wait > 0 | Below port name: `X.Xh wait` — `font:10px 500 #FBBF24` (amber) |
| Wait = 0 or null | Nothing shown |

#### Wait time → API response key mapping

| API key (agri/import example) | Timeline stop |
|---|---|
| `Agri avg WT on im at D` | Irish Port wait — Dublin, import |
| `Agri avg WT on ex at D` | Irish Port wait — Dublin, export |
| `Agri avg WT on im at R` | Irish Port wait — Rosslare, import |
| `Agri avg waiting time on im at liv` | GB Port wait — Liverpool |
| `Agri avg waiting time on im at holy` | GB Port wait — Holyhead |
| `Agri avg waiting time on im at hey` | GB Port wait — Heysham |
| `Agri avg waiting time on im at fish` | GB Port wait — Fishguard |
| `Agri avg waiting time on im at pem` | GB Port wait — Pembroke |

#### Total transit time row

| Property | Value |
|---|---|
| Layout | `display:flex; justify-content:space-between; align-items:center` |
| Top separator | `border-top:1px solid rgba(51,65,85,0.3); margin-top:8px; padding-top:8px` |
| Left label | `font:400 11px #64748B; text:'Total transit time'` |
| Right value | `font:700 14px #2DD4BF; text:'X.X hrs'` |
| Value source | Sum of transportation time + all border wait times from API response |

### 4.5 KPI Cards Grid

#### Grid layout

```css
.kpi-section-title {
  font-size: 10px;
  font-weight: 600;
  color: #64748B;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 12px;
}
.kpi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
```

#### KPI card structure

| Element | Class | Spec |
|---|---|---|
| Card | `.kpi-card.kpi-{theme}` | `border-radius:10px; border:1px solid; padding:14px; display:flex; gap:10px; align-items:flex-start; animation:fadeUp 0.3s ease both` |
| Icon | `.kpi-icon` | `margin-top:2px; font-size:14px; flex-shrink:0` |
| Label | `.kpi-label` | `font:500 10px #64748B; text-transform:UPPERCASE; letter-spacing:0.05em` |
| Value | `.kpi-value` | `font:700 19px; margin-top:2px; colour=theme specific` |
| Unit | `.kpi-unit` | `font:400 11px #94A3B8; margin-left:3px` (inline after value) |
| Sub text | `.kpi-sub` | `font:400 10px #64748B; margin-top:4px` |

#### KPI card colour themes

| Theme | Background | Border | Value colour |
|---|---|---|---|
| `teal` | `rgba(20,184,166,0.1)` | `rgba(20,184,166,0.2)` | `#2DD4BF` |
| `blue` | `rgba(59,130,246,0.1)` | `rgba(59,130,246,0.2)` | `#93C5FD` |
| `amber` | `rgba(245,158,11,0.1)` | `rgba(245,158,11,0.2)` | `#FCD34D` |
| `violet` | `rgba(139,92,246,0.1)` | `rgba(139,92,246,0.2)` | `#C4B5FD` |
| `rose` | `rgba(244,63,94,0.1)` | `rgba(244,63,94,0.2)` | `#FDA4AF` |
| `green` | `rgba(34,197,94,0.1)` | `rgba(34,197,94,0.2)` | `#86EFAC` |

#### KPI cards — API response mapping

| Card label | Icon | Theme | API group | Example API key | Unit |
|---|---|---|---|---|---|
| Transport Time | ⏱ | `teal` | `results.transit` | `Transportation time agri import from GB` | hrs |
| Remaining Shelf Life | ⏳ / ⚠️ | `green` / `rose` | `results.shelf_life` | `Remaining shelflife cat import from GB` | % (×100) |
| Avg Border Wait — Irish Port | 🕐 | `amber` | `results.border_delay` | `Agri avg WT on im at D` | hrs |
| Avg Border Wait — GB Port | 🕐 | `amber` | `results.border_delay` | `Agri avg waiting time on im at liv` | hrs |
| Total Check Cost | 💶 | `blue` | `results.costs` | Sum of doc + phy + sec check cost keys | EUR |
| DAFM Bay Utilisation | 🏥 | `violet` / `rose` | `results.resource_utilisation` | `DDAFM insp bay utilisation` | % (×100) |
| Customs Utilisation | 👮 | `violet` / `rose` | `results.resource_utilisation` | `D custom shed utilisation` | % (×100) |
| Tractor Utilisation | 🚜 | `violet` / `rose` | `results.resource_utilisation` | `D tractor utilisation` | % (×100) |
| Vessel Queue — Irish Port | 🚢 | `rose` / `teal` | `results.vessel_queues` | `Trucks vessel queue length D to UK` | trucks |
| Vessel Queue — GB Port | 🚢 | `rose` / `teal` | `results.vessel_queues` | `Trucks vessel queue length liv to D` | trucks |

> **Note:** Resource utilisation values from the API are fractions (0.0–1.0). Multiply by 100 before displaying as a percentage.

#### Conditional colouring rules

**Shelf life:**
- `value < 30` → theme `rose`, icon `⚠️`
- `value >= 30` → theme `green`, icon `⏳`

**Resource utilisation:**
- `value >= 80%` → theme `rose`
- `value >= 60%` → theme `amber`
- `value < 60%` → theme `violet`

#### Handling status values

| Status | Display behaviour |
|---|---|
| `ok` | Show value normally |
| `low_coverage` | Show value with `⚠` badge appended |
| `zero_predicted` | Show `0` with sub: `No activity predicted` |
| `not_trained` | Skip card entirely (Phase 2 — not available) |
| `value: null` | Do not render the card |

#### Overall confidence badge

Shown between section title and KPI grid:

| `overall_confidence` | Badge |
|---|---|
| `high` | 🟢 High Confidence — `.delta-badge.good` |
| `medium` | 🟡 Medium Confidence — `.delta-badge.neutral` |
| `low` | 🔴 Low Confidence — `.delta-badge.bad` |

---

## 5. Right Panel — Indicators Tab

### 5.1 Filter Bar

| Element | Spec |
|---|---|
| Container `#ind-filter-bar` | `display:none` by default; `display:flex` when Indicators active; `gap:8px; flex-wrap:wrap; align-items:center; padding:12px 16px; border-bottom:1px solid var(--border); background:rgba(2,8,23,0.95); flex-shrink:0` |
| Label | `font:600 11px #94A3B8; UPPERCASE; text:'🔍 Filters'` |
| Direction select `#ind-direction` | Options: All Directions, Inbound to Ireland, Outbound from Ireland — triggers `renderIndicators()` on change |
| Corridor select `#ind-corridor` | Options: All Corridors, East/West Maritime, Land-bridge, Direct — triggers `renderIndicators()` on change |
| Date input `#ind-date` | `type=date; default=today; max=today` — triggers `renderIndicators()` on change |

**Day-of-week traffic factor** (index by `Date.getDay()` — 0 = Sunday):

```javascript
const DAY_FACTOR = [0.55, 0.92, 0.95, 0.90, 0.93, 0.88, 0.60];
```

### 5.2 Section 1 — RoRo Trade Volumes

`SectionCard('1 — RoRo Trade Volumes')` — teal border

| Element | Spec |
|---|---|
| Corridor label `.ind-corridor-label` | `font:600 10px #2DD4BF; UPPERCASE; e.g. 'IRELAND ↔ GB'` |
| Utilisation bar | `UtilBar(util, 'Daily traffic vs annual average')` where `util = Math.round(dayFactor * 100)` |
| Volume row | `IndRow('Imports → Ireland', '{X,XXX} t', 'of which agri-food: {X,XXX} t')` |

### 5.3 Section 2 — Port Capacities

`SectionCard('2 — Port Capacities', 'blue')` — blue border

| Element | Spec |
|---|---|
| Ferry rows | `IndRow(routeLabel, 'X,XXX trailers/day', 'N sailings × M trailers')` — one per ferry route |
| Ferry util bar | `UtilBar(loadFactor, 'Estimated load factor')` where `loadFactor = Math.min(dayFactor * 0.7 * 100, 99)` |
| Port card `.port-card` | `background:rgba(30,41,59,0.4); border-radius:8px; padding:12px; margin-bottom:8px` — up to 4 ports |
| Port card name `.port-card-name` | `font:600 11px #E2E8F0; margin-bottom:6px` |
| Port grid `.port-grid` | `grid 2×2; font:400 10px #64748B` — shows Customs / DAFM / Security / Tractors counts |
| Officer util bar | `UtilBar(util2, 'Est. officer utilisation')` where `util2 = Math.min(dayFactor * 85, 99)` |

### 5.4 Section 3 — Cost for Official Checks

`SectionCard('3 — Cost for Official Checks', 'amber')` — amber border

| Element | Spec |
|---|---|
| Cost card `.cost-card` | `background:rgba(30,41,59,0.4); border:1px solid rgba(245,158,11,0.1); border-radius:8px; padding:12px; margin-bottom:8px` |
| Header `.cost-header` | `flex; justify-content:space-between` |
| Port name `.cost-port` | `font:600 11px #E2E8F0` |
| Daily total `.cost-total` | `font:700 12px #FCD34D` — e.g. `€12,450 est. today` |
| Cost grid `.cost-grid` | `grid 1×2` — Documentary and Physical cost items |
| Cost item `.cost-item` | `background:rgba(15,23,42,0.6); border-radius:6px; padding:6px 8px; text-align:center` |
| Cost label | `font:400 9px #64748B` |
| Cost value | `font:700 13px #FCD34D` |
| Per truck sub | `font:400 9px #475569; text:'/truck'` |

### 5.5 Section 4 — Type of Trucks

`SectionCard('4 — Type of Trucks')`

| Element | Spec |
|---|---|
| Mix grid `.mix-grid` | `grid 1×2; gap:8px; margin-bottom:10px` |
| Card `.mix-card` | `background:rgba(30,41,59,0.5); border-radius:8px; padding:12px; text-align:center` |
| Unaccompanied % `.mix-pct` | `font:700 22px #2DD4BF` |
| Accompanied % `.mix-pct.grey` | `font:700 22px #E2E8F0` |
| Label `.mix-label` | `font:400 11px #94A3B8; margin-top:4px` |
| Util bars | Two `UtilBar`s: `Unaccompanied share` and `Accompanied share` |

---

## 6. Reusable Components

### 6.1 UtilBar

```javascript
function UtilBar(pct, label) {
  // pct >= 90 → 'red'
  // pct >= 70 → 'amber'
  // else     → 'green'
}
```

| Property | Spec |
|---|---|
| Wrapper `.util-bar-wrap` | `margin-bottom:6px` |
| Head `.util-bar-head` | `flex; justify-content:space-between; font:10px #64748B; margin-bottom:3px` |
| Track `.util-bar-track` | `height:6px; background:#1E293B; border-radius:4px; overflow:hidden` |
| Fill `.util-bar-fill.{colour}` | `height:100%; border-radius:4px; width:{pct}%; transition:width 0.8s ease` |
| Fill colours | green `#2DD4BF` / amber `#FBBF24` / red `#EF4444` |

### 6.2 DeltaBadge

```css
.delta-badge        { padding:2px 8px; border-radius:999px; font:600 11px; }
.delta-badge.good   { background:rgba(16,185,129,0.2); color:#34D399; }
.delta-badge.bad    { background:rgba(244,63,94,0.2);  color:#FB7185; }
.delta-badge.neutral{ background:rgba(51,65,85,0.8);   color:#94A3B8; }
```

### 6.3 SectionCard

```css
.ind-section        { background:rgba(15,23,42,0.6); border-radius:14px; border:1px solid rgba(20,184,166,0.2); padding:14px; margin-bottom:12px; }
.ind-section.blue   { border-color: rgba(59,130,246,0.2); }
.ind-section.amber  { border-color: rgba(245,158,11,0.2); }
.ind-section-title  { font:600 11px #94A3B8; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:10px; }
```

### 6.4 IndRow

```css
.ind-row            { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid rgba(30,41,59,0.5); font-size:11px; }
.ind-row:last-child { border-bottom: none; }
.ind-row-label      { color: #94A3B8; }
.ind-row-sub        { color: #64748B; font-size:10px; margin-top:1px; }
.ind-row-value      { font-weight:700; color:white; }
```

### 6.5 EmptyState

```javascript
function EmptyState(icon, title, body, highlightText = null)
```

- Highlight span wraps `highlightText` in `color:#2DD4BF; font-weight:600`

### 6.6 KpiCard

```javascript
function KpiCard({ icon, label, value, unit, sub, theme = 'teal', delay = 0 })
```

- `animationDelay: ${delay}s` — stagger 0.05s increments across cards

---

## 7. Chatbot (Route Advisor)

### 7.1 Toggle Button (FAB)

```css
.chat-toggle {
  position: fixed; bottom: 24px; right: 24px; z-index: 100;
  width: 54px; height: 54px; border-radius: 50%;
  background: #0D9488;
  border: none; color: white; font-size: 20px; cursor: pointer;
  box-shadow: 0 8px 24px rgba(13,148,136,0.35);
  transition: background 0.15s;
}
.chat-toggle:hover { background: #14B8A6; }
```

Icon: `💬`. Toggles `.chat-panel` between `display:none` and `display:flex`.

### 7.2 Chat Panel

```css
.chat-panel {
  position: fixed; bottom: 90px; right: 24px; z-index: 100;
  width: 370px; max-width: calc(100vw - 48px); height: 460px;
  background: #0F172A;
  border: 1px solid rgba(51,65,85,0.5); border-radius: 16px;
  box-shadow: 0 24px 48px rgba(0,0,0,0.5);
  display: flex; flex-direction: column; overflow: hidden;
}
```

Default state: `display:none`.

### 7.3 Chat Header `.chat-header`

`padding:14px 18px; border-bottom:1px solid #1E293B; display:flex; align-items:center; gap:10px`

| Element | Spec |
|---|---|
| Avatar `.chat-avatar` | `30×30px; border-radius:7px; background:rgba(13,148,136,0.2); icon:🤖; font-size:14px` |
| Name `.chat-header-name` | `font:600 13px white; text:'Route Advisor'` |
| Sub `.chat-header-sub` | `font:400 10px #64748B; text:'Ask about RoRo routes & logistics'` |

### 7.4 Messages Area

```css
.chat-messages { flex:1; overflow-y:auto; padding:14px; display:flex; flex-direction:column; gap:10px; }
.chat-msg      { display:flex; gap:7px; }
.chat-msg.user { justify-content:flex-end; }
.chat-bubble.bot  { background:#1E293B; color:#CBD5E1; max-width:80%; border-radius:12px; padding:9px 13px; font:12px/1.55; }
.chat-bubble.user { background:#0D9488; color:white; }
.chat-bot-icon { width:22px; height:22px; border-radius:5px; background:rgba(13,148,136,0.2); font-size:11px; flex-shrink:0; margin-top:2px; }
```

**Typing indicator:**

```css
.typing-dots span { width:5px; height:5px; border-radius:50%; background:#64748B; animation:blink 1.2s infinite; }
.typing-dots span:nth-child(2) { animation-delay:0.2s; }
.typing-dots span:nth-child(3) { animation-delay:0.4s; }
```

### 7.5 Chat Input Row

```css
.chat-input-row { padding:10px 14px; border-top:1px solid #1E293B; display:flex; gap:7px; }
.chat-send { width:34px; height:34px; border-radius:7px; background:#0D9488; border:none; color:white; font-size:14px; }
```

Enter key on input triggers send. Initial greeting on panel open.

### 7.6 Keyword Response Map

| Keyword | Topic |
|---|---|
| `east` / `gb` / `corridor` | East/West Maritime Corridor details |
| `land` / `bridge` | Landbridge — UK transit, Brexit friction |
| `direct` / `cherbourg` / `rotterdam` | Direct EU routes — times, pros/cons |
| `shelf` | Shelf life sensitivity by goods type |
| `cost` / `check` | Check costs — documentary vs physical |
| `sps` / `agri` / `food` | SPS checks — what they are, multiplier |
| `queue` / `wait` | Queue lengths — calculation method |
| `officer` / `dafm` / `customs` | Officer counts — effect on throughput |

---

## 8. API Integration

### 8.1 Endpoint

| Property | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8000/scenario/predict` |
| Content-Type | `application/json` |
| Auth | None (local dev) |
| Options endpoint | `GET http://localhost:8000/scenario/options` — call on page load |
| Validate endpoint | `POST http://localhost:8000/scenario/validate` — optional pre-flight |

> **CORS:** If serving the UI from a different origin than the API, add `CORSMiddleware` to `main.py`:
> ```python
> from fastapi.middleware.cors import CORSMiddleware
> app.add_middleware(CORSMiddleware, allow_origins=["*"])
> ```

### 8.2 Request Construction

```javascript
const requestBody = {
  // Required
  supplier_region:       state.config.supplier_region,
  origin_port:           state.config.origin_port,
  destination_region:    state.config.destination_region,
  destination_port:      state.config.destination_port,
  commodity_type:        state.config.commodity_type,
  direction:             state.config.direction,
  product_volume_tonnes: state.config.product_volume_tonnes,
  route_type:            state.config.route_type,
  check_regime:          state.config.check_regime,

  // Optional — omit if not set (do not send null)
  shelf_life_days:       state.config.shelf_life_days    || undefined,
  customs_officers:      state.config.customs_officers   || undefined,
  dafm_officers:         state.config.dafm_officers      || undefined,
  security_officers:     state.config.security_officers  || undefined,
  tractors:              state.config.tractors           || undefined,
  unaccompanied_pct:     state.config.unaccompanied_pct  || undefined,
};

const response = await fetch('http://localhost:8000/scenario/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(requestBody)
});

if (!response.ok) {
  const err = await response.json();
  throw new Error(`${response.status}: ${err.detail}`);
}

const data = await response.json();
state.lastResult = data;
```

### 8.3 Response Structure

```json
{
  "scenario_id": "sc_a3f2c1...",
  "corridor": "Ireland → Great Britain (Dublin → Liverpool)",
  "commodity": "agri",
  "direction": "import",
  "check_regime": "hard",
  "model_version": "v1",
  "results": {
    "transit": {
      "Transportation time agri import from GB": {
        "value": 16.9, "unit": "hours",
        "status": "ok", "phase": 1,
        "coverage_pct": 23, "r2": 0.87
      }
    },
    "border_delay":          { ... },
    "shelf_life":            { ... },
    "resource_utilisation":  { ... },
    "vessel_queues":         { ... },
    "costs":                 { ... }
  },
  "warnings": [],
  "overall_confidence": "high"
}
```

### 8.4 Error Handling

| HTTP | `error` value | UI action |
|---|---|---|
| 400 | `invalid_input` | Show in right panel: `Invalid input — {detail}` |
| 503 | `model_not_ready` | Show: `ML model not loaded. Run: python src/train.py` |
| Network error | — | Show: `Cannot connect to API. Is the server running on port 8000?` |
| Any error | — | Re-enable Run button; keep form state intact |

### 8.5 Options Endpoint — Call on DOMContentLoaded

```javascript
const optRes = await fetch('http://localhost:8000/scenario/options');
const VALID_OPTIONS = await optRes.json();

// Shape:
// {
//   supplier_region: ["ireland", "great_britain", "eu"],
//   origin_port: {
//     ireland: ["dublin", "rosslare"],
//     great_britain: ["liverpool", "holyhead", "heysham", "fishguard", "pembroke"],
//     eu: ["cherbourg", "rotterdam", "zeebrugge", "bilbao"]
//   },
//   destination_region: ["great_britain", "eu"],
//   destination_port: { great_britain: [...], eu: [...] },
//   commodity_type: ["all_products", "agri", "category"],
//   direction: ["export", "import"],
//   route_type: {
//     great_britain: ["direct_gb"],
//     eu: ["landbridge", "direct_cherbourg", "direct_rotterdam", "direct_zeebrugge", "direct_bilbao"]
//   },
//   check_regime: ["none", "light", "standard", "hard"]
// }
```

---

## 9. Application State

### 9.1 State Object

```javascript
const state = {
  config: {
    // Required API fields
    supplier_region:       "",
    origin_port:           "",
    destination_region:    "",
    destination_port:      "",
    commodity_type:        "",
    direction:             "",
    product_volume_tonnes: 0,
    route_type:            "",
    check_regime:          "",

    // Optional API fields
    shelf_life_days:    0,
    customs_officers:   null,
    dafm_officers:      null,
    security_officers:  null,
    tractors:           null,
    unaccompanied_pct:  null,

    // UI-only
    shipmentDate: new Date().toISOString().split('T')[0],
    notes: "",
  },
  hasRun:      false,   // true after first successful API call
  isLoading:   false,   // true while API call is in flight
  lastResult:  null,    // stores last ScenarioResponse
  apiError:    null,    // stores last error message string
  activeView:  "results",
};
```

### 9.2 Cascade Reset Rules

| Field changed | Fields to reset |
|---|---|
| `supplier_region` | `origin_port`, `destination_port`, `route_type` |
| `direction` | `destination_region`, `destination_port`, `route_type` |
| `destination_region` | `destination_port`, `route_type` |
| `destination_port` | `route_type` (if ambiguous) |
| Any field while `state.hasRun === true` | Re-call API after 300ms debounce → update results live |

### 9.3 Reset Behaviour

- Clears ALL config fields to initial empty/null state
- Sets `state.hasRun = false`, `state.lastResult = null`, `state.apiError = null`
- Re-renders form (empty) and results (empty state)

---

## 10. File Structure & Animations

### 10.1 File Structure

```
project/
├── index.html            ← HTML shell — keep all panel IDs intact
├── app.js                ← State, API calls, render functions
├── styles/
│   └── styles.css        ← ALL styling
├── components/
│   └── components.js     ← el(), UtilBar, KpiCard, SelectField, etc.
└── data/
    └── data.js           ← PORT_COORDS, MAP_ROUTES, display labels
                             (engine.js is REMOVED — replaced by API)
```

### 10.2 Required HTML IDs

| ID | Element | Purpose |
|---|---|---|
| `app` | `div` | Outer wrapper |
| `form-body` | `div.form-body` | Dynamic form fields |
| `form-footer` | `div.form-footer` | Run / Reset buttons |
| `right-content` | `div.panel-scroll` | All results / indicators content |
| `ind-filter-bar` | `div.ind-filters` | Indicator filter bar |
| `results-map` | `div` (created in right-content) | Leaflet map container |
| `chat-panel` | `div.chat-panel` | Chatbot panel |
| `chat-messages` | `div.chat-messages` | Message thread |
| `chat-input` | `input` | Chat text input |
| `ind-direction` | `select` | Indicators direction filter |
| `ind-corridor` | `select` | Indicators corridor filter |
| `ind-date` | `input[date]` | Indicators date filter |

### 10.3 Animations

```css
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes blink {
  0%, 80%, 100% { opacity: 0.2; }
  40%           { opacity: 1; }
}
```

| Animation | Applied to | Timing |
|---|---|---|
| `fadeUp` | KPI cards | `0.3s ease both`; staggered `0.05s` per card |
| `blink` | Chatbot typing dots | `1.2s infinite`; delays `0s`, `0.2s`, `0.4s` |
| Util bar fill | `.util-bar-fill` | `transition: width 0.8s ease` |
| Button hover | Run, Reset, chat FAB, send | `transition: background 0.15s` |
| Input focus ring | All inputs / selects | `transition: border-color 0.15s` |

### 10.4 Scrollbar Styling

```css
::-webkit-scrollbar       { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
```

### 10.5 Responsive Breakpoint

```css
@media (max-width: 640px) {
  .left-panel  { width: 100%; border-right: none; }
  .app-body    { flex-direction: column; }
  .kpi-grid    { grid-template-columns: 1fr; }
  .tab-bar     { display: none; }
}
```

---

## 11. Cursor Implementation Checklist

> Work through these phases in order. Keep `uvicorn main:app --port 8000 --reload` running throughout. Each item is independently testable.

### Phase A — Project Setup

- [ ] Create `ui/` subfolder inside `brexit_ml/` project
- [ ] Copy 5 files from base44 ZIP: `index.html`, `app.js`, `styles/styles.css`, `components/components.js`, `data/data.js`
- [ ] Delete `data/engine.js` — all calculations now come from the API
- [ ] Verify `index.html` has all required IDs from §10.2
- [ ] Confirm Leaflet 1.9.4 CSS + JS CDN links are in `<head>`
- [ ] Confirm `GET http://localhost:8000/scenario/options` returns valid JSON

### Phase B — State & Options Wiring

- [ ] Redefine `state` object per §9.1 — new API field names
- [ ] On `DOMContentLoaded`: call `GET /scenario/options`, store as `VALID_OPTIONS`
- [ ] Implement cascade reset rules from §9.2 in the `update()` function

### Phase C — Input Form Rebuild

- [ ] Field 1: Shipment Date — `DateField`, default today
- [ ] Field 2: Supplier Region — `SelectField` from `VALID_OPTIONS.supplier_region`
- [ ] Field 3: Origin Port — conditional on `supplier_region`; options from `VALID_OPTIONS.origin_port[supplier_region]`
- [ ] Field 4: Direction — `SelectField`: `export` \| `import`
- [ ] Field 5: Destination Region — conditional on `direction`
- [ ] Field 6: Destination Port — conditional on `destination_region`; options from `VALID_OPTIONS.destination_port[destination_region]`
- [ ] Field 7: Commodity Type — from `VALID_OPTIONS.commodity_type`
- [ ] Field 8: Route Type — conditional on `destination_region`; options from `VALID_OPTIONS.route_type[destination_region]`; Phase 2 options shown as disabled
- [ ] Field 9: Check Regime — from `VALID_OPTIONS.check_regime`
- [ ] Field 10: Product Volume — `NumberField`, min 1, hint shows approx truck count
- [ ] Field 11: Shelf Life — `NumberField`, optional
- [ ] Fields 12–16: Advanced Options collapsible — customs/dafm/security officers, tractors, unaccompanied %
- [ ] Run button: disabled until all 9 required fields are set
- [ ] Error hint: list missing required fields below the button
- [ ] Reset button: shown after first run; clears all state

### Phase D — API Call

- [ ] Implement `async runSim()` — set `state.isLoading = true`; show loading indicator
- [ ] Build `requestBody` from `state.config` per §8.2 — omit optional fields if not set
- [ ] `POST` to `/scenario/predict`
- [ ] On success: store in `state.lastResult`; set `state.hasRun = true`; call `renderResults()`
- [ ] On 400: show `Invalid input — {detail}`
- [ ] On 503: show `ML model not loaded. Run: python src/train.py`
- [ ] On network error: show `Cannot connect to API on port 8000`
- [ ] Always: set `state.isLoading = false`; re-enable Run button on error

### Phase E — Map

- [ ] Update `PORT_COORDS` in `data.js` — all 12 ports with exact values from §4.3
- [ ] Update `MAP_ROUTES` in `data.js` — all 11 routes with corridor, colour, dash from §4.3
- [ ] `buildMap(containerId, routeType)`: filter routes by corridor from `route_type`
- [ ] Active ports (in filtered routes) get 10px markers; inactive get 7px
- [ ] Port labels: 10px bold, offset `[-9, 7]`, `interactive:false`
- [ ] Call `fitBounds` on active ports with `[40, 40]` padding
- [ ] Initialise map inside `setTimeout(..., 50)`
- [ ] Destroy previous `mapInstance` before creating a new one

### Phase F — Journey Breakdown Timeline

- [ ] Read transport time from `state.lastResult.results.transit`
- [ ] Read wait times from `state.lastResult.results.border_delay` using §4.4 key mapping
- [ ] Determine stop order from `route_type` + `direction` per §4.4 table
- [ ] Render port stops: circle dot + label + amber wait time (if > 0)
- [ ] Render ferry segments: 🚢 + `Xh` in `#2DD4BF`
- [ ] Render separators between stops
- [ ] Total transit row: sum all times; display in `#2DD4BF`

### Phase G — KPI Cards

- [ ] Render `Key Performance Indicators` section title
- [ ] Render `overall_confidence` badge above the grid
- [ ] Map API response groups to KPI cards per §4.5 table
- [ ] Apply correct colour theme per card type
- [ ] Shelf life: green if ≥ 30%, rose + `⚠️` if < 30%
- [ ] Resource utilisation: convert 0.0–1.0 → %; violet < 60%, amber 60–80%, rose > 80%
- [ ] Skip cards where `value` is `null` or `status` is `not_trained`
- [ ] Append `⚠` to value when `status` is `low_coverage`
- [ ] Apply staggered `fadeUp` animation (0.05s increments per card)

### Phase H — Indicators Tab

- [ ] Tab click shows `ind-filter-bar`; calls `renderIndicatorsWithFilters()`
- [ ] Filter bar: direction + corridor + date selects all trigger re-render
- [ ] Section 1: RoRo Trade Volumes with day-of-week factor
- [ ] Section 2: Port Capacities — ferry daily capacity + port staff cards
- [ ] Section 3: Costs for Official Checks — cost cards per port
- [ ] Section 4: Type of Trucks — mix grid + util bars

### Phase I — Chatbot

- [ ] FAB `💬` button: fixed bottom-right, toggles panel
- [ ] Panel: 370×460px, dark, `border-radius:16px`
- [ ] Initial greeting message on open
- [ ] User input + send button (Enter key also triggers send)
- [ ] Typing indicator (3 animated dots) while processing
- [ ] Keyword matching per §7.6 response map
- [ ] Auto-scroll to bottom after each message

### Phase J — Polish & Verification

- [ ] Scrollbars: 4px, `#334155` thumb
- [ ] All animations working: `fadeUp`, `blink`, util bar fill transition
- [ ] Responsive: 640px breakpoint — single column layout
- [ ] Full round trip test: fill all required fields → Run → map, timeline, KPIs all populate correctly
- [ ] Error state tests: 400 invalid input, 503 model not ready, network error
- [ ] Reset test: form clears, results clear, Run button disables

---

*End of specification. All UI structure derived from the Brexit base44 version prototype. API contract from `POST /scenario/predict` at `http://localhost:8000`.*
