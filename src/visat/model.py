"""Scene-panel physics-informed model. Rows are (cell x scene): each row is
one 100m grid cell observed in one clean Landsat scene, carrying that
scene's own ERA5 weather at overpass hour. This is what lets the model
learn *both* where it's hot (land cover) and how the day's weather changes
it (PS1 Objective 2/3).

Data loading from Earth Engine happens in ee_export.py and needs your own
authenticated GEE session — this module operates on the resulting
DataFrame/array and has no live dependency, so it's fully unit-testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

# Feature order matters: must match MONOTONE_CONSTRAINTS exactly, 1-to-1.
FEATURE_COLUMNS = [
    "built_fraction",       # ESA WorldCover built-up fraction in the cell
    "tree_fraction",        # ESA WorldCover tree-cover fraction
    "water_fraction",       # ESA WorldCover water fraction
    "albedo",               # from Landsat SR bands (Liang's formula)
    "elevation_m",          # SRTM
    "distance_to_water_m",  # nearest water body
    "population_density",   # GHSL
    "building_height_m",    # GHSL
    "energy_balance_feature",  # (1 - albedo) * SSRD, varies scene to scene
    "air_temp_c",            # ERA5 at overpass hour
    "relative_humidity_pct",  # ERA5-derived
    "wind_speed_ms",          # ERA5
]

# +1 = feature can only warm a cell as it increases, -1 = can only cool,
# 0 = no physical warm/cool prior (context features). Concrete only warms;
# trees, water and reflective surfaces only cool (PLAN.md's physics rule).
MONOTONE_CONSTRAINTS: tuple[int, ...] = (
    1,   # built_fraction: more concrete -> only warmer
    -1,  # tree_fraction: more trees -> only cooler
    -1,  # water_fraction: more water -> only cooler
    -1,  # albedo: more reflective -> only cooler
    0,   # elevation_m: no monotone prior
    0,   # distance_to_water_m: no monotone prior (already captured by water_fraction)
    0,   # population_density: context, not a physical driver
    0,   # building_height_m: canyon effects go both ways, no forced monotone prior
    1,   # energy_balance_feature: more absorbed radiation -> only warmer
    0,   # air_temp_c: atmospheric driver, no cell-level monotone prior
    0,   # relative_humidity_pct: atmospheric driver
    0,   # wind_speed_ms: atmospheric driver
)

assert len(FEATURE_COLUMNS) == len(MONOTONE_CONSTRAINTS)


def energy_balance_feature(albedo: pd.Series, ssrd_w_m2: pd.Series) -> pd.Series:
    """(1 - albedo) * incoming solar radiation, per scene per cell — the
    physics feature that makes this genuinely scene-panel, not just a
    cross-sectional model with a static albedo term."""
    return (1 - albedo) * ssrd_w_m2


def assign_spatial_blocks(lat: pd.Series, lon: pd.Series, block_size_m: float) -> pd.Series:
    """Snap each cell to a spatial block id on a simple equirectangular grid,
    for grouped spatial-block cross-validation. A block never appears in
    both train and test — that's what makes the CV honest for a model that
    will be applied to *new* Kochi locations, not just held-out scenes."""
    meters_per_degree_lat = 111_320
    meters_per_degree_lon = 111_320 * np.cos(np.radians(lat.mean()))
    block_lat = (lat * meters_per_degree_lat // block_size_m).astype(int)
    block_lon = (lon * meters_per_degree_lon // block_size_m).astype(int)
    return block_lat.astype(str) + "_" + block_lon.astype(str)


def spatial_block_splits(
    block_ids: pd.Series, n_splits: int = 5, *, random_state: int = 0
) -> list[tuple[np.ndarray, np.ndarray]]:
    """GroupKFold on spatial block id, applied across all scenes at once —
    a block's cells are never split between train and test even though the
    same block appears in many different scene-rows."""
    gkf = GroupKFold(n_splits=n_splits)
    dummy_x = np.zeros((len(block_ids), 1))
    return list(gkf.split(dummy_x, groups=block_ids))


def cross_validated_rmse(
    df: pd.DataFrame,
    target_col: str,
    *,
    n_splits: int = 5,
    xgb_params: dict | None = None,
) -> dict[str, float | list[float]]:
    """Fit the monotone-constrained model on each spatial-block fold, return
    per-fold RMSE and the mean +/- 90%-ish spread (1.645 * std), so results
    are always reported with n and a confidence interval, never a bare
    number, per PLAN.md's honesty rules.

    Requires `xgboost` at call time — imported lazily so the rest of this
    module works without it installed (e.g. for testing feature engineering
    alone).
    """
    import xgboost as xgb

    params = {
        "max_depth": 5,
        "eta": 0.1,
        "objective": "reg:squarederror",
        "monotone_constraints": tuple(MONOTONE_CONSTRAINTS),
    }
    if xgb_params:
        params.update(xgb_params)

    block_ids = assign_spatial_blocks(df["lat"], df["lon"], block_size_m=2000)
    splits = spatial_block_splits(block_ids, n_splits=n_splits)

    rmses = []
    for train_idx, test_idx in splits:
        train_x = df.iloc[train_idx][FEATURE_COLUMNS]
        train_y = df.iloc[train_idx][target_col]
        test_x = df.iloc[test_idx][FEATURE_COLUMNS]
        test_y = df.iloc[test_idx][target_col]

        dtrain = xgb.DMatrix(train_x, label=train_y, feature_names=FEATURE_COLUMNS)
        dtest = xgb.DMatrix(test_x, feature_names=FEATURE_COLUMNS)
        booster = xgb.train(params, dtrain, num_boost_round=200)
        preds = booster.predict(dtest)
        rmse = float(np.sqrt(np.mean((preds - test_y.to_numpy()) ** 2)))
        rmses.append(rmse)

    mean = float(np.mean(rmses))
    std = float(np.std(rmses))
    return {
        "fold_rmse": rmses,
        "n_folds": len(rmses),
        "mean_rmse": mean,
        "ci_90_low": mean - 1.645 * std,
        "ci_90_high": mean + 1.645 * std,
    }
