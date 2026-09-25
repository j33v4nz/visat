# VISAT — full project history

Built from `git log --all`, `gh pr list --state all`, and `git for-each-ref` on
`github.com/j33v4nz/visat`, run fresh on 2026-09-26. Every commit hash, author, date,
diffstat and PR number below is copied directly from those commands, not recalled from
memory. Nothing here is estimated.

## Who's who (git/GitHub identities)

| Name on commits | Email / GitHub login | Role |
|---|---|---|
| **Jeevan George** | `jeevangeorgech@gmail.com` (also committed 3 times under the name `j33v4nz`, same email — GitHub login `j33v4nz`) | Project owner. Wrote the plan docs, the real-data pipeline debugging, reviewed and merged all teammate PRs/branches. |
| **Gouri Sankar A** | `gourisankara@Gouris-MacBook-Air.local`, GitHub login `g0w6y` | Teammate. Opened all 10 PRs (#1–#10) from this account. Human-authored commits under this name. |
| **Codex** | `codex@openai.com`, pushed from the same `g0w6y`-owned branches | An AI coding agent Gouri Sankar A ran locally (OpenAI Codex) — its commits sit on the same branches as Gouri Sankar A's own commits. |
| **Melwin Santhosh** | `mlwnsanthosh@gmail.com`, GitHub login `mlwn4096` | Teammate with merge rights on the repo; merged PR #1. |

(This mapping is inferred from git author fields + `gh pr view --json mergedBy` + which
branch each commit sits on — it is what the metadata says, not something told to me directly.)

---

## Timeline — everything on `main`, in order (35 commits)

### Phase 1 — Planning (2026-09-25, before the event, docs only)
| Time | Author | Commit | What |
|---|---|---|---|
| 18:40 | Jeevan George | `e415a09` | Add VISAT Kochi Heat Action Planner plan for HackMe'26 — first version of `PLAN.md` (196 lines) |
| 19:00 | Jeevan George | `16be494` | Add verified resource pack (`RESOURCES.md`, 130 lines) |
| 19:27 | Jeevan George | `079da16` | Add Heat Impact Check (heat-neutral development) to the plan |
| 19:34 | Jeevan George | `ae1415d` | Add hybrid live weather layer (Open-Meteo) with offline fallback |
| 19:37 | Jeevan George | `cdc96e3` | Add live Malayalam news alert ticker (RSS, multi-channel confirmation) |
| 19:44 | **Gouri Sankar A** | `98910b6`/`32ce83b` | Add README, CI scaffolding, and win-strategy analysis (`STRATEGY.md`) + `config.py` scaffolding — opened as **PR #1** |
| 19:46 | Jeevan George | `6076319` | Add PS1 compliance checklist; close gaps (heat stress map, atmospheric drivers, physics-informed features, water/albedo interventions, ECOSTRESS, UT-GLOBUS, InVEST) |
| 19:54 | **Melwin Santhosh** | `a61fbb0` | **Merged PR #1** (`add-ci-readme-strategy` → `main`) |
| 19:59 | **Gouri Sankar A** | `eb0ea75` | Update STRATEGY.md and config.py to match the PS1 compliance checklist |
| 20:15 | Jeevan George | `a5ff2fe` | Plan v5 after round-4 expert panel: 4 screens, scene-panel physics model, validity matrix, heat-neutral screening check, Kerala policy hooks |
| 21:04 | Jeevan George | `5d56173` | Update README and STRATEGY to match plan v5 and the published HackMe'26 rubric |
| 21:07 | **Gouri Sankar A** | `ed4048c` | Add urgent real-schedule mismatch finding from the official event site (opened as **PR #2**, later closed — see below) |
| 21:15 | **Gouri Sankar A** | `a607efc` | Remove pre-event code (disqualification risk) and fix schedule/rubric claims (opened as **PR #3**, later closed) |
| 21:16 | Jeevan George | `13e23b0` | Add Tier 3 Public Reaction Preview (simulated resident personas) to plan/resources/risk register |
| 22:30 | Jeevan George | `d908985` | Finalise v5 after full cross-check against PS1 and repo: naming, month windows, deploy fixes, pre-event code decision |

### Phase 2 — Event start: real engine built (2026-09-25 23:12 – 2026-09-26 01:31)
| Time | Author | Commit | What |
|---|---|---|---|
| 23:12 | Jeevan George (as `j33v4nz`) | `a7c2e63` | Refresh config surface and tooling for the app build |
| 23:12 | Jeevan George (as `j33v4nz`) | `86b323f` | Add the VISAT engine: model, what-if scenarios, optimizer, validation, live layers (1,535 lines) |
| 23:12 | Jeevan George (as `j33v4nz`) | `b4b7c7b` | Add the Streamlit app, dark theme, generated `data/app` demo artifacts (93,111 lines — mostly generated demo data) |
| 23:47 | Jeevan George | `4bb2662` | Add real-data export (`gee_export`/`osm_features`/`frozen`), reaction preview, 22 tests, deploy files, per-person `TASKS.md` |
| 01:30 | Jeevan George | `4a71e4e` | Fix real Earth Engine issues found running the live Kochi export (auth, projection, memory-limit tiling, type coercion) |
| 01:31 | Jeevan George | `ce6767d` | Update TASKS.md with live status: EE login done, export in progress, fixes applied |

### Phase 3 — Data freeze + teammate PRs (2026-09-26 01:41 – 03:53)
| Time | Author | Commit | What |
|---|---|---|---|
| 01:41 | **Gouri Sankar A** | `a7fdf8b` | Implement Tier 1 pipeline: heat index, live layer, validity matrix, optimizer, scene-panel model scaffolding (opened as **PR #4**, later closed) |
| 01:44 | **Gouri Sankar A** | `f35a032` | Fix rubric pillars (5, not 6) and pitch format (5min+2min, not 3min) (opened as **PR #5**) |
| 01:46 | Jeevan George | `e917f24` | TASKS.md: note the export re-ran clean after the fixes |
| 01:57 | Jeevan George | `f8e5a5a` | Fix GHS_POP nodata sentinel (`-200`) leaking through as literal population |
| 02:01 | **Gouri Sankar A** | `b6e3aff` | Fix Malayalam news filter missing inflected place/heat words (opened as **PR #6**) |
| 02:12 | **Gouri Sankar A** | `5264528` | Add real Kochi ward boundaries + fix a silent ward-name/coordinate bug (opened as **PR #7**) |
| 02:13 | Jeevan George | `4917964` | **DATA FROZEN (H+4 checkpoint):** real Kochi data replaces the demo build — 54,168 cells, 23 satellite scenes (2019–2026 Jan–Apr); spatial-CV R²=0.83 (ours, physics-informed) vs 0.84 (unconstrained) vs 0.62 (linear), reported honestly; back-test r=0.35; fixed `.gitignore`'s silent `cache/` bug in the same commit |
| 02:14 | **Gouri Sankar A** | `34b9c09` | Add real OSM features (roads, schools, markets, canals) for Kochi |
| 02:17 | Jeevan George | `a57b472`, `afac4ca`, `54ccf5c` | **Merged PR #7** (real ward boundaries), **PR #6** (Malayalam keyword fix), **PR #5** (rubric fix) |
| 02:22 | **Gouri Sankar A** | `61db831`/`cce3d13` | TASKS.md: document AI-assisted PRs #5–7 and the pipeline-rerun needed (opened as **PR #8**, later closed — content superseded, see PR table) |
| 02:25 | Jeevan George | `fd55d55` | Rebuild real `data/app/` with the merged real Kochi ward boundaries |
| 02:43 | **Codex** | `1957144` | Polish M3 demo screens and capture deck backups (`artifacts/m3/*.png`) |
| 02:54 | **Codex** | `d9b2418` | Mark only implemented M3 checklist items complete |
| 03:02 | **Gouri Sankar A** | `d328b05` | Re-verify costs/Kerala rules, fix a canal-name error, add 2 Q&A items (opened as **PR #9**) |
| 03:17 | **Codex** | `89e22dd` | Build named Kochi wards and matched back-test support |
| 03:35 | **Codex** | `89acda8` | Complete remaining web plan and ledger features (animated heat ledger, conservative-mode toggle) |
| 03:50 | Jeevan George | `b571c3f` | **Merged PR #9** (costs/rules/canal-name fix) |
| 03:50 | **Codex** | `a864483` | Add Malayalam app mode and ward card (stayed on `update-tasks-md`, not yet merged at this point) |
| 03:51 | Jeevan George | `ebdcc96` | Integrate reviewed Codex/teammate code from closed **PR #8**'s branch (74 real named wards, matched kNN back-test, canal overlay, animated heat ledger, conservative-mode toggle, a real pydeck-rendering bug fix) + fix 2 real bugs found while reviewing it (the `.gitignore` cache bug and a stray "-1" ward bucket in saved plan JSON) |
| 03:53 | Jeevan George | `ab7ce7e` | TASKS.md: bring live status current |

### Phase 4 — Verification + final merge (2026-09-26 04:19 – 04:33)
| Time | Author | Commit | What |
|---|---|---|---|
| 04:19 | Jeevan George | `17e9122` | Verify the app visually in a real browser (Playwright) + fix a real pydeck bug found while checking (heat-map image layer needed string-quoting or pydeck 0.9 misreads it as a JS expression) |
| 04:33 | Jeevan George | `7d063e8` | **Merge Malayalam app mode + ward card** — cherry-picked from `update-tasks-md`'s tip (`a864483`, Codex). Numbers and proper names are never translated, only static UI labels are; English stays default, Malayalam is opt-in. 26/26 tests pass. |

---

## Pull requests (all 10, `gh pr list --state all`)

| # | Title | Branch | Opened by | Result |
|---|---|---|---|---|
| 1 | Add README, CI scaffolding, and win-strategy analysis | `add-ci-readme-strategy` | Gouri Sankar A (`g0w6y`) | **MERGED** by Melwin Santhosh, 2026-09-25 19:54 |
| 2 | URGENT: real schedule mismatch + sync STRATEGY.md to compliance checklist | `fix-strategy-post-compliance-checklist` | Gouri Sankar A | **CLOSED, not merged** — superseded by later, more accurate plan revisions on `main` |
| 3 | Remove pre-event code (DQ risk) + fix rubric/schedule/pitch-format claims | `remove-pre-event-code-and-fix-timeline` | Gouri Sankar A | **CLOSED, not merged** — diverged before the real engine existed; would delete working code if merged now |
| 4 | Implement Tier 1: heat index, live layer, validity matrix, optimizer, model scaffolding | `implement-v5-pipeline` | Gouri Sankar A | **CLOSED, not merged** — same reason as #3, superseded by the real pipeline built directly on `main` |
| 5 | Fix rubric pillars (5 not 6) and pitch format (5min+2min not 3min) | `fix-rubric-and-pitch-format` | Gouri Sankar A | **MERGED** by Jeevan George, 2026-09-26 02:17 |
| 6 | Fix: Malayalam news filter misses inflected place/heat words | `fix-malayalam-inflected-keywords` | Gouri Sankar A | **MERGED** by Jeevan George, 2026-09-26 02:17 |
| 7 | Add real ward boundaries + OSM features | `add-real-ward-boundaries` | Gouri Sankar A | **MERGED** by Jeevan George, 2026-09-26 02:17 |
| 8 | TASKS.md: document AI-assisted PRs #5–7 + pipeline-rerun needed | `update-tasks-md` | Gouri Sankar A / Codex | **CLOSED, not merged as a PR** — but its branch kept getting new commits (Codex work) after closing, and its final commit (`a864483`, Malayalam mode) was reviewed separately and cherry-picked into `main` directly on 2026-09-26 04:33 |
| 9 | M4 tasks: re-verify costs/Kerala rules, fix canal names, add Q&A | `verify-costs-rules-and-baseline-qa` | Gouri Sankar A | **MERGED** by Jeevan George, 2026-09-26 03:50 |
| 10 | TASKS.md: document AI-assisted PRs #5–7 + pipeline rerun (clean re-do) | `update-tasks-md-clean` | Gouri Sankar A | **OPEN, left unmerged** — documents an older state; merging now would make TASKS.md less accurate than what's already on `main` |

---

## Branches at the end of the event (`git branch -r`)

| Branch | Status | Decision |
|---|---|---|
| `main` | active | current, all real work lives here |
| `add-ci-readme-strategy` | merged (PR #1) | done, safe to delete |
| `fix-strategy-post-compliance-checklist` | stale | **not merged** — pre-dates the real engine, would be destructive |
| `remove-pre-event-code-and-fix-timeline` | stale | **not merged** — same reason |
| `implement-v5-pipeline` | stale | **not merged** — same reason |
| `update-tasks-md` | partially integrated | its `a864483` commit (Malayalam mode) was reviewed and cherry-picked to `main`; the branch itself was left unmerged as a whole because its TASKS.md content is stale |
| `update-tasks-md-clean` | open as PR #10 | **not merged** — stale TASKS.md content |

No branch was force-merged or merged without a line-by-line read first. Four branches
(`fix-strategy-post-compliance-checklist`, `remove-pre-event-code-and-fix-timeline`,
`implement-v5-pipeline`, and the whole of `update-tasks-md-clean`) were deliberately left
out because merging them would have deleted or reverted real, tested, working code —
they were all forked from `main` before the real data pipeline existed.

---

## What each person's work actually consisted of

**Jeevan George** (project owner, `jeevangeorgech@gmail.com` / `j33v4nz`):
- Authored the original plan (`PLAN.md` v1 → v5 across an expert-panel review process), `RESOURCES.md`, and the PS1 compliance checklist.
- Wrote the initial real engine (model, scenarios, optimizer, validation, live layers, Streamlit app) once the event started.
- Ran the real Google Earth Engine export for Kochi and fixed every real bug hit along the way: an auth hang (GCE metadata probe), an OAuth project conflict, a `reduceResolution` projection error, `computePixels` memory-limit failures (fixed with row tiling + auto-halving retry), an `Element`-type coercion bug, and a GHS_POP `-200` nodata sentinel leaking through as literal population.
- Found and fixed two of his own earlier bugs during a later audit: a `.gitignore` line that silently never matched (`cache/` had a trailing comment — `.gitignore` has no trailing-comment syntax), and a stray "-1" ward bucket in saved plan JSON.
- Reviewed every teammate PR and every remote branch line-by-line before merging anything; merged PRs #5, #6, #7, #9, and separately cherry-picked the one safe commit off PR #8's branch.
- Verified the running app in a real browser with Playwright (not just headless tests) and found + fixed a genuine pydeck 0.9 rendering bug in the process (unquoted base64 image strings get misread as JS expressions).

**Gouri Sankar A** (teammate, `g0w6y`) — human-authored commits:
- README, CI scaffolding, and win-strategy analysis (`STRATEGY.md`) — PR #1, merged.
- Kept `STRATEGY.md`/`config.py` in sync with the PS1 compliance checklist.
- Flagged a real schedule mismatch against the official event site (PR #2, closed — content folded into later plan revisions instead).
- Proposed removing pre-event code over disqualification risk (PR #3, closed — the team's actual call was to keep the code and treat it as practice, per the plan's own "practice-only" framing).
- Fixed the rubric pillar count (5, not 6) and pitch format (5+2 min, not 3 min) — PR #5, merged.
- Fixed the Malayalam news filter missing inflected place/heat words — PR #6, merged.
- Added real Kochi ward boundaries and fixed a silent ward-name/coordinate bug, plus real OSM features (roads, schools, markets, canals) — PR #7, merged.
- Re-verified intervention costs and Kerala policy rules, fixed a canal-naming error, added 2 Q&A items — PR #9, merged.
- Wrote two versions of a TASKS.md documentation update (PRs #8 and #10) — neither merged as-is because the live-status section had already moved on by the time each was reviewed.

**Codex** (AI agent run by Gouri Sankar A, on the same branches):
- Polished the M3 demo screens and captured 4 backup screenshots for the deck.
- Built the real named-Kochi-ward rollup and matched kNN back-test support.
- Completed the animated heat ledger and conservative-mode toggle.
- Built the English/Malayalam language mode and printable Malayalam ward card — reviewed carefully before merging because it touches the project's standing rule against unreviewed machine-translated Malayalam. It passed review because it never translates numbers or proper names, only static UI labels, and defaults to English — this directly fixes the exact issue (unchecked numbers in translation) the judge panel had vetoed earlier in planning. The label *wording* itself is still flagged in TASKS.md as wanting a native speaker's skim before demo.

**Melwin Santhosh** (teammate, `mlwn4096`):
- Merged PR #1 (README/CI/strategy scaffolding) — the only PR merged by someone other than Jeevan George.

---

## End state (as of the last commit, `7d063e8`, 2026-09-26 04:33 IST)

- 35 commits on `main`, all real work; 12 additional commits exist only on unmerged/stale branches and were deliberately left out.
- 26/26 tests passing, CI green.
- Real Kochi data frozen and committed: 54,168 cells, 23 satellite scenes, 74 real named wards, matched back-test, canal-bank overlay, English/Malayalam UI.
- Visually verified in a real browser via Playwright, not just headless tests.
- Not yet done (unchanged by this history, genuine remaining gaps): nothing deployed to a live URL, no slide deck, no demo video, Malayalam label wording awaiting a native speaker's skim, team rehearsal status unknown.
