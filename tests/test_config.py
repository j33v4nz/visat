from visat import config


def test_grid_and_seasons():
    assert config.GRID_RESOLUTION_M == 100
    assert config.BACKTEST_YEARS[0] < config.BACKTEST_YEARS[1]
    assert set(config.SCENE_MONTHS) >= set(config.BACKTEST_MONTHS)


def test_monotone_constraints_match_physics():
    f = config.FEATURES
    assert f["tree_frac"] == -1 and f["water_frac"] == -1 and f["albedo"] == -1
    assert f["built_frac"] == 1 and f["absorbed_sw"] == 1


def test_every_ps1_intervention_category_is_covered():
    cats = " ".join(v["ps1"] for v in config.INTERVENTIONS.values()).lower()
    for needed in ("greening", "cool roofs", "albedo", "water bodies"):
        assert needed in cats


def test_budget_presets_and_heat_bands():
    assert config.BUDGET_PRESETS_CR == (1, 10, 50)
    assert [b[0] for b in config.HEAT_INDEX_BANDS_C][:3] == ["Caution", "Extreme caution", "Danger"]
