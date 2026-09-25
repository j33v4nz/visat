"""Greedy budget optimizer: pick the interventions with the best
(deg_c * people * vulnerability_weight) / rupee, spending a fixed budget,
counting neighbourhood spillover once (never double-counted).

Compared against two naive baselines so the Plan screen can show VISAT
beating them: spread the budget evenly across candidates, and "trees
everywhere" (only ever plant trees, ignore cost-effectiveness).
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config


@dataclass(frozen=True)
class Candidate:
    """One (cell, intervention) option the optimizer can choose to fund."""

    cell_id: str
    intervention_key: str
    cost_rupees: float
    delta_c: float  # predicted cooling at this cell
    people_protected: int
    vulnerability_weight: float = 1.0
    # cell_ids of neighbours whose exposure this candidate also reduces,
    # so spillover benefit isn't counted twice if a neighbour is separately funded.
    spillover_cell_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.cost_rupees <= 0:
            raise ValueError(f"{self.cell_id}/{self.intervention_key}: cost must be positive")
        if self.delta_c < 0:
            raise ValueError(
                f"{self.cell_id}/{self.intervention_key}: delta_c is negative — "
                "no intervention in the validity matrix may warm a cell"
            )

    @property
    def score(self) -> float:
        """cooling x people x vulnerability, per rupee."""
        return (self.delta_c * self.people_protected * self.vulnerability_weight) / self.cost_rupees


@dataclass
class PlanResult:
    chosen: list[Candidate]
    total_cost_rupees: float
    total_people_protected: int
    weighted_delta_c_people: float  # sum of delta_c * people_protected, spillover deduped
    budget_rupees: float

    @property
    def unspent_rupees(self) -> float:
        return self.budget_rupees - self.total_cost_rupees


def _dedupe_spillover(chosen: list[Candidate]) -> tuple[float, int]:
    """Sum delta_c * people, counting each cell's benefit only once even if
    it appears as a spillover target of more than one chosen candidate."""
    best_effect_per_cell: dict[str, float] = {}

    for c in chosen:
        cells = {c.cell_id, *c.spillover_cell_ids}
        per_cell_effect = c.delta_c * c.people_protected / len(cells)
        for cell in cells:
            best_effect_per_cell[cell] = max(best_effect_per_cell.get(cell, 0.0), per_cell_effect)

    total = sum(best_effect_per_cell.values())
    people = sum(c.people_protected for c in chosen)
    return total, people


def optimize(candidates: list[Candidate], budget_rupees: float) -> PlanResult:
    """Greedy knapsack by score-per-rupee. Deterministic tie-break on
    cell_id so re-runs with the same inputs always pick the same plan —
    needed for the precomputed budget-preset cache to be reproducible."""
    if budget_rupees <= 0:
        raise ValueError("budget_rupees must be positive")

    ranked = sorted(candidates, key=lambda c: (-c.score, c.cell_id, c.intervention_key))

    chosen: list[Candidate] = []
    spent = 0.0
    chosen_cells: set[str] = set()

    for c in ranked:
        if c.cell_id in chosen_cells:
            continue  # one funded intervention per cell — no double-spend on the same ground
        if spent + c.cost_rupees > budget_rupees:
            continue
        chosen.append(c)
        chosen_cells.add(c.cell_id)
        spent += c.cost_rupees

    weighted, people = _dedupe_spillover(chosen)
    return PlanResult(
        chosen=chosen,
        total_cost_rupees=spent,
        total_people_protected=people,
        weighted_delta_c_people=weighted,
        budget_rupees=budget_rupees,
    )


def baseline_spread_evenly(candidates: list[Candidate], budget_rupees: float) -> PlanResult:
    """Naive baseline: split the budget evenly across all candidate cells,
    buying whichever single intervention that cell's share affords."""
    if not candidates:
        return PlanResult([], 0.0, 0, 0.0, budget_rupees)

    by_cell: dict[str, list[Candidate]] = {}
    for c in candidates:
        by_cell.setdefault(c.cell_id, []).append(c)

    share = budget_rupees / len(by_cell)
    chosen: list[Candidate] = []
    spent = 0.0
    for cell_candidates in by_cell.values():
        affordable = [c for c in cell_candidates if c.cost_rupees <= share]
        if not affordable:
            continue
        pick = max(affordable, key=lambda c: c.score)
        chosen.append(pick)
        spent += pick.cost_rupees

    weighted, people = _dedupe_spillover(chosen)
    return PlanResult(chosen, spent, people, weighted, budget_rupees)


def baseline_trees_everywhere(candidates: list[Candidate], budget_rupees: float) -> PlanResult:
    """Naive baseline: only ever fund street-tree candidates, cheapest
    first, ignoring cost-effectiveness against other intervention types."""
    tree_candidates = sorted(
        (c for c in candidates if c.intervention_key == "street_tree"),
        key=lambda c: (c.cost_rupees, c.cell_id),
    )

    chosen: list[Candidate] = []
    spent = 0.0
    chosen_cells: set[str] = set()
    for c in tree_candidates:
        if c.cell_id in chosen_cells or spent + c.cost_rupees > budget_rupees:
            continue
        chosen.append(c)
        chosen_cells.add(c.cell_id)
        spent += c.cost_rupees

    weighted, people = _dedupe_spillover(chosen)
    return PlanResult(chosen, spent, people, weighted, budget_rupees)


def precompute_presets(candidates: list[Candidate]) -> dict[int, PlanResult]:
    """One optimize() call per preset (₹1/10/50 crore), so the Plan screen's
    buttons are instant lookups instead of a laggy live re-optimization."""
    return {
        crore: optimize(candidates, crore * 1e7) for crore in config.BUDGET_PRESETS_CRORE
    }
