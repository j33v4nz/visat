# VISAT — who does what (event day)

**Start here.** The app runs end-to-end on frozen **real Kochi data**. Times are **hours from kick-off (H+0)**;
submission portal locks at **9:00 AM Day 2**.

## 🔴 Live status — update this section as things finish

**🔒 H+4 DATA FROZEN, done.** Real Kochi data is in `data/app/` (committed) and the app runs on it —
`git pull` and you're working against real data now, not demo data. Earth Engine is no longer needed
by anyone except M1 for the optional ECOSTRESS/matched-validation follow-ups below. The ₹10 crore
plan cools about 186,258 people across the study grid.

**Still open, none of these block M2/M3/M4:**
- ~~Kochi ward map not loaded~~ **Done:** `data/app/` now has 74 named wards, reaggregated from the
  frozen app cells and saved OSM data. The raw Earth Engine exports are still needed for a full retrain.
- ECOSTRESS afternoon check not run yet (M1, needs the AppEEARS download)
- CPCB station check not run yet (M4, optional download)

## 🤖 root0x1d + AI-assisted additions (PRs #5, #6, #7 — merged, see `git log`)

Adding this so it's clear to the rest of the team (and your own AI assistants reading this repo) what
came from this side and why, without duplicating or overwriting anyone else's notes above/below.

- **PR #5 — docs only.** Verified two things directly against the event site's own source
  (`chsrikar/hackme-26` on GitHub, not the rendered page): the rubric is **5 weighted pillars summing to
  100%**, not 6 with an invented "UI/UX" category (Innovation 30 / Technical Depth 25 / Working
  Execution 20 / Impact 15 / Presentation 10) — and the real pitch format is **5-minute pitch + 2-minute
  jury Q&A**, not 3 minutes. Fixed PLAN.md §10's demo script and STRATEGY.md's rubric table to match.
- **PR #6 — real bug, verified before fixing.** `news.py`'s Malayalam keyword filter missed real
  headlines that inflect place/heat words (very common — "in Ernakulam" is one word,
  "എറണാകുളത്ത്", not "Ernakulam" + a separate locative word). Confirmed
  `news.classify("എറണാകുളത്ത് ചൂട് ജാഗ്രത")` returned `None` before the fix, despite Ernakulam being
  the district Kochi is in. Fixed with a stem-match helper instead of hand-editing each keyword; 1 new
  regression test, 3 negative cases checked for new false positives (Gulf heat, unrelated Kerala news —
  both still correctly excluded).
- **PR #7 — `data/raw/wards.geojson` + `data/frozen/osm.parquet`, both real, both verified before
  committing:**
  - Downloaded the real 74-ward GeoJSON from BharatLAS (direct link, no click-through needed:
    `https://pub-0429b8e3b5a946e69ea007df844a6f1c.r2.dev/admin/wards-kochi/wards_kochi.geojson`).
  - **Found the file stores coordinates as `[lat, lon]`, not GeoJSON-standard `[lon, lat]`.** Checked
    against a real landmark — "Island North" ward (Willingdon Island) showed raw coordinates
    `[9.96, 76.28]`, and 9.96 is obviously the latitude. Confirmed the effect directly: `assign_wards()`
    on the unswapped file matches **zero** cells (ran it, got 0/54168), silently, no error anywhere.
    Fixed by swapping coordinates before saving.
  - **Also found `exposure.py`'s `assign_wards()` doesn't look for this file's actual name property**
    (`ward_lgd_name`) — only `ward_name`/`name`/`Ward_Name`/`WARD_NAME`, none of which exist here. Left
    as-is, every ward silently falls back to "Ward 1", "Ward 2"... Added `ward_lgd_name` to the lookup.
  - Verified both fixes together against `demo_data.build()`: 74 real LGD ward names resolve correctly
    (Island North, Island South, Edakochi North, Edakochi South, Thazhappu, ...), thousands of cells
    assigned versus zero before.
  - Also ran `osm_features.py` for real (28,378 roads, 542 schools, 62 markets, 390 hospitals, 5
    harbours, 243 parks) — this is what M1's checklist above is already reporting.

**Update:** The ward-only rebuild is now done from saved app cells and OSM counts with
`python -m visat.ward_rollup`; the 575 fallback zones are gone. The raw GEE exports
(`cells_static.parquet`, `scenes.parquet`, `scenes_meta.parquet`, `backtest.parquet`) are still absent
here. Whoever has that local `data/frozen/` folder can run the full pipeline again to compute the
new matched back-test metric:
```bash
uv run python -m visat.pipeline --source frozen
```
The ward-only pass preserved the frozen global model and plan values; its Ward Card action values
come from the already saved per-site plan picks (rounded to 0.01 °C).

**AppEEARS/ECOSTRESS is the one item on this list I genuinely cannot help with** — it needs M1's
personal NASA Earthdata login, which isn't something I have or can create. Everything else above was
either public data (OSM, BharatLAS) or pure local computation.

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
uv run pytest -q                          # run the current suite
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
| 25 tests: budget, never-warms, eligibility, joint vs single, baselines, heat-neutral, fallbacks, Malayalam, number guard, app smoke | `tests/` | Demo safety |

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
- [x] **H+2** Kochi 74-ward map: **done (PR #7, AI-assisted — see the section near the top of this file).**
      OSM doesn't have Kochi's municipal wards well-tagged, so this came from BharatLAS instead — direct
      download link found (no click-through needed): `wards_kochi.geojson` at their R2 bucket. The file
      itself had two real problems, both fixed and verified before committing: its coordinates are
      `[lat, lon]` not GeoJSON-standard `[lon, lat]` (silently matched zero cells otherwise — confirmed),
      and its name property is `ward_lgd_name`, which `exposure.assign_wards()` wasn't checking for
      (silently fell back to "Ward N" otherwise). `data/raw/wards.geojson` is in. The named-ward
      `data/app/` rollup is now built from frozen app cells and OSM counts: 74 wards, 8,063 cells.
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
- [x] **T2** Matched back-test (DiD) implementation: changed cells vs kNN-matched unchanged cells on
      2017 features in `validation.py`, tested on demo data. Never call it "causal".
- [ ] **T2 follow-up** Compute and show the real matched metric after M1's raw `backtest.parquet` is available.
- **Presents:** data + validation slide. **Q&A:** "10:30 AM isn't felt heat", "is it just correlation?"

## M2 — Scenarios & Optimizer (ML)

- [x] **H+0** Read `scenarios.py` + `optimize.py`; the local test suite passes (25 tests).
- [ ] **H+3.5** On real data, open the validity matrix (Plan tab → expander). Check each intervention has eligible
      cells and a sensible median °C. Tune in `config.INTERVENTIONS` (intensity, coverage) and eligibility rules
      in `scenarios.eligible` — **public land only**.
- [x] **H+4** Confirmed the saved real-data plan beats both baselines at ₹1/10/50 Cr; `test_plan_beats_naive_baselines` passes.
- [ ] **H+5** Check the 5–8 Heat-Neutral sites (`heat_neutral.select_sites`) are genuinely open plots on a map;
      adjust `config.SITE_ANCHORS` if one lands on a wetland or paddy (protected).
- [x] **T2** "Conservative mode": show the saved back-test ±MAE as an empirical ΔT band in the Plan summary and site table, explicitly not a confidence interval.
- **Presents:** plan-vs-baselines + Heat-Neutral slide. **Q&A:** "where is the physics?", "why greedy?", "joint vs sum".

## M3 — App (Design)

- [ ] **H+0 🚀 Deploy now** on [Streamlit Community Cloud](https://share.streamlit.io): repo `j33v4nz/visat`,
      branch `main`, main file **`app/streamlit_app.py`**, Python **3.12**. It installs from `requirements.txt`.
      Share the live URL in the team chat. (If the build picks `pyproject.toml`/`uv.lock` instead and fails,
      check the "dependency file" note in RESOURCES.md §4b.)
- [x] **H+1** Projector test: 20 px text, dark theme, map ≥65% width. Hide anything not in the demo in expanders.
- [x] **H+4** Re-check all four screens on the frozen real-data build, the **₹10 crore** preset, and the
      **Kakkanad → IT park** flow. The UI now reports the remaining **+0.26 °C** after offsets honestly.
- [x] **H+4 follow-up** Re-check named ward selection and Ward Cards after the ward-only `data/app/`
      rebuild; the app now has 74 real ward names and boundaries.
- [ ] **H+4 follow-up** Reach heat-neutral for Kakkanad IT park if M2 can produce a valid offset package;
      the current precomputed package does not pass the screen.
- [x] **H+6** Screenshots of the 4 key moments for the deck backup (`artifacts/m3/`).
- [x] **T3** Animated three-line heat ledger and side-by-side modelled project/offset map comparison.
- [x] **T3** Optional overlay of OSM canal/drain/ditch bank tree-strip candidate cells, labelled as
      unverified candidates with 0 °C canal credit.
- [ ] **T3 follow-up** Named IURWTS canal alignments from OSM `waterway=canal` geometry.
- [x] **T3 follow-up** Numerical heat-ledger count-down animation, from project heat added to the saved net change.
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
