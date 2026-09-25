from visat.heat_index import heat_index_band, heat_index_celsius


def test_matches_resources_md_check_value():
    # RESOURCES.md §2b: "32C at 70% humidity should come out ~= 41C"
    hi = heat_index_celsius(32, 70)
    assert 39.5 <= hi <= 41.5


def test_below_threshold_returns_air_temperature():
    assert heat_index_celsius(20, 50) == 20.0


def test_band_boundaries():
    assert heat_index_band(20) is None
    assert heat_index_band(28) == "caution"
    assert heat_index_band(35) == "extreme_caution"
    assert heat_index_band(45) == "danger"
    assert heat_index_band(55) == "extreme_danger"
