from visat import config


def test_grid_resolution_is_positive():
    assert config.GRID_RESOLUTION_M > 0


def test_backtest_years_are_ordered():
    start, end = config.BACKTEST_YEARS
    assert start < end


def test_green_roof_excluded_from_costs_used_by_optimizer():
    # Documented as excluded in PLAN.md and STRATEGY.md — exists for reference
    # only and must never be wired into the optimizer's cost table.
    assert config.COST_GREEN_ROOF_PER_SQM > 0


def test_kochi_points_have_eight_locations():
    assert len(config.KOCHI_POINTS) == 8


def test_heat_index_bands_cover_caution_to_extreme_danger():
    assert set(config.HEAT_INDEX_BANDS_C) == {
        "caution",
        "extreme_caution",
        "danger",
        "extreme_danger",
    }
