# VISAT — Winning Strategy & Risk Register

Companion to [PLAN.md](./PLAN.md) and [RESOURCES.md](./RESOURCES.md). Those cover *what to build*. This covers *how to win*: judging-vector analysis, the risks specific to this plan's current shape (six tabs, two live layers, the Heat Impact Check), and the exact order to cut scope if the clock runs out. Analysis and pre-event decisions only — no project code, per PLAN.md §14.

Written after RESOURCES.md and the Heat Impact Check / live weather / Malayalam news additions — so this reflects the current plan, not an earlier version.

---

## 1. Judging vectors — what actually gets scored

No official HackMe'26 rubric is published. Using 2025–2026 hackathon judging norms as the working model:

| Vector | Typical weight | What judges actually check | Where VISAT stands |
|---|---|---|---|
| **Technical implementation** | ~25% | Real ML, honestly validated, or an API wrapper? | Strong — monotone-constrained XGBoost, spatial block CV, physics energy-balance check, reverse analog-transition for the Heat Impact Check. This is the ceiling of what most teams will attempt. |
| **Problem-solving impact** | ~25% | Solves *this* problem for *this* place, not a generic demo? | Strong — named stakeholder (C-HED), sourced ₹ costs, real ward data, a genuinely new mechanism (heat-neutral development review) with no found Kerala equivalent. |
| **Innovation** | ~20% | Goes beyond "here's a heat map"? | Very strong on paper — warn (live) / plan (optimize) / prevent (Heat Impact Check) / prove (back-test) is a rare four-part story at hackathon level. The risk isn't ambition, it's finishing all four cleanly (§3). |
| **Presentation / demo** | ~20–30% | Does the first 60 seconds land? Does the demo survive being touched? | Now has *two* live external dependencies (Open-Meteo, Malayalam RSS) on top of the satellite pipeline — both already have documented cache/fallback in RESOURCES.md, which is the right call. Demo choreography needs to make the fallback itself look intentional, not broken (§4). |
| **Q&A / defensibility** | folded into technical + impact | Can every number be defended without hand-waving? | PLAN.md §11 is already unusually thorough (12 prepared questions). A few more below (§5) close remaining gaps. |

**Key implication:** the scope here (six tabs, two live feeds, a reverse-optimizer feature, a full back-tested ML pipeline) is large even by ambitious-hackathon standards. The team's own Tier system already sequences this correctly — the win-condition is protecting that sequencing under time pressure, not adding more analysis of what to build.

---

## 2. What's already been checked and fixed (no action needed — noted for completeness)

RESOURCES.md already independently caught and fixed the two data-source issues that came up in earlier review of this plan:
- **ECOSTRESS** — confirmed not ingested for Kochi in Earth Engine (LA-metro tiles only). Correctly dropped.
- **ESA WorldCover time-series** — WorldCover has no 2017/2024 edition (only 2020, 2021). Correctly replaced with Dynamic World for the back-test, WorldCover kept only for the present-day driver map.

One additional gap worth a one-line Q&A answer, not a rebuild:

**GHSL population has no 2024 real epoch.** RESOURCES.md §2 notes GHSL population epochs run every 5 years "to 2020, plus 2025/2030 projections" — so the population layer used to weight 2024-era exposure is technically 2020 (or a projection), not measured 2024 data. This is a minor, disclosable gap, not a blocker — add it to §5 below so it isn't a surprise in Q&A.

---

## 3. Scope risk — the real threat, given how much Tier 2 now holds

Tier 2 (PLAN.md §7) now bundles five substantial builds in the same after-4PM window: the Heat Impact Check engine, the live 72-hour forecast + "where to act today" ranking, the Malayalam news ticker, the matched back-test, and vulnerability weighting. The team roles table already parallelizes these across M1–M4, which is the right structural fix — the remaining risk is sequencing *within* each person's Tier 2 list if they personally run behind.

**Fix — one hard sub-priority per Tier 2 owner, decided now:**
- **M2:** Heat Impact Check engine ships before vulnerability weights. PLAN.md itself calls it "the headline innovation" — it is the one Tier 2 item that must not slip, since it's the newest and most differentiating tab.
- **M1:** live ward-exposure ranking ships before the matched back-test upgrade; the simple (unmatched) back-test from Tier 1 is still honest and demoable on its own.
- **M4:** the Malayalam ticker is real innovation but is also the single most fragile Tier 2 item (external RSS + language-specific keyword matching, §4). If M4 is behind at 7 PM, the live weather strip alone (already Tier 1) is enough to carry the "warn today" story — cut the news ticker before cutting anything else in Tier 2.

---

## 4. Technical risk register (updated for the current plan)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Malayalam RSS ticker shows a wrong/irrelevant headline live in front of judges (Gulf heat story leaks through, or a stale/misclassified item) | Medium | Embarrassing but recoverable if planned for | Keep a small curated backup list of 3–4 known-good confirmed headlines ready to swap into `data/news_cache.json` if the live feed looks bad on demo morning — this is exactly what the cache/fallback mechanism is for, use it proactively, not only on network failure | M4 |
| Judge asks whether scraping Google News RSS / news-site feeds is legitimate | Low | Could read as a credibility wobble if unprepared | One-liner ready: these are public, unauthenticated RSS feeds intended for syndication; only headline + channel + time + link are shown, never article text — already the team's own fair-use rule (RESOURCES.md §2c) | M4 |
| Open-Meteo's 8 query points collapse to ~4 distinct model cells (already found and documented in RESOURCES.md) gets read by a judge as "your live layer isn't really ward-level" | Medium | Could undercut the "live" claim if not framed first | Say it before they ask: "the live layer is intentionally city-scale — it tells you *when* it's dangerous; the satellite layer tells you *where* land cover makes it worse locally." This is already PLAN.md's own framing (§3, "Why the satellite map itself isn't live") — just make sure whoever demos the live strip says this line proactively, not defensively | M3 |
| GHSL population epoch (2020/projection) doesn't match the 2024 back-test year | Low | Minor, but an unprepared answer looks worse than the gap itself | Add to Q&A (§5) | M1 |
| Two live external dependencies (Open-Meteo + RSS) both need to be demoed working *and* demoed failing gracefully, doubling the rehearsal surface | Medium | Eats rehearsal time that's already scarce | Rehearse the Wi-Fi-off fallback for *both* live features together, once, at the 6 AM rehearsal — not as two separate tests | M3 |
| Heat Impact Check's reverse-transition accuracy for a not-yet-built development is inherently harder to validate than the forward what-if | Medium | Could be the toughest Q&A moment given it's the headline feature | Already has a strong answer in PLAN.md §11 ("same model, same back-tested error, shown as a range"). Make sure whoever answers it says the word "range," never a bare number | M2 |
| Six tabs + two live strips is a lot to walk a judge through if they ask to drive the demo themselves | Low-Medium | Judges going off-script can derail pacing | Decide in advance which tab order survives an off-script judge (Heat → Check a project → Proof is the shortest path that hits both the headline feature and the honesty proof) | M3 |

---

## 5. Additional Q&A (complements PLAN.md §11 — doesn't repeat it)

| Question | Who | Answer |
|---|---|---|
| Your population layer — is it really 2024 data? | M1 | GHSL population's most recent real epoch is 2020 (2025/2030 are projections). We use it as a stable population-density weight, not a claim of exact 2024 population — the *temperature* change we're proving is 2017→2024 real satellite data; population is a weighting layer, not the thing being validated. |
| Is scraping news RSS feeds okay to do here? | M4 | These are public, unauthenticated RSS feeds meant for syndication. We show only headline, channel, time and a link — never republish article text — and label everything as coming from Malayalam news versus official IMD/KSDMA alerts. |
| Why should I trust your live layer is really live right now? | M3 | Point at the timestamp in the strip and the "updated Xm ago" label — refresh happens every 15 minutes, and the freshness panel on the Proof tab shows exactly which layers are live, cached, or frozen. |

---

## 6. Presentation checklist

- Color scale: one diverging red/blue for all temperature visuals across all six tabs — decide the exact hex pair now, don't improvise it at 4 AM.
- Belt-and-suspenders: embed 3–4 screenshots of the key demo moments (live strip, Plan slider beating baselines, Check-a-project heat spread, Proof chart) directly into the slide deck, in case both the live URL and the backup video fail during the actual slot.
- State PS1's own language early on slide 1 — "heat stress hotspots," "physics-informed decision making," "cooling interventions" — judges pattern-match problem-statement wording across many teams.
- If forced to cut a rehearsal pass to finish a feature, don't — an unrehearsed extra feature scores worse than a clean pitch of a smaller one. This applies doubly now that there are two live layers to rehearse failing gracefully (§4).
