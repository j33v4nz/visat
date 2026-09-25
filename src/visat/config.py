"""Locked constants for the VISAT pipeline: dataset IDs, live-API config, costs
and study parameters. See RESOURCES.md and PLAN.md for the reasoning behind
each value. No pipeline logic here.
"""

# --- Earth Engine asset IDs -------------------------------------------------

LANDSAT8_LST = "LANDSAT/LC08/C02/T1_L2"
LANDSAT9_LST = "LANDSAT/LC09/C02/T1_L2"  # L2 available through Sep 2026
SENTINEL2_SR = "COPERNICUS/S2_SR_HARMONIZED"
CLOUD_SCORE_PLUS = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
WORLDCOVER_2021 = "ESA/WorldCover/v200"  # present-day driver map only
DYNAMIC_WORLD = "GOOGLE/DYNAMICWORLD/V1"  # 2017-vs-2024 back-test LULC change
GHSL_POP = "JRC/GHSL/P2023A/GHS_POP"  # real epochs to 2020 only; 2025/2030 are projections
GHSL_BUILT_H = "JRC/GHSL/P2023A/GHS_BUILT_H"
GHSL_BUILT_S = "JRC/GHSL/P2023A/GHS_BUILT_S"
SRTM = "USGS/SRTMGL1_003"
# meteorological input (PS1): the scene-panel model gives each Landsat scene
# its own ERA5 values at overpass hour, so (1 - albedo) * SSRD varies scene to
# scene and is genuinely learned, not a rescaled constant. ~9km, so never used
# as a raw per-pixel predictor directly.
ERA5_LAND_HOURLY = "ECMWF/ERA5_LAND/HOURLY"
ERA5_BANDS = (
    "temperature_2m",
    "dewpoint_temperature_2m",  # for relative humidity
    "u_component_of_wind_10m",
    "v_component_of_wind_10m",
    "surface_solar_radiation_downwards",
    "potential_evaporation",
)
# UT-GLOBUS (GEE community catalog) — Kochi coverage unconfirmed; v5 uses
# GHSL + OSM buildings regardless (PS1 says "if available") and states the
# UT-GLOBUS check result honestly either way.
UT_GLOBUS_CATALOG_URL = "https://gee-community-catalog.org/projects/utglobus/"
# ECOSTRESS LST — not in GEE for Kochi (LA-metro tiles only); sourced instead
# via NASA AppEEARS, filtered to 12:00-15:30 local (afternoon, unlike
# Landsat's ~10:30 AM overpass). Compare patterns (Spearman + top-decile
# overlap), not absolute degrees. lst_err layer missing 16 Dec 2025-10 Jun
# 2026 — prefer Feb-Apr 2024-2025 scenes.
ECOSTRESS_PRODUCT = "ECO_L2T_LSTE.002"
ECOSTRESS_LOCAL_HOUR_WINDOW = (12, 0, 15, 30)  # start_h, start_m, end_h, end_m

# --- Landsat surface-temperature scaling (Collection 2 Level 2) ------------

LANDSAT_ST_SCALE = 0.00341802
LANDSAT_ST_OFFSET = 149.0  # kelvin; subtract 273.15 for celsius
LANDSAT_ST_QA_MAX_KELVIN = 2.0  # drop pixels where ST_QA * 0.01 exceeds this

# --- Scene-panel model study window -----------------------------------------

STUDY_MONTHS = (1, 2, 3, 4)  # Jan-Apr, the panel's scene-collection window
BACKTEST_COMPARE_MONTHS = (2, 3, 4)  # Feb-Apr, for the 2017-vs-2024 Dynamic World comparison
BACKTEST_YEARS = (2017, 2024)
SPATIAL_BLOCK_SIZE_M = 2000  # grouped spatial-block CV, across all scenes
NEIGHBOURHOOD_RADII_M = (300, 500)

# --- Physics constants (energy-balance formula, for formula-based interventions) ---

SOLAR_IRRADIANCE_W_M2 = 750  # S, incoming solar radiation used in the cool-roof/pavement check
HEAT_TRANSFER_COEFF_W_M2K = 25  # h, surface-to-air heat transfer coefficient

# --- Grid / ward parameters --------------------------------------------------

GRID_RESOLUTION_M = 100
WARD_COUNT_2024 = 74  # BharatLAS GIS source uses this vintage; state so on stage
WARD_COUNT_2025 = 76  # post-2025 delimitation — no open 76-ward GIS file found

# --- Live weather: Open-Meteo (no API key, non-commercial free tier) --------

OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_TIMEZONE = "Asia/Kolkata"
OPEN_METEO_FORECAST_DAYS = 3
OPEN_METEO_CURRENT_VARS = (
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "wind_speed_10m",
)
OPEN_METEO_HOURLY_VARS = (
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "wet_bulb_temperature_2m",
    "uv_index",
    "shortwave_radiation",
    "wind_speed_10m",
)
OPEN_METEO_CACHE_TTL_SECONDS = 900
OPEN_METEO_TIMEOUT_SECONDS = 3
OPEN_METEO_ATTRIBUTION = "Weather data: Open-Meteo"

# 8 Kochi points (approximate centres) — snap to ~4 distinct ~7km ERA5 model
# cells in practice; treat the live layer as city-scale, not ward-level.
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

# NWS (Rothfusz) heat-index bands, degrees C
HEAT_INDEX_BANDS_C = {
    "caution": (27, 32),
    "extreme_caution": (32, 39),
    "danger": (39, 51),
    "extreme_danger": (52, None),
}

# --- Live Malayalam news (static chip, Tier 2) ------------------------------

NEWS_RSS_CACHE_TTL_SECONDS = 900
NEWS_RSS_TIMEOUT_SECONDS = 5
NEWS_RSS_LOOKBACK_DAYS = 7
NEWS_RSS_FEEDS = {
    "google_news_ml": "https://news.google.com/rss/search?q={query}&hl=ml&gl=IN&ceid=IN:ml",
    "mathrubhumi": "https://www.mathrubhumi.com/rss",
    "twentyfour_news": "https://www.twentyfournews.com/feed",
}
# URL-encode before use; excludes Gulf heat stories, which otherwise leak in.
NEWS_RSS_QUERY = (
    "(ചൂട് OR താപനില OR ഉഷ്ണതരംഗം OR സൂര്യാതപം OR അലർട്ട്) "
    "(കേരളം OR എറണാകുളം OR കൊച്ചി) -യുഎഇ -ഗൾഫ് -സൗദി when:7d"
)
NEWS_HEAT_KEYWORDS = (
    "ചൂട്", "താപനില", "ഉഷ്ണതരംഗം", "സൂര്യാതപം", "സൂര്യാഘാതം", "ഉയർന്ന താപനില",
)
NEWS_ALERT_COLOUR_KEYWORDS = {
    "yellow": "യെല്ലോ അലർട്ട്",
    "orange": "ഓറഞ്ച് അലർട്ട്",
    "red": "റെഡ് അലർട്ട്",
    "caution": "ജാഗ്രത",
}
NEWS_PLACE_KEYWORDS = ("കേരളം", "സംസ്ഥാനത്ത്", "എറണാകുളം", "കൊച്ചി")

# --- Intervention costs (INR), sourced — re-verify links before submission ---

COST_STREET_TREE_INCL_5YR_CARE = 3100  # per tree
COST_CANAL_BANK_TREE_STRIP_PER_M = 1000  # ~1 tree per 3m at COST_STREET_TREE_INCL_5YR_CARE
COST_MANGROVE_PER_HECTARE_LOW = 100_000
COST_MANGROVE_PER_HECTARE_HIGH = 800_000
COST_GREEN_ROOF_PER_SQM = 7500  # simulated and scored; rarely chosen on cost
COST_COOL_ROOF_PER_SQM = 300
COST_COOL_ROOF_RECOAT_PER_SQM = 150  # every ~3 years
COST_COOL_PAVEMENT_PER_SQM = 350  # range 190-500, ~3-year life
COST_POND_RESTORATION_PER_HECTARE = 4_500_000  # Amrit Sarovar rate, ~45 lakh/ha
COST_IURWTS_TOTAL_CRORE = 3716  # committed KMRL project; not bought by the optimizer

# --- Budget optimizer presets (precomputed, no drag slider) -----------------

BUDGET_PRESETS_CRORE = (1, 10, 50)
