# LLM integration and persona layer — design

**Goal:** A layer that reads **only structured pipeline outputs** (metrics, conformal intervals, SHAP CSV) and drives an LLM in **persona-appropriate** language, with **session memory** so answers stay consistent with earlier numbers.

**Non-goals:** No scraping PDFs, slide decks, or arbitrary web text. Facts enter only via the fixed schema assembled from `experimenting_ml/outputs/*.json` and `step4_shap/*__importance.csv`.

---

## 1. Fixed schema (`AttributionSnapshot`)

Implemented in `experimenting_ml/src/llm_attribution/schema.py` (Pydantic).

| Field | Source |
|--------|--------|
| `target` | Argument + `test_results.json` |
| `selected_model` | `step4_shap/shap_selected_models.csv` or override |
| `metrics` | `test_results.json` + `cv_results.json` (test RMSE/MAE/R²; CV mean/std RMSE) |
| `interval_90` | `conformal_results.json` row for the selected model (nominal `coverage_level`, `quantile` as half-width, `interval_width`, `empirical_coverage`, `relative_rmse_to_best`) |
| `top_shap_features` | `step4_shap/<target>__<model>__importance.csv` (top‑k by mean \|SHAP\|) |
| `residual_summary` | Derived from `test_results.json` residuals for that model |
| `caveats` | Short static + design-appropriate strings (NOLHC *n*, conformal interpretation) |
| `modelling_context` | `split_meta.json` (`n_train`, `n_test`); `shap_selected_models.csv` (selection policy, explain split) |

**Note:** The field name `interval_90` reflects the usual reporting band; the pipeline uses **adaptive nominal coverage** per model, so `nominal_coverage` may be 0.9, 0.95, or 0.99 — always read `nominal_coverage` in the JSON.

---

## 2. Personas

Defined in `experimenting_ml/src/llm_attribution/personas.py`.

| `persona_id` | Audience |
|----------------|----------|
| `executive` | CSCO / COO — strategy, resilience, investment framing; minimal jargon |
| `risk_compliance` | Trade compliance — interval width, coverage, limitations, no false guarantees |
| `operations` | Freight ops — levers, dwell/route language, near-term actions |
| `analyst_methods` | Data science — SHAP, CV, test size, composite vs `composite_pre_test` caveats |

The **system** message sets tone; the **user** message always includes the full `AttributionSnapshot` JSON plus `USER_QUESTION`.

---

## 3. Session persistence

`experimenting_ml/src/llm_attribution/session_store.py` — `FileSessionStore(base_dir)`:

- One file per `thread_id`: `{thread_id}.json`
- Fields: `target`, `last_snapshot` (dict), `turns` (list of `{user, assistant}`)

On each turn, reload or create the session, pass prior `turns` into `build_messages` when you implement multi-turn (extend `prompting.py` to thread history).

---

## 4. Building prompts

`build_messages(persona_id, snapshot, user_message, prior_turns=None)` returns OpenAI-style `messages[]`.

**LLM call (your integration):** Send `messages` to your provider; **do not** add RAG or PDF tools for this path.

---

## 5. Testing strategy

1. **Assembler integration:** `python -m unittest experimenting_ml.tests.test_llm_attribution` (requires `outputs/` artefacts).
2. **Golden numeric fidelity:** `golden_numeric_fidelity(assistant_text, snapshot)` — flags if headline numbers from the snapshot are absent from the assistant reply (mitigates hallucinated metrics).
3. **Scripted prompts:** For each persona, fixed questions, e.g. *“Explain this target”*, *“What could go wrong?”*, *“What changes if we exclude feature X?”* — the last question requires either a second snapshot with feature X removed from `top_shap_features` only (weak) or a **counterfactual re-run** of SHAP (not implemented here); document that true exclusion needs a new model fit or SHAP run.

---

## 6. CLI (no API key)

```bash
cd experimenting_ml
python run_llm_attribution_snapshot.py --target TT_OB_Agri
python run_llm_attribution_snapshot.py --target TT_OB_Agri --persona analyst_methods --question "Summarize uncertainty."
```

---

## 7. Dependencies

`pydantic>=2` added to `experimenting_ml/requirements.txt` for schema validation and JSON export.
