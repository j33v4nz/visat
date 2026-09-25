# VISAT — who does what (event day)

**Start here.** The whole app already runs end-to-end on **DEMO data** (synthetic Kochi, always labelled DEMO).
Your job: swap in **real data**, verify, polish, and pitch. Times are **hours from kick-off (H+0)**;
submission portal locks at **9:00 AM Day 2**.

## 🔴 Live status — update this section as things finish

**🔒 H+4 DATA FROZEN, done.** Real Kochi data is in `data/app/` (committed) and the app runs on it —
`git pull` and you're working against real data now, not demo data. Earth Engine is no longer needed
by anyone except M1 for the optional ECOSTRESS/wards follow-ups below. **App looks/behaves the same
either way** — same 4 screens, just real numbers now (₹10cr plan → 186,258 people cooled, for real).

**Still open, none of these block M2/M3/M4:**
- Kochi ward map not loaded (using 575 1-km zones instead — see M1's list below for why + the fix)
- ECOSTRESS afternoon check not run yet (M1, needs the AppEEARS download)
- CPCB station check not run yet (M4, optional download)

**Fixed today, already pushed (see `git log` for details), you don't need to redo this:**
- Earth Engine login hung on this machine (tries to detect if it's a Google server) → fixed with `force=True`.
- `computePixels` hit "User memory limit exceeded" on the full-size grid → now split into row tiles
  (`gee_export.TILE_ROWS = 15`), auto-halves further if a tile still overflows.
- `reduceResolution` rejected multi-source composites (Sentinel-2 + WorldCover) with no projection →
  fixed with `setDefaultProjection` before reducing.
- `.copyProperties()` returns the wrong type in Earth Engine's Python library and broke `.toFloat()` → cast
  back to `ee.Image` explicitly.
- **`ST_QA_MAX_K` (temperature-precision filter) raised from 2.0 → 3.0.** At 2K only **4 of 89** Jan–Apr
  scenes passed — Kochi's humid coastal air makes Landsat's temperature readings less certain even on
  clear days. 3K gives **28 scenes**, in our target range. This is a legitimate, measured choice — good
  Q&A answer if asked ("why 3K not 2K": we measured it on real data, see `config.py` comment).

**If you hit a NEW Earth Engine error not listed above:** check the exact message, it's usually one of:
memory limit (tile smaller), projection (setDefaultProjection), or a type mismatch (wrap in `ee.Image(...)`).
These are normal for Earth Engine at this data volume, not signs something is fundamentally wrong.

```bash
git pull
uv sync --all-groups                      # app + tests
uv run pytest -q                          # 22 tests should pass
uv run streamlit run app/streamlit_app.py # open http://localhost:8501
```

## ✅ Already built (don't rebuild — improve)

| Piece | File | PS1 |
|---|---|---|
| Physics-informed scene-panel XGBoost (monotone constraints, per-scene ERA5, (1−α)·S↓) | `src/visat/model.py` | Obj 3 |
| Grouped spatial-block CV vs linear + unconstrained baselines, random-CV shown for honesty | `model.py` | Outcome: validated model |
| Atmospheric drivers with bootstrap CIs over scenes | `model.py` | Obj 2 |
| Heat Stress Map (LST rank × heat index × population), ward roll-up, hotspots, "act today" | `src/visat/exposure.py` | Obj 1 |
| What-if engine: analog transitions (k=20 real Kochi donors, P1–P99 support, cooling-direction only), energy-balance formulas, joint re-prediction, spillover | `src/visat/scenarios.py` | Obj 4 |
| Validity matrix (all 7 interventions + IURWTS canals at 0 °C credit) | `scenarios.py` | Outcome: scenario evaluation |
| Budget optimizer + "spread evenly" / "trees everywhere" baselines, ₹1/10/50 Cr presets | `src/visat/optimize.py` | Outcome: optimal strategy |
| Heat-Neutral Development Check (reverse transition, context-matched donors, cheapest offset) | `src/visat/heat_neutral.py` | Innovation |
| Back-test 2017→2024, ECOSTRESS agreement, CPCB check | `src/visat/validation.py` | Proof |
| Live Open-Meteo strip + Malayalam news chip, both with cache → snapshot fallback | `live.py`, `news.py` | Live layer |
| Ward Heat Card (printable HTML) | `src/visat/report.py` | Impact |
| Public Reaction Preview (Tier 3, simulated personas, number guard) | `src/visat/reactions.py` | Extra |
| Earth Engine export, OSM features, frozen loader | `gee_export.py`, `osm_features.py`, `frozen.py` | Inputs |
| 4-screen Streamlit app, dark projector theme | `app/streamlit_app.py`, `.streamlit/config.toml` | UI |
| 22 tests: budget, never-warms, eligibility, joint vs single, baselines, heat-neutral, fallbacks, Malayalam, number guard, app smoke | `tests/` | Demo safety |

---

## M1 — Data & Model (ML)

- [x] **H+0** Earth Engine registered and logged in (project `sinuous-wording-468112-s2`).
- [ ] **H+0** Submit the **AppEEARS** request (NASA Earthdata login): product `ECO_L2T_LSTE.002`, layer **LST**,
      area = bbox `76.20, 9.88, 76.40, 10.10`, dates **Jan–Apr 2024 and 2025**, GeoTIFF, EPSG:4326.
      When ready, unzip all `*LST_doy*.tif` into `data/raw/ecostress/`. **Still needs doing — do this now,
      it takes a while to process on NASA's side.**
- [x] **H+0.5** `visat.gee_export` done for real: 54,168 cells, **23 clean scenes** (Jan-2019–Feb-2026),
      2017/2024 back-test composites. Took ~20 min after 2 Earth Engine fixes (see below).
- [x] **H+2** OSM features done: 28,378 roads, 542 schools, 62 markets, 390 hospitals, 16 construction, 5 harbours, 243 parks, 5,525 canal-bank cells.
- [ ] **H+2** Kochi 74-ward map: **not loaded yet.** OSM doesn't have Kochi's municipal wards well-tagged
      (tried; only found district/state boundaries). App currently falls back to **575 1-km zones**
      (labelled honestly, this fallback was always in the plan). **Nice-to-have, not a blocker:** manually
      download the GeoJSON from [BharatLAS](https://bharatlas.com/view/wards_kochi) (their site needs a
      click-through, no public API found) → `data/raw/wards.geojson`, then rerun `visat.pipeline`.
- [ ] **H+2.5** (optional, M4 downloads) CPCB Vyttila/Eloor CSVs → `data/raw/cpcb/`. Also optional: the
      AppEEARS ECOSTRESS download (M1, still pending — see top of file).
- [x] **H+3** `visat.pipeline --source frozen` run — **real `data/app/` built and committed.**
      **Real numbers:** ₹1cr → 52,951 people cooled · ₹10cr → 186,258 · ₹50cr → 433,751.
      **Honest validation:** spatial-CV R² = 0.83 (ours) vs 0.84 (unconstrained) vs 0.62 (linear) — physics
      constraints cost a little raw fit for guaranteed-sensible behaviour, both crush the linear baseline.
      **Back-test:** r = 0.35 (positive, real, not spectacular — say so, don't oversell it).
      **Real finding worth knowing for Q&A:** albedo and built-up density are correlated (r≈0.47) in real
      Kochi, so the ML model alone understates cool-roof cooling — this is exactly why we cross-check
      against the physics formula (see Proof tab). Good, honest talking point, not a bug.
- [x] **H+4 🔒 DATA FROZEN** — real `data/app/` committed and pushed. From here the app never needs Earth
      Engine. **M2/M3/M4: pull now and work against real data.**
- [ ] **T2** Matched back-test (DiD): changed cells vs kNN-matched unchanged cells on 2017 features, in
      `validation.py`. Never call it "causal".
- **Presents:** data + validation slide. **Q&A:** "10:30 AM isn't felt heat", "is it just correlation?"

## M2 — Scenarios & Optimizer (ML)

- [ ] **H+0** Read `scenarios.py` + `optimize.py`; run `uv run pytest -q`.
- [ ] **H+3.5** On real data, open the validity matrix (Plan tab → expander). Check each intervention has eligible
      cells and a sensible median °C. Tune in `config.INTERVENTIONS` (intensity, coverage) and eligibility rules
      in `scenarios.eligible` — **public land only**.
- [ ] **H+4** Confirm our plan beats both baselines on real data at ₹1/10/50 Cr (test `test_plan_beats_naive_baselines`).
- [ ] **H+5** Check the 5–8 Heat-Neutral sites (`heat_neutral.select_sites`) are genuinely open plots on a map;
      adjust `config.SITE_ANCHORS` if one lands on a wetland or paddy (protected).
- [ ] **T2** "Conservative mode": use the back-test error (±MAE) as the ΔT band on the Plan table.
- **Presents:** plan-vs-baselines + Heat-Neutral slide. **Q&A:** "where is the physics?", "why greedy?", "joint vs sum".

## M3 — App (Design)

- [ ] **H+0 🚀 Deploy now** on [Streamlit Community Cloud](https://share.streamlit.io): repo `j33v4nz/visat`,
      branch `main`, main file **`app/streamlit_app.py`**, Python **3.12**. It installs from `requirements.txt`.
      Share the live URL in the team chat. (If the build picks `pyproject.toml`/`uv.lock` instead and fails,
      check the "dependency file" note in RESOURCES.md §4b.)
- [ ] **H+1** Projector test: 20 px text, dark theme, map ≥65% width. Hide anything not in the demo in expanders.
- [ ] **H+4** After M1's real data lands: re-check every screen; click wards; the **₹10 crore** preset and the
      **Kakkanad → IT park → heat-neutral** flow must look perfect.
- [ ] **H+6** Screenshots of the 4 key moments for the deck backup.
- [ ] **T3** Heat-ledger count-down animation; before/after image comparison (`streamlit-image-comparison`,
      2017 vs 2024 or before/after offset); IURWTS canal overlay (OSM `waterway=canal` names).
- **Presents:** live demo (screens 1–4). **Q&A:** "walk me through one ward", "what if Wi-Fi fails?"

## M4 — Product & Pitch (Design)

- [x] **H+0** Verify costs in `config.INTERVENTIONS` (`cost_note` sources) and Kerala rules (Labour order dates,
      KMBR FSI clause, SEIAA thresholds, IURWTS status). **Re-verified (AI-assisted, fresh web searches, not
      just re-reading the doc):** Labour order 13 Feb–20 May, 12–3 PM rest, max 8h between 7 AM–7 PM — exact
      match. KMBR 2019 extra-FSI incentive — confirmed, matches. SEIAA Form-1A 20,000–150,000 m² — confirmed
      exact threshold. IURWTS ₹3,716 crore — confirmed current. **One real error found and fixed** in
      RESOURCES.md's canal list: it read "Edappally, Chilavannur, Thevara–Perandoor, Thevara, Konthuruthy,
      Market" — which lists "Thevara" twice and never names "Perandoor" cleanly. The real 6 are Edappally,
      **Perandoor**, Chilavannur, Thevara, Konthuruthy, Market (confirmed against Onmanorama/Swarajya) — fixed.
      All cost figures (`cost_per_cell`/`cost_per_m2` in `config.py`) checked, nothing else wrong.
- [x] **H+1** Official alert source: put the best IMD/KSDMA link(s) in `config.OFFICIAL_ALERT_LINKS`.
      **Already done and verified live** — both `mausam.imd.gov.in/thiruvananthapuram/` and
      `sdma.kerala.gov.in` return 200. Just the checkbox was stale.
- [ ] **H+2** Malayalam: a **native speaker** fills `report.ML_LABELS` (Ward Card headings). No machine translation.
- [ ] **H+2** Review the news keyword lists in `news.py` (HEAT, PLACE, GULF) with a native reader.
- [ ] **H+3** Deck (5 slides): problem (2026 heat facts) → data → model + proof → plan vs baselines + Heat-Neutral →
      impact/scale. Include the **AI-use disclosure** (Claude-assisted coding; reaction preview uses Claude Opus 5
      only to phrase simulated personas — never numbers). **Ready-to-paste draft (verified against the actual
      code, not just described from memory):**
      > *This project used Claude (Anthropic) as a coding assistant throughout the build — data pipeline,
      > model, optimizer, app and tests. Where AI is used at runtime, it's narrowly scoped and disclosed on
      > screen: the optional Public Reaction Preview (Tier 3) uses Claude Opus 5, at low effort, only to phrase
      > how simulated resident personas might react — a number guard automatically drops any AI-generated reply
      > that quotes a figure not already present in our own computed results, so it can describe our numbers
      > but never invent new ones. Every °C, ₹ and person figure elsewhere in the app comes from our own model
      > and optimizer, not from an AI call.*
- [ ] **T3** Public Reaction Preview: `uv sync --extra reactions`, set `ANTHROPIC_API_KEY`, run
      `uv run python -m visat.reactions` (~24 calls, ~$2–4) → commits `data/app/reactions_cache.json`.
- [ ] **H+19** Record the 2–3 min demo video (backup). **H+22.5** submit: repo, live URL, video, deck.
- **Presents:** problem + impact. **Q&A:** costs, "is heat-neutral legal?", "doesn't Kawaki do this?", "is news reliable?"

---

## Checkpoints (everyone)

| When | Gate |
|---|---|
| H+2 | Live URL works (demo data) · CI green |
| **H+4** | ✅ **Real data frozen and committed** |
| **H+6** | Checkpoint 1: real Heat Stress Map + honest CV on screen → start Tier 2 |
| **H+13** | Checkpoint 2: all 4 screens on real data, live URL → start Tier 3 |
| H+15 | If anything core is broken → ship ranked hotspots + °C per fix |
| H+16–19 | Sleep in shifts (M1+M3, then M2+M4) |
| **H+19** | Feature freeze · record video |
| **H+20** | **Code freeze** · 3 rehearsals, one with Wi-Fi OFF |
| H+22.5 | Warm up the app · submit before the portal locks |

**Rules:** commit small and often; never commit secrets (`.streamlit/secrets.toml`, `.env`); every number on
screen keeps its label ("surface °C, ~10:30 AM, Jan–Apr" / "city-scale"); PS1 checklist is PLAN.md §0.
