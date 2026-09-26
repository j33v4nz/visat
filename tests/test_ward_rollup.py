"""Guard the committed 74-ward app build against a silent zone fallback."""

import json

import pandas as pd
import pytest

from uhi import config


def test_named_ward_artifacts_match_cell_assignment():
    app = config.APP
    cells = pd.read_parquet(app / "cells.parquet")
    wards = pd.read_parquet(app / "wards.parquet")
    geo = json.loads((app / "wards.geojson").read_text(encoding="utf-8"))
    plans = json.loads((app / "plans.json").read_text(encoding="utf-8"))
    metrics = json.loads((app / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["area_kind"] == "wards"
    assert len(wards) == len(geo["features"]) == 74
    assert cells.loc[cells.ward_id >= 0, "ward_id"].nunique() == 74
    assert wards["people"].sum() == pytest.approx(cells.loc[cells.ward_id >= 0, "pop"].sum())
    names = wards.set_index("ward_id")["ward"]
    for feature in geo["features"]:
        props = feature["properties"]
        assert props["name"] == names.loc[props["ward_id"]]
    assert set(plans["presets"]["10"]["ward_actions"]) <= set(names.index.astype(str))
