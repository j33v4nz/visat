"""Earth Engine export → data/frozen/*.parquet (M1, hours 0–4). Run once, then freeze.

    uv sync --extra pipeline
    uv run earthengine authenticate            # once per laptop
    uv run python -m uhi.gee_export --project <your-gee-cloud-project>

Writes cells.parquet (static features), scenes.parquet (cell × scene LST), scenes_meta.parquet
(per-scene ERA5 at overpass), backtest.parquet (2017 vs 2024, one consistent sensor pair).
"""

import argparse
import time

import numpy as np
import pandas as pd
from scipy.ndimage import distance_transform_edt

from uhi import config

ee = None
NODATA = -9999.0


def _init(project: str):
    global ee
    import ee as _ee

    ee = _ee
    ee.Initialize(project=project)


def grid_shape():
    lon0, lat0, lon1, lat1 = config.BBOX
    return round((lat1 - lat0) / config.CELL_DEG), round((lon1 - lon0) / config.CELL_DEG)


def _transform():
    lon0, _, _, lat1 = config.BBOX
    return [config.CELL_DEG, 0, lon0, 0, -config.CELL_DEG, lat1]


def _aoi():
    return ee.Geometry.Rectangle(list(config.BBOX))


TILE_ROWS = 15  # 30 rows still overflows EE's synchronous memory limit over the dense urban core


def _pixels_request(image, n_cols, row_start, height, lon0, lat1):
    return {
        "expression": image,
        "fileFormat": "NUMPY_NDARRAY",
        "grid": {
            "dimensions": {"width": n_cols, "height": height},
            "affineTransform": {"scaleX": config.CELL_DEG, "shearX": 0, "translateX": lon0,
                                "shearY": 0, "scaleY": -config.CELL_DEG,
                                "translateY": lat1 - row_start * config.CELL_DEG},
            "crsCode": "EPSG:4326",
        },
    }


def pixels(image, tile_rows: int = TILE_ROWS) -> np.ndarray:
    """Pull an image onto the exact 100 m grid, tiled by rows so each request stays small enough
    for Earth Engine's synchronous computePixels memory limit (this matters most for composites
    that need reduceResolution, e.g. Sentinel-2/WorldCover/Dynamic World at their native 10 m)."""
    n_rows, n_cols = grid_shape()
    lon0, _, _, lat1 = config.BBOX
    img = image.unmask(NODATA)
    tiles = []
    for start in range(0, n_rows, tile_rows):
        height = min(tile_rows, n_rows - start)
        req = _pixels_request(img, n_cols, start, height, lon0, lat1)
        for attempt in range(4):
            try:
                tiles.append(ee.data.computePixels(req))
                break
            except Exception as e:
                is_memory = "memory limit" in str(e).lower()
                if attempt == 3 or (is_memory and tile_rows <= 2):
                    raise
                if is_memory:  # halve the tile size once, then keep retrying at that size
                    return pixels(image, tile_rows=max(2, tile_rows // 2))
                time.sleep(5 * (attempt + 1))
    return np.concatenate(tiles, axis=0)


def _mean_to_grid(img, scale=10):
    # Band math / multi-source composites (S2 normalizedDifference, WorldCover masks, Dynamic
    # World means) lose their native projection, so reduceResolution needs one declared explicitly.
    return img.setDefaultProjection(crs="EPSG:4326", scale=scale).reduceResolution(
        ee.Reducer.mean(), maxPixels=4096).reproject(crs="EPSG:4326", crsTransform=_transform())


def _landsat(start, end, months):
    col = (ee.ImageCollection(config.LANDSAT8).merge(ee.ImageCollection(config.LANDSAT9))
           .filterBounds(_aoi()).filterDate(start, end)
           .filter(ee.Filter.calendarRange(months[0], months[-1], "month"))
           .filter(ee.Filter.lt("CLOUD_COVER", 70)))
    return col


def _clear(img):
    return img.select("QA_PIXEL").bitwiseAnd(0b11110).eq(0)  # dilated cloud, cirrus, cloud, shadow


def _lst(img):
    st = img.select("ST_B10").multiply(config.LANDSAT_ST_SCALE).add(config.LANDSAT_ST_OFFSET).subtract(273.15)
    good = _clear(img).And(img.select("ST_QA").multiply(0.01).lte(config.ST_QA_MAX_K))
    # .copyProperties() returns a generic Element in the Python client, not an Image — cast it back
    # so later Image-only calls (.toFloat(), etc.) work.
    return ee.Image(st.updateMask(good).rename("lst").copyProperties(img, ["system:time_start"]))


def _sr(img, band):
    return img.select(band).multiply(config.LANDSAT_SR_SCALE).add(config.LANDSAT_SR_OFFSET)


def _albedo(img):  # Liang (2001) for OLI bands
    a = (_sr(img, "SR_B2").multiply(0.356).add(_sr(img, "SR_B4").multiply(0.130))
         .add(_sr(img, "SR_B5").multiply(0.373)).add(_sr(img, "SR_B6").multiply(0.085))
         .add(_sr(img, "SR_B7").multiply(0.072)).subtract(0.0018))
    return a.updateMask(_clear(img)).rename("albedo")


def _ndvi_landsat(img):
    return img.normalizedDifference(["SR_B5", "SR_B4"]).updateMask(_clear(img)).rename("ndvi")


def select_scenes():
    y0, y1 = config.SCENE_YEARS
    col = _landsat(f"{y0}-01-01", f"{y1}-12-31", config.SCENE_MONTHS).map(_lst)
    aoi = _aoi()

    def valid(img):
        n = img.mask().reduceRegion(ee.Reducer.mean(), aoi, 300, maxPixels=1e9).get("lst")
        return img.set("valid", n)

    info = col.map(valid).filter(ee.Filter.gte("valid", config.MIN_VALID_FRACTION)).sort(
        "valid", False).limit(config.MAX_SCENES).reduceColumns(
        ee.Reducer.toList(3), ["system:index", "system:time_start", "valid"]).get("list").getInfo()
    return pd.DataFrame(info, columns=["index", "time_ms", "valid"])


def era5_at(time_ms: int) -> dict:
    t = ee.Date(time_ms)
    h = t.update(minute=0, second=0)
    col = ee.ImageCollection(config.ERA5_LAND_HOURLY).filterDate(h.advance(-1, "hour"), h.advance(1, "minute"))
    imgs = col.sort("system:time_start").toList(2)
    prev, cur = ee.Image(imgs.get(0)), ee.Image(imgs.get(1))
    bands = ["temperature_2m", "dewpoint_temperature_2m", "u_component_of_wind_10m",
             "v_component_of_wind_10m", "surface_solar_radiation_downwards"]
    v = cur.select(bands).reduceRegion(ee.Reducer.mean(), _aoi(), 11132).getInfo()
    p = prev.select("surface_solar_radiation_downwards").reduceRegion(ee.Reducer.mean(), _aoi(), 11132).getInfo()
    from uhi.features import relative_humidity

    t_c, td_c = v["temperature_2m"] - 273.15, v["dewpoint_temperature_2m"] - 273.15
    ssrd = (v["surface_solar_radiation_downwards"] - p["surface_solar_radiation_downwards"]) / 3600
    if ssrd <= 0:  # accumulation resets at 00 UTC; overpass is ~05 UTC so this is rare
        ssrd = v["surface_solar_radiation_downwards"] / max(pd.Timestamp(time_ms, unit="ms").hour, 1) / 3600
    return {"t2m_c": t_c, "rh": float(relative_humidity(t_c, td_c)),
            "wind_ms": float(np.hypot(v["u_component_of_wind_10m"], v["v_component_of_wind_10m"])),
            "ssrd_wm2": float(ssrd)}


def static_image():
    y0, y1 = config.SCENE_YEARS
    months = ee.Filter.calendarRange(config.SCENE_MONTHS[0], config.SCENE_MONTHS[-1], "month")
    cs = ee.ImageCollection(config.CLOUD_SCORE_PLUS)
    s2 = (ee.ImageCollection(config.SENTINEL2_SR).filterBounds(_aoi()).filterDate(f"{max(y0, 2023)}-01-01",
          f"{y1}-12-31").filter(months).linkCollection(cs, ["cs"])
          .map(lambda i: i.updateMask(i.select("cs").gte(0.6))).median())
    ndvi = s2.normalizedDifference(["B8", "B4"]).rename("ndvi")
    ndbi = s2.normalizedDifference(["B11", "B8"]).rename("ndbi")
    mndwi = s2.normalizedDifference(["B3", "B11"]).rename("mndwi")
    albedo = _landsat(f"{y0}-01-01", f"{y1}-12-31", config.SCENE_MONTHS).map(_albedo).median()
    wc = ee.ImageCollection(config.WORLDCOVER).first().select("Map")
    fr = ee.Image.cat([wc.eq(10).rename("tree_frac"), wc.eq(50).rename("built_frac"),
                       wc.eq(80).rename("water_frac"), wc.eq(95).rename("mangrove_frac"),
                       wc.eq(20).Or(wc.eq(30)).Or(wc.eq(40)).Or(wc.eq(60)).rename("grass_bare_frac")])
    pop = ee.Image(f"{config.GHSL_POP}/2020").select("population_count").rename("pop")
    height = ee.Image(f"{config.GHSL_BUILT_H}/2018").select("built_height").rename("built_height")
    bsurf = ee.Image(f"{config.GHSL_BUILT_S}/2020").select("built_surface").divide(10_000).rename("building_frac")
    elev = ee.Image(config.SRTM).select("elevation").rename("elevation")
    means = _mean_to_grid(ee.Image.cat([ndvi, ndbi, mndwi, fr]).toFloat())
    return ee.Image.cat([means, albedo.toFloat(), pop.toFloat(), height.toFloat(),
                         bsurf.toFloat(), elev.toFloat()])


def backtest_image(year: int):
    col = _landsat(f"{year}-01-01", f"{year}-12-31", config.BACKTEST_MONTHS)
    lst = col.map(_lst).median().rename(f"lst_{year}")
    ndvi = col.map(_ndvi_landsat).median().rename(f"ndvi_{year}")
    albedo = col.map(_albedo).median().rename(f"albedo_{year}")
    dw = (ee.ImageCollection(config.DYNAMIC_WORLD).filterBounds(_aoi())
          .filterDate(f"{year}-01-01", f"{year}-12-31")
          .filter(ee.Filter.calendarRange(config.BACKTEST_MONTHS[0], config.BACKTEST_MONTHS[-1], "month"))
          .select(["trees", "built", "water"]).mean())
    dwg = _mean_to_grid(dw).rename([f"tree_{year}", f"built_{year}", f"water_{year}"])
    return ee.Image.cat([lst, ndvi, albedo, dwg]).toFloat()


def _frame(arr: np.ndarray) -> pd.DataFrame:
    n_rows, n_cols = arr.shape
    rows, cols = np.meshgrid(np.arange(n_rows), np.arange(n_cols), indexing="ij")
    df = pd.DataFrame({name: arr[name].ravel().astype(float) for name in arr.dtype.names})
    df = df.mask(df <= NODATA + 1)
    df.insert(0, "col", cols.ravel())
    df.insert(0, "row", rows.ravel())
    return df


def run(project: str):
    _init(project)
    config.FROZEN.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.1f}s] {m}", flush=True)

    cells = _frame(pixels(static_image()))
    lon0, _, _, lat1 = config.BBOX
    cells["lat"] = lat1 - (cells["row"] + 0.5) * config.CELL_DEG
    cells["lon"] = lon0 + (cells["col"] + 0.5) * config.CELL_DEG
    for c in ("tree_frac", "built_frac", "water_frac", "mangrove_frac", "grass_bare_frac", "pop",
              "built_height", "building_frac"):
        cells[c] = cells[c].fillna(0.0)
    cells["pop"] = cells["pop"].clip(lower=0)  # GHS_POP's own nodata sentinel (-200) isn't EE-masked
    for c in ("ndvi", "ndbi", "mndwi", "albedo", "elevation"):
        cells[c] = cells[c].fillna(cells[c].median())
    n_rows, n_cols = grid_shape()
    water = cells["water_frac"].to_numpy().reshape(n_rows, n_cols) >= 0.5
    cells["dist_water_m"] = (distance_transform_edt(~water) * config.GRID_RESOLUTION_M).ravel()
    cells.insert(0, "cell_id", np.arange(len(cells)))
    cells.to_parquet(config.FROZEN / "cells_static.parquet", index=False)
    log(f"static features: {len(cells)} cells")

    scenes = select_scenes()
    log(f"{len(scenes)} clean scenes selected")
    meta, panels = [], []
    for sid, s in enumerate(scenes.itertuples()):
        y0, y1 = config.SCENE_YEARS  # merged L8+L9 indexes look like "1_LC08_…" / "2_LC09_…"
        img = _lst(_landsat(f"{y0}-01-01", f"{y1}-12-31", config.SCENE_MONTHS)
                   .filter(ee.Filter.eq("system:index", s.index)).first())
        arr = _frame(pixels(img.toFloat()))
        ok = arr["lst"].notna()
        panels.append(pd.DataFrame({"cell_id": cells["cell_id"][ok.to_numpy()], "scene_id": sid,
                                    "lst_c": arr.loc[ok, "lst"].to_numpy()}))
        met = era5_at(int(s.time_ms))
        meta.append({"scene_id": sid, "date": pd.Timestamp(s.time_ms, unit="ms").strftime("%Y-%m-%d"),
                     "system_index": s.index, "valid": s.valid, **met})
        log(f"scene {sid + 1}/{len(scenes)} {meta[-1]['date']}: {ok.sum()} valid cells")
    pd.concat(panels).to_parquet(config.FROZEN / "scenes.parquet", index=False)
    pd.DataFrame(meta).to_parquet(config.FROZEN / "scenes_meta.parquet", index=False)

    bt = _frame(pixels(ee.Image.cat([backtest_image(y) for y in config.BACKTEST_YEARS])))
    bt.insert(0, "cell_id", cells["cell_id"])
    bt.drop(columns=["row", "col"]).to_parquet(config.FROZEN / "backtest.parquet", index=False)
    log("back-test composites saved — data frozen. Next: python -m uhi.osm_features")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="Google Cloud project registered for Earth Engine")
    run(ap.parse_args().project)
