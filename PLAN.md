# VISAT: Kochi Heat Action Planner

**HackMe'26 · VISAT Engineering College · AI/ML track · PS1: Urban Heat Mitigation via AI/ML**

> **"VISAT tells Kochi where to spend ₹10 crore to cool the most people, and checks every new project so the city stops getting hotter. We prove it against real change from 2017 to 2024."**

---

## 1. The problem

- Kerala's heat is becoming dangerous. In April 2026, IMD issued heatwave warnings, Ernakulam was forecast to reach ~38 °C, and schools in Kollam and Thrissur were closed. KSDMA even had to debunk a viral "55 °C" rumour.
- Kochi has been losing trees, wetlands and mangroves to concrete, especially along the IT corridor (Kakkanad), the Metro corridor and Vyttila.
- Kochi Municipal Corporation already wants to act, through its climate cell (C-HED) and the Kawaki native-tree programme. What it lacks is an answer to one question: **where should a limited budget go to protect the most people?**

Most heat projects stop at a heat map. A map shows where it's hot, but it doesn't tell a city what to do or where to spend. And every one of them only reacts to heat that already exists. Nobody checks whether the *next* mall or IT park will make a neighbourhood hotter.

## 2. Our solution

VISAT is a web app for **Kochi Corporation's C-HED climate cell and ward councillors**. It uses only free satellite data (no hardware or sensors) and machine learning to:

1. **Find** where heat hurts the most people, on a 100 m grid of Kochi.
2. **Explain** why each ward is hot (concrete, missing trees, distance from water).
3. **Simulate** realistic fixes: street trees, cool roofs, mangrove restoration.
4. **Optimise** a budget: which fix, where, how many °C of cooling, and for how many people.
5. **Prevent** new heat with the **Heat Impact Check**: before a project is approved, predict how much hotter it will make the area and what it would cost to cancel that out.
6. **Prove** the model works by checking it against real changes in Kochi between 2017 and 2024.

## 3. What the judges see

One web app with 6 tabs:

| Tab | What it shows | Demo line |
|---|---|---|
| **1. Heat** | Kochi in 100 m squares, coloured by surface temperature. The top 10% by heat × population is highlighted | "This is where heat hurts the most people." |
| **2. Why** | Click a ward to see what's driving its heat (SHAP explanations) | "Ward X is hot mainly because of concrete and missing trees." |
| **3. Plan** | Budget slider (₹1–50 crore) → map of which fix goes where, with "−X °C for Y people". Compared live against simple strategies | "Our plan cools more people than spreading the money evenly." |
| **4. Check a project** ⭐ | **Heat Impact Check.** Click any plot and choose what's proposed (e.g. green plot → IT park). See the heat spread on the map: "+X °C for Y people within 500 m". Then press **"Make it heat-neutral"** to get the cheapest offset plan (trees + cool roofs, with ₹) | "Before Kochi approves this building, it knows the heat bill and how to pay it." |
| **5. Proof** | Predicted vs actual temperature change for places that really changed 2017→2024, plus honest accuracy scores and a physics check | "We predicted X; reality did Y." |
| **6. Ward Heat Card** | One page per ward: hotspots, schools, anganwadis and markets inside them, the top 3 actions with ₹ and °C, native tree species | "A councillor can take this to the next council meeting." |

**Honesty rule:** every number is labelled **"surface °C, ~10:30 AM, Feb–Apr"**. The satellite measures ground temperature at its morning overpass, not the air temperature people feel. We never overclaim.

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
```

1. **Collect the data, then freeze it.** From Google Earth Engine (all free and open):
   - Landsat 8/9 surface temperature, Feb–Apr, with cloud and quality filters
   - Sentinel-2 greenery, built-up and water indices
   - ESA WorldCover land cover: trees, buildings, water, mangroves
   - GHSL population and building height
   - SRTM elevation
   - neighbourhood features (what is within 300 m and 500 m of each square)
   - 2017 and 2024 snapshots for the back-test

   Everything is saved to files early, so the live demo never depends on Wi-Fi.
2. **Model.** XGBoost predicts each square's surface temperature from what's on the ground.
   - **Physics rules are built in** as monotone constraints: concrete can only warm a place, and trees, water and reflective roofs can only cool it. We call this *physically consistent*.
   - It is validated honestly on **whole neighbourhoods it never saw** (2 km spatial block cross-validation) and compared with simpler baseline models.
3. **Danger zones.** Heat × population, top 10%, rolled up to Kochi's 74 wards (2024 ward map; the 2025 delimitation increased this to 76).
4. **Realistic what-ifs (analog transitions).** To simulate "this street with trees", we don't just change one number. We find 20 real Kochi squares that already look like that and move the square's whole profile toward them. We never go beyond what exists in the real data.
   - Trees go on **public land only**: roads, schools, parks. Paddy land and wetlands are protected under the Kerala Conservation of Paddy Land and Wetland Act, 2008.
   - Cool roofs go on buildings only.
   - Mangroves go only on government or Coastal Regulation Zone (CRZ) shoreline, never on open water.
5. **Back-test: the key proof.** Find squares where Kochi *really* lost trees or gained concrete between 2017 and 2024. Compare the change our model predicts with the change the satellite actually measured.
6. **Budget optimizer.** Picks the fixes with the most °C × people per rupee, counting the cooling that spreads to neighbouring squares. We show that it beats "spread the money evenly" and "plant trees everywhere". The budget curve is precomputed, so the slider responds instantly.
7. **Heat Impact Check (prevention).** Runs the what-if in reverse. A planner picks a plot and a proposed land use (IT park, mall, housing, parking), and the plot's profile moves toward real Kochi squares that already look like that. Because the model uses 300/500 m neighbourhood features, it predicts the heat **spreading to neighbouring squares**, not just the plot itself. The optimizer then finds the **cheapest heat offset**: trees on nearby public land plus cool roofs on the project, until the net change is ≤ 0 °C. It reuses the analog transitions and the optimizer, so it's about 2–3 hours of new work.
   - Output: "+1.3 °C for 4,200 people within 500 m. To be heat-neutral: 40 street trees + 6,000 m² cool roof ≈ ₹38 lakh." (Illustrative only; the real numbers come from the model.)
   - Why it matters: GCDA and Kochi Corporation already approve building permits. Cities abroad require canopy or cool roofs on new development, but we found no Kerala equivalent. This gives Kochi a way to start **heat-neutral development**, like carbon offsets but for heat.
8. **Physics check.** For cool roofs, compare the model's answer with a textbook surface energy-balance calculation.
9. **Dashboard.** Streamlit + pydeck, deployed online, with automated tests, a README, 5 slides and a demo video.

## 5. Why this can win

| Judging area | What we bring |
|---|---|
| **Technical depth** | Physically consistent ML, spatial cross-validation against baselines, analog-transition simulation, a budget optimizer with spatial spillover, and a real-world back-test |
| **Innovation** | Most teams stop at a heat map. We decide **where to spend**, **prevent new heat** with the Heat Impact Check (heat-neutral development, new for Kerala), and prove it on real change |
| **Working demo** | Data frozen to files, deployed live URL, CI-tested code, a rehearsed demo that doesn't crash |
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
| Green roof | ₹7,500 per m² → **evaluated and excluded** (never cost-effective) | IndiaSpend |

## 7. Build tiers

We move to the next tier only after the previous checkpoint passes.

**Tier 1: Core (must ship)**
- The full 8-step pipeline above.
- CI with GitHub Actions: tests and lint from hour 2.
- A data manifest listing dataset IDs and file hashes, for reproducibility.

**Tier 2: Prevention + stronger proof (after the 4 PM checkpoint)**
- ⭐ **Heat Impact Check**, the headline innovation, built first in Tier 2: reverse what-if, neighbourhood spread, cheapest heat-neutral offset, and the "Check a project" tab.
- **Quasi-experimental back-test:** squares that lost trees compared with matched, similar squares that didn't. We never call it "causal".
- **Error ranges:** 90% intervals on temperature predictions. What-if ranges come from the back-test error spread. A "conservative mode" optimizer uses the low end.
- **Protect vulnerable places:** schools, anganwadis, hospitals and markets (from OpenStreetMap) get extra weight, adjustable with a slider.
- **Independent check:** comparison with CPCB/IMD air-temperature stations in Kochi.

**Tier 3: Polish and reach (after the 11 PM checkpoint)**
- A before/after swipe map and a printable Ward Heat Card, including a Malayalam version translated by a team member.
- **"Ask VISAT":** type a request such as "₹2 crore for ward 23, protect schools". An AI model only turns the request into optimizer settings, and every number comes from our own code. A typed form stays available as a fallback. This is shown after the main demo, never instead of it.
- Thiruvananthapuram hotspots, generated from the same config, to show that it scales.

**Deliberately avoided:** machine-translated text with unchecked numbers, calling correlation "causal", false certainty on what-if numbers, and flashy animations.

## 8. Team roles

| Member | Builds | Presents / Q&A |
|---|---|---|
| **M1, Data & Model** | Earth Engine exports (frozen by 2 PM) → model + validation + baselines → back-test → hotspots → *(Tier 2)* matched back-test, error ranges | Slides 2–3; data and validation questions |
| **M2, Scenarios & Optimizer** | Analog-transition fixes → budget optimizer + baselines → cool-roof physics check → tests and CI → *(Tier 2)* **Heat Impact Check engine** (reverse transition + offset optimizer), vulnerability weights → *(Tier 3)* Ask VISAT tools | Slide 4; optimizer and physics questions |
| **M3, Dashboard** | Hello-world deployed by 12 PM → 6-tab app → public-land and school/market layers → Ward Heat Card → *(Tier 2)* "Check a project" tab (plot click + land-use picker) → *(Tier 3)* swipe map, printable card | Live demo; ward walkthrough |
| **M4, Product & Pitch** | Sourced costs → baseline comparison slide → README + AI-use disclosure → 5 slides, demo video, demo script → timekeeping and submission | Slides 1 and 5; costs and impact questions |

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
- 0:00: the ₹10 crore question
- 0:15: Heat tab
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
| Where exactly is the physics? | M2 | Monotone constraints on every land-cover feature plus an energy-balance check for cool roofs. We call it "physically consistent", not "physics-informed". |
| Satellite surface temperature isn't the heat people feel. | M1 | Correct, and every number is labelled as surface temperature. It's the only open, city-wide 100 m data. We use it to rank options, not to forecast air temperature. |
| Where do the costs come from? What if they're off by 2×? | M4 | Every cost has a source. The optimizer re-runs instantly, so we can show whether the ranking changes. |
| Any independent check beyond satellite data? | M1 | CPCB/IMD station comparison. Only a few stations, so it's a sanity check, and we say so. |
| What if a place gets both trees and a cool roof? | M2 | One fix per square is a deliberate simplification to avoid overstating the cooling. It's our next step. |
| How accurate is the Heat Impact Check for a building that doesn't exist yet? | M2 | It uses the same model and analog method we back-tested on real 2017→2024 construction, so its error is the back-test error. We show it as a range, not a single promise. |
| Doesn't Kawaki already do this? | M4 | Kawaki proves Kochi wants data-driven cooling; it picks tree-grove sites. VISAT adds budget trade-offs (trees vs cool roofs vs mangroves), prevention for new projects, and verification. It's a tool for C-HED to plan the next Kawaki sites. |
| Walk me through one ward. | M3 | Open its Ward Heat Card: hotspots, vulnerable sites, what drives the heat, and the top 3 actions with ₹ and °C. |

## 12. Before the event (no code is written before the event)

- **Everyone:** register for Google Earth Engine now (approval can take days), install Python + `uv`, set up GitHub.
- **M1:** list dataset IDs, bands and scaling factors; download the Kochi ward map (OpenCity).
- **M2:** practise XGBoost monotone constraints, spatial cross-validation and nearest-neighbour search.
- **M3:** practise Streamlit + pydeck; deploy a hello-world; sketch the 6 tabs, the "Check a project" flow and the ward card.
- **M4:** verify costs; collect heat news; contact Kochi Corporation's C-HED, a ward councillor or KSDMA for real feedback (only genuine quotes); download CPCB/IMD station temperatures; prepare the slide template.

## 13. Backup plans

- **If the problem list changes on the day:** PS2 (crop type and moisture stress) shares about 70% of this pipeline; PS6 (carbon tracker) is the second fallback.
- **If the Wi-Fi fails:** data is already frozen to files; bring two phone hotspots.

## 14. Rules we follow

- All project code is written during the event. This document is a plan only.
- AI assistants are allowed and are disclosed in the presentation.
- Submission: public GitHub repo with README, live URL and a 2–3 minute video, and a 5-slide deck.
- Demo data, if ever shown, is clearly labelled. Every team member presents.

---

*Author: Jeevan George*
