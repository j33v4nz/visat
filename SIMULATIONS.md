# VISAT: every simulation PS1 needs

This file lists every simulation or what-if run that Problem Statement 1 asks for, how VISAT runs it, and where it stands. All numbers come from the committed build in `data/app/`, which uses real data: `source: frozen`, built 26 Sep 2026 03:48 IST from 54,168 cells and 23 Landsat scenes. To regenerate everything:

```bash
uv run python -m uhi.pipeline --source frozen
```

## How every simulation runs

Every what-if uses the same engine, `src/uhi/scenarios.py` (`Engine`), and follows the same rules:

- **Analog fixes** move a cell toward the median of its k=20 most similar real Kochi cells that already have the fix. The result is clipped to the observed range (1st to 99th percentile), and changes are only allowed in the cooling direction.
- **Formula fixes** cover cool roofs, cool pavements and green roofs, which have no data analog. They use a labelled energy-balance formula, ΔT ≈ −Δα × S / h × area share (S = 750 W/m², h = 25 W/m²K), and get no spillover credit.
- **Joint re-prediction:** every reported ΔT comes from one model run with all changed cells applied together, so the 300 m and 500 m neighbourhood features and the spillover are recomputed.

## 1. Intervention simulations (PS1 Obj 4: greening, cool roofs, albedo, water bodies)

Each intervention is simulated on every eligible cell and scored in the validity matrix (`validity_matrix()`, shown in the app's "Budget curve & scenario evaluation" expander).

| # | Simulation | PS1 category | Method | Eligible cells | Median ΔT per cell | Within data support | Status |
|---|---|---|---|---|---|---|---|
| 1 | Street trees (30 trees, ₹93k/cell) | Urban greening | Analog | 14,142 | −0.15 °C | 97.0 % | ✅ Done |
| 2 | Canal-bank tree strip | Greening + water bodies | Analog | 2,348 | −0.08 °C | 94.3 % | ✅ Done |
| 3 | Mangrove restoration | Urban greening | Analog | 757 | −0.50 °C | 12.1 % ⚠️ | ✅ Done, low support |
| 4 | Pond restoration (0.5 ha) | Water bodies | Analog | 1,612 | −1.86 °C | 3.4 % ⚠️ | ✅ Done, low support |
| 5 | Cool roofs (Δα 0.40, 50 % of roofs) | Cool roofs | Formula | 22,997 | −1.92 °C | n/a | ✅ Done |
| 6 | Cool pavements (Δα 0.25, 60 % of roads) | Albedo changes | Formula | 25,347 | −0.58 °C | n/a | ✅ Done |
| 7 | Green roofs (20 % of roofs) | Urban greening | Formula | 22,997 | −0.51 °C | n/a | ✅ Done, rarely cost-effective |
| 8 | IURWTS canals (KMRL) | Water bodies | Overlay, 0 °C credit | n/a | 0.0 °C | n/a | ✅ Shown, no cooling credit (canals are narrower than a 100 m cell) |

⚠️ Mangroves and ponds mostly fall outside the observed data range. Their ΔT numbers are clipped extrapolations, so present them as indicative only.

## 2. Budget-optimised plan (PS1 Outcome: optimal strategy with type, placement and °C)

`src/uhi/optimize.py` picks the most person-°C of cooling per rupee, with one fix per cell, on public land only, weighted by vulnerability. Each plan is compared with two naive baselines and evaluated jointly.

| Budget | Strategy | People cooled | Person-°C cooling | Mean ΔT for cooled people | Status |
|---|---|---|---|---|---|
| ₹1 cr | **VISAT plan** (cool roofs + street trees, 100 cells) | 52,951 | 46,972 | −0.85 °C | ✅ |
| | Spread evenly | 212 | 107 | | ✅ baseline |
| | Trees everywhere | 13,196 | 4,632 | | ✅ baseline |
| ₹10 cr | **VISAT plan** (4 fix types, 431 cells) | **186,258** | 228,650 | −1.20 °C | ✅ headline number |
| | Spread evenly | 9,272 | 10,453 | | ✅ baseline |
| | Trees everywhere | 113,022 | 44,298 | | ✅ baseline |
| ₹50 cr | **VISAT plan** (4 fix types, 1,188 cells) | 433,751 | 810,418 | −1.86 °C | ✅ |
| | Spread evenly | 42,090 | 50,608 | | ✅ baseline |
| | Trees everywhere | 550,369 | 194,048 | | ✅ baseline |

At ₹50 cr, "Trees everywhere" cools more people but only by a little each: VISAT gives about 4× the person-°C. If a judge asks, say so plainly. The optimiser targets total person-°C, not headcount.

The budget curve in the chart is estimated as a sum of per-site effects. The three presets above use full joint evaluation.

## 3. Heat-Neutral Development Check (proposed projects)

`src/uhi/heat_neutral.py` works in two steps. First it simulates developing a 3×3 block (about 9 ha, green to built) using real Kochi donors for that use. Then it finds the cheapest offset (trees within about 1 km, plus cool or green roofs on the project) that brings people-weighted °C back to zero within ±500 m.

That gives 6 sites × 4 uses = **24 simulations, all done**:

| Site | Warming before offset (°C) | Heat-neutral after offset? | Offset cost |
|---|---|---|---|
| Kakkanad | +0.45 to +0.56 | ❌ No, for all 4 uses | ₹38.6–63.2 lakh (still short) |
| Kalamassery | +0.36 to +0.43 | ✅ Yes | ₹14.7 lakh |
| Edappally | +0.49 to +1.00 | ✅ Yes | ₹28.0–29.0 lakh |
| Vyttila | +0.42 to +0.44 | ✅ Yes | ₹16.2 lakh |
| Maradu | +0.56 to +0.69 | ✅ Yes | ₹80.8–97.7 lakh |
| Thrikkakara | +0.30 to +0.45 | ✅ Yes | ₹60.6–68.5 lakh |

The uses are IT park, mall, housing, and parking or paved yard. Kakkanad can't be offset with the local options, which is a demo point worth showing.

## 4. Model and validation runs (PS1 Obj 2/3 and Outcome: validated model)

These aren't interventions, but every scenario number depends on them.

| # | Run | Result | Status |
|---|---|---|---|
| 9 | Spatial block CV (140 blocks, about 2 km each) | Ours R² 0.83 / RMSE 1.40 °C; unconstrained 0.84; linear 0.62 | ✅ |
| 10 | Atmospheric what-ifs (+1 °C air, +10 % RH, +1 m/s wind, +100 W/m² sun) | +0.51, −0.90, −0.18, +1.32 °C (with CIs) | ✅ |
| 11 | Back-test on real land-cover change, 2017→2024 (8,000 cells) | r 0.35, MAE 1.40 °C | ✅ |
| 12 | Matched kNN back-test against similar unchanged cells | in the Proof screen | ✅ |
| 13 | Physics cross-check: model versus formula on cool roofs (2,000 cells) | model ≈ 0 °C vs formula −2.33 °C, explained by albedo and built-up correlation (r 0.47), so the formula is used | ✅ |
| 14 | ECOSTRESS afternoon LST agreement | code ready (`validation.ecostress_agreement`) | ❌ Not run: needs a NASA Earthdata login. Future work |
| 15 | CPCB station air-temperature check | code ready (`validation.cpcb_check`) | ❌ Not run: needs station CSVs. Future work |

## 5. Optional and extra simulations

| # | Simulation | Status |
|---|---|---|
| 16 | Public Reaction Preview: simulated resident personas (`reactions.py`), labelled SIMULATED, with a number guard so it never changes °C or ₹ | ✅ Precomputed, shown on the Check-a-Project screen |
| 17 | SOLWEIG (pedestrian thermal comfort) | ⏭️ Optional in PS1. Future scope |
| 18 | InVEST Urban Cooling | ⏭️ Optional in PS1. Future scope |

## Still to do

Nothing that PS1 requires is missing. Only items 14 and 15 remain, and both are blocked on outside access, so pitch them as future work. If time allows, it's worth adding one more sensitivity run: re-run the ₹10 cr plan with vulnerability weighting switched off (`all_candidates(vulnerability=False)`). That shows how much the plan depends on the vulnerability weights.
