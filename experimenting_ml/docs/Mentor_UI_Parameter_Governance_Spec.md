# Mentor Note: UI Parameter Governance and Reliability Guardrails

**Project:** NOLHC ML Decision Intelligence  
**Purpose:** Define scenario-specific editable inputs, defaulting behavior, slider bounds, and reliability guardrails before final deployment.

---

## 1) Context

The surrogate ML stack predicts **20 targets** from **35 inputs** using NOLHC data (**129 rows**).  
For mentor/professor usage, the UI should expose only scenario-relevant controls and prevent unrealistic manual inputs.

This note defines a policy to:
- keep scenario interaction consistent and interpretable,
- preserve physically meaningful input combinations,
- keep user inputs near the calibrated model domain,
- improve reliability of predictions shown to reviewers.

---

## 2) Scenario-Family Editable Matrix

## 2.1 Direct Route Scenario Family (confirmed)

### Shifts in Trade Volume
- **Policy:** locked (not user-editable in this scenario family).

### Direct Routes to Mainland Europe
- **Policy:** only the predefined route-split parameters are editable:
  - `NA_Im_LB`
  - `NA_Im_DR`
  - `NA_Ex_LB`
  - `NA_Ex_DR`
  - `A_Im_LB`
  - `A_Im_DR`
  - `A_Ex_LB`
  - `A_Ex_DR`

### Customs Expertise & Resources
- **Policy:** all parameters editable.

### Border Checks & Intervention
- **Policy:** all parameters editable.

## 2.2 Non-Tariff Barrier Scenario Family (to be signed off)

Apply the same matrix structure (editable vs locked vs derived) and finalize exact keys with mentor approval.  
Implementation should not proceed for this family until the mapping table is signed off.

---

## 3) Default Value Policy

For each scenario family and level (`As-Is`, `Scenario 1`, `Scenario 2`):

1. **Editable parameters**
   - default to the selected scenario-level value from workbook/preset.
   - user may modify within allowed slider bounds.

2. **Locked parameters**
   - shown as read-only (visible for transparency).
   - always set by the selected scenario-level default (no user override).

3. **Derived parameters**
   - auto-computed from governing inputs (for consistency constraints, e.g., corridor splits).
   - not directly editable.

This ensures full reproducibility of scenario inputs and avoids hidden state.

---

## 4) Slider Bounds and Reliability Statement

## 4.1 What slider ranges represent

Slider min/max should be based on the calibrated feature domain used by the inference stack:
- training-data support (from NOLHC dataset),
- optionally expanded/validated by scenario workbook bounds,
- then clipped to physically valid ranges (fractions, counts, times, capacities).

## 4.2 Correct interpretation (important)

Being inside slider min/max **improves plausibility**, but does **not guarantee equal prediction accuracy everywhere**.  
With 129 samples, reliability is strongest near dense regions of observed training combinations.

Recommended wording for reviewers:

> “Predictions are most reliable within the calibrated operating domain derived from training and workbook bounds. Inputs are constrained in UI to reduce unrealistic scenarios; uncertainty intervals remain available for decision support.”

---

## 5) UI Behavior Requirements

1. Scenario-family selection activates the approved mapping.
2. UI displays an “editable count” summary (e.g., `Editable 21 / 35`).
3. Locked controls are visible, disabled, and tagged with reason.
4. All editable controls use bounded sliders (same governance in both Scenario Controls and Decision Intelligence page).
5. Full 35-feature vector is still sent to inference API (editable + locked + derived) so all **20 targets** are predicted.

---

## 6) Validation Checklist Before Deployment

- [ ] Direct Route mapping exactly matches approved list above.
- [ ] Non-Tariff mapping table is signed off.
- [ ] Locked fields cannot be changed via UI interaction.
- [ ] Derived fields remain internally consistent.
- [ ] No out-of-bound payload reaches `/api/predict`.
- [ ] 20/20 targets return for all scenario families and levels.
- [ ] UI labels clearly specify inbound/outbound, import/export, and Dublin/Rosslare context.

---

## 7) Recommendation

Proceed with bounded sliders and scenario-specific editable matrices in both UI surfaces.  
This is the right balance of realism, reliability, and auditability for university-board review.

