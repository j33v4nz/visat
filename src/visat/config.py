"""Locked-in constants decided pre-event. See RESOURCES.md and STRATEGY.md for reasoning.

No pipeline logic here — dataset IDs, live-API config, costs, and study parameters only.
"""

# Earth Engine asset IDs
LANDSAT8_LST = "LANDSAT/LC08/C02/T1_L2"
LANDSAT9_LST = "LANDSAT/LC09/C02/T1_L2"  # L2 available through Sep 2026
SENTINEL2_SR = "COPERNICUS/S2_SR_HARMONIZED"
CLOUD_SCORE_PLUS = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
WORLDCOVER_2021 = "ESA/WorldCover/v200"  # present-day driver map only — no 2017/2024 edition
DYNAMIC_WORLD = "GOOGLE/DYNAMICWORLD/V1"  # used for the 2017-vs-2024 back-test instead
GHSL_POP = "JRC/GHSL/P2023A/GHS_POP"  # real epochs to 2020 only; 2025/2030 are projections
GHSL_BUILT_H = "JRC/GHSL/P2023A/GHS_BUILT_H"
GHSL_BUILT_S = "JRC/GHSL/P2023A/GHS_BUILT_S"
SRTM = "USGS/SRTMGL1_003"
ERA5_LAND_HOURLY = "ECMWF/ERA5_LAND/HOURLY"  # not a model feature — heat index/UTCI + physics check only

# Landsat ST scaling (Collection 2 Level 2)
LANDSAT_ST_SCALE = 0.00341802
LANDSAT_ST_OFFSET = 149.0  # kelvin; subtract 273.15 for celsius
LANDSAT_ST_QA_MAX_KELVIN = 2.0  # drop pixels where ST_QA * 0.01 exceeds this

# Live weather — Open-Meteo (no API key, non-commercial free tier)
OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_MAX_CALLS_PER_DAY = 10_000
OPEN_METEO_CACHE_TTL_SECONDS = 900
OPEN_METEO_TIMEOUT_SECONDS = 3

KOCHI_POINTS = {
    "fort_kochi": (9.965, 76.242),
    "mattancherry": (9.958, 76.259),
    "ernakulam_south": (9.968, 76.284),
    "kaloor": (9.997, 76.291),
    "edappally": (10.024, 76.308),
    "vyttila": (9.968, 76.320),
    "kakkanad": (10.016, 76.352),
    "kalamassery": (10.055, 76.321),
}

# NWS heat index bands (deg C)
HEAT_INDEX_BANDS_C = {
    "caution": (27, 32),
    "extreme_caution": (32, 39),
    "danger": (39, 51),
    "extreme_danger": (52, None),
}

# Malayalam news RSS
NEWS_RSS_CACHE_TTL_SECONDS = 900
NEWS_RSS_TIMEOUT_SECONDS = 5
NEWS_RSS_FEEDS = {
    "google_news_ml": "https://news.google.com/rss/search?q={query}&hl=ml&gl=IN&ceid=IN:ml",
    "mathrubhumi": "https://www.mathrubhumi.com/rss",
    "twentyfour_news": "https://www.twentyfournews.com/feed",
}

# Study parameters
GRID_RESOLUTION_M = 100
STUDY_MONTHS = (2, 3, 4)  # Feb-Apr
BACKTEST_YEARS = (2017, 2024)
WARD_COUNT_2024 = 74  # BharatLAS GIS source uses this vintage
WARD_COUNT_2025 = 76  # post-delimitation — no open 76-ward GIS file found; use 74 and say so on stage

# Intervention costs (INR), sourced — re-verify links before the event
COST_PER_STREET_TREE_INCL_5YR_MAINTENANCE = 3100
COST_COOL_ROOF_PER_SQM = 300
COST_COOL_ROOF_RECOAT_PER_SQM = 150  # every 3 years
COST_MANGROVE_PER_HECTARE_LOW = 100_000
COST_MANGROVE_PER_HECTARE_HIGH = 800_000
COST_GREEN_ROOF_PER_SQM = 7500  # excluded from optimizer — never cost-effective
