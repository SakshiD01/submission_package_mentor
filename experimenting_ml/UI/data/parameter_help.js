/**
 * Valid-input lines + technical report context (Post-Brexit Irish freight study, 2020).
 * Complements PARAMETER_META for modal sections.
 */

import { PARAMETER_META, formatRangeLabel } from "./parameter_meta.js";

/** What users may type; enforced by UI min/max. */
export const VALID_INPUT_BY_KEY = {
  NA_Im:
    "Positive number in tonnes (whole or decimal). Typical national trade magnitudes are in the millions of tonnes per year.",
  NA_Ex:
    "Positive number in tonnes. Represents outbound non-agri demand to GB; use CSO/IMDO-style annual tonnage thinking.",
  A_Im:
    "Positive number in tonnes. Agri-food flows drive SPS/DAFM workload at Irish ports (see report: non-tariff barriers, DAFM).",
  A_Ex:
    "Positive number in tonnes. Outbound agri exports affect UK-side and Irish port SPS queues.",
  NA_Im_LB:
    "Tonnes ≥ 0. Share of non-agri imports using the UK Land-bridge (report: ~16% of Ireland–GB Ro/Ro via land-bridge to EU context).",
  NA_Im_DR:
    "Tonnes ≥ 0. Direct EU routes (Cherbourg, Rotterdam, Zeebrugge) per report’s continental corridor definition.",
  NA_Ex_LB: "Tonnes ≥ 0. Non-agri exports routed via Land-bridge (GB transit).",
  NA_Ex_DR: "Tonnes ≥ 0. Non-agri exports on direct EU sailings.",
  A_Im_LB:
    "Tonnes ≥ 0. Agri imports via Land-bridge incur UK border stages before re-entry to EU.",
  A_Im_DR: "Tonnes ≥ 0. Agri imports on direct EU routes (bypasses UK on that leg).",
  A_Ex_LB: "Tonnes ≥ 0. Agri exports via Land-bridge.",
  A_Ex_DR: "Tonnes ≥ 0. Agri exports via direct EU routes.",
  VCap_Dub_Hey:
    "Integer trailers per sailing (average). Report Table 5 lists route capacities in freight units; align with Dublin–Heysham operators.",
  VCap_Dub_Holy:
    "Integer trailers per sailing. East/West corridor — Holyhead is a high-frequency Dublin link in the report.",
  VCap_Dub_Liv: "Integer trailers per sailing (Dublin–Liverpool East/West corridor).",
  VCap_Ross_Fish: "Integer trailers per sailing (Rosslare–Fishguard).",
  VCap_Ross_Pem: "Integer trailers per sailing (Rosslare–Pembroke).",
  ChkTime_Doc:
    "Minutes per truck (decimal allowed). Maps to documentary and seal-identity checks in the report’s import process mapping.",
  ChkTime_Phy:
    "Minutes per truck for full physical inspection (red lane / SPS). Report distinguishes documentary vs physical border times.",
  NumCusShed_D:
    "Whole number ≥ 1. Revenue (customs) inspection/depot capacity at Dublin — report: customs resources at Irish ports.",
  NumDAFM_D:
    "Whole number ≥ 1. DAFM SPS bays at Dublin — report highlights SPS on agri-food vs non-agri customs-only flows.",
  NumCusShed_R: "Whole number ≥ 1. Revenue sheds at Rosslare.",
  NumDAFM_R: "Whole number ≥ 1. DAFM SPS bays at Rosslare.",
  Pct_NA_OB_Green:
    "Percentage 0–100 in the form (stored as 0–1). Share on green (low inspection) lane at UK outbound ports.",
  Pct_NA_OB_Red:
    "Percentage 0–100. Share sent to red-route physical checks at UK ports — report truck routing categories.",
  Pct_A_OB_Red:
    "Percentage 0–100. Agri SPS inspection share at UK ports; ties to sanitary/phytosanitary measures in the report.",
  Pct_NA_IB_Green: "Percentage 0–100. Green lane share for non-agri imports at Irish ports.",
  Pct_NA_IB_Red: "Percentage 0–100. Red-route physical check share for non-agri imports at Irish ports.",
  Pct_A_IB_Red: "Percentage 0–100. Agri SPS selection rate at Irish ports (DAFM workload driver).",
  Pct_IB_PreBoard: "Percentage 0–100. Pre-boarding stops on inbound legs (UK ports in report flow diagrams).",
  Pct_OB_PreBoard: "Percentage 0–100. Pre-boarding stops on outbound legs at Irish ports.",
};

/** Short quotes / themes from the technical report (trade corridors, Table 6-style inputs, AUW, border checks). */
export const REPORT_NOTE_BY_KEY = {
  NA_Im:
    "Report: Irish maritime trade is largely seaport-based; Ro/Ro is dominant for Ireland–GB. Inbound volumes feed the East/West and corridor split used in the study.",
  NA_Ex:
    "Report: Outbound Ro/Ro to GB is analysed alongside EU land-bridge and direct routes; tonnage scales to freight units via average unit weight (IMDO uses ~21 t/HGV in the document).",
  A_Im:
    "Report: Agri-food faces SPS and related non-tariff barriers; DAFM categories and inspection intensity are central to import-side delays.",
  A_Ex:
    "Report: Export agri flows interact with UK and EU port checks; scenario mapping varies trade and border parameters.",
  NA_Im_LB:
    "Report: Land-bridge combines East/West links with Dover–Calais and western GB ports; a share of Ireland–EU Ro/Ro uses this chain.",
  NA_Im_DR:
    "Report: Direct continental services (e.g. Cherbourg, Rotterdam, Zeebrugge) are itemised; CSO/Eurostat tonnage sources underpin route splits.",
  NA_Ex_LB: "Report models EU-bound traffic via GB transit as distinct from direct sailings.",
  NA_Ex_DR: "Report: Direct EU routes grew (~15% in cited period) as operators added capacity.",
  A_Im_LB: "Report: Agri Land-bridge traffic encounters UK border stages before EU destination.",
  A_Im_DR: "Report: Direct routes avoid UK land border on the continental leg; SPS still applies at Irish/EU nodes as modelled.",
  A_Ex_LB: "Report: Outbound agri via Land-bridge aligns with west GB ports and Dover–Calais transit.",
  A_Ex_DR: "Report: Outbound agri on direct EU sailings from Dublin/Rosslare corridors.",
  VCap_Dub_Hey:
    "Report Table 5: route-level sailing frequency, transit time, and average freight-unit capacity inform operational congestion.",
  VCap_Dub_Holy: "Report: Dublin–Holyhead carries very large tonnage in cited tables; capacity drives queueing when demand is high.",
  VCap_Dub_Liv: "Report: Liverpool services listed under East/West operators (P&O, SeaTruck, etc.).",
  VCap_Ross_Fish: "Report: Rosslare–Fishguard is part of the Southern corridor in the maritime description.",
  VCap_Ross_Pem: "Report: Pembroke–Rosslare capacity figures appear alongside other east/west routes.",
  ChkTime_Doc:
    "Report: Import checks include documentary and seal-identity steps before physical/SPS paths; times are scenario inputs.",
  ChkTime_Phy:
    "Report: Physical inspections apply to selected trucks (red lane / SPS); durations differ from documentary checks.",
  NumCusShed_D:
    "Report Table 6: checking resources and capacities at Irish ports — Revenue (customs) staffing and infrastructure.",
  NumDAFM_D: "Report: DAFM resources for SPS inspections at Dublin; agri-food focus in methodology section.",
  NumCusShed_R: "Report: Rosslare customs capacity as part of dual-port Irish gateway analysis.",
  NumDAFM_R: "Report: DAFM bays at Rosslare for agri-food inspection.",
  Pct_NA_OB_Green:
    "Report: Proportions of trucks in routing categories (green/red) are scenario levers for border intervention testing.",
  Pct_NA_OB_Red: "Report: Red-route physical checks increase processing time and queue formation at ports.",
  Pct_A_OB_Red: "Report: Agri exports may be channelled to SPS checks at GB ports under post-Brexit assumptions.",
  Pct_NA_IB_Green: "Report: Irish inbound green vs red split for non-agri mirrors customs process mapping.",
  Pct_NA_IB_Red: "Report: Non-agri red-route share drives physical inspection load at Dublin/Rosslare.",
  Pct_A_IB_Red: "Report: Agri import SPS share is tied to DAFM utilisation and waiting-time KPIs.",
  Pct_IB_PreBoard: "Report: Security and pre-boarding stops appear in border intervention conceptual models.",
  Pct_OB_PreBoard: "Report: Outbound pre-boarding at Irish ports affects departure queues.",
};

/**
 * Structured modal content for the (i) dialog.
 * @param {string} apiKey
 * @param {boolean} isPercent
 * @returns {{ label: string; text: string }[]}
 */
export function getParameterModalSections(apiKey, isPercent) {
  const m = PARAMETER_META[apiKey];
  if (!m) return [];
  const rangeText = formatRangeLabel(apiKey, isPercent);
  const sections = [
    { label: "Definition", text: m.detail },
    {
      label: "Valid input",
      text: VALID_INPUT_BY_KEY[apiKey] || "Numeric value within the allowed range for this field.",
    },
    { label: "Allowed range", text: rangeText },
  ];
  if (REPORT_NOTE_BY_KEY[apiKey]) {
    sections.push({
      label: "Technical report context",
      text: REPORT_NOTE_BY_KEY[apiKey],
    });
  }
  return sections;
}

/**
 * Help text that lives only in this file (Valid input + report notes + range).
 * Omits PARAMETER_META `detail` so Settings / reference views are not duplicates
 * of the (i) modal “Definition” or short form tooltips.
 */
export function getParameterHelpOnlySections(apiKey, isPercent) {
  const m = PARAMETER_META[apiKey];
  if (!m) return [];
  const rangeText = formatRangeLabel(apiKey, isPercent);
  const sections = [
    {
      label: "Valid input",
      text:
        VALID_INPUT_BY_KEY[apiKey] ||
        "Numeric value within the allowed range for this field.",
    },
    { label: "Allowed range", text: rangeText },
  ];
  if (REPORT_NOTE_BY_KEY[apiKey]) {
    sections.push({
      label: "Technical report context",
      text: REPORT_NOTE_BY_KEY[apiKey],
    });
  }
  return sections;
}
