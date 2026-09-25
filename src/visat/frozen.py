"""Load the real frozen export (data/frozen + data/raw) in the same format as demo_data.build()."""

import json
import warnings

import numpy as np
import pandas as pd

from visat import config, validation


def load() -> dict:
    f = config.FROZEN
    need = ["cells_static.parquet", "scenes.parquet", "scenes_meta.parquet", "backtest.parquet"]
    missing = [n for n in need if not (f / n).exists()]
    if missing:
        raise FileNotFoundError(f"Missing {missing} in data/frozen — run python -m visat.gee_export first")
    cells = pd.read_parquet(f / "cells_static.parquet")
    cells["pop"] = cells["pop"].clip(lower=0)  # GHS_POP's nodata sentinel (-200); older exports may
    # still have it baked in even after the gee_export.py fix, since parquet files aren't regenerated
    if (f / "osm.parquet").exists():
        cells = cells.merge(pd.read_parquet(f / "osm.parquet"), on="cell_id", how="left").fillna(0)
    else:
        warnings.warn("No osm.parquet — using proxies (no schools/markets/canals). Run visat.osm_features.")
        cells["road_frac"] = np.clip(cells["built_frac"] - cells["building_frac"], 0, 0.4)
        for c in ("n_school", "n_market", "n_hospital", "n_construction", "n_harbour", "is_park",
                  "canal_bank"):
            cells[c] = 0
    meta = pd.read_parquet(f / "scenes_meta.parquet")

    eco = validation.ecostress_from_appeears(config.RAW / "ecostress", cells)
    cells["eco_anom"] = eco if eco is not None else np.nan

    wards = None
    wpath = config.RAW / "wards.geojson"
    if wpath.exists():
        wards = json.loads(wpath.read_text())
    cpcb = validation.cpcb_check(config.RAW / "cpcb", meta) if (config.RAW / "cpcb").exists() else None
    return {"cells": cells, "scenes": pd.read_parquet(f / "scenes.parquet"), "scenes_meta": meta,
            "backtest": pd.read_parquet(f / "backtest.parquet"), "wards": wards, "cpcb": cpcb,
            "source": "frozen"}
