"""Proof screen: 2017→2024 back-test, ECOSTRESS afternoon agreement, CPCB station check."""

import re
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from visat import config
from visat.features import add_focal_features, heat_index_c
from visat.model import predict, with_atmos


def backtest(model, cells: pd.DataFrame, bt: pd.DataFrame, atmos: dict, min_change=0.1) -> dict:
    """Predict 2017→2024 ΔLST from land-cover change alone and compare with what was observed.

    Features for each year = today's features + that year's change measured with ONE consistent
    sensor pair (Landsat NDVI/albedo + Dynamic World fractions), so sensor differences cancel.
    Observed LST per year is normalised to its own city median, so weather differences cancel.
    """
    base = cells.sort_values("cell_id").reset_index(drop=True)
    b = bt.set_index("cell_id").reindex(base["cell_id"])
    years = {}
    for y in ("2017", "2024"):
        f = base.copy()
        f["built_frac"] = np.clip(base["built_frac"] + b[f"built_{y}"].to_numpy() - b["built_2024"].to_numpy(), 0, 1)
        f["tree_frac"] = np.clip(base["tree_frac"] + b[f"tree_{y}"].to_numpy() - b["tree_2024"].to_numpy(), 0, 1)
        f["water_frac"] = np.clip(base["water_frac"] + b[f"water_{y}"].to_numpy() - b["water_2024"].to_numpy(), 0, 1)
        f["ndvi"] = base["ndvi"] + b[f"ndvi_{y}"].to_numpy() - b["ndvi_2024"].to_numpy()
        f["albedo"] = base["albedo"] + b[f"albedo_{y}"].to_numpy() - b["albedo_2024"].to_numpy()
        ratio = np.where(base["built_frac"] > 0, f["built_frac"] / base["built_frac"].clip(lower=1e-6), 1.0)
        f["building_frac"] = np.clip(base["building_frac"] * ratio, 0, 1)
        years[y] = predict(model, with_atmos(add_focal_features(f), atmos))
    obs17 = b["lst_2017"] - b["lst_2017"].median()
    obs24 = b["lst_2024"] - b["lst_2024"].median()
    pred = years["2024"] - years["2017"]
    obs = (obs24 - obs17).to_numpy()
    changed = (((np.abs(b["built_2024"] - b["built_2017"]) > min_change)
                | (np.abs(b["tree_2024"] - b["tree_2017"]) > min_change)).to_numpy()
               & (base["water_frac"] <= 0.5).to_numpy() & np.isfinite(obs))
    p, o = pred[changed], obs[changed]
    if len(p) < 10:
        return {"n_changed_cells": len(p), "note": "Too few changed cells for a back-test."}
    slope = float(np.polyfit(p, o, 1)[0])
    rng = np.random.default_rng(0)
    pick = rng.choice(len(p), min(2000, len(p)), replace=False)
    return {
        "n_changed_cells": len(p),
        "pearson_r": float(pearsonr(p, o)[0]),
        "slope_obs_vs_pred": slope,
        "mae_c": float(np.mean(np.abs(p - o))),
        "bias_c": float(np.mean(p - o)),
        "mean_pred_c": float(p.mean()), "mean_obs_c": float(o.mean()),
        "points": [[round(float(a), 2), round(float(c), 2)] for a, c in zip(p[pick], o[pick])],
        "label": "Δ surface-°C 2017→2024 (Feb–Apr), each year normalised to its city median",
    }


def ecostress_agreement(cells: pd.DataFrame) -> dict | None:
    """Do the morning (Landsat) hotspots hold in the afternoon (ECOSTRESS 12:00–15:30)?"""
    if "eco_anom" not in cells or cells["eco_anom"].notna().sum() < 100:
        return None
    land = cells[(cells["water_frac"] <= 0.5) & cells["eco_anom"].notna()]
    rho = float(spearmanr(land["lst_anom"], land["eco_anom"]).statistic)
    top_l = land["lst_anom"] >= land["lst_anom"].quantile(0.9)
    top_e = land["eco_anom"] >= land["eco_anom"].quantile(0.9)
    wards = land[land["ward_id"] >= 0].groupby("ward_id")[["lst_anom", "eco_anom"]].mean()
    return {"spearman_cells": rho,
            "spearman_wards": float(spearmanr(wards["lst_anom"], wards["eco_anom"]).statistic),
            "top_decile_overlap_pct": float((top_l & top_e).sum() / top_l.sum() * 100),
            "n_cells": len(land)}


_DOY = re.compile(r"doy(\d{4})(\d{3})(\d{2})(\d{2})(\d{2})")


def ecostress_from_appeears(folder: Path, cells: pd.DataFrame) -> pd.Series | None:
    """Afternoon ECOSTRESS anomaly per cell from AppEEARS GeoTIFFs (LST layer, kelvin)."""
    files = sorted(folder.glob("*LST_doy*.tif"))
    if not files:
        return None
    import rasterio
    from rasterio.warp import transform

    # IST wall-clock window taken straight from config — deliberately naive, so %z is not applicable
    lo, hi = (datetime.strptime(t, "%H:%M").time() for t in config.ECOSTRESS_LOCAL_WINDOW)  # noqa: DTZ007
    stacks = []
    for f in files:
        m = _DOY.search(f.name)
        if not m:
            continue
        y, doy, hh, mm, ss = map(int, m.groups())
        # naive UTC built from the filename's day-of-year/hms, then shifted to IST below
        utc = datetime(y, 1, 1) + timedelta(days=doy - 1, hours=hh, minutes=mm, seconds=ss)  # noqa: DTZ001
        ist = (utc + timedelta(hours=5, minutes=30)).time()
        if not (lo <= ist <= hi):
            continue
        with rasterio.open(f) as src:
            xs, ys = transform("EPSG:4326", src.crs, cells["lon"].tolist(), cells["lat"].tolist())
            vals = np.array([v[0] for v in src.sample(zip(xs, ys))], float)
            nodata = src.nodata
        vals[(vals <= 200) | (vals > 350) | (vals == nodata)] = np.nan
        vals -= 273.15
        if np.isfinite(vals).mean() > 0.3:
            stacks.append(vals - np.nanmedian(vals))
    if not stacks:
        return None
    return pd.Series(np.nanmedian(np.vstack(stacks), axis=0), index=cells.index)


def cpcb_check(folder: Path, meta: pd.DataFrame) -> dict | None:
    """Compare station heat index (≈10–11 AM on scene days) with ERA5 heat index used by the model."""
    files = list(folder.glob("*.csv")) + list(folder.glob("*.xlsx"))
    if not files:
        return None
    frames = []
    for f in files:
        df = pd.read_csv(f) if f.suffix == ".csv" else pd.read_excel(f)
        cols = {c.lower().strip(): c for c in df.columns}
        tcol = next((cols[c] for c in cols if c in ("at", "temp", "temperature", "at (degree c)")
                     or c.startswith("at ")), None)
        rcol = next((cols[c] for c in cols if c in ("rh", "rh (%)") or c.startswith("rh")), None)
        dcol = next((cols[c] for c in cols if "date" in c or "time" in c or "from" in c), None)
        if not (tcol and rcol and dcol):
            continue
        d = pd.DataFrame({"when": pd.to_datetime(df[dcol], errors="coerce", dayfirst=True),
                          "t": pd.to_numeric(df[tcol], errors="coerce"),
                          "rh": pd.to_numeric(df[rcol], errors="coerce"), "station": f.stem})
        frames.append(d.dropna())
    if not frames:
        return None
    st = pd.concat(frames)
    st = st[st["when"].dt.hour.isin([10, 11])]
    st["date"] = st["when"].dt.strftime("%Y-%m-%d")
    daily = st.groupby("date")[["t", "rh"]].mean().rename(columns={"t": "t_station", "rh": "rh_station"})
    m = meta.set_index("date").join(daily, how="inner")
    if len(m) < 3:
        return {"n_days": len(m), "note": "Too few scene days overlap station data."}
    hi_station = heat_index_c(m["t_station"], m["rh_station"])
    hi_era5 = heat_index_c(m["t2m_c"], m["rh"])
    return {"n_days": len(m), "stations": sorted(st["station"].unique().tolist()),
            "mae_heat_index_c": float(np.mean(np.abs(hi_station - hi_era5))),
            "bias_c": float(np.mean(hi_era5 - hi_station))}
