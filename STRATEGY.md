# VISAT — Winning Strategy & Risk Register

Companion to [PLAN.md](./PLAN.md) and [RESOURCES.md](./RESOURCES.md). Those two cover *what to build*. This one covers *how to win*:
- the judging criteria
- the risks specific to this plan's shape: four screens, a live weather strip plus alert/news chips, the Heat-Neutral Development Check, and a scene-panel physics model
- the exact order to cut scope if the clock runs out

It is analysis and pre-event decisions only, with no project code (PLAN.md §14).

**Updated for plan v5**, after four expert-review rounds (remote sensing, ML engineering, hackathon strategy, Kerala planning, UX, and a judge scoring against the HackMe'26 rubric). The earlier version of this file was written against v4, with six tabs, a scrolling news ticker and ECOSTRESS dropped.

---

## 0. Corrections verified against the official event site's source

Pulled directly from `chsrikar/hackme-26` (the site's own source, `src/pages/RubricPage.jsx`, `src/data/schedule.js`, `src/pages/RulesPage.jsx`) rather than the rendered page, since the site is a client-rendered SPA that doesn't show its text to a normal fetch. Two corrections to what's below and to PLAN.md:

**1. The rubric has exactly 5 weighted pillars, not 6 — "UI/UX" isn't a separate line.** Confirmed verbatim from the rubric page: Innovation & Originality 30%, Technical Complexity & Depth 25%, Working Execution & Live Demo 20%, Practical Utility & Impact 15%, Presentation Craft & Jury Q&A 10%. These sum to exactly 100%. §1's table below folds UI/UX in as if it had its own "remainder" weight — it doesn't; UI quality is judged as part of *Working Execution* (does the live demo work well) and *Presentation* (does it communicate clearly), not as a sixth pillar. Don't budget extra effort assuming UI/UX has independent scoring weight beyond that.

**2. The real pitch format is a 5-minute pitch + 2-minute jury Q&A, not the 3-minute demo PLAN.md §10 rehearses.** Confirmed from the rubric page: "Functioning prototype during the **5-minute team pitch**" and "Crisp, confident responses... during **2 min Q&A**." PLAN.md §10's "3-minute demo" script should be rewritten for the actual 5-minute window — there's 2 extra minutes to use, likely best spent slowing down on the Proof screen (the back-test is the hardest thing to rush) and giving the Check-a-Project moment more room to land, rather than compressing everything to fit an assumed shorter slot.

**3. Real hacking time is split by a 4.5-hour mandatory social block, not continuous — this still isn't reflected in PLAN.md §9.** From the actual timed schedule (`src/data/schedule.js`):

| Real block | Time | What it is |
|---|---|---|
| Work block 1 | 2:00–4:30 PM | 2.5 hours |
| Ice-breaking, live music band, games | **5:00–9:30 PM** | **4.5 hours, no work — organizer-scheduled** |
| Work block 2 | 9:30 PM–9:00 AM | 11.5 hours, the real main build window |
| Hard submission deadline | 9:00 AM Day 2 | Portal locks strictly; no commits after count |

Total real build time is **~14 hours**, not the ~23 continuous hours PLAN.md §9's checkpoint schedule (4 PM, 7 PM, 11 PM, 1 AM, 5 AM, 6 AM) currently assumes. **Action needed:** either shrink the 4 PM checkpoint 1 bar (PLAN.md currently expects "scene-panel model + exposure map on screen" from a block that only has 2.5 hours including setup), or move checkpoint 1 to right after the 9:30 PM restart. Decide as a team before 2 PM whether anyone skips part of the 5–9:30 PM block — nothing in the rules forbids it, but losing the time by default versus choosing to is a real difference given how tight Tier 1+2 already are.

---

## 1. Judging criteria: what actually gets scored

The HackMe'26 site ([hackme-26.vercel.app](https://hackme-26.vercel.app/)) publishes a rubric with **5 weighted pillars summing to 100%** (verified against the site's source — see §0.1, which corrects the "6 categories with a remainder" framing this table used before):

| Criterion | Weight | What judges check (site wording) | Where VISAT v5 stands |
|---|---|---|---|
| **Innovation & Originality** | 30% | Novel architecture, creative synthesis across domains, *differentiation from existing off-the-shelf solutions* | **Strong.** The Heat-Neutral Development Check (a screening tool tied to KMBR/SEIAA hooks) plus a warn / plan / prevent / prove story. Kochi-specific pieces: IURWTS canal overlay, Labour-order-linked "act today". |
| **Technical Complexity & Depth** | 25% | Engineering depth, system architecture, robust algorithms, code quality, non-trivial algorithmic logic | **Strong.** Scene-panel physics-informed XGBoost (cells × scenes with per-scene ERA5), grouped spatial-block CV against baselines, validity matrix, joint re-prediction with tests, an optimizer that beats naive baselines, and a 2017→2024 back-test. |
| **Working Execution & Live Demo** | 20% | Functioning prototype during the 5-min pitch; handles edge cases without crashing; test passes; reproducible deployment | **The main risk (§3–4).** Mitigated by data frozen by 2 PM, cached ₹1/10/50 crore presets, a fallback for every live item, pre-drawn project sites, a backup recording, and warming the app up before the slot. UI quality (four plain-language screens, dark projector theme, printable Ward Card) is judged here, not as a separate category. |
| **Practical Utility & Impact** | 15% | Target users defined; viability; potential to scale beyond the sprint | Named user (C-HED), sourced costs, public land only, a "which rule / who signs" line, and config-driven so it can scale to other cities. |
| **Presentation Craft & Jury Q&A** | 10% | Clarity, 5-min time adherence, equal participation, crisp 2-min Q&A answers | Each member presents one screen and owns set Q&A topics (PLAN.md §11). Rehearse for the real 5+2 minute window (§0.2), not 3 minutes. |

The judge-panel estimate for v5 is **about 84/100 with Tier 1+2 and about 86 with everything.** A perfect 10/10 isn't realistic, but 9s are reachable in technical depth, innovation and impact. **The deciders are a demo that doesn't crash and all four members answering questions.**

---

## 2. What's already been checked and fixed (noted for completeness)

- **ECOSTRESS.** It is not in Earth Engine for Kochi (only Los Angeles tiles), but **PS1 lists it as an input**, so v5 keeps it through **NASA AppEEARS**. Tier 1 shows an afternoon (12:00–15:30) map on the Proof screen. Tier 2 adds rank agreement with Landsat (Spearman correlation + top-decile overlap). *(The v4 version of this file said "correctly dropped". That would have left a PS1 gap.)*
- **ESA WorldCover time series.** There is no 2017 or 2024 edition, so the back-test uses Dynamic World and WorldCover is used only for the present-day map.
- **Sentinel-2 in 2017.** Surface reflectance over India reportedly starts around Dec 2018, so the 2017 back-test uses **Landsat NDVI**. M1 confirms this in GEE before the event.
- **ERA5 is now a real model input.** The scene-panel model gives each satellite scene its own ERA5 weather, so (1 − albedo) × incoming sunlight varies by scene and is actually learned. *(The v4 note "ERA5 not a model feature" is out of date — no longer an issue now that the pre-event `config.py` has been removed, see §4.)*
- **Canals** get **no °C credit**, because they are narrower than the 100 m grid. Instead, the KMRL IURWTS canal project is shown as an overlay, and tree strips along the canal banks are offered as the actual intervention.

One additional gap needs only a one-line Q&A answer, not a rebuild:

**GHSL population has no real 2024 epoch.** The last real epoch is 2020, and 2025/2030 are projections. The population layer is a weighting, not the thing being validated (see §5).

---

## 3. Scope risk: the real threat

v5 already cut a lot (Ask VISAT, Thiruvananthapuram, InVEST, UT-GLOBUS, the swipe map, the scrolling ticker, the separate 72-hour screen, conformal intervals, the drag slider). But **Tier 2 still has six items** in the after-4 PM window:
- the Heat-Neutral Check
- ECOSTRESS stats
- the alert and news chips
- "who signs" lines
- vulnerability weights
- DiD

The roles table spreads these across M1–M4. What remains is sequencing *within* each person's list.

**Fix: one hard sub-priority per Tier 2 owner, decided now.**
- **M2:** the **Heat-Neutral Check engine ships before vulnerability weights.** It is the hero screen, the one Tier 2 item that must not slip.
- **M1:** **ECOSTRESS rank agreement ships before the matched back-test (DiD).** It answers the most likely scientific attack ("10:30 AM isn't the heat people feel"). The plain Tier 1 back-test is still honest and demoable.
- **M3:** **the Check-a-Project UI ships before anything cosmetic.** Use pre-drawn sites plus the use picker; the ledger animation can wait for Tier 3.
- **M4:** **the official KSDMA/IMD alert chip ships before the Malayalam news chip.** The news chip is the most fragile Tier 2 item (external RSS plus Malayalam keyword matching). If M4 is behind at 7 PM, the live weather strip plus the official alert carry the "warn today" story; cut the news chip before anything else in Tier 2.
- **Scene-panel fallback:** if the scene-panel model isn't working by the **4 PM checkpoint**, switch to the single-composite model, describe it honestly, and move on.

---

## 4. Technical risk register (v5)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| ~~Pre-event code in the repo~~ **Fixed.** `src/visat/config.py`, `pyproject.toml`, the CI workflow and tests were removed from `main` — the rules explicitly name "code, schemas and configurations" as things that must be written during the event, with disqualification as the stated consequence for pre-existing code. Recreate all of it live at the event; only PLAN/RESOURCES/STRATEGY (plans, not code) stay pre-event | — | — | Resolved | Team |
| Scene-panel model underperforms or is late | Medium | Weakens the physics-informed and atmospheric-driver story | 4 PM checkpoint fallback to the composite model, described honestly. Report n scenes and confidence intervals either way | M1 |
| pydeck can't register clicks on arbitrary land (`on_select` returns only picked objects), and reruns reset the view | High if unplanned | The hero screen breaks live | **5–8 pre-drawn candidate sites** as a pickable polygon layer, `st.segmented_control` for the use type, `view_state` kept in `session_state`, and all results cached | M3 |
| Budget interaction lags on rerun | Medium | The wow moment stutters | **Preset buttons for ₹1/10/50 crore** with precomputed results, no drag slider | M3 |
| Malayalam news chip shows a wrong or irrelevant headline in front of judges (a Gulf heat story leaks in, or an item is stale or misclassified) | Medium | Embarrassing but recoverable | It's a **static chip next to the official alert**, and the headlines sit behind an expander. Keep 3–4 known-good items ready to swap into `data/news_cache.json` on demo morning; if there's no cache, the chip hides itself | M4 |
| Judge asks whether using news RSS feeds is legitimate | Low | Credibility wobble if unprepared | Public syndication feeds; only headline, channel, time and link are shown, never article text (RESOURCES.md §2c) | M4 |
| Open-Meteo's 8 points collapse to about 4 model cells, and a judge reads that as "not ward-level" | Medium | Undercuts the live claim | Say it first: the live layer is **city-scale** and tells you *when*; the satellite layer tells you *where* | M3 |
| A judge attacks the Heat-Neutral Check ("heat-neutral isn't a law", "you can't predict a building that doesn't exist") | Medium | The toughest Q&A moment | Call it a **screening tool and a policy proposal**, never an approval. Mention the KMBR extra-FSI incentive and SEIAA Form-1A hooks. Use donors that match the site's context. Say "surface-°C, morning" and always say **"range"**, never a bare number | M2 + M4 |
| A judge attacks the physics or the canal assumptions | Medium | Credibility | Show the validity matrix: which interventions use analogs, which use the formula, which get no credit. Canals get 0 °C credit; IURWTS is an overlay | M2 |
| Streamlit Cloud cold start or venue Wi-Fi fails during the slot | Medium | The demo dies | Warm the app up 10 minutes early; keep a backup screen recording; freeze the data; rehearse with Wi-Fi off | M3 |
| GHSL population epoch (2020 or projection) doesn't match the 2024 back-test year | Low | Minor | Q&A answer ready (§5) | M1 |

---

## 5. Additional Q&A (complements PLAN.md §11, doesn't repeat it)

| Question | Who | Answer |
|---|---|---|
| Your population layer: is it really 2024 data? | M1 | GHSL's latest real epoch is 2020 (2025/2030 are projections). It's a population-density weight, not what we validate. The *temperature* change we prove is real 2017→2024 satellite data. |
| Is using news RSS feeds okay here? | M4 | They're public syndication feeds. We show only headline, channel, time and link, never article text, and it sits next to the official KSDMA/IMD alert, which is the authority. |
| How do I know the live layer is really live right now? | M3 | Look at the timestamp on the strip ("updated X min ago"). It refreshes every 15 minutes, and the freshness panel on the Proof screen shows which layers are live, cached or frozen. |
| Why only four screens? | M3 | A councillor needs four answers: where it's dangerous today, what to do with the money, whether a new project adds heat, and whether to trust it. Everything else is in expanders for Q&A. |

---

## 6. Presentation checklist

- **Visual system (v5):** dark theme; red/orange means *heat* only and teal means *fixes* only (inferno-style scale), with no third accent. Text at least 20 px, key numbers 48–64 px. Decide the exact hex values now, not at 4 AM.
- **Backup:** put 3–4 screenshots of the key moments into the deck, in case both the live URL and the backup video fail. The key moments are the Today strip with "act today", the Plan ₹10 crore preset beating the baselines, the Check-a-Project ledger going +1.3 → 0.0 °C, and the Proof back-test chart.
- **Use PS1's own words on slide 1:** "heat stress hotspots", "physics-informed", "cooling interventions". Judges pattern-match problem-statement wording.
- **Physical takeaway:** hand out printed A5 Ward Cards for the jury's own area at the close (Tier 3). Judges discuss the thing they hold.
- **One closing number, repeated at the start and the end:** "₹10 crore → −X surface-°C for Y people, back-test error ±Z."
- **Rehearse over adding.** If you have to choose between finishing a feature and a rehearsal pass, rehearse. An unrehearsed extra feature scores worse than a clean pitch of a smaller one. Rehearse all live fallbacks together once, with Wi-Fi off.
