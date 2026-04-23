/**
 * ============================================================
 *  UI COMPONENTS — components.js
 *  Small reusable pieces of the interface.
 *  Nothing here knows about data — it just renders what it's given.
 * ============================================================
 */

import { GOODS_ICONS } from "../data/data.js";

// ── Tooltip (NOLHC_ML_UI_Spec.md §4) ───────────────────────────
export function TooltipIcon(text) {
  const wrap = el("span", { class: "tooltip-wrap" });
  const icon = el("span", { class: "tooltip-icon" }, "ℹ");
  const popup = el("div", { class: "tooltip-popup" }, text);
  wrap.append(icon, popup);
  return wrap;
}

// ── Utility: create a DOM element easily ──────────────────────
export function el(tag, attrs = {}, ...children) {
  const elem = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "class") elem.className = v;
    else if (k === "style") Object.assign(elem.style, v);
    else if (k.startsWith("on")) elem.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "disabled" || k === "checked" || k === "readonly" || k === "required") {
      if (v) elem.setAttribute(k, "");
      else elem.removeAttribute(k);
    } else elem.setAttribute(k, v);
  });
  children.forEach(c => {
    if (c == null) return;
    elem.append(typeof c === "string" ? document.createTextNode(c) : c);
  });
  return elem;
}

// ── Utilisation Bar ───────────────────────────────────────────
// Renders a labelled progress bar — green/amber/red based on value.
export function UtilBar(pct, label) {
  const colour = pct >= 90 ? "red" : pct >= 70 ? "amber" : "green";
  const wrap  = el("div", { class: "util-bar-wrap" });
  const head  = el("div", { class: "util-bar-head" },
    el("span", {}, label),
    el("span", { class: colour }, `${pct}%`)
  );
  const track = el("div", { class: "util-bar-track" });
  const fill  = el("div", { class: `util-bar-fill ${colour}`, style: { width: `${pct}%` } });
  track.append(fill);
  wrap.append(head, track);
  return wrap;
}

// ── Delta Badge ───────────────────────────────────────────────
// Shows % change between two values. Green = better, red = worse.
export function DeltaBadge(valueA, valueB, lowerIsBetter = false) {
  const a = parseFloat(valueA), b = parseFloat(valueB);
  if (isNaN(a) || isNaN(b) || a === 0) return null;

  const diff    = ((b - a) / Math.abs(a)) * 100;
  const absDiff = Math.abs(diff).toFixed(1);

  if (Math.abs(diff) < 0.1) {
    return el("span", { class: "delta-badge neutral" }, "≈ No change");
  }

  const isGood  = lowerIsBetter ? diff < 0 : diff > 0;
  const cls     = isGood ? "good" : "bad";
  const icon    = diff > 0 ? "↑" : "↓";
  const sign    = diff > 0 ? "+" : "";

  return el("span", { class: `delta-badge ${cls}` }, `${icon} ${sign}${absDiff}%`);
}

// ── KPI Card ──────────────────────────────────────────────────
// One card in the results dashboard.
export function KpiCard({ icon, label, value, unit, sub, theme = "teal", delay = 0, tooltip = null }) {
  const card = el("div", { class: `kpi-card kpi-${theme}`, style: { animationDelay: `${delay}s` } });

  const iconEl = el("div", { class: "kpi-icon" }, icon);
  const body   = el("div", {});
  const lbl    = el("div", { class: "kpi-label" }, label);
  if (tooltip) lbl.append(TooltipIcon(tooltip));
  const valRow = el("div", {});
  const valEl  = el("span", { class: "kpi-value" }, String(value));
  const unitEl = unit ? el("span", { class: "kpi-unit" }, unit) : null;
  valRow.append(valEl);
  if (unitEl) valRow.append(unitEl);
  body.append(lbl, valRow);
  if (sub) body.append(el("div", { class: "kpi-sub" }, sub));

  card.append(iconEl, body);
  return card;
}

// ── Select Field ──────────────────────────────────────────────
// A labelled dropdown for the form.
export function SelectField({ id, label, required, options, value, placeholder, onChange, disabled = false, tooltip = null }) {
  const wrap    = el("div", { class: "form-field" });
  const lbl     = el("label", { class: "form-label", for: id }, label);
  if (required) lbl.append(el("span", { class: "required" }, " *"));
  if (tooltip) lbl.append(TooltipIcon(tooltip));

  const sel = el("select", { id });
  sel.disabled = disabled;
  if (disabled) sel.style.opacity = "0.4";

  if (placeholder) sel.append(el("option", { value: "" }, placeholder));
  options.forEach(opt => {
    const isObj  = typeof opt === "object";
    const optVal = isObj ? opt.value : opt;
    const optLbl = isObj ? opt.label : opt;
    const o = el("option", { value: optVal }, optLbl);
    if (isObj && opt.disabled) o.disabled = true;
    if (optVal === value) o.selected = true;
    sel.append(o);
  });

  sel.addEventListener("change", () => onChange(sel.value));
  wrap.append(lbl, sel);
  return wrap;
}

// ── Number Input Field ────────────────────────────────────────
export function NumberField({
  id,
  label,
  required,
  value,
  placeholder,
  min = 0,
  max,
  step,
  onChange,
  hint = null,
  nullable = false,
  /** `type="text"` + `inputmode="decimal"` — free typing, no mobile number stepper. */
  usePlainText = false,
  tooltip = null,
  /** Leading emoji / symbol for parameter type (agri, commodity, ship, officer, …). */
  fieldIcon = null,
  /** Staggered entrance delay in ms (left-panel field animations). */
  staggerMs = null,
}) {
  const wrapClasses = ["form-field", "form-field--enter"];
  if (fieldIcon) wrapClasses.push("form-field--has-type-icon");
  const wrap = el("div", { class: wrapClasses.join(" ") });
  if (staggerMs != null && staggerMs >= 0) wrap.style.animationDelay = `${staggerMs}ms`;

  const lblRow = el("div", { class: "form-label-row" });
  if (fieldIcon) {
    lblRow.append(el("span", { class: "form-field-type-icon", "aria-hidden": "true", title: "" }, fieldIcon));
  }
  const lbl = el("label", { class: "form-label", for: id }, label);
  if (required) lbl.append(el("span", { class: "required" }, " *"));
  if (tooltip) lbl.append(TooltipIcon(tooltip));
  lblRow.append(lbl);
  wrap.append(lblRow);

  const inp = el("input", {
    id,
    type: usePlainText ? "text" : "number",
    placeholder,
    autocomplete: "off",
  });
  if (!usePlainText) {
    inp.min = String(min);
    if (max != null) inp.max = String(max);
    if (step != null) inp.step = String(step);
  } else {
    inp.setAttribute("inputmode", "decimal");
    inp.setAttribute("enterkeyhint", "done");
  }
  if (value !== "" && value != null) inp.value = value;
  inp.addEventListener("input", () => {
    const raw = inp.value.trim();
    if (raw === "" && nullable) {
      onChange(null);
      return;
    }
    const n = parseFloat(raw.replace(",", "."));
    onChange(Number.isFinite(n) ? n : 0);
  });

  const shell = el("div", { class: "form-input-shell" });
  shell.append(inp);
  wrap.append(shell);
  if (hint) {
    const hintEl = el("div", { class: "hint-text" });
    hintEl.textContent = hint;
    hintEl.id = id + "-hint";
    wrap.append(hintEl);
  }
  return { wrap, inp };
}

// ── Date Input Field ──────────────────────────────────────────
export function DateField({ id, label, value, max, onChange }) {
  const wrap = el("div", { class: "form-field" });
  const lbl  = el("label", { class: "form-label", for: id }, label);
  const inp  = el("input", { id, type: "date", value, max });
  inp.addEventListener("change", () => onChange(inp.value));
  wrap.append(lbl, inp);
  return wrap;
}

// ── Section Card (for Indicators) ────────────────────────────
export function SectionCard(title, theme = "", ...children) {
  const div = el("div", { class: `ind-section ${theme}` });
  const ttl = el("div", { class: "ind-section-title" }, title);
  div.append(ttl, ...children);
  return div;
}

// ── Indicator Row ─────────────────────────────────────────────
export function IndRow(label, value, sub = null) {
  const row = el("div", { class: "ind-row" });
  const left = el("div", {});
  left.append(el("div", { class: "ind-row-label" }, label));
  if (sub) left.append(el("div", { class: "ind-row-sub" }, sub));
  row.append(left, el("div", { class: "ind-row-value" }, String(value)));
  return row;
}

// ── Empty State ───────────────────────────────────────────────
export function EmptyState(icon, title, body, highlightText = null) {
  const wrap = el("div", { class: "empty-state" });
  const iconDiv = el("div", { class: "empty-icon" }, icon);
  const h3 = el("h3", {}, title);
  const p  = el("p", {});

  if (highlightText) {
    const parts = body.split(highlightText);
    p.append(parts[0]);
    p.append(el("span", { class: "highlight" }, highlightText));
    if (parts[1]) p.append(parts[1]);
  } else {
    p.textContent = body;
  }

  wrap.append(iconDiv, h3, p);
  return wrap;
}

// ── Goods Type Badge ──────────────────────────────────────────
export function GoodsBadge(goodsType) {
  if (!goodsType) return null;
  return el("div", { class: "hint-text" },
    `${GOODS_ICONS[goodsType] || "📦"} ${goodsType}`
  );
}
