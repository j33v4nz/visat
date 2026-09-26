"""Synthetic Kochi-like data in exactly the frozen-export format. ALWAYS labelled DEMO in the app.

Lets M2/M3/M4 build and test everything before the real Earth Engine export is ready.
"""

import numpy as np
import pandas as pd
from scipy.ndimage import distance_transform_edt, gaussian_filter

from uhi import config

RNG_SEED = 26


def _grid():
    lon0, lat0, lon1, lat1 = config.BBOX
    n_cols = round((lon1 - lon0) / config.CELL_DEG)
    n_rows = round((lat1 - lat0) / config.CELL_DEG)
    rows, cols = np.meshgrid(np.arange(n_rows), np.arange(n_cols), indexing="ij")
    lat = lat1 - (rows + 0.5) * config.CELL_DEG
    lon = lon0 + (cols + 0.5) * config.CELL_DEG
    return rows, cols, lat, lon


def _blob(lat, lon, clat, clon, radius_deg):
    return np.exp(-(((lat - clat) ** 2 + (lon - clon) ** 2) / (2 * radius_deg**2)))


def build(seed: int = RNG_SEED) -> dict:
    rng = np.random.default_rng(seed)
    rows, cols, lat, lon = _grid()
    shape = rows.shape

    # water: sea + backwaters west of a wavy shoreline, Vembanad arm to the south-east of the core
    shore = 76.262 + 0.010 * np.sin((lat - 9.9) * 40)
    water = (lon < shore).astype(float)
    water[(lon > 76.215) & (lon < 76.245) & (lat > 9.955) & (lat < 10.02)] = 0.0  # islands
    lake = _blob(lat, lon, 9.925, 76.300, 0.012) > 0.55
    water[lake] = 1.0
    water = np.clip(gaussian_filter(water, 1.0) + rng.normal(0, 0.03, shape), 0, 1)

    urban = (
        1.0 * _blob(lat, lon, 9.980, 76.285, 0.020)  # Ernakulam core
        + 0.8 * _blob(lat, lon, 10.015, 76.350, 0.014)  # Kakkanad / Infopark
        + 0.7 * _blob(lat, lon, 10.050, 76.315, 0.012)  # Kalamassery industrial
        + 0.6 * _blob(lat, lon, 10.025, 76.305, 0.010)  # Edappally
        + 0.5 * _blob(lat, lon, 9.965, 76.245, 0.008)  # Fort Kochi / Mattancherry
    )
    built = np.clip(urban * (1 - water) + rng.normal(0, 0.06, shape), 0, 1) * (1 - water)
    tree = np.clip((1 - built) * (1 - water) * 0.75 + rng.normal(0, 0.08, shape), 0, 1)
    tree *= 1 - water
    mangrove_zone = (distance_transform_edt(water < 0.5) < 3) & (water < 0.5)
    mangrove = np.where(mangrove_zone & (built < 0.3), rng.uniform(0.1, 0.6, shape), 0.0)
    mangrove += 0.6 * (_blob(lat, lon, 9.990, 76.274, 0.002) > 0.4)  # Mangalavanam
    mangrove = np.clip(mangrove, 0, 1) * (1 - water)
    grass_bare = np.clip(1 - built - tree - water - mangrove, 0, 1)

    elevation = np.clip((lon - 76.25) * 120 + rng.normal(0, 1.0, shape), 0, 25) * (1 - water)
    dist_water = distance_transform_edt(water < 0.5) * config.GRID_RESOLUTION_M
    building = built * rng.uniform(0.45, 0.7, shape)
    height = np.clip(built * 18 + rng.normal(0, 2, shape), 0, 60)
    pop = np.clip(built * 260 + tree * 15 + rng.normal(0, 10, shape), 0, None) * (1 - water)
    albedo = np.clip(0.14 + 0.05 * built - 0.02 * tree + rng.normal(0, 0.015, shape), 0.05, 0.35)
    albedo = np.where(water > 0.5, 0.06, albedo)
    ndvi = np.clip(0.12 + 0.65 * tree - 0.1 * built - 0.3 * water + rng.normal(0, 0.03, shape), -0.3, 0.9)
    ndbi = np.clip(-0.2 + 0.45 * built - 0.25 * tree - 0.3 * water, -0.6, 0.5)
    mndwi = np.clip(-0.4 + 0.9 * water + 0.1 * mangrove, -0.6, 0.8)
    road = np.clip(built * 0.25 + rng.normal(0, 0.02, shape), 0, 0.4)

    cells = pd.DataFrame(
        {
            "row": rows.ravel(), "col": cols.ravel(), "lat": lat.ravel(), "lon": lon.ravel(),
            "ndvi": ndvi.ravel(), "ndbi": ndbi.ravel(), "mndwi": mndwi.ravel(),
            "albedo": albedo.ravel(), "tree_frac": tree.ravel(), "built_frac": built.ravel(),
            "water_frac": water.ravel(), "mangrove_frac": mangrove.ravel(),
            "grass_bare_frac": grass_bare.ravel(), "building_frac": building.ravel(),
            "built_height": height.ravel(), "pop": pop.ravel(), "elevation": elevation.ravel(),
            "dist_water_m": dist_water.ravel(), "road_frac": road.ravel(),
        }
    )
    cells.insert(0, "cell_id", np.arange(len(cells)))
    n = len(cells)
    busy = cells["built_frac"].to_numpy() > 0.35
    cells["n_school"] = (rng.random(n) < 0.03 * busy).astype(int)
    cells["n_market"] = (rng.random(n) < 0.01 * busy).astype(int)
    cells["n_construction"] = (rng.random(n) < 0.015 * busy).astype(int)
    cells["n_hospital"] = (rng.random(n) < 0.005 * busy).astype(int)
    cells["n_harbour"] = ((cells["dist_water_m"] < 200) & (cells["lon"] < 76.27)
                          & (rng.random(n) < 0.05)).astype(int)
    cells["is_park"] = ((cells["tree_frac"] > 0.5) & (rng.random(n) < 0.05)).astype(int)
    canal_lat = [9.99, 10.02, 9.96]
    near_canal = np.zeros(n, bool)
    for clat in canal_lat:
        near_canal |= (np.abs(cells["lat"] - clat) < 0.0009) & (cells["lon"] > 76.27) & (cells["lon"] < 76.33)
    cells["canal_bank"] = (near_canal & (cells["water_frac"] < 0.5)).astype(int)
    cells["eco_anom"] = np.nan  # filled below after LST exists

    # ---- scenes (cells × scenes panel) with per-scene ERA5 atmosphere
    n_scenes = 16
    dates = pd.to_datetime(
        [f"{y}-{m:02d}-{d:02d}" for y, m, d in zip(
            rng.integers(2019, 2027, n_scenes), rng.integers(1, 5, n_scenes), rng.integers(1, 28, n_scenes)
        )]
    )
    meta = pd.DataFrame(
        {
            "scene_id": np.arange(n_scenes), "date": dates.strftime("%Y-%m-%d"),
            "t2m_c": rng.uniform(27.5, 33.5, n_scenes), "rh": rng.uniform(55, 82, n_scenes),
            "wind_ms": rng.uniform(1.0, 5.0, n_scenes), "ssrd_wm2": rng.uniform(600, 900, n_scenes),
        }
    )
    from uhi.features import add_focal_features

    focal = add_focal_features(cells)
    base = (
        24.0 + 7.5 * focal["built_frac"] + 3.0 * focal["built_frac_300"] - 3.5 * focal["tree_frac"]
        - 2.5 * focal["tree_frac_300"] - 5.0 * focal["water_frac"] - 2.0 * focal["water_frac_300"]
        - 2.0 * focal["mangrove_frac"] + 0.0004 * focal["dist_water_m"] - 0.05 * focal["elevation"]
        + 0.03 * focal["built_height"]
    ).to_numpy()
    panels = []
    for s in meta.itertuples():
        sw = (1 - cells["albedo"].to_numpy()) * s.ssrd_wm2
        lst = (base + 0.8 * (s.t2m_c - 30) + 0.012 * (sw - 650) - 0.35 * (s.wind_ms - 3)
               + rng.normal(0, 0.8, n))
        valid = rng.random(n) > rng.uniform(0.05, 0.3)
        panels.append(pd.DataFrame({"cell_id": cells["cell_id"][valid], "scene_id": s.scene_id,
                                    "lst_c": lst[valid]}))
    scenes = pd.concat(panels, ignore_index=True)

    lst_mean = scenes.groupby("cell_id")["lst_c"].mean().reindex(cells["cell_id"]).to_numpy()
    anom = lst_mean - np.nanmedian(lst_mean)
    cells["eco_anom"] = 1.1 * anom + rng.normal(0, 0.9, n)  # afternoon ECOSTRESS stand-in

    # ---- back-test: 2017 vs 2024 with real-looking change around Kakkanad / Kalamassery
    growth = np.clip(0.9 * _blob(lat, lon, 10.012, 76.355, 0.008).ravel()
                     + 0.6 * _blob(lat, lon, 10.055, 76.325, 0.006).ravel(), 0, 1)
    d_built = np.clip(growth * rng.uniform(0.2, 0.5, n), 0, None) * (cells["water_frac"] < 0.5)
    bt = pd.DataFrame({"cell_id": cells["cell_id"]})
    bt["built_2024"] = cells["built_frac"]
    bt["built_2017"] = np.clip(cells["built_frac"] - d_built, 0, 1)
    bt["tree_2024"] = cells["tree_frac"]
    bt["tree_2017"] = np.clip(cells["tree_frac"] + 0.8 * d_built, 0, 1)
    bt["water_2024"] = cells["water_frac"]
    bt["water_2017"] = cells["water_frac"]
    bt["ndvi_2024"] = cells["ndvi"]
    bt["ndvi_2017"] = np.clip(cells["ndvi"] + 0.5 * d_built, -0.3, 0.9)
    bt["albedo_2024"] = cells["albedo"]
    bt["albedo_2017"] = cells["albedo"] - 0.01 * d_built
    effect = 7.5 * d_built + 3.5 * 0.8 * d_built
    bt["lst_2024"] = anom + rng.normal(0, 0.6, n)
    bt["lst_2017"] = anom - effect + rng.normal(0, 0.6, n)

    return {"cells": cells, "scenes": scenes, "scenes_meta": meta, "backtest": bt,
            "cpcb": None, "wards": None, "source": "demo"}
