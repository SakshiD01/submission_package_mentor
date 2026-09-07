# Parameter-Mapping Verification — Findings from the Real NOLHC Design + Model List Files

**Owner:** Sakshi
**Purpose:** Amr's email raised three open items — the `A_Im_DR`-style multi-parameter mapping formula, the 3 "phantom" yellow-highlighted parameters in the Actual Values tab, and (from Iniya's earlier questions) the 122-fixed-input and replication-count assumptions. This note answers what the two files Amr referenced (`NOLHC_Designs__AL_Students_Recent_26.xlsx`, `Model_List_of_input_and_output_parameters__recent_26.xlsx`) actually say, cell by cell — not what any spec.md draft claims they say.

**Status:** 2 of 3 open items resolved with direct evidence from the files. 1 item (5 replications) remains unconfirmed — no evidence for or against it exists in these two files.

---

## 1. The `A_Im_DR` mapping — resolved, and it corrects an inaccurate claim in the team's spec.md

**What the formula sheet actually does.** `ExpValues Eq` (the sheet that generates all 129 runs' raw AnyLogic inputs) computes each product/direction group from three linked cells. Using `A_Im` (agri imports) as the concrete example, row 4 (run 1):

- `L4` = `'Actual Values'!$C$7 * 'NOLH Designs (2)'!E5` — the landbridge baseline (`VolAgriImEULB` = 555,114) scaled by that run's NOLHC multiplier (range 0.77–1.23 per the low/high rows in `NOLH Designs (2)`). This *is* the raw AnyLogic parameter `VolAgriImEULB` fed into the simulation for this run.
- `M4` (factor name `A_Im_LB`) = `'Actual Values'!$C$7 - L4` — the amount that shifted off the landbridge relative to baseline.
- `N4` (factor name `A_Im_DR`) = `L4 + 'Actual Values'!$D$7` — the scaled landbridge volume plus the baseline direct-route volume (`VolAgriImViaChe` = 173,605).

So in the actual 129-run design, `A_Im_DR` touches **exactly one raw AnyLogic parameter family: Cherbourg (`VolAgriImViaChe`)**. There is no Rotterdam/Zeebrugge/Bilbao term anywhere in this formula.

**But the ports themselves are real, not invented.** `Model_List_of_input_and_output_parameters__recent_26.xlsx` → `Input Parameters & Sources` does contain full raw-parameter groups for all four direct-route ports (rows 25–52): Cherbourg, Rotterdam, Zeebrugge, and Bilbao, each with six parameters (`VolAllPIm/Ex`, `VolAgriIm/Ex`, `VolCatIm/Ex`) plus dedicated vessel-capacity parameters for Rotterdam (`DToRottVesselCap`), Zeebrugge (`DToZeeVesselCap`) and Bilbao (`RToBilVesselCap`, row 175). So a 4-port structure genuinely exists in the underlying AnyLogic model.

**The resolution:** every non-Cherbourg direct-route parameter is documented at baseline value **0**, with an explicit sourcing note in row 26: *"TU Dublin couldn't find clear figures on the traffic flow within the direct route... it is expected that 20% of the landbridge traffic will be replaced with the direct route traffic to EU Post-Brexit... the model provides flexibility to the user to change these values."* In other words: Rotterdam, Zeebrugge and Bilbao are real, wired-up parameters in the AnyLogic model, but they are held fixed at zero across all 129 NOLHC runs — they belong to the fixed-input set, not the 35-factor experimental design. Only Cherbourg carries a nonzero baseline and is the one actually driven by the `A_Im_DR`/`NA_Im_DR` factors.

**What this means for the team's spec.md:** the version of spec.md claiming a "worked Excel-formula derivation" splitting `A_Im_DR` across Cherbourg/Rotterdam/Zeebrugge/Bilbao is not supported by the actual formula sheet — the split doesn't happen in the 129-run design at all. I'd guess whoever wrote that pulled the four port names from Amr's own comment in `Input Parameter Design` row 12 ("Rosslare-Bilbao (other Spain ports) to be added") — a note about a *future* extension, not something already implemented — and reasoned the rest. Worth raising in the meeting so it doesn't get carried into T2.5's ground-truth backend as fact.

## 2. The 3 "phantom" parameters — identified, with corroborating evidence from both files

`Actual Values` has exactly three cells with a distinct highlight (theme accent-2 orange, lightened — visually reads as gold/yellow, different from the pale-yellow row-index shading used elsewhere in the workbook and from the header-blue used everywhere else in this sheet): `A27`, `A28`, `A29`:

- "Percentage of non-agri outbound green route trucks"
- "Percentage of non-agri outbound red route trucks"
- "Percentage of agri outbound red route trucks"

Two independent pieces of evidence say these are the ones Amr means:

1. **Structural gap in `Actual Values` itself.** Every other route-percentage row (30–34: inbound green/red, pre-boarding stop) has raw AnyLogic parameter names filled into columns B–D (`PerGreenTrucksAPImIR`, `PerPhyChkAPImIR`, etc.) and is formatted identically to the rest of the sheet. Rows 27–29 have a label only — no raw parameter name, no baseline value — and carry the one-off highlight.
2. **Confirmed absent from the full raw-parameter list.** I searched all 186 rows of `Input Parameters & Sources` (the complete AnyLogic parameter inventory) for anything matching "outbound green route" or "outbound red route." Nothing exists. The only outbound-side checks documented anywhere in that file are `PerCusIntTrucksAPExIR`/`AgriExIR`/`CatExIR` — "outbound trucks subject to customs intervention" — a different check entirely from a green/red physical-check split. Green/red route splits exist **only for inbound** trucks (Irish ports, west-GB ports, east-GB/Dover, and Calais).

**Conclusion for the meeting:** these 3 rows are design-intent placeholders that were never actually implemented as AnyLogic parameters. Amr's ask ("check that removing them is safe") looks safe to action — they don't drive anything in the model. Recommend explicitly confirming with Amr/Iniya before deleting, since removing a row from the Excel design sheet is irreversible for anyone else who might still be referencing it, but I found no raw parameter, no formula, and no simulation output anywhere tied to them.

## 3. Items still open — not resolved by these two files

- **5 replications per NOLHC point.** Neither file contains any per-replication data, replication count, or seed information. `ExpValues`/`SimResults` only ever show one row per NOLHC point (129 rows total) — consistent with either "5 replications, mean reported" or "1 replication" from the file's structure alone. I found nothing here confirming or contradicting the "5 replications, mentor confirmed" claim in the elaborate spec.md — that claim still needs to come from Wael/Amr directly, not from this workbook. Worth asking outright at tomorrow's meeting rather than assuming either way.
- **122 fixed-input baseline count.** `Input Parameters & Sources` lists 146 named-parameter rows and 39 section-header rows under `Input Parameters & Sources` (before any dedup — a few names like `VolCatImGB` repeat across product categories). The 35 NOLHC design factors (from `Input Parameter Design`, expanding the 4 "Shifts in Trade Volume" sub-codes NA-IM/NA-EX/A-IMP/A-EXP into individual factors) are a subset of this raw list, but I have not yet done the row-by-row reconciliation needed to land on exactly "122." I'd treat 122 as Wael's number until someone actually walks the full mapping — I can do that reconciliation before the meeting if it's useful, but it's a genuinely time-consuming cross-check (146+ raw names against 35 design factors plus the fixed-but-nonzero ones like officer counts and vessel capacities) and I didn't want to rush a number I can't stand behind.

## 4. Recommended follow-up for T2.4 (novelty scorer) and the meeting

Wael's new requirement — record the 122 fixed-input baselines and flag any future scenario that alters one as "out-of-scope" rather than scoring it for novelty — is not yet implemented in `novelty_scorer.py`. It's straightforward to add once the fixed-input list is nailed down (a baseline dict + an equality/tolerance check ahead of the existing `IsolationForest`/GP-std logic), but it depends on resolving item 3 above first — implementing it against a guessed 122-item list risks silently missing some fixed inputs or wrongly flagging genuine 35-factor inputs as out-of-scope.

For tomorrow's ~11:00 meeting, the three concrete, evidence-backed things worth raising: (1) the `A_Im_DR` 4-port claim in spec.md is not what the formula sheet does — only Cherbourg is live, the other three ports are real but fixed at zero; (2) the 3 phantom parameters are almost certainly the outbound green/red-route rows — safe to remove pending Amr/Iniya's confirmation; (3) still need a straight answer on the replication count, since nothing in these files settles it either way.
