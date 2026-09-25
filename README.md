# VISAT: Kochi Heat Action Planner

**HackMe'26 · VISAT Engineering College · AI/ML track · PS1: Urban Heat Mitigation via AI/ML**

> "VISAT shows Kochi where heat is dangerous today, where ₹10 crore cools the most people, and screens every new project so the city stops getting hotter. We prove it against real change from 2017 to 2024."

**Plan version: v5 (final)**, after four expert-review rounds and a full cross-check against PS1 and this repo (25 Sep 2026). Four screens: **Today → Plan ₹ → Check a Project → Proof & Ward Card**.

## Documents

- **[PLAN.md](./PLAN.md)** — the build plan: PS1 compliance checklist, scene-panel physics-informed model, four-screen app, intervention validity matrix, Heat-Neutral Development Check, live layer, build tiers, timeline, team roles.
- **[RESOURCES.md](./RESOURCES.md)** — the verified resource pack: dataset IDs, live APIs, local Kochi data, library gotchas, costs, pitch facts.
- **[STRATEGY.md](./STRATEGY.md)** — the win analysis: judging-vector breakdown, risk register, and the cut-list order if the clock runs short. Companion to PLAN.md, not a replacement for it.

## Repo layout

```
app.py                 # Streamlit entry point — 4 screens, dark theme, live strip
src/visat/
  config.py             # dataset IDs, live-API config, costs, study params (constants only)
  heat_index.py          # NWS heat index + band, verified against RESOURCES.md's check value
  live_weather.py        # Open-Meteo fetch, 3-layer fallback (runtime cache -> snapshot -> banner)
  news_ticker.py          # Malayalam RSS chip, Unicode chillu normalisation, same fallback pattern
  physics.py               # energy-balance formula for cool roofs/pavements/green roofs
  validity_matrix.py        # every intervention: method, where allowed, cost function
  optimizer.py                # greedy budget optimizer + 2 naive baselines
  model.py                     # scene-panel feature engineering, monotone constraints, spatial-block CV
  ee_export.py                  # Earth Engine queries — run yourself after `ee.Authenticate()`
tests/                  # pytest — the pure-logic modules (everything except ee_export, live app)
data/app/               # small, tracked, app-ready files (Streamlit Cloud only sees git-tracked files)
requirements.txt        # lean, app-only deps for Streamlit Cloud (see its comment — RESOURCES.md §4b)
pyproject.toml          # full pipeline deps (uv) — NOT used by Streamlit Cloud
```

**What's real vs. what needs your own credentials:** `heat_index.py`, `optimizer.py`, `validity_matrix.py`,
`physics.py`, `news_ticker.py`'s parsing/matching, and `model.py`'s feature engineering + spatial-CV
splitting are working code with passing tests (`pytest`, all green). `live_weather.py` and
`news_ticker.py`'s live fetch, `model.py`'s actual training, and all of `ee_export.py` need a live
network / your own GEE, NASA Earthdata, and Streamlit Cloud sessions to run for real — wire in your
frozen scene stack and re-run once the data exists.

## Team

| Member | Owns |
|---|---|
| M1 | Data & Model (Earth Engine scene stack, scene-panel model, Heat Stress Map, back-test, ECOSTRESS check) |
| M2 | Scenarios & Optimizer (validity matrix, joint re-prediction, optimizer, Heat-Neutral Check engine, tests) |
| M3 | App (4 screens, live strip, Check-a-Project UI, Ward Card PDF, deploy) |
| M4 | Product & Pitch (costs + Kerala rules, alert + Malayalam news chips, README, deck, video, submission) |

See PLAN.md for the full role breakdown and 24-hour timeline.

## Running it

```
uv sync --all-groups
uv run pytest          # 36 tests, pure logic only, no credentials needed
uv run streamlit run app.py   # placeholder data until the real scene stack is wired in
```

## Status

Written live during HackMe'26. Working: heat index, live-weather + news fallback chains (tested by
simulating total network failure), the validity matrix, the optimizer (beats both naive baselines
on the test fixtures), and the scene-panel model's feature engineering + spatial-block CV split
(verified: no spatial block ever appears in both train and test). Not yet real: the actual GEE scene
export has to be run with your own authenticated session, and the app screens are placeholders until
that data exists.
