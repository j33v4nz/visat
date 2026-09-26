"""Budget optimizer: most person-°C of cooling per rupee, one fix per cell, public land only.
Compared against two naive baselines so judges can see it actually beats simple spending."""

import numpy as np
import pandas as pd

from uhi import config
from uhi.scenarios import Engine


def all_candidates(engine: Engine, vulnerability: bool = True) -> pd.DataFrame:
    weights = engine.cells["pop"].to_numpy().copy()
    if vulnerability:
        weights *= engine.cells["site_weight"].to_numpy()
    frames = [engine.candidates(k, weights) for k in config.INTERVENTIONS]
    cand = pd.concat([f for f in frames if len(f)])
    cand["ratio"] = cand["benefit"] / cand["cost"]
    return cand


def greedy(cand: pd.DataFrame, budget: float) -> pd.DataFrame:
    """Best benefit-per-rupee first; one intervention per cell; skip what no longer fits."""
    ordered = cand.sort_values("ratio", ascending=False)
    ordered = ordered[~ordered.index.duplicated(keep="first")]  # best fix per cell
    fits = ordered["cost"].cumsum() <= budget
    chosen = ordered[fits]
    left = budget - chosen["cost"].sum()
    rest = ordered[~fits]
    extra = rest[rest["cost"] <= left]
    extra = extra[extra["cost"].cumsum() <= left]
    return pd.concat([chosen, extra])


def even_spread(cand: pd.DataFrame, cells: pd.DataFrame, budget: float, seed=0) -> pd.DataFrame:
    """Baseline: split the money equally across wards, random eligible fixes inside each ward."""
    one = cand.sample(frac=1, random_state=seed)
    one = one[~one.index.duplicated(keep="first")]
    one = one.assign(ward_id=cells.loc[one.index, "ward_id"].to_numpy())
    # round-robin: each ward in turn gets its next random fix until the money runs out
    one["turn"] = one.groupby("ward_id").cumcount()
    rng = np.random.default_rng(seed)
    order = {w: i for i, w in enumerate(rng.permutation(one["ward_id"].unique()))}
    one["ward_order"] = one["ward_id"].map(order)
    one = one.sort_values(["turn", "ward_order"])
    return one[one["cost"].cumsum() <= budget].drop(columns=["turn", "ward_order"])


def trees_everywhere(cand: pd.DataFrame, budget: float, seed=0) -> pd.DataFrame:
    """Baseline: only street trees, placed wherever eligible (random order)."""
    t = cand[cand["intervention"] == "street_trees"].sample(frac=1, random_state=seed)
    t = t[~t.index.duplicated(keep="first")]
    return t[t["cost"].cumsum() <= budget]


def summarise(engine: Engine, selection: pd.DataFrame, label: str) -> dict:
    res = engine.evaluate(selection)
    mix = selection.groupby("intervention")["cost"].agg(["count", "sum"])
    return {
        "strategy": label,
        "cost_rs": res["cost"],
        "person_deg_cooling": -res["person_deg"],
        "people_cooled": res["people_cooled"],
        "mean_dt_cooled": res["mean_dt_cooled"],
        "cells": res["n_cells"],
        "mix": {config.INTERVENTIONS[k]["label"]: {"cells": int(r["count"]), "cost_rs": float(r["sum"])}
                for k, r in mix.iterrows()},
        "_dt": res["dt"],
    }


def budget_curve(cand: pd.DataFrame, cells, budgets_cr) -> list[dict]:
    """Estimated (sum of per-site effects) curve for the chart; presets use joint evaluation."""
    rows = []
    for b in budgets_cr:
        budget = b * config.CRORE
        rows.append({
            "budget_cr": b,
            "UHI plan": float(greedy(cand, budget)["benefit"].sum()),
            "Spread evenly": float(even_spread(cand, cells, budget)["benefit"].sum()),
            "Trees everywhere": float(trees_everywhere(cand, budget)["benefit"].sum()),
        })
    return rows
