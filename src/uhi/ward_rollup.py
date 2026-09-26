"""Rebuild named ward views from frozen app cells when raw Earth Engine exports are unavailable.

This only changes ward IDs, summaries, map outlines, and Ward Card actions. Model outputs,
heat values, intervention placements, and citywide plan totals remain the frozen build's values.

    python -m uhi.ward_rollup
"""

import json
from datetime import datetime

import pandas as pd

from uhi import config, exposure
from uhi.live import IST


def ward_actions_from_picks(picks: list, cells: pd.DataFrame) -> dict:
    """Reassign the saved joint-plan picks to wards; saved per-pick °C is rounded to 0.01."""
    sel = pd.DataFrame(picks, columns=["lat", "lon", "fix", "dt", "cost"])
    coords = cells[["lat", "lon", "ward_id", "pop"]].copy()
    coords[["lat", "lon"]] = coords[["lat", "lon"]].round(5)
    sel = sel.merge(coords, on=["lat", "lon"], how="left", validate="many_to_one")
    if sel["ward_id"].isna().any():
        raise ValueError("Saved plan picks do not all match a frozen app cell")
    out = {}
    for ward_id, g in sel[sel["ward_id"] >= 0].groupby("ward_id"):
        rows = []
        for fix, gg in g.groupby("fix"):
            rows.append({"label": fix, "cells": len(gg),
                         "cost_rs": float(gg["cost"].sum()),
                         "dt": float(gg["dt"].mean()),
                         "person_deg": float(-(gg["dt"] * gg["pop"]).sum())})
        out[str(int(ward_id))] = sorted(rows, key=lambda r: -r["person_deg"])[:3]
    return out


def run() -> dict:
    app = config.APP
    cells = pd.read_parquet(app / "cells.parquet")
    osm = pd.read_parquet(config.FROZEN / "osm.parquet")
    geo = json.loads((config.RAW / "wards.geojson").read_text(encoding="utf-8"))
    metrics = json.loads((app / "metrics.json").read_text(encoding="utf-8"))
    manifest = json.loads((app / "manifest.json").read_text(encoding="utf-8"))
    plans = json.loads((app / "plans.json").read_text(encoding="utf-8"))
    if manifest["source"] != "frozen":
        raise ValueError("Ward rollup requires the real frozen app build")
    if len(geo["features"]) != 74:
        raise ValueError("Expected the corrected 74-ward Kochi GeoJSON")

    ward, info = exposure.assign_wards(cells, geo)
    if ward[ward >= 0].nunique() != 74:
        raise ValueError("Some Kochi wards have no matched 100 m cells; check coordinates")
    cells["ward_id"] = ward.to_numpy()
    full = cells.merge(osm, on="cell_id", how="left", validate="one_to_one", sort=False)
    counts = ["n_school", "n_market", "n_construction", "n_hospital", "n_harbour"]
    if full[counts].isna().any().any():
        raise ValueError("OSM counts are missing for some app cells")
    full["site_weight"] = 1 + 0.5 * full[counts].sum(axis=1).clip(0, 4)
    driver_cols = [c for c in cells if c in config.DRIVER_GROUPS]
    drivers = full[driver_cols].copy()
    wards = exposure.ward_summary(full.drop(columns=driver_cols), drivers, info["names"])
    if len(wards) != 74:
        raise ValueError("Ward summary did not produce 74 rows")

    for ward_id, feature in enumerate(geo["features"]):
        row = wards.loc[ward_id]
        feature["properties"].update({
            "ward_id": ward_id, "name": row["ward"],
            "heat_stress": float(row["heat_stress"]),
            "lst_anom": float(row["lst_anom"]),
            "people": float(row["people"]),
        })
    plans["presets"]["10"]["ward_actions"] = ward_actions_from_picks(
        plans["presets"]["10"]["picks"], cells)
    metrics["area_kind"] = "wards"
    manifest["ward_rollup_built_at"] = datetime.now(IST).isoformat(timespec="minutes")
    manifest["ward_rollup_method"] = "74 named wards from frozen app cells and OSM counts"

    cells.to_parquet(app / "cells.parquet", index=False)
    wards.reset_index().to_parquet(app / "wards.parquet", index=False)
    exposure.save_json(geo, app / "wards.geojson")
    exposure.save_json(plans, app / "plans.json")
    exposure.save_json(metrics, app / "metrics.json")
    exposure.save_json(manifest, app / "manifest.json")
    return {"wards": len(wards), "assigned_cells": int((ward >= 0).sum()),
            "assigned_people": round(float(wards["people"].sum()))}


if __name__ == "__main__":
    print(run())
