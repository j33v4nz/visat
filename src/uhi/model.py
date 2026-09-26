"""Scene-panel physics-informed XGBoost: cells × scenes, per-scene ERA5, monotone constraints."""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, KFold

from uhi import config
from uhi.features import add_physics_feature, block_ids, model_matrix

PARAMS = {
    "objective": "reg:squarederror",
    "tree_method": "hist",
    "max_depth": 6,
    "eta": 0.08,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "nthread": -1,
    "verbosity": 0,
}
ROUNDS = 300
MONOTONE = "(" + ",".join(str(v) for v in config.FEATURES.values()) + ")"


def build_panel(cells: pd.DataFrame, scenes: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """One row per (cell, scene). Mixed land–water pixels (>50% water) are excluded from training."""
    land = cells[cells["water_frac"] <= 0.5]
    panel = scenes.merge(land, on="cell_id").merge(meta[["scene_id", *config.ATMOS_FEATURES]], on="scene_id")
    return add_physics_feature(panel)


def with_atmos(cells: pd.DataFrame, atmos: dict) -> pd.DataFrame:
    frame = cells.copy()
    for k in config.ATMOS_FEATURES:
        frame[k] = atmos[k]
    return add_physics_feature(frame)


def typical_atmos(meta: pd.DataFrame) -> dict:
    return {k: float(meta[k].median()) for k in config.ATMOS_FEATURES}


def fit(panel: pd.DataFrame, constrained: bool = True, rounds: int = ROUNDS) -> xgb.Booster:
    params = dict(PARAMS)
    if constrained:
        params["monotone_constraints"] = MONOTONE
    dtrain = xgb.DMatrix(model_matrix(panel), label=panel["lst_c"])
    return xgb.train(params, dtrain, num_boost_round=rounds)


def predict(model: xgb.Booster, frame: pd.DataFrame) -> np.ndarray:
    return model.predict(xgb.DMatrix(model_matrix(frame)))


def _scores(y, p):
    return {"r2": float(r2_score(y, p)), "rmse": float(np.sqrt(mean_squared_error(y, p)))}


def cross_validate(panel: pd.DataFrame, max_rows: int = 250_000, seed: int = 0) -> dict:
    """Grouped spatial-block CV (2 km blocks, across all scenes) vs baselines, plus random CV."""
    sample = panel.sample(min(max_rows, len(panel)), random_state=seed)
    X, y = model_matrix(sample), sample["lst_c"].to_numpy()
    groups = block_ids(sample)
    out = {"n_rows": len(sample), "n_scenes": int(sample["scene_id"].nunique()),
           "n_blocks": len(np.unique(groups))}

    def run(splitter, split_groups, kind):
        preds = np.zeros(len(y))
        for tr, te in splitter.split(X, y, split_groups):
            if kind == "linear":
                m = Ridge(alpha=1.0).fit(X.iloc[tr], y[tr])
                preds[te] = m.predict(X.iloc[te])
            else:
                params = dict(PARAMS)
                if kind == "constrained":
                    params["monotone_constraints"] = MONOTONE
                booster = xgb.train(params, xgb.DMatrix(X.iloc[tr], label=y[tr]), 150)
                preds[te] = booster.predict(xgb.DMatrix(X.iloc[te]))
        return _scores(y, preds)

    spatial = GroupKFold(n_splits=5)
    out["spatial_cv"] = {
        "Physics-informed XGBoost (ours)": run(spatial, groups, "constrained"),
        "Unconstrained XGBoost": run(spatial, groups, "unconstrained"),
        "Linear baseline": run(spatial, groups, "linear"),
    }
    out["random_cv_ours"] = run(KFold(5, shuffle=True, random_state=seed), None, "constrained")
    return out


def driver_contributions(model: xgb.Booster, frame: pd.DataFrame) -> pd.DataFrame:
    """Native TreeSHAP contributions, grouped into plain-language driver groups (°C)."""
    contrib = model.predict(xgb.DMatrix(model_matrix(frame)), pred_contribs=True)
    names = list(config.FEATURES)
    df = pd.DataFrame(contrib[:, : len(names)], columns=names, index=frame.index)
    return pd.DataFrame({g: df[cols].sum(axis=1) for g, cols in config.DRIVER_GROUPS.items()})


def atmospheric_sensitivity(model, panel, meta, n_cells=3000, n_boot=200, seed=0) -> dict:
    """°C of surface-temperature change per unit of each weather variable, with bootstrap CIs
    over scenes (n = number of scenes is small, so intervals are reported honestly)."""
    rng = np.random.default_rng(seed)
    sample = panel.sample(min(n_cells * 5, len(panel)), random_state=seed)
    steps = {"t2m_c": 1.0, "rh": 10.0, "wind_ms": 1.0, "ssrd_wm2": 100.0}
    units = {"t2m_c": "+1 °C air temp", "rh": "+10% humidity", "wind_ms": "+1 m/s wind",
             "ssrd_wm2": "+100 W/m² sunlight"}
    base = predict(model, sample)
    result = {}
    for var, step in steps.items():
        bumped = sample.copy()
        bumped[var] = bumped[var] + step
        bumped = add_physics_feature(bumped)
        diff = predict(model, bumped) - base
        per_scene = pd.Series(diff).groupby(sample["scene_id"].to_numpy()).mean().to_numpy()
        boots = [rng.choice(per_scene, len(per_scene)).mean() for _ in range(n_boot)]
        result[var] = {"label": units[var], "effect_c": float(per_scene.mean()),
                       "ci_low": float(np.percentile(boots, 2.5)),
                       "ci_high": float(np.percentile(boots, 97.5))}
    return {"n_scenes": int(meta["scene_id"].nunique()), "effects": result}
