# UHI: Urban Heat Intelligence - Kochi Heat Action Planner

**HackMe'26 · AI/ML track · PS1: Urban Heat Mitigation via AI/ML**

> "UHI shows Kochi where heat is dangerous today, where ₹10 crore cools the most people, and screens every new project so the city stops getting hotter. We prove it against real change from 2017 to 2024."

Five workspaces, one question each: Heat overview (where is heat dangerous?), cooling plan (what should we do?), scenario simulation (what could a ward become under changed weather and cooling measures?), project check (will it add heat?), and evidence (can we trust it?). Ward Heat Cards are downloadable from the dashboard.

## Run it

```bash
uv sync --all-groups
uv run streamlit run app/streamlit_app.py      # reads the committed data/app/ build
uv run pytest -q                                # 22 tests
```

Rebuild the app data:

```bash
uv run python -m uhi.pipeline --source demo     # synthetic Kochi, labelled DEMO in the app
# real data (M1): Earth Engine + OSM → data/frozen → data/app
uv sync --all-groups --extra pipeline
uv run earthengine authenticate
uv run python -m uhi.gee_export --project <gee-cloud-project>
uv run python -m uhi.osm_features
uv run python -m uhi.pipeline --source frozen
```

**Deploy:** Streamlit Community Cloud → repo `j33v4nz/visat`, branch `main`, main file `app/streamlit_app.py`, Python 3.12. It installs the lean `requirements.txt` and serves the committed `data/app/` — no Earth Engine at runtime.

## How it works

| Step | Module | What it does |
|---|---|---|
| Data | `gee_export.py`, `osm_features.py`, `frozen.py` | 20–30 clean Landsat 8/9 scenes (Jan–Apr) + ERA5-Land at each overpass, Sentinel-2, WorldCover, Dynamic World, GHSL, SRTM, OSM → 100 m grid |
| Model | `model.py` | Scene-panel XGBoost (cells × scenes) with a physics feature (1−albedo)×sunlight and monotone constraints; grouped spatial-block CV vs baselines; TreeSHAP drivers; atmospheric sensitivity with CIs |
| Heat Stress Map | `exposure.py` | LST rank (where) × heat index (when) × population (who); ward roll-up; "act today" |
| Scenario simulation | `app/streamlit_app.py` | Ward selection, weather-state adjustments, available cooling action, live sensitivity estimate and downloadable report with limitations |
| What-ifs | `scenarios.py` | Analog transitions toward real Kochi cells (k=20, in-support, cooling-only) or labelled energy-balance formulas; one joint re-prediction with spillover |
| Plan | `optimize.py` | Most person-°C per ₹, public land only; beats "spread evenly" and "trees everywhere" |
| Heat-Neutral Check | `heat_neutral.py` | Screening tool: a proposed IT park / mall / housing / parking → added surface heat → cheapest offset |
| Proof | `validation.py` | 2017→2024 back-test, ECOSTRESS afternoon agreement, CPCB station check |
| Live | `live.py`, `news.py` | Open-Meteo heat index (city-scale) + Malayalam news chip, both with offline fallback |
| Ward Card | `report.py` | Printable one-page plan per ward |
| Tier 3 | `reactions.py` | Simulated resident personas (Claude Opus 5, structured output, number guard, precomputed) |

Honesty labels are on every screen: satellite values are **surface °C at ~10:30 AM, Jan–Apr** (not air temperature); live weather is **city-scale**; canals get **no °C credit**; the Heat-Neutral Check is **a screening tool, not an approval**; results are never called causal.

## Documents

- **[TASKS.md](./TASKS.md)** — who does what, right now (commands, checks, checkpoints).
- **[PLAN.md](./PLAN.md)** — the build plan and PS1 compliance checklist (§0).
- **[RESOURCES.md](./RESOURCES.md)** — dataset IDs, APIs, local Kochi data, costs, pitch facts.
- **[STRATEGY.md](./STRATEGY.md)** — judging criteria, risk register, cut order.

## Team

| Member | Owns |
|---|---|
| M1 | Data & Model (Earth Engine scene stack, scene-panel model, Heat Stress Map, back-test, ECOSTRESS check) |
| M2 | Scenarios & Optimizer (validity matrix, joint re-prediction, optimizer, Heat-Neutral Check engine, tests) |
| M3 | App (5 workspaces, live strip, Check-a-Project UI, Ward Card, deploy) |
| M4 | Product & Pitch (costs + Kerala rules, alert + Malayalam news chips, deck, video, submission) |

## AI-use disclosure

Code was written during HackMe'26 with AI coding assistance (Claude), reviewed and run by the team. The optional Public Reaction Preview uses Claude Opus 5 only to phrase clearly labelled simulated personas; it never produces or changes any °C, ₹ or ranking number.

Data credits: USGS Landsat, ESA Sentinel-2 & WorldCover, Google Dynamic World, JRC GHSL, ECMWF ERA5-Land, NASA ECOSTRESS, OpenStreetMap contributors, weather data by Open-Meteo (CC-BY 4.0).
