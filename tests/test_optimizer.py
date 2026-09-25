import pytest

from visat.optimizer import Candidate, baseline_spread_evenly, baseline_trees_everywhere, optimize


def make_candidates():
    return [
        Candidate("cell_a", "street_tree", cost_rupees=31_000, delta_c=1.5, people_protected=500),
        Candidate("cell_b", "cool_roof", cost_rupees=300_000, delta_c=2.0, people_protected=2000),
        Candidate("cell_c", "street_tree", cost_rupees=31_000, delta_c=1.2, people_protected=300),
        Candidate(
            "cell_d",
            "mangrove",
            cost_rupees=5_000_000,
            delta_c=0.5,
            people_protected=100,
            spillover_cell_ids=("cell_e",),
        ),
    ]


def test_optimize_never_exceeds_budget():
    result = optimize(make_candidates(), budget_rupees=100_000)
    assert result.total_cost_rupees <= 100_000


def test_optimize_picks_at_most_one_intervention_per_cell():
    result = optimize(make_candidates(), budget_rupees=10_000_000)
    cell_ids = [c.cell_id for c in result.chosen]
    assert len(cell_ids) == len(set(cell_ids))


def test_candidate_rejects_negative_cooling():
    with pytest.raises(ValueError):
        Candidate("cell_x", "street_tree", cost_rupees=1000, delta_c=-0.1, people_protected=10)


def test_candidate_rejects_nonpositive_cost():
    with pytest.raises(ValueError):
        Candidate("cell_x", "street_tree", cost_rupees=0, delta_c=1.0, people_protected=10)


def test_optimize_beats_or_matches_spread_evenly_baseline():
    candidates = make_candidates()
    budget = 3_000_000
    optimized = optimize(candidates, budget)
    baseline = baseline_spread_evenly(candidates, budget)
    assert optimized.weighted_delta_c_people >= baseline.weighted_delta_c_people


def test_optimize_beats_or_matches_trees_everywhere_baseline():
    candidates = make_candidates()
    budget = 3_000_000
    optimized = optimize(candidates, budget)
    baseline = baseline_trees_everywhere(candidates, budget)
    assert optimized.weighted_delta_c_people >= baseline.weighted_delta_c_people


def test_deterministic_across_repeated_runs():
    candidates = make_candidates()
    r1 = optimize(candidates, 3_000_000)
    r2 = optimize(candidates, 3_000_000)
    assert [c.cell_id for c in r1.chosen] == [c.cell_id for c in r2.chosen]


def test_zero_budget_raises():
    with pytest.raises(ValueError):
        optimize(make_candidates(), budget_rupees=0)
