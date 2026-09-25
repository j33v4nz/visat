"""Heat Stress Map (PS1 Objective 1): LST rank (where) × heat index (when) × population (who)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from visat import config
from visat.features import heat_band, heat_index_c


def composite_anomaly(scenes: pd.DataFrame, cells: pd.DataFrame) -> pd.Series:
    """Median over scenes of each scene's anomaly from its own city median (removes weather)."""
    s = scenes.copy()
    s["anom"] = s["lst_c"] - s.groupby("scene_id")["lst_c"].transform("median")
    return s.groupby("cell_id")["anom"].median().reindex(cells["cell_id"]).fillna(0.0)


def season_heat_index(meta: pd.DataFrame) -> float:
    return float(np.median(heat_index_c(meta["t2m_c"], meta["rh"])))


def assign_wards(cells: pd.DataFrame, wards_geojson: dict | None) -> tuple[pd.Series, dict]:
    """Ward id per cell from the ward GeoJSON; falls back to labelled 1 km zones."""
    if wards_geojson:
        from shapely import points
        from shapely.geometry import shape
        from shapely.strtree import STRtree

        feats = wards_geojson["features"]
        geoms = [shape(f["geometry"]) for f in feats]
        tree = STRtree(geoms)
        pts = points(cells["lon"].to_numpy(), cells["lat"].to_numpy())
        pt_idx, geom_idx = tree.query(pts, predicate="within")
        ward = np.full(len(cells), -1)
        ward[pt_idx] = geom_idx
        names = {}
        for i, f in enumerate(feats):
            p = f.get("properties", {})
            # "ward_lgd_name" is what BharatLAS's actual Kochi wards.geojson uses (verified
            # against the real downloaded file) — without it every real ward silently falls
            # back to "Ward N" and the genuine LGD ward names never reach the Ward Card.
            names[i] = str(p.get("ward_lgd_name") or p.get("ward_name") or p.get("name")
                           or p.get("Ward_Name") or p.get("WARD_NAME")
                           or f"Ward {p.get('ward_no', i + 1)}")
        return pd.Series(ward, index=cells.index), {"kind": "wards", "names": names,
                                                    "geojson": wards_geojson}
    zr, zc = cells["row"] // 10, cells["col"] // 10
    zone = zr * 1000 + zc
    names = {int(z): f"Zone {int(z) // 1000}-{int(z) % 1000}" for z in np.unique(zone)}
    return zone, {"kind": "zones", "names": names, "geojson": None}


def zones_geojson(cells: pd.DataFrame, ward: pd.Series, names: dict) -> dict:
    feats = []
    half = config.CELL_DEG / 2
    for z, g in cells.groupby(ward):
        if z < 0:
            continue
        lon0, lon1 = g["lon"].min() - half, g["lon"].max() + half
        lat0, lat1 = g["lat"].min() - half, g["lat"].max() + half
        feats.append({"type": "Feature", "properties": {"ward_id": int(z), "name": names[int(z)]},
                      "geometry": {"type": "Polygon", "coordinates": [[
                          [lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]]}})
    return {"type": "FeatureCollection", "features": feats}


def heat_stress(cells: pd.DataFrame, anom: pd.Series, season_hi: float) -> pd.DataFrame:
    out = cells.copy()
    out["lst_anom"] = anom.to_numpy()
    land = out["water_frac"] <= 0.5
    out["lst_rank"] = 0.0
    out.loc[land, "lst_rank"] = out.loc[land, "lst_anom"].rank(pct=True)
    hi_factor = max(season_hi, 27.0) / 27.0  # 1.0 at the "Caution" threshold
    pop_norm = out["pop"] / max(out["pop"].quantile(0.99), 1.0)
    out["heat_stress"] = out["lst_rank"] * hi_factor * pop_norm.clip(0, 1)
    thresh = out.loc[land & (out["pop"] > 0), "heat_stress"].quantile(0.9)
    out["hotspot"] = (out["heat_stress"] >= thresh) & land & (out["pop"] > 0)
    out["site_weight"] = 1 + 0.5 * out[["n_school", "n_market", "n_construction", "n_hospital",
                                        "n_harbour"]].sum(axis=1).clip(0, 4)
    return out


def ward_summary(cells: pd.DataFrame, drivers: pd.DataFrame, names: dict) -> pd.DataFrame:
    df = cells[cells["ward_id"] >= 0].join(drivers)
    w = df["pop"].clip(lower=1e-6)

    def agg(g):
        ww = w.loc[g.index]
        row = {
            "ward": names[int(g.name)],
            "people": float(g["pop"].sum()),
            "lst_anom": float(np.average(g["lst_anom"], weights=ww)),
            "people_in_hotspots": float(g.loc[g["hotspot"], "pop"].sum()),
            "heat_stress": float(np.average(g["heat_stress"], weights=ww)),
            "schools": int(g["n_school"].sum()), "markets": int(g["n_market"].sum()),
            "construction_sites": int(g["n_construction"].sum()),
            "hospitals": int(g["n_hospital"].sum()), "harbours": int(g["n_harbour"].sum()),
            "exposure_weight": float((g["heat_stress"] * g["site_weight"] * g["pop"]).sum()),
        }
        for grp in drivers.columns:
            row[f"drv::{grp}"] = float(np.average(g[grp], weights=ww))
        return pd.Series(row)

    out = df.groupby("ward_id").apply(agg, include_groups=False)
    out.index.name = "ward_id"
    return out.sort_values("heat_stress", ascending=False)


def act_today(wards: pd.DataFrame, peak_hi_c: float, top: int = 5) -> dict:
    """'Act today' line: wards ranked by exposure × today's forecast peak heat index."""
    band = heat_band(peak_hi_c)
    ranked = wards.assign(score=wards["exposure_weight"] * max(peak_hi_c, 1.0)).nlargest(top, "score")
    return {"peak_heat_index_c": round(float(peak_hi_c), 1), "band": band,
            "wards": ranked["ward"].tolist(), "advice": config.ACT_TODAY_ADVICE}


def save_json(obj, path: Path):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
