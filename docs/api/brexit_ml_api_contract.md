# Brexit ML Engine — API contract (UI / frontend)

**Service:** FastAPI + Uvicorn  
**Default base URL (local):** `http://localhost:8000`  
**JSON:** request/response bodies are `application/json` unless noted.  
**Auth:** none (local dev).  
**CORS:** `main.py` enables permissive CORS for local dev (alternate static servers / `file://`).

**UI bundled with API:** run `uvicorn main:app` from `brexit_ml/` and open **http://127.0.0.1:8000/** — static files from `ui/` are mounted at `/` (same origin as `/scenario/*`).

**OpenAPI:** interactive docs at `GET /docs` and raw schema at `GET /openapi.json` (always use these for field-level detail).

---

## 1. Semantic API (wizard / end-user)

These routes are the primary surface for a UI: seven semantic dimensions → KPI predictions.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/scenario/predict` | Full prediction for one scenario |
| `POST` | `/scenario/validate` | Validate payload (and Phase 1 rules) without running models |
| `GET` | `/scenario/options` | Dropdown values / dependent lists (`VALID_OPTIONS`) |
| `GET` | `/scenario/schema` | Wizard step metadata + JSON Schema for `ScenarioRequest` |

### 1.1 `POST /scenario/predict`

**Request body:** `ScenarioRequest` (see §1.3).

**200 response:** `ScenarioResponse`

```json
{
  "scenario_id": "sc_<hash>",
  "corridor": "Great Britain → Ireland (liverpool → dublin)",
  "commodity": "agri",
  "direction": "import",
  "check_regime": "hard",
  "model_version": "v1",
  "results": {
    "transit": { "<display name>": { "value": 16.9, "unit": "hours", "status": "ok", "phase": 1, "coverage_pct": 23, "r2": 0.87 } },
    "border_delay": { },
    "shelf_life": { },
    "resource_utilisation": { },
    "vessel_queues": { },
    "costs": { }
  },
  "warnings": [],
  "overall_confidence": "high"
}
```

- **`results`** keys are **group ids** (e.g. `transit`, `border_delay`, `shelf_life`, `resource_utilisation`, `vessel_queues`, `costs`). Inner keys are **human-readable KPI names** (not slugs).
- **`PredictionResult` per KPI:**

| Field | Type | Notes |
|-------|------|--------|
| `value` | number \| null | `null` when `status` is `not_trained` |
| `unit` | string | e.g. `hours`, `EUR`, `fraction`, `trucks` |
| `status` | string | `ok` \| `low_coverage` \| `zero_predicted` \| `not_trained` |
| `phase` | 1 \| 2 | Phase 2 outputs may be `not_trained` in v1 |
| `coverage_pct` | 0–100 | Training coverage |
| `r2` | number \| null | CV R²; null if not trained |

- **`overall_confidence`:** `high` \| `medium` \| `low` (derived from returned KPI statuses; see spec §23).

**Error responses (semantic layer):**

| HTTP | When | Body shape |
|------|------|------------|
| 400 | Invalid body, Pydantic validation, or **Phase 1 scenario not allowed** | `{ "error": "invalid_input", "detail": "<message>" }` |
| 503 | Models missing (`models/v1/` not trained) | `{ "error": "model_not_ready", "detail": "..." }` |

**Phase 1 (v1) behaviour:** only **IRE ↔ Great Britain** scenarios with `route_type: "direct_gb"` and **Section 19** port pairs are accepted. Other combinations return **400** `invalid_input` (see `phase1_scenarios` + spec §19).

---

### 1.2 `POST /scenario/validate`

**Request body:** same shape as `ScenarioRequest` (full object recommended).

**200 (success):**

```json
{
  "valid": true,
  "warnings": [],
  "active_corridor": "IRE_GB"
}
```

- **`active_corridor`:** coarse label when validation passes; with models loaded, derived from translated `Vol*` inputs; without models, `IRE_GB` when `route_type` is `direct_gb`.

**400 (validation failure):**

```json
{
  "valid": false,
  "errors": [ "<message or Pydantic error detail>" ]
}
```

---

### 1.3 `ScenarioRequest` — fields for forms

**Required (Pydantic — must be present in every `POST /scenario/predict` and `POST /scenario/validate` body)**

These nine keys are non-optional in `ScenarioRequest` (`brexit_ml/src/schemas.py`). Omitting any of them yields **422** validation errors from FastAPI.

| # | Field | Type | Notes |
|---|-------|------|--------|
| 1 | `supplier_region` | `"ireland"` \| `"great_britain"` \| `"eu"` | |
| 2 | `origin_port` | port enum | Allowed values depend on `supplier_region`; see `GET /scenario/options` → `origin_port` |
| 3 | `destination_region` | `"ireland"` \| `"great_britain"` \| `"eu"` | |
| 4 | `destination_port` | port enum | Allowed values depend on `destination_region`; see `GET /scenario/options` → `destination_port` |
| 5 | `commodity_type` | `"all_products"` \| `"agri"` \| `"category"` | |
| 6 | `direction` | `"export"` \| `"import"` | Irish perspective: export = goods leaving Ireland; import = goods arriving in Ireland |
| 7 | `product_volume_tonnes` | number, **> 0** | Single shipment volume in tonnes |
| 8 | `route_type` | see below | Phase 1 only `direct_gb` is accepted by predict |
| 9 | `check_regime` | `"none"` \| `"light"` \| `"standard"` \| `"hard"` | |

**JSON Schema:** `GET /scenario/schema` → `scenario_request_schema.required` matches the list above (order may differ).

**Phase 1 (v1) — required *plus* allowed combinations**

Even with all nine fields present, **400** `invalid_input` applies unless:

- `route_type` is exactly `"direct_gb"`.
- Neither `supplier_region` nor `destination_region` is `"eu"`.
- **Export:** `supplier_region` = `ireland`, `destination_region` = `great_britain`, and `(origin_port, destination_port)` is one of the §19 pairs (e.g. `dublin` → `liverpool`).
- **Import:** `supplier_region` = `great_britain`, `destination_region` = `ireland`, and `(origin_port, destination_port)` is the reverse of a §19 pair (e.g. `liverpool` → `dublin`).

**Minimal valid Phase 1 bodies (nine required keys only)**

Import (GB → Ireland), schema-valid and Phase 1–valid:

```json
{
  "supplier_region": "great_britain",
  "origin_port": "liverpool",
  "destination_region": "ireland",
  "destination_port": "dublin",
  "commodity_type": "all_products",
  "direction": "import",
  "product_volume_tonnes": 100,
  "route_type": "direct_gb",
  "check_regime": "standard"
}
```

Export (Ireland → GB):

```json
{
  "supplier_region": "ireland",
  "origin_port": "dublin",
  "destination_region": "great_britain",
  "destination_port": "liverpool",
  "commodity_type": "all_products",
  "direction": "export",
  "product_volume_tonnes": 100,
  "route_type": "direct_gb",
  "check_regime": "standard"
}
```

Optional fields (officers, `shelf_life_days`, costs, etc.) can be added; the translator applies defaults when they are omitted.

**`route_type` values**

| Value | Phase (v1) |
|-------|------------|
| `direct_gb` | Phase 1 — supported for IRE↔GB |
| `landbridge`, `direct_cherbourg`, `direct_rotterdam`, `direct_zeebrugge`, `direct_bilbao` | Phase 2 — **rejected** at semantic predict/validate until enabled |

**Optional (defaults filled by translator if omitted)**

| Field | Constraints |
|-------|-------------|
| `vessel_capacity_trailers` | int ≥ 1 |
| `physical_check_pct` | 0..1 |
| `physical_check_time_mins` | int ≥ 0 |
| `doc_check_time_mins` | int ≥ 0 |
| `security_check_pct` | 0..1 |
| `security_check_time_mins` | int ≥ 0 |
| `customs_officers`, `dafm_officers`, `security_officers`, `tractors` | int ≥ 0 |
| `shelf_life_days` | > 0 |
| `unaccompanied_pct` | 0..1 |
| `doc_check_cost_eur`, `phy_check_cost_eur`, `sec_check_cost_eur` | ≥ 0 |

**Dropdowns:** use `GET /scenario/options` (same structure as `VALID_OPTIONS` in `schemas.py`). Dependent fields: `origin_port` and `destination_port` are keyed by region; `route_type` is keyed under `great_britain` vs `eu`.

---

### 1.4 `GET /scenario/options`

Returns the `VALID_OPTIONS` object for building cascading dropdowns.

### 1.5 `GET /scenario/schema`

Returns:

- `wizard_steps`: ordered steps with field name lists (labels for UX).
- `scenario_request_schema`: JSON Schema for `ScenarioRequest` (types, enums, required).

### 1.6 Local dev — run UI and hit the model

From the **`brexit_ml/`** directory (models trained under `models/v1/`):

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

1. Open **http://127.0.0.1:8000/** (or **http://localhost:8000/**).
2. Set **Supplier** → Ireland or Great Britain (Phase 1), complete **origin**, **direction**, **destination**, **commodity**, **route type** (`direct_gb`), **regime**, **tonnes** (≥ 1).
3. Click **Run Simulation**. The page calls `GET /scenario/options` then `POST /scenario/predict`.
4. Expect: loading state, then **corridor** line, **journey timeline** (if transit/border keys exist), **KPI cards** under `results` groups (`transit`, `border_delay`, …). If the API returns **503**, train models first (`python src/train.py` from `brexit_ml/` per health detail).

Automated check for the predict **JSON shape** the UI expects: `pytest tests/test_ui_predict_flow.py` (skips when `models/v1/registry.json` is missing).

---

## 2. Raw ML API (advanced / debugging)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Model registry health |
| `POST` | `/predict` | Predict all 136 outputs from **raw** AnyLogic input dict (153 keys) |
| `POST` | `/predict/selective` | Predict subset: `{ "outputs": ["<slug>", ...], "<input>": ... }` |
| `GET` | `/outputs` | List outputs + registry metadata |
| `GET` | `/inputs` | List 153 inputs + typical values |

**503** if `models/v1/` is missing: `{ "error": "model_not_ready", "detail": "..." }`.

**`/predict` response:** map of **slug** → `PredictionResult` (same shape as inside semantic `results`, but keys are slugs like `transportation_time_agri_import_from_gb`).

---

## 3. References in this repo

| Doc | Path |
|-----|------|
| Full spec | `docs/ml/spec/brexit_ml_engine_spec.md` |
| Pydantic models | `brexit_ml/src/schemas.py` |
| Phase 1 journeys | spec §19 |
| UI smoke (Node loads `app.js` + imports) | `brexit_ml/ui/scripts/smoke-load-app.mjs` — from **repo root**: `node brexit_ml/ui/scripts/smoke-load-app.mjs` and `pytest brexit_ml/tests/test_ui_app_smoke.py`; from **`brexit_ml/`** cwd: `node ui/scripts/smoke-load-app.mjs` and `pytest tests/test_ui_app_smoke.py` (requires Node on `PATH`) |
| UI ↔ ML predict shape (integration) | `pytest tests/test_ui_predict_flow.py` (from **`brexit_ml/`**; needs trained `models/v1/`) |

---

*Generated for frontend handoff; behaviour matches `brexit_ml` implementation as of the repo version that contains this file.*
