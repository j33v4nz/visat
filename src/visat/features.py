"""Shared feature maths: heat index, humidity, neighbourhood (focal) features, physics feature."""

import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter

from visat import config


def relative_humidity(t_c, td_c):
    """RH (%) from air and dewpoint temperature (Magnus formula)."""
    t_c, td_c = np.asarray(t_c, float), np.asarray(td_c, float)
    return 100 * np.exp(17.625 * td_c / (243.04 + td_c)) / np.exp(17.625 * t_c / (243.04 + t_c))


def heat_index_c(t_c, rh):
    """NWS heat index (Rothfusz regression with adjustments), °C in, °C out."""
    t_c, rh = np.asarray(t_c, float), np.asarray(rh, float)
    t = t_c * 9 / 5 + 32
    simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094)
    hi = (
        -42.379 + 2.04901523 * t + 10.14333127 * rh - 0.22475541 * t * rh
        - 6.83783e-3 * t**2 - 5.481717e-2 * rh**2 + 1.22874e-3 * t**2 * rh
        + 8.5282e-4 * t * rh**2 - 1.99e-6 * t**2 * rh**2
    )
    low_rh = (rh < 13) & (t >= 80) & (t <= 112)
    hi = np.where(low_rh, hi - ((13 - rh) / 4) * np.sqrt(np.clip((17 - np.abs(t - 95)) / 17, 0, None)), hi)
    high_rh = (rh > 85) & (t >= 80) & (t <= 87)
    hi = np.where(high_rh, hi + ((rh - 85) / 10) * ((87 - t) / 5), hi)
    hi = np.where((simple + t) / 2 < 80, simple, hi)
    return (hi - 32) * 5 / 9


def heat_band(hi_c):
    for name, lo, hi in config.HEAT_INDEX_BANDS_C:
        if lo <= hi_c < hi:
            return name
    return "Below caution"


def grid_array(cells: pd.DataFrame, column: str, fill=0.0) -> np.ndarray:
    n_rows, n_cols = int(cells["row"].max()) + 1, int(cells["col"].max()) + 1
    arr = np.full((n_rows, n_cols), fill, dtype=float)
    arr[cells["row"].to_numpy(), cells["col"].to_numpy()] = cells[column].to_numpy(float)
    return arr


def add_focal_features(cells: pd.DataFrame) -> pd.DataFrame:
    """Neighbourhood means (≈300 m / 500 m) so cooling can spill over to nearby cells."""
    out = cells.copy()
    for base in ("tree_frac", "built_frac", "water_frac"):
        arr = grid_array(cells, base)
        for tag, size in config.FOCAL_SIZES.items():
            focal = uniform_filter(arr, size=size, mode="nearest")
            out[f"{base}_{tag}"] = focal[cells["row"].to_numpy(), cells["col"].to_numpy()]
    return out


def add_physics_feature(panel: pd.DataFrame) -> pd.DataFrame:
    """Energy-balance interaction: shortwave actually absorbed by the surface (W/m²)."""
    out = panel.copy()
    out["absorbed_sw"] = (1 - out["albedo"]) * out["ssrd_wm2"]
    return out


def model_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[list(config.FEATURES)].astype(float)


def block_ids(cells: pd.DataFrame) -> np.ndarray:
    b = config.BLOCK_CELLS
    return (cells["row"].to_numpy() // b) * 10_000 + cells["col"].to_numpy() // b
