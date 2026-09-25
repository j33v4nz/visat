import numpy as np
import pytest

from visat import config, heat_neutral, optimize, validation
from visat.features import heat_band, heat_index_c, relative_humidity
from visat.scenarios import eligible


def test_heat_index_matches_nws_table():
    assert heat_index_c(32.22, 70) == pytest.approx(41.1, abs=0.3)  # NWS table: 90 °F / 70% → 106 °F
    assert heat_band(41) == "Danger"
    assert relative_humidity(30, 30) == pytest.approx(100, abs=0.1)


@pytest.mark.parametrize("crore", config.BUDGET_PRESETS_CR)
def test_plan_stays_within_budget(world, crore):
    sel = optimize.greedy(world["cand"], crore * config.CRORE)
    assert sel["cost"].sum() <= crore * config.CRORE
    assert not sel.index.duplicated().any()  # one intervention per cell


def test_no_fix_ever_warms(world):
    assert (world["cand"]["own_dt"] <= 1e-6).all()
    sel = optimize.greedy(world["cand"], 10 * config.CRORE)
    res = world["engine"].evaluate(sel)
    assert res["dt"].max() <= 1e-4
    assert res["person_deg"] < 0


def test_fixes_only_on_eligible_land(world):
    eng, sel = world["engine"], optimize.greedy(world["cand"], 50 * config.CRORE)
    for key, grp in sel.groupby("intervention"):
        assert eligible(eng.cells, key).loc[grp.index].all(), key
    mang = sel[sel["intervention"] == "mangroves"].index
    assert (eng.cells.loc[mang, "dist_water_m"] <= 200).all()


def test_joint_reprediction_consistent_with_single_estimate(world):
    eng, cand = world["engine"], world["cand"]
    one = cand[cand["method"] == "analog"].nlargest(1, "benefit")
    dt = eng.evaluate(one)["dt"]
    i = one.index[0]
    assert dt[i] == pytest.approx(one["own_dt"].iloc[0], abs=0.05)


def test_plan_beats_naive_baselines(world):
    eng, cand = world["engine"], world["cand"]
    budget = 10 * config.CRORE
    ours = eng.evaluate(optimize.greedy(cand, budget))["person_deg"]
    even = eng.evaluate(optimize.even_spread(cand, eng.cells, budget))["person_deg"]
    trees = eng.evaluate(optimize.trees_everywhere(cand, budget))["person_deg"]
    assert ours < even and ours < trees  # more negative = more cooling


def test_heat_neutral_check(world):
    eng = world["engine"]
    sites = heat_neutral.select_sites(eng.cells)
    assert sites
    r = heat_neutral.check(eng, sites[0], "it_park", world["cand"])
    assert r["before"]["person_deg"] > 0
    assert r["after"]["net_person_deg"] < r["before"]["person_deg"]


def test_backtest_runs(world):
    bt = validation.backtest(world["model"], world["engine"].cells, world["data"]["backtest"],
                             world["engine"].atmos)
    assert bt["n_changed_cells"] > 10 and np.isfinite(bt["mae_c"])
    assert bt["matched"]["n_changed_matched"] > 10
    assert np.isfinite(bt["matched"]["mae_c"])


def test_matched_backtest_removes_local_control_trend():
    import pandas as pd

    n = 12
    cells = pd.DataFrame({"water_frac": np.zeros(2 * n)})
    base = np.linspace(0.1, 0.8, n)
    bt = pd.DataFrame({
        "built_2017": np.r_[base, base],
        "built_2024": np.r_[base + 0.2, base],
        "tree_2017": np.r_[1 - base, 1 - base],
        "tree_2024": np.r_[1 - base, 1 - base],
        "water_2017": np.zeros(2 * n), "water_2024": np.zeros(2 * n),
        "ndvi_2017": np.r_[1 - base, 1 - base],
        "albedo_2017": np.full(2 * n, 0.2),
    })
    # Changed cells warmed 1.5 °C beyond the common 1 °C local trend.
    observed = np.r_[np.full(n, 2.5), np.full(n, 1.0)]
    predicted = np.r_[np.full(n, 1.4), np.zeros(n)]
    result = validation.matched_backtest(cells, bt, predicted, observed)
    assert result["n_changed_matched"] == n
    assert result["mean_observed_did_c"] == pytest.approx(1.5)
    assert result["mean_predicted_did_c"] == pytest.approx(1.4)
    assert result["mae_c"] == pytest.approx(0.1)
