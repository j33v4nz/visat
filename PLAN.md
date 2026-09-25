# VISAT: Kochi Heat Action Planner (v5)

**HackMe'26 · VISAT Engineering College · AI/ML track · PS1: Urban Heat Mitigation via AI/ML**

> **"VISAT shows Kochi where heat is dangerous today, where ₹10 crore cools the most people, and screens every new project so the city stops getting hotter. We prove it against real change from 2017 to 2024."**

**Closing line of the pitch:** *"₹10 crore → −X surface-°C for Y people, back-test error ±Z."*

v5 is the result of four rounds of expert review (remote sensing, ML engineering, hackathon strategy, Kerala urban planning, UX design, and a judge scoring against the HackMe'26 rubric). The judge's final estimate: **~84/100 with Tier 1+2, ~86 with everything.** A perfect 10/10 isn't realistic: satellite surface temperature isn't the heat people feel, and 24-hour code shows seams. But **9s are reachable in technical depth, innovation and impact.** What decides the result is a demo that never crashes and all four members answering questions.

---

## 0. Problem Statement 1 compliance checklist

Every requirement in PS1 (from the hackathon doc), and where VISAT covers it. **Re-check this table after every change and before submission.**

| PS1 requirement | Where VISAT covers it | Tier |
|---|---|---|
| **Description:** geospatial AI/ML, physics-informed decision making, hotspots, drivers, optimized scenario-based interventions | The whole system; the scene-panel physics model; the optimizer | 1 |
| **Obj 1:** heat stress maps from **satellite *and* meteorological data** | **Heat Exposure Index** = satellite LST rank (*where*) × meteorological heat index (*when*, from ERA5 per scene + live Open-Meteo) × population (*who*) | 1 |
| **Obj 2:** drivers: **LULC, urban morphology, vegetation, atmospheric conditions** | SHAP from the **scene-panel model**: land cover, morphology (GHSL height/volume, OSM building density), vegetation, **plus per-scene atmospheric variables** (air temp, humidity, wind, solar radiation). Reported with n and confidence intervals | 1 |
| **Obj 3:** LST ↔ factors with **physics-informed ML** | Scene-panel model with an **energy-balance interaction feature** (1 − albedo) × incoming solar radiation, which varies by scene and so is genuinely learned; **monotone physics constraints**; and an **energy-balance formula** for interventions without data analogs | 1 |
| **Obj 4:** simulate **urban greening, cool roofs, albedo changes, water bodies**; evaluate effectiveness | Street and canal-bank trees, mangroves, green roofs (greening); cool roofs; cool pavements (albedo); **pond restoration + canal-bank strips** (water bodies). All are scored in the validity matrix (section 5) | 1 |
| **Input:** Landsat 8 LST | Landsat 8 + 9 Collection 2 L2, 20–30 clean Jan–Apr scenes | 1 |
| **Input:** ECOSTRESS LST | Afternoon (12:00–15:30) scenes via NASA AppEEARS. **T1:** an afternoon ECOSTRESS map on the Proof screen next to the Landsat morning map. **T2:** rank agreement (Spearman + top-decile overlap) | 1 (map) / 2 (stats) |
| **Input:** LULC from Sentinel-2 / Landsat | Sentinel-2 indices (2019+), **Landsat for 2017** (Sentinel-2 surface reflectance over India starts ~Dec 2018), ESA WorldCover, Dynamic World | 1 |
| **Input:** ERA5 & CPCB meteorology | ERA5-Land per scene (model) + CPCB Vyttila and Eloor (heat-index validation) | 1 |
| **Input:** OSM, GHSL, UT-GLOBUS (if available) | OSM + GHSL. **UT-GLOBUS:** checked before the event; skipped because GHSL covers building height (stated openly) | 1 |
| **Optional:** SOLWEIG & InVEST | Not used, and listed as future scope. PS1 marks them optional | — |
| **Outcome:** heat stress maps identifying hotspots | "Today" screen | 1 |
| **Outcome:** quantitative assessment of drivers | Ward driver panel + city atmospheric panel, with numbers and CIs | 1 |
| **Outcome:** validated AI/ML model | Proof screen: grouped spatial-block CV against baselines, 2017→2024 back-test, CPCB check, ECOSTRESS agreement (T2) | 1–2 |
| **Outcome:** scenario-based evaluation | Validity matrix + °C per intervention per ward | 1 |
| **Outcome:** optimal strategy with **type, spatial placement, °C reduction** | Plan table: type · ward + map location · −°C (with back-test error band) · people · ₹ | 1 |

---

## 1. The problem

- In **April 2026** IMD issued heatwave warnings, Ernakulam was forecast to reach ~38 °C, and schools in Kollam and Thrissur were closed. The Labour Department ordered a **12–3 PM rest period** for outdoor workers. KSDMA had to debunk a viral "55 °C" rumour.
- Kochi keeps losing trees, wetlands and mangroves to concrete: Kakkanad, the Metro corridor, Vyttila.
- Kochi Corporation's climate cell (**C-HED**) and its **Kawaki** tree programme want to act, but a city with a limited budget has to answer three questions: **where is it dangerous today, where should the money go, and will the next big project make it worse?**

## 2. Our solution

VISAT is a web app for **C-HED and ward councillors**. It uses free satellite data, weather data (historical and live), and physics-informed machine learning. It has four screens:

| Screen | Question it answers | What's on it |
|---|---|---|
| **1. Today** | *Where is heat dangerous today?* | **Heat Exposure Map** (Kochi in 100 m squares); live strip (temperature, humidity, heat index, danger band); **"Act today: wards X, Y, Z"** tied to the Labour order and KSDMA advisories; official alert chip + Malayalam news chip (T2). **Click a ward** to open a driver panel in plain words: *"Low tree cover adds +1.8 °C."* |
| **2. Plan ₹** | *What should we do with our money?* | Preset buttons **₹1 / ₹10 / ₹50 crore** (instant, cached). Plan map + table: type · place · −°C · people · ₹. Compared with "spread evenly" and "trees everywhere". Big numbers: people protected, °C, ₹ per °C |
| **3. Check a Project** ⭐ | *Will this new project make it hotter?* | **The hero screen.** Pick one of 5–8 pre-drawn sites and a use (IT park / mall / housing / parking). A **heat ledger** shows *"+1.3 surface-°C (morning) · 4,200 people"*, then the cheapest offset brings it to *"0.0 °C · ₹38 L"*, with a "which rule / who signs" line (the figures here are illustrative) |
| **4. Proof & Ward Card** | *Can we trust it? What do I take to council?* | 2017→2024 back-test chart, honest accuracy vs baselines, validity matrix, CPCB and ECOSTRESS checks, data freshness, limits. **Download Ward Heat Card (PDF)** |

**Design rules** (from the UX review)
- Dark theme; text at least 20 px, key numbers 48–64 px.
- Red/orange means heat; teal means fixes. No other accent colour.
- Screen names are questions, and each screen has one headline sentence generated from the data.
- Diagnostics (CV charts, physics tables) sit in expanders and come out for Q&A.
- The map takes at least 65% of the width. Hide Streamlit's menu, footer and sidebar.

**Honesty rules**
- Satellite values are labelled **"surface °C, ~10:30 AM"**.
- Live weather is labelled **"city-scale"**.
- News is supporting evidence; official alerts come from KSDMA/IMD.
- The Heat-Neutral Check is **"a screening tool and a policy proposal"**, never an approval.
- Canals get **no °C credit**.
- We never call anything "causal" or a "PINN".

---

## 3. How it works

```
DATA (frozen by 2 PM)                         MODEL & ANALYSIS                          SCREENS
Landsat 8/9 scenes (20–30, Jan–Apr)  ─┐
ERA5-Land per scene (T, RH, wind, S↓) ├──► scene-panel XGBoost ──► SHAP drivers ──────► Today
S2 / Landsat / WorldCover / DW        │     (physics feature +       exposure index
GHSL, OSM, SRTM, wards, CPCB         ─┘      monotone constraints)
                                              │
                                              ├──► validity matrix ──► optimizer ──────► Plan ₹
                                              │    (analog / formula,   (vs baselines)
                                              │     joint re-prediction)
                                              ├──► reverse transition + offset ────────► Check a Project
                                              └──► back-test 2017→2024, CV, ECOSTRESS ─► Proof & Ward Card
LIVE: Open-Meteo (15 min) + official alert + Malayalam news chip ──► strip on every screen (cached fallback)
```

1. **Data, frozen by 2 PM.** Earth Engine exports:
   - **20–30 clean Landsat scenes** (Jan–Apr 2019–2026), each with its own **ERA5-Land** air temperature, humidity, wind and solar radiation at overpass time
   - Sentinel-2 indices (2019+), and **Landsat NDVI for 2017**
   - WorldCover, Dynamic World, GHSL, SRTM, OSM buildings/roads/sites, the 74-ward map, CPCB stations
   - 300/500 m neighbourhood features

   The **AppEEARS ECOSTRESS request is submitted at hour 0.**
2. **Scene-panel model (physics-informed).** Each row is one 100 m cell in one satellite scene (cells × scenes), so the model learns **both** where it's hot (land cover) **and** how the day's weather changes it.
   - The physics feature **(1 − albedo) × incoming solar radiation** varies from scene to scene, so the model really learns the energy balance.
   - Monotone constraints: concrete only warms; trees, water and reflective surfaces only cool.
   - Validated with **grouped spatial-block CV** (2 km blocks across all scenes) against a linear model and an unconstrained model. Atmospheric effects are reported with n and CIs.
   - **Fallback** if this isn't working at 4 PM: a single-composite model, described honestly.
3. **Heat Exposure Index.** LST rank (*where*) × heat index (*when*) × population (*who*), rolled up to 74 wards (76 after the 2025 delimitation, stated openly). Validated against CPCB stations.
4. **Interventions.** Each is modelled the most honest way the data allows; see the validity matrix in section 5. Every reported °C comes from **one joint re-prediction**, and tests prevent spillover from being counted twice.
5. **Optimizer.** Greedy on (°C × people × vulnerability weight) / ₹, public land only, with neighbourhood spillover counted once. Compared with naive baselines. Results for ₹1/10/50 crore are precomputed.
6. **Back-test.** For cells that really changed between 2017 and 2024, each scene is **normalised to the city median** first, then predicted ΔLST is compared with observed ΔLST.
7. **Heat-Neutral Development Check (T2).**
   - Reverse transition to the chosen use, using **donors matched to the site's context** (an inland site isn't compared with port land).
   - Joint re-prediction of the site and its neighbourhood.
   - The cheapest offset that brings the net change to 0 surface-°C (morning).
   - Policy hooks: **KMBR extra-FSI incentive** for climate measures; **SEIAA Form-1A** for 20,000–150,000 m² projects; Kochi Master Plan 2040 resilience guidance.
8. **Live layer.**
   - **Open-Meteo:** temperature, humidity and heat index, updated every 15 minutes, city-scale.
   - **"Act today"**: one line ranking wards by exposure × today's forecast peak, weighted by construction sites, markets and schools. It links to the Labour order (12–3 PM rest) and KSDMA advisories (drinking-water kiosks / *thanneer pandal*, school assembly limits, avoiding the 11–3 sun, market fire safety).
   - Every live item has a **cached fallback** with a timestamp. The app is tested with Wi-Fi off.

---

## 4. Live Malayalam news (your request, final form)

- **Where it appears:** a **static chip** on the Today screen: *"⚠ Heat reported by N Malayalam channels today"*. It sits **next to an official KSDMA/IMD alert chip**; the official alert is the authority, the news is supporting evidence.
- **When you click it:** it opens a list of headlines, each with channel, time and link, plus the fetch time.
- **Sources:** Google News Malayalam search (aggregates Asianet, 24 News, MediaOne, Manorama, News18, Kaumudi) + Mathrubhumi + 24 News RSS. Keyword-filtered for Kerala heat, with Malayalam Unicode normalised.
- **Not included:** no scrolling ticker (unreadable on a projector), no AI summaries.
- **Fallback:** the last cached fetch with its timestamp; if there is none, the chip is hidden.
- **Build:** Tier 2, M4.

## 5. Interventions: validity matrix

| Intervention | PS1 category | How we model it | Where allowed | Cost |
|---|---|---|---|---|
| Street trees | Greening | **Analog** (real leafy Kochi cells) | OSM roads, schools, parks (public land only) | ₹3,100/tree |
| Canal-bank tree strips | Greening + water | **Analog** | Banks of the 6 canals in KMRL's IURWTS canal project | ~₹1,000/m (~1 tree per 3 m; estimate) |
| Mangroves | Greening | **Analog** | CRZ / government shoreline only | ₹1–8 lakh/ha |
| Green roofs | Greening | **Energy-balance formula** (labelled) | Buildings | ₹7,500/m², shown as "evaluated, not cost-effective" |
| Cool roofs | Cool roofs | **Energy-balance formula** (labelled) | Buildings | ₹300/m² (+ recoat every ~3 yrs) |
| Cool pavements | Albedo | **Energy-balance formula** (labelled) | OSM road cells | ₹350/m² (₹190–500, ~3-yr life) |
| Pond restoration (≥ 1 ha) | Water bodies | **Analog to water cells** where data supports it, otherwise the formula | Low-lying public land | ~₹45 lakh/ha (Amrit Sarovar rate) |
| IURWTS canals (KMRL) | Water bodies | **Committed overlay, 0 °C credit**; cooling counted as a co-benefit only (canals are narrower than one 100 m cell) | 6 canals | Committed ₹3,716 crore project, not bought by our optimizer |

Every row also shows its **"within-support %"**: how much of the change stays inside what real Kochi data has seen.

---

## 6. Why this can win

| Judging area | What we bring |
|---|---|
| Technical depth | Scene-panel physics-informed model, grouped spatial CV against baselines, joint re-prediction, validity matrix, optimizer beating baselines, 2017→2024 back-test, ECOSTRESS afternoon check |
| Innovation | Heat-Neutral Development Check (screening + offsets), tied to real Kerala rules (KMBR, SEIAA) |
| Working demo | Data frozen early, cached presets, a fallback for every live feed, CI, backup recording, app warmed up before judging |
| UI/UX | 4 plain-language screens, dark projector theme, heat ledger, printable ward card |
| Impact | Named user (C-HED), real costs, public land only, "which rule / who signs", links to the Labour order and the IURWTS canal project |
| Q&A | Every member owns topics; everyone can explain the back-test in one sentence |

---

## 7. Build tiers (move up only when the checkpoint passes)

**Tier 1: must ship (covers all of PS1)**
1. Data freeze by 2 PM: scene stack, ERA5 per scene, Landsat 2017, OSM, wards, CPCB. AppEEARS request at hour 0.
2. Hello-world deploy + CI (tests + lint) by 12 PM.
3. Scene-panel model + baselines + SHAP (fallback: composite model).
4. Heat Exposure Map + ward roll-up.
5. Validity matrix + joint re-prediction + tests.
6. Optimizer vs naive baselines, with ₹1/10/50 crore presets.
7. Back-test normalised to the city median; **ECOSTRESS afternoon map** on the Proof screen (~30 min, keeps PS1 input coverage even if Tier 2 slips).
8. The four screens, Open-Meteo strip with fallback, Ward Card PDF, README, deck.

**Tier 2: after the 4 PM checkpoint**
- ⭐ Heat-Neutral Development Check.
- ECOSTRESS validation (Spearman + top-decile overlap).
- Official alert chip + Malayalam news chip.
- "Which rule / who signs" lines.
- Vulnerability weights (schools, anganwadis, markets, construction sites).
- Matched before/after comparison (DiD).

**Tier 3: after the 11 PM checkpoint**
- IURWTS canal overlay.
- Heat ledger animation.
- Before/after image comparison.
- Printed A5 ward cards for the jury.

**Cut** (mentioned only as future scope):
- Ask VISAT chatbot
- Thiruvananthapuram
- InVEST, SOLWEIG, UT-GLOBUS
- scrolling ticker
- swipe map
- a separate 72-hour ranking screen
- conformal intervals (back-test bands are used instead)
- the budget drag slider
- AI-translated Malayalam

## 8. Team roles

| Member | Builds | Presents / Q&A |
|---|---|---|
| **M1, Data & Model (ML)** | AppEEARS request (hour 0) → Earth Engine scene stack + ERA5 + 2017 Landsat, frozen by 2 PM → scene-panel model + CV + baselines + SHAP → exposure map → back-test → ECOSTRESS afternoon map → *(T2)* ECOSTRESS rank agreement, DiD | Data, model, validation |
| **M2, Scenarios & Optimizer (ML)** | Validity matrix → analog + formula scenarios → joint re-prediction + tests → optimizer + baselines + presets → *(T2)* Heat-Neutral Check engine, vulnerability weights | Optimizer, physics, Heat-Neutral Check |
| **M3, App (Design)** | Hello-world + CI by 12 PM → 4 screens, dark theme → Open-Meteo strip + fallback → Ward Card PDF → *(T2)* Check-a-Project UI (pre-drawn sites, use picker) → *(T3)* ledger animation, before/after, IURWTS overlay | Live demo, ward walkthrough |
| **M4, Product & Pitch (Design)** | Costs + rules → README + AI disclosure → *(T2)* official alert chip + Malayalam news chip, "who signs" lines → deck, video, demo script → *(T3)* printed A5 cards → timekeeper and submitter | Problem, costs, policy, impact |

## 9. 24-hour timeline (work starts ~10 AM)

| Time | Milestone |
|---|---|
| 10:00 | Repo, data columns, roles; **AppEEARS request submitted** |
| 12:00 | Hello-world online, CI running |
| **2:00 PM** | **Data frozen** |
| **4:00 PM** | **Checkpoint 1:** scene-panel model (or fallback) + exposure map on screen → Tier 2 unlocked |
| 7:00 PM | Validity matrix, optimizer, back-test done |
| **11:00 PM** | **Checkpoint 2:** all 4 screens live online → Tier 3 unlocked |
| **1:00 AM** | If the optimizer is broken, ship ranked hotspots + °C per intervention |
| 2–5 AM | Sleep in shifts (M1 + M3 from 2:00 to 3:30, M2 + M4 from 3:30 to 5:00) |
| 5:00 AM | Feature freeze; record the backup demo video |
| **6:00 AM** | **Code freeze**; 3 rehearsals, one with Wi-Fi off |
| 8:30 AM | Warm up the app; submit repo, URL, video and deck before 9:00 |

## 10. The 3-minute demo

| Time | What happens |
|---|---|
| **0:00–0:20 · Today** | "Right now Kochi's heat index is X, which is *Danger*. Act today in wards X, Y, Z: water kiosks, and the Labour order's 12–3 rest period." |
| **0:20–1:00 · Plan ₹** | Press **₹10 crore**: "−X °C for Y people, N% better than spreading the money evenly." |
| **1:00–1:50 · Check a Project** ⭐ | Pick the Kakkanad site, choose *IT park* → **+1.3 °C, 4,200 people** → *Make it heat-neutral* → **0.0 °C, ₹38 L**, then 2 seconds of silence (numbers illustrative). |
| **1:50–2:30 · Proof** | "We predicted 2024 from 2017 and were within ±Z. The afternoon ECOSTRESS check agrees N%. Here's what we model and how." |
| **2:30–3:00 · Close** | Hand each judge the Ward Card for their area, and say the closing number. |

Each member presents one screen. Keep the backup recording ready and warm the app up 10 minutes early.

## 11. Questions to prepare for

| Question | Who | Answer |
|---|---|---|
| Where is the physics? | M2 | The scene-panel model learns (1 − albedo) × incoming sunlight, which changes from scene to scene. Monotone constraints set the direction of each effect. Cool roofs, cool pavements and green roofs use the energy-balance formula, and we label it. It's physics-informed ML, not a neural-network PINN. |
| Isn't this just correlation? | M1 | The back-test compares predictions with 2017→2024 changes that really happened (T2 adds a matched comparison). We never say "causal". |
| Surface temperature isn't the heat people feel. | M1 | Correct, and every value is labelled. LST ranks *where*, the heat index says *when*, and ECOSTRESS confirms the ranking holds in the afternoon. |
| How do satellite and weather combine? | M1 | Exposure = LST rank × heat index × population. The weather model is city-scale, so it sets the day's danger, not the differences between wards. |
| Do canals cool the city? | M4 | Not much. They're narrower than our 100 m grid, so we give them 0 °C credit. IURWTS is shown as a committed project, and we offer tree strips along its banks. |
| Is heat-neutral development legal? | M4 | It's a screening tool and a policy proposal. It could run as a voluntary offset for a KMBR extra-FSI incentive, or be attached to SEIAA Form-1A for large projects. |
| Doesn't Kawaki already do this? | M4 | Kawaki picks tree-grove sites. VISAT adds budget trade-offs, project screening, and verification, so it can plan the next Kawaki sites. |
| Why Malayalam news? Isn't it unreliable? | M4 | It's supporting evidence shown next to the official KSDMA/IMD alert, with channel, time and link. |
| What if the live feed fails? | M3 | Every live item falls back to its last cached value with a timestamp. We rehearsed with Wi-Fi off. |
| Did you cover the whole problem statement? | M4 | Yes. Section 0 maps every PS1 objective, input and outcome to a feature. |
| Walk me through one ward. | M3 | Open its Ward Card: hotspots, drivers, vulnerable sites, top 3 actions with ₹ and °C, and who signs. |

**One sentence everyone can say:** *"Where Kochi really lost trees or gained concrete between 2017 and 2024, our model predicted the temperature change, and here's how close it got."*

## 12. Before the event (no code carried in)

- **Everyone:** Earth Engine sign-up (now), Python + `uv`, GitHub.
- **M1:**
  - Create a NASA Earthdata account and practise an AppEEARS request.
  - List the dataset IDs.
  - Confirm UT-GLOBUS coverage (to state it honestly).
  - Download the ward map.
- **M2:** practise panel data + grouped CV, monotone XGBoost, kNN analogs.
- **M3:** practise Streamlit dark theme, pydeck pickable polygons + `on_select`, `st.segmented_control`, PDF export; deploy a hello-world.
- **M4:**
  - Verify costs and policy facts: Labour order dates, KMBR FSI clause, SEIAA thresholds, IURWTS status.
  - Find an official KSDMA/IMD alert source.
  - Contact C-HED or a councillor (only genuine quotes).
  - Download CPCB data.
  - Prepare the deck template.

## 13. Backup plans

- **Problem list changes on the day:** PS2 (shares ~70% of the pipeline), then PS6.
- **Wi-Fi fails:** data is frozen and every live item has a cache; bring phone hotspots and the backup recording.
- **Scene-panel model fails by 4 PM:** use the composite model, described honestly.

## 14. Rules we follow

- All code is written during the event; this file is a plan.
- AI assistants are allowed and disclosed.
- Submit: public repo + README, live URL + a 2–3 minute video, 5 slides.
- Label anything that isn't real data. Everyone presents.

---

*Author: Jeevan George*
