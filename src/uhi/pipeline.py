"""Build every app artifact into data/app/ (tracked in git, read by Streamlit Cloud).

    uv run python -m uhi.pipeline --source demo      # synthetic, labelled DEMO
    uv run python -m uhi.pipeline --source frozen    # real Earth Engine / OSM export
"""

import argparse
import time
from datetime import datetime

import numpy as np
from PIL import Image

from uhi import config, exposure, heat_neutral, live, model, news, optimize, validation
from uhi.features import add_focal_features, grid_array
from uhi.scenarios import Engine, validity_matrix

INFERNO = [(0, 0, 4), (40, 11, 84), (101, 21, 110), (159, 42, 99), (212, 72, 66), (245, 125, 21),
           (250, 193, 39), (252, 255, 164)]


def load(source: str) -> dict:
    if source == "demo":
        from uhi import demo_data
        return demo_data.build()
    from uhi import frozen
    return frozen.load()


def colorize(values: np.ndarray, mask: np.ndarray, lo: float, hi: float) -> Image.Image:
    t = np.clip((values - lo) / (hi - lo), 0, 1)
    pos = t * (len(INFERNO) - 1)
    i0 = np.floor(pos).astype(int).clip(0, len(INFERNO) - 2)
    frac = (pos - i0)[..., None]
    pal = np.array(INFERNO, float)
    rgb = pal[i0] * (1 - frac) + pal[i0 + 1] * frac
    alpha = np.where(mask, 200, 0)[..., None]
    return Image.fromarray(np.concatenate([rgb, alpha], axis=-1).astype(np.uint8), "RGBA")


def physics_check(engine: Engine, n=2000, seed=0) -> dict:
    """Cool-roof ΔT: model (via its learned albedo response) vs textbook energy balance."""
    c = engine.cells
    idx = c.index[c["building_frac"] > 0.2].to_numpy()
    if len(idx) == 0:
        return {}
    idx = np.random.default_rng(seed).choice(idx, min(n, len(idx)), replace=False)
    spec = config.INTERVENTIONS["cool_roofs"]
    area = c.loc[idx, "building_frac"].to_numpy() * spec["coverage"]
    frame = model.with_atmos(c.loc[idx], engine.atmos)
    frame["albedo"] = frame["albedo"] + spec["delta_albedo"] * area
    frame = model.with_atmos(frame, engine.atmos)
    dt_model = model.predict(engine.model, frame) - engine.base[idx]
    dt_formula, _ = engine.formula_delta(idx, "cool_roofs")
    albedo_built_r = float(c["albedo"].corr(c["built_frac"]))
    gap_note = (
        f"Energy balance: ΔT ≈ Δα × S / h (S=750 W/m², h=25 W/m²K) × roof share. In this city, albedo and "
        f"built-up density are correlated (r={albedo_built_r:.2f} here) — darker roofs coincide with denser "
        f"building, so the model already explains most warming through built-up features and has little "
        f"signal left for albedo alone. The physics formula is the more trustworthy number for a single "
        f"roof; the model's plan-level total reflects this conservatism."
        if abs(albedo_built_r) > 0.4 else
        "Energy balance: ΔT ≈ Δα × S / h (S=750 W/m², h=25 W/m²K) × roof share."
    )
    return {"median_model_c": float(np.median(dt_model)), "median_formula_c": float(np.median(dt_formula)),
            "ratio_model_to_formula": float(np.median(dt_model) / np.median(dt_formula)),
            "n_cells": len(idx), "albedo_built_frac_corr": albedo_built_r, "note": gap_note}


def ward_actions(engine, selection, dt, cells) -> dict:
    sel = selection.assign(ward_id=cells.loc[selection.index, "ward_id"].to_numpy(),
                           dt=dt[selection.index], pop=cells.loc[selection.index, "pop"].to_numpy())
    out = {}
    for w, g in sel.groupby("ward_id"):
        rows = []
        for k, gg in g.groupby("intervention"):
            rows.append({"label": config.INTERVENTIONS[k]["label"], "cells": len(gg),
                         "cost_rs": float(gg["cost"].sum()), "dt": float(gg["dt"].mean()),
                         "person_deg": float(-(gg["dt"] * gg["pop"]).sum())})
        out[int(w)] = sorted(rows, key=lambda r: -r["person_deg"])[:3]
    return out


def run(source: str) -> dict:
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.1f}s] {m}", flush=True)
    config.APP.mkdir(parents=True, exist_ok=True)
    d = load(source)
    cells, scenes, meta = d["cells"], d["scenes"], d["scenes_meta"]
    log(f"loaded {source}: {len(cells)} cells, {meta['scene_id'].nunique()} scenes")

    focal = add_focal_features(cells)
    panel = model.build_panel(focal, scenes, meta)
    fitted = model.fit(panel)
    atmos = model.typical_atmos(meta)
    log("model trained")
    cv = model.cross_validate(panel)
    sens = model.atmospheric_sensitivity(fitted, panel, meta)
    log("validation done")

    ward, winfo = exposure.assign_wards(cells, d.get("wards"))
    cells = cells.assign(ward_id=ward.to_numpy())
    anom = exposure.composite_anomaly(scenes, cells)
    season_hi = exposure.season_heat_index(meta)
    cells = exposure.heat_stress(cells, anom, season_hi)
    engine = Engine(fitted, cells, atmos)
    drivers = model.driver_contributions(fitted, model.with_atmos(engine.cells, atmos))
    drivers = drivers.sub(drivers.mean())  # relative to the city average cell
    cells = engine.cells
    wards = exposure.ward_summary(cells, drivers, winfo["names"])
    log(f"heat stress map + {len(wards)} {winfo['kind']}")

    vm = validity_matrix(engine)
    cand = optimize.all_candidates(engine)
    plans = {"presets": {}, "curve": optimize.budget_curve(cand, cells, [0.5, 1, 2, 5, 10, 20, 35, 50])}
    for b in config.BUDGET_PRESETS_CR:
        budget = b * config.CRORE
        ours_sel = optimize.greedy(cand, budget)
        ours = optimize.summarise(engine, ours_sel, "UHI plan")
        base = [optimize.summarise(engine, optimize.even_spread(cand, cells, budget), "Spread evenly"),
                optimize.summarise(engine, optimize.trees_everywhere(cand, budget), "Trees everywhere")]
        dt = ours.pop("_dt")
        for s in base:
            s.pop("_dt")
        picks = [[round(float(cells.at[i, "lat"]), 5), round(float(cells.at[i, "lon"]), 5),
                  config.INTERVENTIONS[k]["label"], round(float(dt[i]), 2), float(c)]
                 for i, k, c in zip(ours_sel.index, ours_sel["intervention"], ours_sel["cost"])]
        cooled = np.where(dt <= -0.05)[0]
        plans["presets"][str(b)] = {
            "ours": ours, "baselines": base, "picks": picks,
            "cooling": [[round(float(cells.at[i, "lat"]), 5), round(float(cells.at[i, "lon"]), 5),
                         round(float(dt[i]), 2)] for i in cooled],
            "ward_actions": ward_actions(engine, ours_sel, dt, cells) if b == 10 else {},
        }
        log(f"plan ₹{b} cr: {ours['people_cooled']:,.0f} people cooled")

    sites = heat_neutral.select_sites(cells)
    hn = {"sites": sites, "results": {}}
    for s in sites:
        for use in config.PROJECT_USES:
            hn["results"][f"{s['site']}|{use}"] = heat_neutral.check(engine, s, use, cand)
    log(f"heat-neutral: {len(hn['results'])} site × use results")

    bt = validation.backtest(fitted, cells, d["backtest"], atmos)
    eco = validation.ecostress_agreement(cells)
    cpcb = d.get("cpcb")
    phys = physics_check(engine)
    log("proof metrics done")

    land = cells["water_frac"] <= 0.5
    arr = grid_array(cells, "lst_anom")
    mask = grid_array(cells.assign(m=land.astype(float)), "m") > 0
    lo, hi = np.percentile(cells.loc[land, "lst_anom"], [2, 98])
    colorize(arr, mask, lo, hi).save(config.APP / "heat.png")
    lon0, _lat0, _lon1, lat1 = config.BBOX
    n_rows, n_cols = arr.shape
    bounds = [lon0, lat1 - n_rows * config.CELL_DEG, lon0 + n_cols * config.CELL_DEG, lat1]

    keep = ["cell_id", "row", "col", "lat", "lon", "lst_anom", "heat_stress", "hotspot", "pop",
            "ward_id", "water_frac", "eco_anom"]
    app_cells = cells[[k for k in keep if k in cells]].join(drivers.round(3))
    app_cells.to_parquet(config.APP / "cells.parquet", index=False)

    geo = winfo["geojson"] or exposure.zones_geojson(cells, cells["ward_id"], winfo["names"])
    wmap = wards.reset_index().set_index("ward_id")
    for f in geo["features"]:
        wid = f["properties"].get("ward_id")
        if wid is None:
            wid = geo["features"].index(f)
            f["properties"]["ward_id"] = wid
        if wid in wmap.index:
            r = wmap.loc[wid]
            f["properties"].update({"name": r["ward"], "heat_stress": float(r["heat_stress"]),
                                    "lst_anom": float(r["lst_anom"]), "people": float(r["people"])})
    exposure.save_json(geo, config.APP / "wards.geojson")
    wards.reset_index().to_parquet(config.APP / "wards.parquet", index=False)

    exposure.save_json(plans, config.APP / "plans.json")
    exposure.save_json(hn, config.APP / "heat_neutral.json")
    exposure.save_json({
        "cv": cv, "atmospheric": sens, "validity_matrix": vm, "backtest": bt, "ecostress": eco,
        "cpcb": cpcb, "physics_check": phys, "season_heat_index_c": season_hi,
        "typical_atmosphere": atmos, "heat_png_bounds": bounds, "heat_png_range": [lo, hi],
        "n_scenes": int(meta["scene_id"].nunique()), "scene_dates": meta["date"].tolist(),
        "area_kind": winfo["kind"],
    }, config.APP / "metrics.json")

    snap = live.get(config.DATA / "live_cache.json", config.APP / "live_snapshot.json")
    if snap.get("status") == "live":
        exposure.save_json(snap, config.APP / "live_snapshot.json")
    now = datetime.now(live.IST).isoformat(timespec="minutes")
    try:
        items = news.fetch()
        exposure.save_json({"items": items, "fetched_at": now}, config.APP / "news_snapshot.json")
    except Exception as exc:  # noqa: BLE001 — news is best-effort, the rest of the build must stand
        log(f"news snapshot skipped: {exc}")
    exposure.save_json({"source": source, "built_at": now,
                        "label_surface": config.LABEL_SURFACE, "label_live": config.LABEL_LIVE},
                       config.APP / "manifest.json")
    log("wrote data/app/")
    return {"cv": cv, "backtest": {k: v for k, v in bt.items() if k != "points"}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["demo", "frozen"], default="demo")
    print(run(ap.parse_args().source))
