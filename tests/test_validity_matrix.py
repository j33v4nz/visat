from visat.physics import DEFAULT_DELTA_ALBEDO, delta_t_from_albedo_change
from visat.validity_matrix import (
    INTERVENTIONS,
    Method,
    cost_cool_roof,
    cost_street_tree,
    optimizer_eligible_interventions,
)


def test_every_intervention_has_a_callable_cost_function():
    import visat.validity_matrix as vm

    for intervention in INTERVENTIONS.values():
        assert hasattr(vm, intervention.cost_fn_name), intervention.key


def test_green_roof_and_iurwts_excluded_from_optimizer():
    eligible_keys = {i.key for i in optimizer_eligible_interventions()}
    assert "green_roof" not in eligible_keys
    assert "iurwts_canal" not in eligible_keys
    assert "street_tree" in eligible_keys


def test_iurwts_is_no_credit_method():
    assert INTERVENTIONS["iurwts_canal"].method == Method.NO_CREDIT


def test_cost_street_tree_scales_linearly():
    assert cost_street_tree(10) == 10 * cost_street_tree(1)


def test_cool_roof_cost_includes_recoats_over_time():
    one_year = cost_cool_roof(100, years=1)
    four_years = cost_cool_roof(100, years=4)
    assert four_years > one_year


def test_energy_balance_formula_only_cools():
    delta = delta_t_from_albedo_change(DEFAULT_DELTA_ALBEDO["cool_roof"])
    assert delta > 0  # positive = cooling


def test_energy_balance_formula_rejects_negative_albedo_change():
    import pytest

    with pytest.raises(ValueError):
        delta_t_from_albedo_change(-0.1)
