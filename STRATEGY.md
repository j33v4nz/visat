# VISAT — Winning Strategy & Risk Register

Companion to [PLAN.md](./PLAN.md) and [RESOURCES.md](./RESOURCES.md). Those cover *what to build*. This covers *how to win*: judging-vector analysis, competitive intelligence, the risks specific to this plan's current shape, and the exact order to cut scope if the clock runs out. Analysis and pre-event decisions only — no project code, per PLAN.md §14.

Written against PLAN.md as of the section-0 PS1 compliance-checklist commit — the most current version. This plan has moved fast (four substantial revisions in one day); re-check this doc's claims against PLAN.md §0 before relying on it if more changes land.

---

## 1. Competitive intelligence — worth knowing before the pitch

- **PS1's exact wording ran nationally at ISRO's Bharatiya Antariksh Hackathon 2026** ("Optimizing Urban Heat Mitigation and cooling strategies via AI/ML"), with 15,104 teams. HackMe'26 is very likely reusing that official problem statement text — which means the PS1 compliance checklist in PLAN.md §0 is a genuinely high-value thing to have done; a judge familiar with the BAH framing will recognize the wording being matched precisely.
- **The generic 2026 hackathon "urban heat" template is now a commodity.** Multiple independent teams (HeatShield-style projects, seen across several 2026 hackathons) converge on the same shape: a hyperlocal temperature API, a 0–100 heat-risk score, a "what-if mitigation simulator," a cooling-center optimizer, and an AI chatbot advisor. That means **a heat map + optimizer + chatbot alone is no longer a differentiator** — most competent teams will have something that looks like that.
- **What actually separates VISAT from that template**, and should be said explicitly and early in the pitch rather than assumed obvious:
  1. **Physics-informed ML with three concrete ingredients** (energy-balance-derived features, monotone constraints, an energy-balance cross-check) — the common template uses plain RF/XGBoost with no physical grounding at all.
  2. **A real 2017→2024 back-test against actual measured change** — almost no hackathon-timescale project validates against real historical change; most validate only against same-period held-out data, which is a weaker claim.
  3. **The Heat Impact Check (prevention, not just reaction)** — running the model in reverse to price the heat cost of a *proposed* development is not present in any reviewed comparable project. This is VISAT's most defensible "nobody else has this" claim; lean on it hardest in Q&A and the opening pitch, not just slide 4.
  4. Language-localized live alerts (Malayalam news ticker) — a hyperlocal touch competitors targeting generic "any city" dashboards don't have.

---

## 2. Judging vectors — what actually gets scored

No official HackMe'26 rubric is published. Using 2025–2026 hackathon judging norms as the working model:

| Vector | Typical weight | Where VISAT stands |
|---|---|---|
| **Technical implementation** | ~25% | Very strong on paper — arguably the strongest of any comparable project reviewed (§1). The risk has shifted from "is it technically deep enough" to "can four people actually finish it" (§3). |
| **Problem-solving impact** | ~25% | Strong — real stakeholder (C-HED), sourced costs, a genuinely new mechanism (heat-neutral development review) with no found Kerala equivalent. |
| **Innovation** | ~20% | Strong, but §1 shows the "map + optimizer" shell is now common — the win condition is making sure the Heat Impact Check and the real back-test get top billing, not buried as tab 4 and tab 5. |
| **Presentation / demo** | ~20–30% | Now the highest-risk vector given how much surface area exists to demo (six tabs, two live feeds, an offline AppEEARS dependency, an InVEST benchmark). See §4. |
| **Q&A / defensibility** | folded in | PLAN.md §11 is unusually thorough. A few additions below (§5). |

---

## 3. Scope and execution risk — the real threat now

PLAN.md §0's compliance checklist is excellent for the written submission but has pulled several previously-optional items (atmospheric driver analysis, physics-derived energy-balance features, water-body and green-roof scenarios) into Tier 1. Combined with Tier 2's ECOSTRESS/AppEEARS ingestion and UT-GLOBUS coverage check, **M1's task list is now the single longest and most front-loaded critical path in the whole plan**: submit the AppEEARS request at hour 0, pull Landsat + Sentinel-2 + ERA5-Land + GHSL + UT-GLOBUS + SRTM, build the heat stress index, run the atmospheric-driver regression, engineer the physics-derived features, train and validate the model, run the back-test, *and* build the live heat-index helper — largely before the 4 PM checkpoint even asks for a working heat map.

**Fix — protect the 4 PM checkpoint bar specifically, not the whole Tier 1 list:**
- The checkpoint itself only requires "real heat map and honest accuracy on screen" (PLAN.md §9). Treat atmospheric-driver analysis, physics-derived features (absorbed shortwave, evapotranspiration potential), and the full four-intervention scenario set as **things that can still be landing between 4 PM and 7 PM**, not blockers to unlocking Tier 2. Don't let the compliance checklist's completeness quietly turn into a harder Tier-1 gate than the timeline actually needs.
- If M1 is genuinely behind by 4 PM, the fallback order is: ship the heat stress map with satellite LST alone first (ERA5 heat-index layer can be a same-day addition after checkpoint 1), and treat UT-GLOBUS/ECOSTRESS as what they're already scheduled as — Tier 2, optional-with-documented-fallback, never a Tier 1 blocker.
- Consider one explicit reallocation: M2 or M4 picks up the ERA5-Land ingestion call itself (it's one Earth Engine query, not model work) so M1's Tier-1 critical path is shorter on hour 1–2.

---

## 4. Technical risk register

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| M1's Tier 1 task list (§3) runs past 4 PM | Medium-High | Delays Tier 2 unlock for the whole team | See §3 fix — decouple "checkpoint passes" from "every compliance-checklist item is done" | M1 |
| NASA AppEEARS ECOSTRESS order takes longer than expected to process (it's a request/fulfillment queue, not an instant API call) | Medium | ECOSTRESS check slips past Tier 2's window entirely | Already correctly planned — request submitted at hour 0 (PLAN.md §12) so there's maximum lead time; if it hasn't arrived by the time Tier 2 ECOSTRESS work is scheduled, skip it silently rather than waiting — it was already Tier 2/optional in the compliance table | M1 |
| UT-GLOBUS doesn't cover Kochi | Medium | Minor — already has a stated fallback (GHSL + OSM buildings) | No action needed, already handled correctly in RESOURCES.md | M1 |
| Two live external dependencies (Open-Meteo + Malayalam RSS) both need to be demoed working *and* failing gracefully | Medium | Eats scarce rehearsal time | Rehearse both Wi-Fi-off fallbacks together in one pass at the 6 AM rehearsal | M3 |
| Six tabs plus an InVEST benchmark (Tier 3) is a lot of surface area if a judge asks to drive the demo | Low-Medium | Derails pacing | Pre-decide the shortest path that hits the two rarest differentiators: Heat → Check a project → Proof | M3 |
| "Physics-informed" claim gets probed on the difference from a PINN | Low | PLAN.md already has the exact right answer prepared (§11) — no new risk, just make sure whoever answers says "physics-informed ML, not a physics-informed neural network" verbatim, it's a precise and defensible distinction | M2 |
| GHSL population epoch (2020/projection) doesn't match the 2024 back-test year | Low | Minor, but an unprepared answer looks worse than the gap itself | Add to Q&A (§6) | M1 |

---

## 5. Cheap, high-leverage additions still open (not yet in PLAN.md)

None of these are urged into Tier 1 or 2 given §3 — they're ranked by effort-to-value and meant as **Tier 3 stretch candidates**, to pick up only if a team member is genuinely ahead of schedule.

1. **Cooling-point finder for the live "Where to act today" tab** (~30–45 min, cheapest idea here). The common hackathon template (§1) includes a "cooling center optimizer" — VISAT doesn't have an equivalent yet. Since OSM is already being queried for schools/hospitals/markets, add public water points, community halls, and shaded parks as "nearest cooling refuge" candidates, and surface the nearest one for the top-ranked ward in the live tab. Pure OSM query + nearest-neighbour, no new ML, no new dataset.
2. **Ventilation-corridor overlay** (~1–2 h, zero-cost recommendation). Cities from Stuttgart to Guangzhou to Singapore protect corridors that let cooler air (here, off Kochi's backwaters) flow into hot areas, using building-roughness-along-a-transect as a cheap proxy for wind permeability. This reuses data already being pulled (GHSL building height/volume) — no new dataset. Frame it explicitly as an illustrative overlay, not a certified wind-engineering result (same honesty-labelling pattern the team already uses elsewhere). Pitch value: it's the one recommendation in the whole app that costs ₹0 — "don't build here" is a strong contrast to every other tab's "spend ₹X here."
3. **GeoParquet + DuckDB for the app backend** (efficiency, not a feature). Precomputing everything (already planned) into a single GeoParquet file and querying it with DuckDB's spatial extension in Streamlit, instead of live geopandas joins, is the current fast/simple/Pythonic standard for exactly this kind of dashboard — meaningfully snappier slider response than pandas joins on every rerun, and less code than hand-rolled caching. Worth it only if M3 already knows the stack; not worth learning for the first time on event day.

None of these are required — they're here so that if a team member finishes their Tier 2 item early, there's a vetted, low-risk place to spend the extra time instead of scope-creeping into something unplanned.

---

## 6. Additional Q&A (complements PLAN.md §11 — doesn't repeat it)

| Question | Who | Answer |
|---|---|---|
| Isn't a heat map + optimizer + chatbot just what every team builds now? | M4 | That's exactly why we lead with the two things that template doesn't have: physics-informed features validated against real 2017→2024 change, and the Heat Impact Check, which prices the heat cost of developments that don't exist yet — not just the ones that already do. |
| Your population layer — is it really 2024 data? | M1 | GHSL population's most recent real epoch is 2020 (2025/2030 are projections). We use it as a stable population-density weight, not a claim of exact 2024 population — the *temperature* change we're proving is 2017→2024 real satellite data; population is a weighting layer, not the thing being validated. |
| Is scraping news RSS feeds okay to do here? | M4 | These are public, unauthenticated RSS feeds meant for syndication. We show only headline, channel, time and a link — never republish article text — and label everything as coming from Malayalam news versus official IMD/KSDMA alerts. |

---

## 7. Presentation checklist

- Color scale: one diverging red/blue for all temperature visuals across all six tabs — decide the exact hex pair now.
- Belt-and-suspenders: embed 3–4 screenshots of the key demo moments (live strip, Plan slider beating baselines, Check-a-project heat spread, Proof chart) directly into the slide deck, in case both the live URL and the backup video fail.
- Open the pitch by naming what's rare, not just what's present: physics-informed validation and the Heat Impact Check, ahead of the tab-by-tab walkthrough.
- If forced to cut a rehearsal pass to finish a feature, don't — an unrehearsed extra feature scores worse than a clean pitch of a smaller one.
