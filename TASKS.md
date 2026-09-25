# VISAT — who does what (event day)

**Start here.** The whole app already runs end-to-end on **DEMO data** (synthetic Kochi, always labelled DEMO).
Your job: swap in **real data**, verify, polish, and pitch. Times are **hours from kick-off (H+0)**;
submission portal locks at **9:00 AM Day 2**.

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

- [ ] **H+0** Make sure your Google Cloud project is registered for Earth Engine (noncommercial). Then:
  ```bash
  uv sync --all-groups --extra pipeline
  uv run earthengine authenticate
  ```
- [ ] **H+0** Submit the **AppEEARS** request (NASA Earthdata login): product `ECO_L2T_LSTE.002`, layer **LST**,
      area = bbox `76.20, 9.88, 76.40, 10.10`, dates **Jan–Apr 2024 and 2025**, GeoTIFF, EPSG:4326.
      When ready, unzip all `*LST_doy*.tif` into `data/raw/ecostress/`.
- [ ] **H+0.5** `uv run python -m visat.gee_export --project <your-project>` → `data/frozen/`.
      Check the log: **20–30 clean scenes**. If fewer, lower `MIN_VALID_FRACTION` in `config.py` to 0.5.
- [ ] **H+2** `uv run python -m visat.osm_features` (roads, schools, markets, hospitals, harbours, parks, canals).
- [ ] **H+2** Download the Kochi 74-ward map from [BharatLAS](https://bharatlas.com/view/wards_kochi) (GeoJSON) →
      `data/raw/wards.geojson`. If ward names don't show, add the property name to `exposure.assign_wards`.
- [ ] **H+2.5** (optional, M4 downloads) CPCB Vyttila/Eloor CSVs → `data/raw/cpcb/`.
- [ ] **H+3** `uv run python -m visat.pipeline --source frozen` → real `data/app/`.
      **Sanity checks:** Kakkanad/Ernakulam core hotter than Mangalavanam and the backwaters; our spatial-CV R²
      reported honestly (even if a baseline wins — say so); back-test slope > 0.
- [ ] **H+4 🔒 DATA FROZEN** — commit `data/app/` (real) and push. From here the app never needs Earth Engine.
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

- [ ] **H+0** Verify costs in `config.INTERVENTIONS` (`cost_note` sources) and Kerala rules (Labour order dates,
      KMBR FSI clause, SEIAA thresholds, IURWTS status). Fix anything wrong directly in `config.py`.
- [ ] **H+1** Official alert source: put the best IMD/KSDMA link(s) in `config.OFFICIAL_ALERT_LINKS`.
- [ ] **H+2** Malayalam: a **native speaker** fills `report.ML_LABELS` (Ward Card headings). No machine translation.
- [ ] **H+2** Review the news keyword lists in `news.py` (HEAT, PLACE, GULF) with a native reader.
- [ ] **H+3** Deck (5 slides): problem (2026 heat facts) → data → model + proof → plan vs baselines + Heat-Neutral →
      impact/scale. Include the **AI-use disclosure** (Claude-assisted coding; reaction preview uses Claude Opus 5
      only to phrase simulated personas — never numbers).
- [ ] **T3** Public Reaction Preview: `uv sync --extra reactions`, set `ANTHROPIC_API_KEY`, run
      `uv run python -m visat.reactions` (~24 calls, ~$2–4) → commits `data/app/reactions_cache.json`.
- [ ] **H+19** Record the 2–3 min demo video (backup). **H+22.5** submit: repo, live URL, video, deck.
- **Presents:** problem + impact. **Q&A:** costs, "is heat-neutral legal?", "doesn't Kawaki do this?", "is news reliable?"

---

## Checkpoints (everyone)

| When | Gate |
|---|---|
| H+2 | Live URL works (demo data) · CI green |
| **H+4** | **Real data frozen and committed** |
| **H+6** | Checkpoint 1: real Heat Stress Map + honest CV on screen → start Tier 2 |
| **H+13** | Checkpoint 2: all 4 screens on real data, live URL → start Tier 3 |
| H+15 | If anything core is broken → ship ranked hotspots + °C per fix |
| H+16–19 | Sleep in shifts (M1+M3, then M2+M4) |
| **H+19** | Feature freeze · record video |
| **H+20** | **Code freeze** · 3 rehearsals, one with Wi-Fi OFF |
| H+22.5 | Warm up the app · submit before the portal locks |

**Rules:** commit small and often; never commit secrets (`.streamlit/secrets.toml`, `.env`); every number on
screen keeps its label ("surface °C, ~10:30 AM, Jan–Apr" / "city-scale"); PS1 checklist is PLAN.md §0.
