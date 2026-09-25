# VISAT: Kochi Heat Action Planner

**HackMe'26 · VISAT Engineering College · AI/ML track · PS1: Urban Heat Mitigation via AI/ML**

> **"VISAT shows Kochi where heat is dangerous *today*, where to spend ₹10 crore to cool the most people for good, and checks every new project so the city stops getting hotter. We prove it against real change from 2017 to 2024."**

---

## 0. Problem Statement 1 compliance checklist

Every requirement from PS1 in the hackathon doc, and where VISAT covers it. **Re-check this table after every plan change and again before submission.**

| PS1 requirement (doc wording) | Where VISAT covers it | Tier |
|---|---|---|
| **Description:** geospatial AI/ML system, *physics-informed decision making*, hotspots, drivers, optimized scenario-based interventions | The whole pipeline; physics-informed model (step 2); optimizer (step 6) | 1 |
| **Obj 1:** heat stress maps using **satellite *and* meteorological data** | **Heat Stress Map** = Landsat LST (satellite, 100 m) + ERA5-Land Feb–Apr afternoon **heat index** (meteorological), combined into a Heat Stress Index, plus the live heat index layer | 1 |
| **Obj 2:** quantify drivers: **LULC, urban morphology, vegetation, atmospheric conditions** | SHAP for land cover, morphology (GHSL height/volume, OSM building density, UT-GLOBUS if Kochi is covered) and vegetation. **Atmospheric:** scene-by-scene analysis of city LST vs ERA5 air temp, humidity, wind and radiation at overpass time | 1 |
| **Obj 3:** LST ↔ factors with **physics-informed ML** | XGBoost with **physics-derived features** (absorbed shortwave (1−α)·S from ERA5 radiation, evaporative-cooling potential from NDVI × ET₀) + **monotone physics constraints** + an **energy-balance cross-check**. It is physics-informed ML, not a physics-informed neural network (PINN) | 1 |
| **Obj 4:** simulate **urban greening, cool roofs, albedo changes, water bodies**; evaluate effectiveness in reducing heat stress | What-ifs for **street trees, mangroves, green roofs, cool roofs, cool pavements (albedo), water-body/canal restoration**. All are simulated and scored in °C; the optimizer picks among the cost-effective ones | 1 (trees, cool roofs, water, green roofs) / 2 (cool pavements, mangroves) |
| **Input:** Landsat 8 LST | Landsat 8 **and** 9 Collection 2 L2 | 1 |
| **Input:** ECOSTRESS LST | Downloaded through **NASA AppEEARS** (not in GEE for Kochi): Feb–Apr 2024–25 **afternoon** scenes, used to check that hotspots hold at 1–3 PM, not only at 10:30 AM | 2 |
| **Input:** LULC from Sentinel-2 / Landsat | Sentinel-2 indices + ESA WorldCover + Dynamic World | 1 |
| **Input:** ERA5 & CPCB air temp, humidity, wind | ERA5-Land (heat stress map, atmospheric drivers, physics features) + **CPCB Vyttila and Eloor** stations (validation) | 1 |
| **Input:** OSM, GHSL, UT-GLOBUS (if available) | OSM buildings, roads and sites; GHSL; UT-GLOBUS through the GEE community catalog **if Kochi is covered** (checked before the event; otherwise stated) | 1 |
| **Optional:** SOLWEIG & InVEST | **InVEST Urban Cooling** (Python `natcap.invest`) as a process-based benchmark to compare with our ML ranking. SOLWEIG is skipped (needs a detailed surface model; future scope) | 3 |
| **Outcome:** heat stress maps identifying hotspots | Tab 1 | 1 |
| **Outcome:** quantitative assessment of key drivers | Tab 2 (spatial SHAP + atmospheric scene analysis) | 1 |
| **Outcome:** validated AI/ML model | Tab 5 (spatial CV, baselines, 2017→2024 back-test, CPCB, ECOSTRESS) | 1–2 |
| **Outcome:** scenario-based evaluation of interventions | Tab 3: every intervention's °C effect per ward, including ones not chosen | 1 |
| **Outcome:** optimal strategy with **type, spatial placement, °C reduction** | Tab 3 plan table: intervention type · ward + map location · estimated °C reduction (with range) · people · ₹ | 1 |

Extra, beyond PS1: live weather and Malayalam news alerts, the Heat Impact Check, and Ward Heat Cards.

---

## 1. The problem

- Kerala's heat is becoming dangerous. In April 2026, IMD issued heatwave warnings, Ernakulam was forecast to reach ~38 °C, and schools in Kollam and Thrissur were closed. KSDMA even had to debunk a viral "55 °C" rumour.
- Kochi has been losing trees, wetlands and mangroves to concrete, especially along the IT corridor (Kakkanad), the Metro corridor and Vyttila.
- Kochi Municipal Corporation already wants to act, through its climate cell (C-HED) and the Kawaki native-tree programme. What it lacks is an answer to one question: **where should a limited budget go to protect the most people?**

Most heat projects stop at a heat map. A map shows where it's hot, but it doesn't tell a city what to do or where to spend. And every one of them only reacts to heat that already exists. Nobody checks whether the *next* mall or IT park will make a neighbourhood hotter.

## 2. Our solution

VISAT is a web app for **Kochi Corporation's C-HED climate cell and ward councillors**. It uses free satellite data, **live weather data** (no hardware or sensors) and machine learning to:

0. **Warn today (live):** current temperature, humidity and heat index for Kochi, a 72-hour heat forecast, **live weather alerts from Malayalam news channels** (Asianet News, 24 News, MediaOne, Manorama, Mathrubhumi and others), and a ranking of **where to act today** (wards with the most exposed people when today's heat peaks).
1. **Find** where heat hurts the most people, on a 100 m grid of Kochi.
2. **Explain** why each ward is hot (concrete, missing trees, distance from water).
3. **Simulate** realistic fixes: street trees, cool roofs, mangrove restoration.
4. **Optimise** a budget: which fix, where, how many °C of cooling, and for how many people.
5. **Prevent** new heat with the **Heat Impact Check**: before a project is approved, predict how much hotter it will make the area and what it would cost to cancel that out.
6. **Prove** the model works by checking it against real changes in Kochi between 2017 and 2024.

## 3. What the judges see

One web app with 6 tabs, plus a **live strip on top of every tab**:

> **Today in Kochi (live)** · 33 °C · 74% humidity · feels like 41 °C · Heat index: **Danger** · peak 1–4 PM · updated 10:42 · *Weather data: Open-Meteo*
> 📰 **Kerala alerts (Malayalam news, live):** "എറണാകുളം ഉൾപ്പെടെ 6 ജില്ലകളിൽ യെല്ലോ അലർട്ട്" · *reported by 4 channels* · Asianet News · 2 h ago → link
> (Example values only. The real strip shows live numbers and real headlines.)

| Tab | What it shows | Demo line |
|---|---|---|
| **1. Heat** | **Heat Stress Map** (satellite LST + ERA5 meteorological heat index), toggled with plain surface temperature, with the top 10% by heat stress × population highlighted. **Live:** 72-hour heat-index forecast and **"Where to act today"**, ranking wards by today's forecast peak × exposed people × vulnerable sites | "Right now it feels like X °C. These wards need water points and shifted work hours today, and this is where heat hurts most all season." |
| **2. Why** | Click a ward to see what's driving its heat (SHAP: land cover, morphology, vegetation), plus a city panel on **atmospheric drivers** (how air temperature, humidity, wind and sunlight shift Kochi's heat from day to day) | "Ward X is hot mainly because of concrete and missing trees, and on humid, still days the whole city gets Y °C worse." |
| **3. Plan** | **Scenario evaluation:** °C effect of every intervention (trees, mangroves, green roofs, cool roofs, cool pavements, water bodies) per ward. **Optimal strategy:** a budget slider (₹1–50 crore) → table and map of *type · placement · estimated °C reduction · people · ₹*, compared live against simple strategies | "Our plan cools more people than spreading the money evenly." |
| **4. Check a project** ⭐ | **Heat Impact Check.** Click any plot and choose what's proposed (e.g. green plot → IT park). See the heat spread on the map: "+X °C for Y people within 500 m". Then press **"Make it heat-neutral"** to get the cheapest offset plan (trees + cool roofs, with ₹) | "Before Kochi approves this building, it knows the heat bill and how to pay it." |
| **5. Proof** | Predicted vs actual temperature change for places that really changed 2017→2024, plus honest accuracy scores and a physics check | "We predicted X; reality did Y." |
| **6. Ward Heat Card** | One page per ward: hotspots, schools, anganwadis and markets inside them, the top 3 actions with ₹ and °C, native tree species | "A councillor can take this to the next council meeting." |

**Honesty rules**
- Satellite numbers are labelled **"surface °C, ~10:30 AM, Feb–Apr"**. The satellite measures ground temperature at its morning overpass, not the air temperature people feel.
- Live numbers are labelled **"live weather, city-scale"**. The weather model is several km across, so differences between wards come from the satellite layer, not the live feed.
- News items are shown as **headline + channel name + time + link only** (never copied article text), labelled "from Malayalam news; official alerts: IMD / KSDMA". An alert reported by **several channels** is marked as confirmed, and a single-source claim is marked as unconfirmed. This helps against rumours like the viral "55 °C" message KSDMA debunked in 2026.
- The Proof tab has a **data freshness panel**: satellite composite dates, the latest Landsat scene date, the live-weather timestamp, and for every source whether it is *live*, *cached* or *frozen*.

**Why the satellite map itself isn't live:** Landsat passes over Kochi only every 8–16 days, and calling Earth Engine during judging could crash the demo. So the satellite layers are real data frozen at the event, and the weather layer on top is live.

## 4. How it works

```
Satellite data ──► frozen to files ──► ML model ──► Why (SHAP)
                                         │
                                         ├──► What-if fixes ──► Budget optimizer ──► Plan
                                         │
                                         ├──► Reverse what-if (green → built) ──► offset plan ──► Heat Impact Check
                                         │
                                         └──► Back-test 2017→2024 ──► Proof
                                                   all ──► Dashboard + Ward Heat Cards

LIVE:  Open-Meteo API (every 15 min) ──► heat index + 72 h forecast ──┐
       ward exposure (from satellite + population + OSM sites) ───────┴──► "Where to act today"
       Malayalam news RSS (every 15 min) ──► filter Kerala weather/heat ──► district + alert colour ──► ticker ("confirmed by N channels")
       └── on any failure: last good snapshot (data/live_cache.json, data/news_cache.json) + "showing data from <time>"
```

1. **Collect the data, then freeze it.** From Google Earth Engine (all free and open):
   - Landsat 8/9 surface temperature, Feb–Apr, with cloud and quality filters
   - Sentinel-2 greenery, built-up and water indices
   - ESA WorldCover land cover: trees, buildings, water, mangroves
   - GHSL population and building height
   - SRTM elevation
   - neighbourhood features (what is within 300 m and 500 m of each square)
   - 2017 and 2024 snapshots for the back-test
   - **ERA5-Land**: Feb–Apr afternoon air temperature, humidity, wind and solar radiation, plus values at each Landsat overpass time
   - **Urban morphology**: GHSL building height and volume, OSM building footprint density, and **UT-GLOBUS** if Kochi is covered
   - **CPCB** Vyttila and Eloor station air temperature and humidity (downloaded as data before the event)
   - **ECOSTRESS** afternoon LST from NASA AppEEARS (Tier 2; request submitted at hour 0)

   Everything is saved to files early, so the live demo never depends on Wi-Fi.
2. **Model.** XGBoost predicts each square's surface temperature from what's on the ground.
   - **Physics-informed ML** (PS1 Objective 3), with three physics ingredients:
     - **physics-derived features** from the surface energy balance: absorbed shortwave radiation (1 − albedo) × incoming sunlight (ERA5), and evaporative-cooling potential (greenness × reference evapotranspiration)
     - **monotone physics constraints**: concrete can only warm a place; trees, water and reflective surfaces can only cool it
     - an **energy-balance cross-check** of the model's cool-roof results

     We say exactly this and never call it a PINN.
   - It is validated honestly on **whole neighbourhoods it never saw** (2 km spatial block cross-validation) and compared with simpler baseline models.
   - **Atmospheric drivers** (PS1 Objective 2): for each clean Landsat scene, relate Kochi's city-wide heat and its urban–rural difference to ERA5 air temperature, humidity, wind and radiation at overpass. This tells us how much the weather shifts the whole city on a given day. Land cover explains *where* it's hot; the atmosphere explains *how hot the day is*.
3. **Heat stress map and danger zones** (PS1 Objective 1). Heat Stress Index = satellite surface-temperature anomaly (100 m) combined with the ERA5-Land Feb–Apr afternoon **heat index** (meteorological). Checked against CPCB station readings. Heat stress × population, top 10%, rolled up to Kochi's 74 wards (2024 ward map; the 2025 delimitation increased this to 76).
4. **Realistic what-ifs (analog transitions).** To simulate "this street with trees", we don't just change one number. We find 20 real Kochi squares that already look like that and move the square's whole profile toward them. We never go beyond what exists in the real data.
   These are all the intervention types PS1 lists (urban greening, cool roofs, albedo changes, water bodies):

   | Intervention (PS1 category) | Where it's allowed |
   |---|---|
   | **Street trees** (greening) | **Public land only**: roads, schools, parks. Paddy land and wetlands are protected under the Kerala Conservation of Paddy Land and Wetland Act, 2008 |
   | **Mangroves** (greening) | Government or Coastal Regulation Zone (CRZ) shoreline only, never on open water |
   | **Green roofs** (greening) | Buildings. Simulated and scored in °C; the optimizer usually skips them because of cost (₹7,500/m²) |
   | **Cool roofs** (cool roofs / albedo) | Buildings only |
   | **Cool pavements** (albedo changes) | Road cells (OSM roads) |
   | **Water bodies: canal / pond restoration** (water bodies) | Cells along existing canals and drains (OSM `waterway=canal/drain`) and low-lying non-built land. Kochi's canal rejuvenation work makes this realistic |

   Every intervention is **simulated and evaluated** (°C effect per ward, PS1 Objective 4), even when the optimizer doesn't choose it.
5. **Back-test: the key proof.** Find squares where Kochi *really* lost trees or gained concrete between 2017 and 2024. Compare the change our model predicts with the change the satellite actually measured.
6. **Budget optimizer.** Picks the fixes with the most °C × people per rupee, counting the cooling that spreads to neighbouring squares. We show that it beats "spread the money evenly" and "plant trees everywhere". The budget curve is precomputed, so the slider responds instantly.
7. **Heat Impact Check (prevention).** Runs the what-if in reverse. A planner picks a plot and a proposed land use (IT park, mall, housing, parking), and the plot's profile moves toward real Kochi squares that already look like that. Because the model uses 300/500 m neighbourhood features, it predicts the heat **spreading to neighbouring squares**, not just the plot itself. The optimizer then finds the **cheapest heat offset**: trees on nearby public land plus cool roofs on the project, until the net change is ≤ 0 °C. It reuses the analog transitions and the optimizer, so it's about 2–3 hours of new work.
   - Output: "+1.3 °C for 4,200 people within 500 m. To be heat-neutral: 40 street trees + 6,000 m² cool roof ≈ ₹38 lakh." (Illustrative only; the real numbers come from the model.)
   - Why it matters: GCDA and Kochi Corporation already approve building permits. Cities abroad require canopy or cool roofs on new development, but we found no Kerala equivalent. This gives Kochi a way to start **heat-neutral development**, like carbon offsets but for heat.
8. **Physics check and extra validation.**
   - For cool roofs, compare the model's answer with a textbook surface energy-balance calculation.
   - *(Tier 2)* **ECOSTRESS afternoon LST** checks whether our hotspot ranking holds at 1–3 PM.
   - *(Tier 3)* **InVEST Urban Cooling**, a process-based model and optional PS1 tool, is run on the same land cover to compare its cooling ranking with ours.
9. **Live layer.** One request to the free **Open-Meteo** forecast API (no key) covers ~8 Kochi points: Fort Kochi, Mattancherry, Ernakulam South, Kaloor, Edappally, Vyttila, Kakkanad, Kalamassery.
   - It returns current temperature, humidity, feels-like and wind, plus hourly heat, wet-bulb, UV and sunlight for 72 hours.
   - From these we compute the **heat index**, the humid-heat measure KSDMA's alerts use, and its category band.
   - "Where to act today" = today's forecast peak heat index × each ward's exposure: satellite heat anomaly × population × schools, anganwadis, markets and harbours.
   - **Live Malayalam news alerts.** RSS feeds, tested working on 25 Sep 2026:
     - a **Google News Malayalam** search, which aggregates Asianet News, 24 News, MediaOne, News18 Malayalam, Manorama, Kerala Kaumudi and Indian Express Malayalam
     - **Mathrubhumi** and **24 News** direct feeds

     We keep only Kerala weather items using Malayalam keywords (ചൂട്, താപനില, ഉഷ്ണതരംഗം, സൂര്യാതപം, അലർട്ട്, plus district names such as എറണാകുളം, കൊച്ചി), and drop Gulf/UAE stories. From each headline we pull out **district + alert colour** (യെല്ലോ / ഓറഞ്ച് / റെഡ്), then group matching headlines to show "confirmed by N channels".
   - **Heat first, weather always.** Heat alerts are highlighted. If there are no heat alerts in the last 7 days (e.g. during the monsoon), the ticker says "No heat alerts this week" and shows the latest Kerala weather alerts, so it is never empty on demo day.
   - **Never-crash rule:** 3-second timeout, results cached for 15 minutes, and on any failure the app loads the last good snapshot (`data/live_cache.json`, `data/news_cache.json`) with a "showing data from <time>" banner. It is tested with Wi-Fi off.
10. **Dashboard.** Streamlit + pydeck, deployed online, with automated tests, a README, 5 slides and a demo video.

## 5. Why this can win

| Judging area | What we bring |
|---|---|
| **Technical depth** | Physics-informed ML (energy-balance features + monotone constraints + energy-balance check), satellite + meteorological heat stress map, atmospheric driver analysis, spatial cross-validation against baselines, analog-transition simulation, a budget optimizer with spatial spillover, and a real-world back-test |
| **Innovation** | Most teams stop at a heat map. We **warn today** (live), decide **where to spend**, **prevent new heat** with the Heat Impact Check (heat-neutral development, new for Kerala), and prove it on real change |
| **Working demo** | Live weather with an offline fallback, satellite data frozen to files, a deployed live URL, CI-tested code, and a rehearsed demo that doesn't crash |
| **UI/UX** | Six clear tabs, a live budget slider, a one-click "Check a project" flow, and a Ward Heat Card anyone can read |
| **Impact & scale** | Built for a real user (Kochi Corporation's C-HED), sourced costs, public-land only, and config-driven so it works for any Kerala city |
| **Q&A** | Every member owns a topic, and everyone can explain the back-test in one sentence |

## 6. Intervention costs (sourced; to be re-verified before the event)

| Fix | Cost | Source |
|---|---|---|
| Street tree, including 5-year maintenance | ₹3,100 per tree | BBMP tender (Deccan Herald) |
| Cool roof coating | ₹300 per m² | Telangana Cool Roof Policy 2023 |
| Cool roof recoat (humid climate) | ₹150 per m², every 3 years | Our estimate |
| Mangrove restoration | ₹1–8 lakh per hectare | CEEW (Odisha); One Earth, 2025 |
| Green roof | ₹7,500 per m² → **simulated and scored**, but rarely chosen because of cost | IndiaSpend |
| Cool pavement (reflective road coating) | **To research (M4)** | Indian cool-pavement pilots / CPWD rates |
| Canal / pond restoration (water bodies) | **To research (M4)** | Kochi canal rejuvenation project costs / AMRUT water-body rejuvenation rates |

## 7. Build tiers

We move to the next tier only after the previous checkpoint passes.

**Tier 1: Core (must ship)**
- The core pipeline above (steps 1–6, 8 and 10), which covers **every PS1 objective and outcome** (see the checklist in section 0). That includes the **satellite + meteorological heat stress map**, **atmospheric drivers**, **physics-informed features**, and scenarios for **trees, green roofs, cool roofs and water bodies**.
- **Live strip + cache/fallback** (~1.5 h): current Kochi weather, heat index, update time and Open-Meteo credit, working with Wi-Fi off.
- CI with GitHub Actions: tests and lint from hour 2.
- A data manifest listing dataset IDs and file hashes, for reproducibility.

**Tier 2: Prevention + stronger proof (after the 4 PM checkpoint)**
- ⭐ **Heat Impact Check**, the headline innovation, built first in Tier 2: reverse what-if, neighbourhood spread, cheapest heat-neutral offset, and the "Check a project" tab.
- **Live 72-hour forecast + "Where to act today" ward ranking** (~2 h), plus the data freshness panel.
- **ECOSTRESS afternoon LST check** (~1 h once the AppEEARS files arrive): do hotspots hold at 1–3 PM?
- **Cool pavements and mangroves** added to the scenarios.
- **Live Malayalam news alert ticker** (~1.5–2 h): RSS fetch, keyword filter, district + alert-colour extraction, "confirmed by N channels", cache/fallback.
- **Quasi-experimental back-test:** squares that lost trees compared with matched, similar squares that didn't. We never call it "causal".
- **Error ranges:** 90% intervals on temperature predictions. What-if ranges come from the back-test error spread. A "conservative mode" optimizer uses the low end.
- **Protect vulnerable places:** schools, anganwadis, hospitals and markets (from OpenStreetMap) get extra weight, adjustable with a slider.
- **Independent check:** comparison with CPCB/IMD air-temperature stations in Kochi.

**Tier 3: Polish and reach (after the 11 PM checkpoint)**
- A before/after swipe map and a printable Ward Heat Card, including a Malayalam version translated by a team member.
- **"Ask VISAT":** type a request such as "₹2 crore for ward 23, protect schools". An AI model only turns the request into optimizer settings, and every number comes from our own code. A typed form stays available as a fallback. This is shown after the main demo, never instead of it.
- Thiruvananthapuram hotspots, generated from the same config, to show that it scales.
- **InVEST Urban Cooling benchmark** (an optional PS1 tool): run on the same land cover and compare its cooling ranking with ours.

**Deliberately avoided:** machine-translated text with unchecked numbers, calling correlation "causal", false certainty on what-if numbers, and flashy animations.

## 8. Team roles

| Member | Builds | Presents / Q&A |
|---|---|---|
| **M1, Data & Model** | Submit the ECOSTRESS AppEEARS request at hour 0 → Earth Engine exports incl. ERA5-Land and morphology (frozen by 2 PM) → heat stress map + atmospheric driver analysis → model + validation + baselines → back-test → hotspots → heat-index helper for the live strip → *(Tier 2)* live ward exposure × forecast ranking, matched back-test, error ranges | Slides 2–3; data and validation questions |
| **M2, Scenarios & Optimizer** | Physics-derived features → analog-transition fixes for all PS1 intervention types (trees, green roofs, cool roofs, water bodies; *Tier 2* cool pavements, mangroves) → budget optimizer + baselines → cool-roof physics check → tests and CI → *(Tier 2)* **Heat Impact Check engine** (reverse transition + offset optimizer), vulnerability weights → *(Tier 3)* Ask VISAT tools | Slide 4; optimizer and physics questions |
| **M3, Dashboard** | Hello-world deployed by 12 PM → **live strip** (Open-Meteo fetch, 15-min cache, offline fallback) → 6-tab app → public-land and school/market layers → Ward Heat Card → *(Tier 2)* "Check a project" tab (plot click + land-use picker), 72-hour forecast chart, "Where to act today" list, freshness panel → *(Tier 3)* swipe map, printable card | Live demo; ward walkthrough |
| **M4, Product & Pitch** | Sourced costs → baseline comparison slide → README + AI-use disclosure → *(Tier 2)* **Malayalam news alert feed**: RSS fetch, keyword list and district/alert-colour rules, with AI-assistant help; a native Malayalam reader checks the keywords. M3 builds the ticker UI → 5 slides, demo video, demo script → timekeeping and submission | Slides 1 and 5; costs and impact questions |

## 9. 24-hour timeline (work starts ~10 AM)

| Time | Milestone |
|---|---|
| 10:00 AM | Everyone: create the repo, agree the data columns, confirm the problem statement |
| 12:00 PM | Hello-world app live; CI running |
| **2:00 PM** | **Data frozen to files** |
| **4:00 PM** | **Checkpoint 1:** real heat map and honest accuracy on screen → Tier 2 unlocked |
| 7:00 PM | What-if fixes and back-test done |
| **11:00 PM** | **Checkpoint 2:** full demo working on the live URL → Tier 3 unlocked |
| **1:00 AM** | Fallback: if the optimizer isn't working, ship ranked hotspots + °C per fix |
| 2:00–5:00 AM | Sleep in shifts (M1 + M3 2:00–3:30, M2 + M4 3:30–5:00) |
| 5:00 AM | Feature freeze; record the demo video |
| **6:00 AM** | **Code freeze**; 3 full rehearsals, one with Wi-Fi off |
| 8:00–8:45 AM | Submit: GitHub repo, live URL, video, 5 slides (portal locks at 9:00 AM) |

## 10. Demo and slides

**3-minute demo**
- 0:00: **open live**: "Right now in Kochi it's X °C and feels like Y. Here's where it's dangerous today…"
- 0:15: "…and here's how we fix it for good. With ₹10 crore, where do we start?" Heat tab (satellite)
- 0:40: Why tab
- 1:00: **move the Plan slider and beat the baselines** (key moment 1)
- 1:45: **Check a project**: click a green plot in Kakkanad → "IT park" → the heat spreads → "Make it heat-neutral" (key moment 2)
- 2:30: Proof tab, "we predicted X, reality did Y"

**5 slides**
1. Problem (M4)
2. Data (M1)
3. Model + proof (M1/M2)
4. Fix today (plan vs baselines) + prevent tomorrow (Heat Impact Check) (M2)
5. Impact, ward cards, heat-neutral development, scale (M3/M4)

**One sentence every member can say:**
> "Where Kochi really lost trees or gained concrete between 2017 and 2024, our model predicted the temperature change, and here's how close it got."

## 11. Questions to prepare for

| Question | Who answers | Short answer |
|---|---|---|
| Why should we believe planting trees *causes* your ΔT? | M1 | Physics rules fix the direction of each effect, what-ifs move toward real Kochi squares, and the 2017→2024 back-test compares predictions with reality. |
| Where exactly is the physics? | M2 | Three places: (1) features built from the surface energy balance: absorbed sunlight (1 − albedo) × incoming radiation, and evaporative-cooling potential; (2) monotone constraints so concrete can only warm and trees, water and reflective surfaces can only cool; (3) an energy-balance cross-check of cool-roof results. It's physics-informed ML, not a physics-informed neural network, and we say that plainly. |
| Did you cover everything in the problem statement? | M4 | Yes. Section 0 of our plan maps every PS1 objective, dataset and outcome to a feature: satellite + meteorological heat stress maps, all four driver groups, physics-informed ML, all four intervention types, and the optimal strategy with type, placement and °C. |
| Satellite surface temperature isn't the heat people feel. | M1 | Correct, and every number is labelled as surface temperature. It's the only open, city-wide 100 m data. We use it to rank options, not to forecast air temperature. |
| Where do the costs come from? What if they're off by 2×? | M4 | Every cost has a source. The optimizer re-runs instantly, so we can show whether the ranking changes. |
| Any independent check beyond satellite data? | M1 | CPCB/IMD station comparison. Only a few stations, so it's a sanity check, and we say so. |
| What if a place gets both trees and a cool roof? | M2 | One fix per square is a deliberate simplification to avoid overstating the cooling. It's our next step. |
| How accurate is the Heat Impact Check for a building that doesn't exist yet? | M2 | It uses the same model and analog method we back-tested on real 2017→2024 construction, so its error is the back-test error. We show it as a range, not a single promise. |
| Doesn't Kawaki already do this? | M4 | Kawaki proves Kochi wants data-driven cooling; it picks tree-grove sites. VISAT adds budget trade-offs (trees vs cool roofs vs mangroves), prevention for new projects, and verification. It's a tool for C-HED to plan the next Kawaki sites. |
| Is your heat map live? | M3 | The weather and today's risk ranking are live, updated every 15 minutes. The satellite map can't be real-time because Landsat only passes every 8–16 days, so it's real data frozen at the event. It shows *where* land cover makes heat worse; the live layer shows *when* it's dangerous. |
| Why use news headlines? Aren't they unreliable? | M4 | People in Kerala hear about heat through Malayalam news first, so we show what they're seeing, always with channel name, time and link. An alert reported by several channels is marked as confirmed; a single-source claim is not. Official alerts still come from IMD and KSDMA, and we say so on screen. |
| What if the live feed fails during the demo? | M3 | It falls back to the last good snapshot with a clear "showing data from <time>" banner. We rehearsed with Wi-Fi off. |
| Walk me through one ward. | M3 | Open its Ward Heat Card: hotspots, vulnerable sites, what drives the heat, and the top 3 actions with ₹ and °C. |

## 12. Before the event (no code is written before the event)

- **Everyone:** register for Google Earth Engine now (approval can take days), install Python + `uv`, set up GitHub.
- **M1:** list dataset IDs, bands and scaling factors; download the Kochi ward map (BharatLAS/OpenCity); create a **NASA Earthdata** account and practise an AppEEARS ECOSTRESS request; **check whether UT-GLOBUS covers Kochi**.
- **M2:** practise XGBoost monotone constraints, spatial cross-validation and nearest-neighbour search.
- **M3:** practise Streamlit + pydeck; deploy a hello-world; sketch the 6 tabs, the "Check a project" flow and the ward card.
- **M4:** verify costs, and **research cool-pavement and canal/pond-restoration costs**; collect heat news; contact Kochi Corporation's C-HED, a ward councillor or KSDMA for real feedback (only genuine quotes); download CPCB/IMD station temperatures; prepare the slide template.

## 13. Backup plans

- **If the problem list changes on the day:** PS2 (crop type and moisture stress) shares about 70% of this pipeline; PS6 (carbon tracker) is the second fallback.
- **If the Wi-Fi fails:** satellite data is already frozen to files, and the live strip falls back to its last snapshot. Bring two phone hotspots.

## 14. Rules we follow

- All project code is written during the event. This document is a plan only.
- AI assistants are allowed and are disclosed in the presentation.
- Submission: public GitHub repo with README, live URL and a 2–3 minute video, and a 5-slide deck.
- Demo data, if ever shown, is clearly labelled. Every team member presents.

---

*Author: Jeevan George*
