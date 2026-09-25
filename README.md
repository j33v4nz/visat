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
src/visat/       # pipeline code — written live during the hackathon
tests/           # tests — written live during the hackathon
.github/         # CI — lint + test on every push, running from hour 2 per PLAN.md §7
```

## Team

| Member | Owns |
|---|---|
| M1 | Data & Model (Earth Engine scene stack, scene-panel model, Heat Stress Map, back-test, ECOSTRESS check) |
| M2 | Scenarios & Optimizer (validity matrix, joint re-prediction, optimizer, Heat-Neutral Check engine, tests) |
| M3 | App (4 screens, live strip, Check-a-Project UI, Ward Card PDF, deploy) |
| M4 | Product & Pitch (costs + Kerala rules, alert + Malayalam news chips, README, deck, video, submission) |

See PLAN.md for the full role breakdown and 24-hour timeline.

## Status

Pre-event. Per PLAN.md §14, all project code is written during HackMe'26 itself — this repo currently holds the plan, resource research, win strategy, and CI/config scaffolding only.
