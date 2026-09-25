from visat import config


def test_grid_resolution_is_positive():
    assert config.GRID_RESOLUTION_M > 0


def test_backtest_years_are_ordered():
    start, end = config.BACKTEST_YEARS
    assert start < end


def test_green_roofs_are_costed_but_flagged_rarely_cost_effective():
    # PLAN.md §5 keeps green roofs IN the cost table (they must be comparable, not hidden)
    # but labels them "evaluated, rarely cost-effective" — the honest outcome at ₹7,500/m².
    spec = config.INTERVENTIONS["green_roofs"]
    assert spec["cost_per_m2"] == 7_500
    assert spec["method"] == "formula"
    assert "cost-effective" in spec["cost_note"]


def test_kochi_points_have_eight_locations():
    assert len(config.KOCHI_POINTS) == 8


def test_heat_index_bands_cover_caution_to_extreme_danger():
    bands = config.HEAT_INDEX_BANDS_C  # [(label, low °C, high °C), ...], consumed by features.py
    assert [name.lower().replace(" ", "_") for name, _, _ in bands] == [
        "caution",
        "extreme_caution",
        "danger",
        "extreme_danger",
    ]
    lows = [lo for _, lo, _ in bands]
    highs = [hi for _, _, hi in bands]
    assert lows[0] == 27  # NWS caution threshold
    assert highs[:-1] == lows[1:]  # bands are contiguous, no gaps
    assert highs[-1] == 200  # open-ended top band
