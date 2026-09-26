from uhi.simulation import scenario_report, validation_inventory, weather_response


def test_negative_weather_changes_reverse_interval_endpoints():
    effects = {k: {"effect_c": 1, "ci_low": .5, "ci_high": 2}
               for k in ("t2m_c", "rh", "wind_ms", "ssrd_wm2")}
    result = weather_response(effects, {"t2m_c": -2, "rh": 10, "wind_ms": 0, "ssrd_wm2": 100})
    assert result.iloc[0][["effect_c", "low", "high"]].tolist() == [-2, -4, -1]
    assert result.effect_c.sum() == 0
    assert (result.low <= result.high).all()


def test_report_escapes_data_and_keeps_source_provenance():
    report = scenario_report("<script>bad</script>", {"Ward": "<img src=x>"},
                             ["Not a forecast"], {"source": "frozen", "built_at": "2026-09-26"})
    assert "<script>" not in report
    assert "&lt;img src=x&gt;" in report
    assert "Not a forecast" in report and "2026-09-26" in report


def test_missing_artifacts_do_not_claim_completed_runs():
    status = validation_inventory({"backtest": {"n_changed_cells": 8000}}, {})
    assert status["2017 to 2024 back-test"]
    assert not status["Matched kNN back-test"]
    assert not status["Resident reaction preview"]
    assert not status["Vulnerability weighting sensitivity"]
