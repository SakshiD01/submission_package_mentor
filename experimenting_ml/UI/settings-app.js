/**
 * Settings page — all parameters with ranges, ports, validation, and modal info.
 */

import { NOLHC_MEDIANS } from "./data/data.js";
import {
  CONFIG_STORAGE_KEY,
  PARAMETER_LABELS,
  PARAMETER_META,
  PARAMETER_ORDER,
  SETTINGS_GROUPS,
  formatRangeLabel,
  loadSavedConfig,
  saveConfigToStorage,
} from "./data/parameter_meta.js";
import { getParameterHelpOnlySections } from "./data/parameter_help.js";
import { el, NumberField, InfoIconButton } from "./components/components.js";

/** Renders Valid input + range + technical report lines from `parameter_help.js` (not PARAMETER_META detail). */
function buildHelpPanel(apiKey, isPercent) {
  const sections = getParameterHelpOnlySections(apiKey, isPercent);
  const wrap = el("div", { class: "settings-help-panel" });
  sections.forEach(({ label, text }) => {
    wrap.append(
      el(
        "div",
        { class: "settings-help-section" },
        el("div", { class: "settings-help-label" }, label),
        el("div", { class: "settings-help-text" }, text),
      ),
    );
  });
  return wrap;
}

const config = { ...NOLHC_MEDIANS };

const requiredKeys = new Set([
  "NA_Im",
  "NA_Ex",
  "A_Im",
  "A_Ex",
  "VCap_Dub_Hey",
  "VCap_Dub_Holy",
  "VCap_Dub_Liv",
  "VCap_Ross_Fish",
  "VCap_Ross_Pem",
  "ChkTime_Doc",
  "ChkTime_Phy",
  "NumCusShed_D",
  "NumDAFM_D",
  "NumCusShed_R",
  "NumDAFM_R",
]);

function mergeSaved() {
  const saved = loadSavedConfig();
  if (!saved) return;
  for (const k of Object.keys(NOLHC_MEDIANS)) {
    if (typeof saved[k] === "number" && Number.isFinite(saved[k])) {
      config[k] = saved[k];
    }
  }
}

function fieldId(apiKey) {
  return `sf-${apiKey.replace(/_/g, "-").toLowerCase()}`;
}

function buildField(apiKey, staggerMs) {
  const m = PARAMETER_META[apiKey];
  const isPercent = apiKey.startsWith("Pct_");
  const labelBase = PARAMETER_LABELS[apiKey] || apiKey;
  const label = isPercent ? `${labelBase} (%)` : labelBase;
  const min = m != null ? (isPercent ? m.min * 100 : m.min) : 0;
  const max = m != null ? (isPercent ? m.max * 100 : m.max) : undefined;
  const step = m?.step != null && !isPercent ? m.step : isPercent ? 1 : undefined;
  const displayValue = isPercent ? Math.round(config[apiKey] * 10000) / 100 : config[apiKey];

  return NumberField({
    id: fieldId(apiKey),
    label,
    required: requiredKeys.has(apiKey),
    value: displayValue,
    min,
    max,
    step,
    staggerMs,
    onChange: (v) => {
      config[apiKey] = isPercent ? v / 100 : v;
    },
  }).wrap;
}

function buildParamBlock(apiKey, staggerMs) {
  const m = PARAMETER_META[apiKey];
  const isPercent = apiKey.startsWith("Pct_");
  const block = el("div", { class: "settings-param-block" });

  const metaRow = el("div", { class: "settings-param-meta" });
  metaRow.append(el("code", { class: "settings-param-key" }, apiKey));
  if (m) {
    metaRow.append(el("span", { class: "settings-param-range-pill" }, formatRangeLabel(apiKey, isPercent)));
    if (m.ports && m.ports.length) {
      const chips = el("div", { class: "settings-port-chips settings-port-chips--inline" });
      m.ports.forEach((p) => chips.append(el("span", { class: "settings-port-chip" }, p)));
      metaRow.append(chips);
    }
  }
  block.append(metaRow);
  block.append(buildField(apiKey, staggerMs));
  if (m) {
    block.append(buildHelpPanel(apiKey, isPercent));
  }
  return block;
}

function createSettingsGroup(g, open, staggerStart) {
  let n = staggerStart;
  const grp = el("div", { class: `settings-factor-group factor-group${open ? " open" : ""}` });
  const hdr = el("div", { class: "factor-group-header" });
  const left = el("div", { class: "factor-group-title-row" },
    el("span", { class: "factor-group-chevron" }, "▼"),
    el("span", {}, g.title),
  );
  if (g.headerDetail) left.append(InfoIconButton(g.title, g.headerDetail, null));
  hdr.append(
    el(
      "div",
      {
        style: {
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          width: "100%",
          gap: "10px",
        },
      },
      left,
      el("span", { class: "factor-group-badge" }, g.badge),
    ),
  );
  hdr.addEventListener("click", () => grp.classList.toggle("open"));
  const body = el("div", { class: "factor-group-body" });

  const keys = PARAMETER_ORDER.filter((k) => PARAMETER_META[k].group === g.id);
  keys.forEach((apiKey) => {
    if (apiKey === "NA_Im_LB") {
      body.append(el("div", { class: "form-subheading" }, "Volume shifts (tonnes)"));
    }
    if (apiKey === "VCap_Dub_Hey") {
      body.append(el("div", { class: "form-subheading" }, "Vessel capacities (trailers)"));
    }
    body.append(buildParamBlock(apiKey, n * 38));
    n += 1;
  });

  grp.append(hdr, body);
  return { node: grp, nextStagger: n };
}

function render() {
  const root = document.getElementById("settings-root");
  if (!root) return;
  root.innerHTML = "";
  root.append(
    el(
      "p",
      { class: "settings-lead" },
      "Below every input: Valid input, Allowed range, and Technical report context from parameter_help.js (Post-Brexit Irish freight study). Adjust values here or use Save to return to the simulator.",
    ),
  );

  let stagger = 0;
  SETTINGS_GROUPS.forEach((g, i) => {
    const { node: grpEl, nextStagger } = createSettingsGroup(g, i === 0, stagger);
    stagger = nextStagger;
    root.append(grpEl);
  });

  const actions = el("div", { class: "settings-actions" });
  actions.append(
    el(
      "button",
      {
        type: "button",
        class: "btn-run-simulation btn-run-simulation--ready",
        onclick: () => {
          saveConfigToStorage(config);
          window.location.href = "index.html";
        },
      },
      "Save & return to simulator",
    ),
    el(
      "button",
      {
        type: "button",
        class: "btn-reset-simulation",
        onclick: () => {
          try {
            localStorage.removeItem(CONFIG_STORAGE_KEY);
          } catch {
            /* ignore */
          }
          Object.assign(config, NOLHC_MEDIANS);
          render();
        },
      },
      "↺ Reset to defaults",
    ),
    el("a", { href: "index.html", class: "settings-back-link" }, "← Back without saving"),
  );
  root.append(actions);
}

mergeSaved();
document.addEventListener("DOMContentLoaded", render);
