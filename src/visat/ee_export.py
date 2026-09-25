"""Earth Engine data export for the scene-panel model. Run this yourself —
it needs your own authenticated GEE session and cannot run in this
environment:

    ee.Authenticate()  # one-time, opens a browser
    ee.Initialize(project="<your-cloud-project>")
    python -m visat.ee_export --out data/frozen/scenes.parquet

This intentionally keeps GEE calls out of model.py and the app, so the
rest of the pipeline stays testable without live credentials.
"""

from __future__ import annotations

import argparse

from . import config


def initialise(project: str) -> None:
    import ee

    ee.Authenticate()
    ee.Initialize(project=project)


def clean_landsat_scenes(aoi, start: str, end: str):
    """Landsat 8+9 Collection 2 Level 2 surface temperature, cloud-masked,
    scaled to Celsius, restricted to config.STUDY_MONTHS (Jan-Apr)."""
    import ee

    def scale_and_mask(image):
        st_kelvin = (
            image.select("ST_B10")
            .multiply(config.LANDSAT_ST_SCALE)
            .add(config.LANDSAT_ST_OFFSET)
        )
        st_celsius = st_kelvin.subtract(273.15).rename("lst_c")

        qa = image.select("QA_PIXEL")
        cloud_mask = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))  # cloud, cloud shadow bits

        st_qa_kelvin = image.select("ST_QA").multiply(0.01)
        confidence_mask = st_qa_kelvin.lte(config.LANDSAT_ST_QA_MAX_KELVIN)

        return image.addBands(st_celsius).updateMask(cloud_mask).updateMask(confidence_mask)

    def month_filter(collection):
        return collection.filter(ee.Filter.calendarRange(
            config.STUDY_MONTHS[0], config.STUDY_MONTHS[-1], "month"
        ))

    l8 = month_filter(ee.ImageCollection(config.LANDSAT8_LST).filterDate(start, end).filterBounds(aoi))
    l9 = month_filter(ee.ImageCollection(config.LANDSAT9_LST).filterDate(start, end).filterBounds(aoi))

    return l8.merge(l9).map(scale_and_mask)


def era5_at_scene(scene_image, aoi):
    """ERA5-Land hourly values at the scene's overpass hour — this is what
    makes the model scene-panel rather than cross-sectional: each scene row
    gets its own weather, so (1 - albedo) * SSRD is really learned."""
    import ee

    scene_time = ee.Date(scene_image.get("system:time_start"))
    era5_hour = (
        ee.ImageCollection(config.ERA5_LAND_HOURLY)
        .filterDate(scene_time.advance(-1, "hour"), scene_time.advance(1, "hour"))
        .filterBounds(aoi)
        .select(list(config.ERA5_BANDS))
        .first()
    )
    return era5_hour


def sentinel2_indices(aoi, start: str, end: str):
    """NDVI/NDBI/MNDWI from Sentinel-2 (not Landsat) to avoid leaking
    Landsat's own NDVI-based emissivity correction into the target."""
    import ee

    def add_indices(image):
        ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
        ndbi = image.normalizedDifference(["B11", "B8"]).rename("ndbi")
        mndwi = image.normalizedDifference(["B3", "B11"]).rename("mndwi")
        return image.addBands([ndvi, ndbi, mndwi])

    return (
        ee.ImageCollection(config.SENTINEL2_SR)
        .filterDate(start, end)
        .filterBounds(aoi)
        .map(add_indices)
    )


def ghsl_morphology(aoi):
    import ee

    pop = ee.Image(config.GHSL_POP).clip(aoi)
    built_h = ee.Image(config.GHSL_BUILT_H).clip(aoi)
    built_s = ee.Image(config.GHSL_BUILT_S).clip(aoi)
    return pop, built_h, built_s


def worldcover_fractions(aoi):
    """ESA WorldCover class fractions at 100m — present-day driver map only.
    Do NOT use this for the 2017-vs-2024 back-test (only 2020/2021 editions
    exist); use dynamic_world_backtest_pair below instead."""
    import ee

    wc = ee.Image(config.WORLDCOVER_2021).clip(aoi)
    return {
        "tree": wc.eq(10),
        "built": wc.eq(50),
        "water": wc.eq(80),
        "mangrove": wc.eq(95),
    }


def dynamic_world_backtest_pair(aoi):
    """Dynamic World LULC probability composites for Feb-Apr 2017 and
    Feb-Apr 2024, for the back-test change comparison."""
    import ee

    def composite(year: int):
        start = f"{year}-{config.BACKTEST_COMPARE_MONTHS[0]:02d}-01"
        end = f"{year}-{config.BACKTEST_COMPARE_MONTHS[-1]:02d}-28"
        return (
            ee.ImageCollection(config.DYNAMIC_WORLD)
            .filterDate(start, end)
            .filterBounds(aoi)
            .select(["trees", "built", "water"])
            .mean()
        )

    year_2017, year_2024 = config.BACKTEST_YEARS
    return composite(year_2017), composite(year_2024)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="your GEE cloud project id")
    parser.add_argument("--out", required=True, help="output parquet path, e.g. data/frozen/scenes.parquet")
    parser.add_argument("--start", default="2019-01-01")
    parser.add_argument("--end", default="2026-04-30")
    args = parser.parse_args()

    initialise(args.project)
    print(
        "GEE session initialised. Wire up your Kochi AOI and call "
        "clean_landsat_scenes / era5_at_scene / sentinel2_indices / "
        "worldcover_fractions / dynamic_world_backtest_pair, then export "
        f"the assembled scene-panel table to {args.out}."
    )


if __name__ == "__main__":
    main()
