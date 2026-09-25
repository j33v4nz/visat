"""Heat-Neutral Development Check — a screening tool and policy proposal, never an approval.

For a pre-drawn site and a proposed use: reverse analog transition (green → built) using donors
matched to the site's context, joint re-prediction of the neighbourhood, then the cheapest offset
(trees nearby + cool/green roofs on the project) that brings people-weighted surface-°C back to 0.
"""

import numpy as np
import pandas as pd

from visat import config
from visat.scenarios import Engine


def select_sites(cells: pd.DataFrame) -> list[dict]:
    """Greenest open 3×3 block near each anchor (a stand-in for real proposed plots)."""
    k = config.SITE_BLOCK
    grid = cells.set_index(["row", "col"])
    sites, used = [], set()
    for name, (lat, lon) in config.SITE_ANCHORS.items():
        near = cells[(abs(cells["lat"] - lat) < 0.012) & (abs(cells["lon"] - lon) < 0.012)]
        best, best_score = None, -np.inf
        for r, c in near[["row", "col"]].to_numpy()[::2]:
            keys = [(r + i, c + j) for i in range(k) for j in range(k)]
            if any(key not in grid.index for key in keys) or used & set(keys):
                continue
            blk = grid.loc[keys]
            if blk["water_frac"].max() > 0.2:
                continue
            open_bonus = 1.0 if blk["built_frac"].mean() <= 0.25 else 0.0  # prefer truly open land
            score = (open_bonus + (blk["tree_frac"] + blk["grass_bare_frac"]).mean()
                     - blk["built_frac"].mean())
            if score > best_score:
                best, best_score = keys, score
        if best is None:
            continue
        used |= set(best)
        blk = grid.loc[best]
        half = config.CELL_DEG / 2
        lon0, lon1 = blk["lon"].min() - half, blk["lon"].max() + half
        lat0, lat1 = blk["lat"].min() - half, blk["lat"].max() + half
        sites.append({"site": name, "cell_ids": blk["cell_id"].astype(int).tolist(),
                      "center": [float(blk["lat"].mean()), float(blk["lon"].mean())],
                      "polygon": [[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]})
    return sites


def _use_donors(cells: pd.DataFrame, use: str) -> pd.Series:
    spec = config.PROJECT_USES[use]
    m = cells["built_frac"] >= spec["built_min"]
    if "height_min" in spec:
        m &= cells["built_height"] >= spec["height_min"]
    if "height_max" in spec:
        m &= cells["built_height"] <= spec["height_max"]
    if m.sum() < 30:  # relax if the city has too few examples
        m = cells["built_frac"] >= spec["built_min"] - 0.2
    return m & (cells["water_frac"] < 0.3)


def check(engine: Engine, site: dict, use: str, candidates: pd.DataFrame) -> dict:
    cells = engine.cells
    site_idx = cells.index[cells["cell_id"].isin(site["cell_ids"])].to_numpy()
    target = engine._knn_target(site_idx, _use_donors(cells, use))
    developed, _ = engine.analog_transition(site_idx, "street_trees", intensity=1.0,
                                            cooling_only=False, target=target)
    dt_dev = engine.joint(overrides=developed)

    rows, cols = cells.loc[site_idx, "row"], cells.loc[site_idx, "col"]
    n = config.NEIGHBOURHOOD_CELLS
    hood = ((cells["row"].between(rows.min() - n, rows.max() + n))
            & (cells["col"].between(cols.min() - n, cols.max() + n))).to_numpy()
    pop = cells["pop"].to_numpy()
    affected = hood & (dt_dev >= 0.05)
    people = float(pop[affected].sum())
    person_deg = float((dt_dev[hood] * pop[hood]).sum())
    mean_dt = person_deg / people if people else 0.0

    # offset candidates: fixes within ~1 km (not on the site) + cool/green roofs on the new project
    far = 2 * n
    zone = ((cells["row"].between(rows.min() - far, rows.max() + far))
            & (cells["col"].between(cols.min() - far, cols.max() + far)))
    nearby = candidates[zone.loc[candidates.index].to_numpy() & ~candidates.index.isin(site_idx)]
    roof_rows = []
    for key in ("cool_roofs", "green_roofs"):
        dt, cost = engine.formula_delta(site_idx, key, building_frac=developed["building_frac"])
        roof_rows.append(pd.DataFrame({"cell_id": cells.loc[site_idx, "cell_id"].to_numpy(),
                                       "intervention": key, "method": "formula", "own_dt": dt,
                                       "cost": cost, "benefit": -dt * pop[site_idx],
                                       "within_support": True}, index=site_idx))
    pool = pd.concat([nearby, *roof_rows])
    pool = pool[pool["cost"] > 0]
    pool["ratio"] = pool["benefit"] / pool["cost"]

    ordered = pool.sort_values("ratio", ascending=False)
    ordered = ordered[~ordered.index.duplicated(keep="first")]
    est = ordered["benefit"].cumsum().to_numpy()
    chosen, net, factor = ordered.iloc[:0], person_deg, 1.0
    for _ in range(12):  # grow the offset until the JOINT re-prediction is heat-neutral
        if net <= 0:
            break
        k = min(len(ordered), int(np.searchsorted(est, person_deg * factor)) + 1)
        chosen = ordered.iloc[:k]
        overrides = [developed]
        formula = []
        for key, grp in chosen.groupby("intervention"):
            idx = grp.index.to_numpy()
            if config.INTERVENTIONS[key]["method"] == "formula":
                bf = developed["building_frac"].reindex(idx).fillna(cells.loc[idx, "building_frac"])
                d, _c = engine.formula_delta(idx, key, building_frac=bf)
                formula.append(pd.Series(d, index=idx))
            else:
                overrides.append(pd.DataFrame(list(grp["new_lc"]), index=idx))
        ov = pd.concat(overrides)
        ov = ov[~ov.index.duplicated(keep="first")]
        fd = pd.concat(formula).groupby(level=0).sum() if formula else None
        dt_all = engine.joint(overrides=ov, formula_dt=fd)
        net = float((dt_all[hood] * pop[hood]).sum())
        factor *= 1.3
        if k == len(ordered):
            break

    mix = chosen.groupby("intervention")["cost"].agg(["count", "sum"])
    trees = int(mix.loc["street_trees", "count"] * 30) if "street_trees" in mix.index else 0
    return {
        "site": site["site"], "use": config.PROJECT_USES[use]["label"],
        "before": {"mean_dt_c": round(mean_dt, 2), "people": round(people),
                   "person_deg": round(person_deg, 1)},
        "after": {"net_person_deg": round(net, 1),
                  "mean_dt_c": round(net / people, 2) if people else 0.0,
                  "heat_neutral": bool(net <= 0)},
        "offset_cost_rs": float(chosen["cost"].sum()),
        "offset_mix": {config.INTERVENTIONS[k]["label"]: {"cells": int(r["count"]),
                                                          "cost_rs": float(r["sum"])}
                       for k, r in mix.iterrows()},
        "street_trees": trees,
        "heat_cells": [[float(cells.at[i, "lat"]), float(cells.at[i, "lon"]), round(float(dt_dev[i]), 2)]
                       for i in np.where(hood & (dt_dev >= 0.05))[0]],
        "offset_cells": [[float(cells.at[i, "lat"]), float(cells.at[i, "lon"]),
                          config.INTERVENTIONS[k]["label"]]
                         for i, k in zip(chosen.index, chosen["intervention"])],
        "policy": config.POLICY_HOOKS,
        "label": "surface-°C (morning), people-weighted, within ~500 m",
    }
