"""Single source of truth for VISAT constants (plan v5). Written at HackMe'26."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"  # manual downloads (wards, CPCB, ECOSTRESS) — gitignored
FROZEN = DATA / "frozen"  # Earth Engine / OSM exports — gitignored
APP = DATA / "app"  # small app-ready artifacts — TRACKED, read by Streamlit Cloud

# ---------------------------------------------------------------- study area / grid
# Kochi + surroundings (Fort Kochi, Mattancherry, Ernakulam, Edappally, Kakkanad, Kalamassery).
BBOX = (76.20, 9.88, 76.40, 10.10)  # (lon_min, lat_min, lon_max, lat_max)
CELL_DEG = 0.0009  # ≈100 m at 10°N
GRID_RESOLUTION_M = 100
FOCAL_SIZES = {"300": 3, "500": 5}  # neighbourhood windows in cells
BLOCK_CELLS = 20  # 20 cells ≈ 2 km spatial-CV blocks

# ---------------------------------------------------------------- seasons
SCENE_MONTHS = (1, 2, 3, 4)  # Jan–Apr: hot + clearest skies (before monsoon)
SCENE_YEARS = (2019, 2026)
MAX_SCENES = 30
MIN_VALID_FRACTION = 0.6
BACKTEST_MONTHS = (2, 3, 4)  # Feb–Apr
BACKTEST_YEARS = (2017, 2024)
ECOSTRESS_LOCAL_WINDOW = ("12:00", "15:30")  # IST afternoon window
LABEL_SURFACE = "surface °C, ~10:30 AM, Jan–Apr"
LABEL_LIVE = "live weather, city-scale"

# ---------------------------------------------------------------- Earth Engine asset IDs
LANDSAT8 = "LANDSAT/LC08/C02/T1_L2"
LANDSAT9 = "LANDSAT/LC09/C02/T1_L2"
LANDSAT_ST_SCALE = 0.00341802
LANDSAT_ST_OFFSET = 149.0  # kelvin
LANDSAT_SR_SCALE = 0.0000275
LANDSAT_SR_OFFSET = -0.2
ST_QA_MAX_K = 2.0  # drop pixels whose ST_QA * 0.01 exceeds this
SENTINEL2_SR = "COPERNICUS/S2_SR_HARMONIZED"  # 2019+ over India
CLOUD_SCORE_PLUS = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
WORLDCOVER = "ESA/WorldCover/v200"  # 2021: present-day land cover
DYNAMIC_WORLD = "GOOGLE/DYNAMICWORLD/V1"  # 2015+: back-test land-cover change
GHSL_POP = "JRC/GHSL/P2023A/GHS_POP"  # latest real epoch 2020
GHSL_BUILT_H = "JRC/GHSL/P2023A/GHS_BUILT_H"
GHSL_BUILT_S = "JRC/GHSL/P2023A/GHS_BUILT_S"
SRTM = "USGS/SRTMGL1_003"
ERA5_LAND_HOURLY = "ECMWF/ERA5_LAND/HOURLY"  # per-scene model input (scene-panel)
ECOSTRESS_PRODUCT = "ECO_L2T_LSTE.002"  # via NASA AppEEARS (not in GEE for Kochi)

# ---------------------------------------------------------------- model features
# +1 = can only warm, -1 = can only cool, 0 = free (physics-informed monotone constraints)
FEATURES = {
    "ndvi": -1,
    "tree_frac": -1,
    "water_frac": -1,
    "mangrove_frac": -1,
    "mndwi": -1,
    "albedo": -1,
    "built_frac": 1,
    "ndbi": 1,
    "building_frac": 1,
    "built_height": 0,
    "elevation": 0,
    "dist_water_m": 1,
    "tree_frac_300": -1,
    "built_frac_300": 1,
    "water_frac_300": -1,
    "tree_frac_500": -1,
    "built_frac_500": 1,
    "water_frac_500": -1,
    # per-scene atmosphere (ERA5-Land at overpass) + energy-balance interaction
    "t2m_c": 1,
    "rh": 0,
    "wind_ms": -1,
    "ssrd_wm2": 1,
    "absorbed_sw": 1,  # (1 - albedo) * incoming shortwave, W/m²
}
ATMOS_FEATURES = ["t2m_c", "rh", "wind_ms", "ssrd_wm2"]
DRIVER_GROUPS = {
    "Vegetation": ["ndvi", "tree_frac", "tree_frac_300", "tree_frac_500"],
    "Concrete & buildings": [
        "built_frac", "ndbi", "building_frac", "built_height", "built_frac_300", "built_frac_500",
    ],
    "Water nearby": [
        "water_frac", "mangrove_frac", "mndwi", "dist_water_m", "water_frac_300", "water_frac_500",
    ],
    "Surface reflectivity": ["albedo", "absorbed_sw"],
    "Weather of the day": ATMOS_FEATURES,
    "Terrain": ["elevation"],
}
LC_FEATURES = [
    "ndvi", "tree_frac", "water_frac", "mangrove_frac", "mndwi", "albedo",
    "built_frac", "ndbi", "building_frac", "built_height",
]
CONTEXT_FEATURES = ["elevation", "dist_water_m", "built_frac_500", "tree_frac_500"]

# ---------------------------------------------------------------- physics (energy balance)
SOLAR_SHORTWAVE_WM2 = 750.0  # typical clear-sky midday incoming shortwave
HEAT_LOSS_WM2K = 25.0  # combined convective + radiative loss coefficient

# ---------------------------------------------------------------- interventions & costs (INR)
KNN_DONORS = 20
SUPPORT_QUANTILES = (0.01, 0.99)
INTERVENTIONS = {
    "street_trees": {
        "label": "Street trees", "ps1": "Urban greening", "method": "analog",
        "cost_per_cell": 30 * 3100, "cost_note": "30 trees × ₹3,100 (planting + 5-yr care, BBMP)",
        "intensity": 0.15,
    },
    "canal_bank_trees": {
        "label": "Canal-bank tree strip", "ps1": "Urban greening + water bodies",
        "method": "analog", "cost_per_cell": 100 * 1000,
        "cost_note": "100 m × ~₹1,000/m (estimate)", "intensity": 0.12,
    },
    "mangroves": {
        "label": "Mangrove restoration", "ps1": "Urban greening", "method": "analog",
        "cost_per_cell": int(0.5 * 100_000), "cost_note": "0.5 ha × ₹1 lakh/ha (range ₹1–8 lakh)",
        "intensity": 0.5,
    },
    "pond": {  # 0.5 ha keeps the change inside what the model has seen (≥1 acre Amrit Sarovar size)
        "label": "Pond restoration (0.5 ha)", "ps1": "Water bodies", "method": "analog",
        "cost_per_cell": 2_250_000, "cost_note": "0.5 ha × ~₹45 lakh/ha (Amrit Sarovar rate)",
        "intensity": 0.5,
    },
    "cool_roofs": {
        "label": "Cool roofs", "ps1": "Cool roofs", "method": "formula",
        "cost_per_m2": 300, "cost_note": "₹300/m² (Telangana Cool Roof Policy) + recoat ~3 yrs",
        "delta_albedo": 0.40, "coverage": 0.5,
    },
    "cool_pavements": {
        "label": "Cool pavements", "ps1": "Albedo changes", "method": "formula",
        "cost_per_m2": 350, "cost_note": "₹350/m² (₹190–500, ~3-yr life)",
        "delta_albedo": 0.25, "coverage": 0.6,
    },
    "green_roofs": {
        "label": "Green roofs", "ps1": "Urban greening", "method": "formula",
        "cost_per_m2": 7500, "cost_note": "₹7,500/m² (IndiaSpend) — evaluated, rarely cost-effective",
        "surface_cooling_k": 8.0, "coverage": 0.2,
    },
}
CANAL_CREDIT_NOTE = (
    "IURWTS canals (KMRL, ₹3,716 crore, 6 canals): committed project, shown as an overlay with "
    "0 °C credit — canals are narrower than a 100 m cell. We offer canal-bank tree strips instead."
)
BUDGET_PRESETS_CR = (1, 10, 50)
CRORE = 10_000_000

# ---------------------------------------------------------------- Heat-Neutral Development Check
PROJECT_USES = {
    "it_park": {"label": "IT park", "built_min": 0.55, "height_min": 8.0},
    "mall": {"label": "Mall", "built_min": 0.70, "height_min": 6.0},
    "housing": {"label": "Housing", "built_min": 0.40, "height_max": 12.0},
    "parking": {"label": "Parking / paved yard", "built_min": 0.60, "height_max": 4.0},
}
SITE_ANCHORS = {  # approximate centres; the pipeline picks the greenest open block nearby
    "Kakkanad": (10.015, 76.345),
    "Kalamassery": (10.050, 76.320),
    "Edappally": (10.025, 76.305),
    "Vyttila": (9.970, 76.320),
    "Maradu": (9.945, 76.320),
    "Thrikkakara": (10.035, 76.330),
}
SITE_BLOCK = 3  # 3×3 cells ≈ 9 ha
NEIGHBOURHOOD_CELLS = 5  # ±5 cells ≈ 500 m
POLICY_HOOKS = (
    "Screening tool and policy proposal — not an approval. Possible hooks: voluntary offset for a "
    "KMBR 2019 extra-FSI incentive; attach to SEIAA Form-1A for 20,000–150,000 m² projects; "
    "Kochi Master Plan 2040 resilience guidance. Signed off by: Corporation building-permit "
    "section / Town Planning Committee."
)

# ---------------------------------------------------------------- live weather (Open-Meteo)
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_TIMEOUT_S = 6
LIVE_TTL_S = 900
KOCHI_POINTS = {
    "Fort Kochi": (9.965, 76.242),
    "Mattancherry": (9.958, 76.259),
    "Ernakulam South": (9.968, 76.284),
    "Kaloor": (9.997, 76.291),
    "Edappally": (10.024, 76.308),
    "Vyttila": (9.968, 76.320),
    "Kakkanad": (10.016, 76.352),
    "Kalamassery": (10.055, 76.321),
}
HEAT_INDEX_BANDS_C = [  # NWS bands
    ("Caution", 27, 32),
    ("Extreme caution", 32, 39),
    ("Danger", 39, 51),
    ("Extreme danger", 51, 200),
]
ACT_TODAY_ADVICE = [
    "Outdoor work rest 12–3 PM (Labour Commissioner order)",
    "Open drinking-water kiosks (thanneer pandal)",
    "Schools: no assemblies or outdoor classes 11 AM–3 PM",
    "Markets and waste dumps: fire-safety watch",
]
OFFICIAL_ALERT_LINKS = {
    "IMD Kerala warnings": "https://mausam.imd.gov.in/thiruvananthapuram/",
    "KSDMA": "https://sdma.kerala.gov.in/",
}

# ---------------------------------------------------------------- Malayalam news RSS
NEWS_TIMEOUT_S = 5
NEWS_QUERY = (
    "(ചൂട് OR താപനില OR ഉഷ്ണതരംഗം OR സൂര്യാതപം OR അലർട്ട്) (കേരളം OR എറണാകുളം OR കൊച്ചി) "
    "-യുഎഇ -ഗൾഫ് -സൗദി when:7d"
)
NEWS_FEEDS = {
    "google_news_ml": "https://news.google.com/rss/search?q={query}&hl=ml&gl=IN&ceid=IN:ml",
    "mathrubhumi": "https://www.mathrubhumi.com/rss",
    "twentyfour_news": "https://www.twentyfournews.com/feed",
}

# ---------------------------------------------------------------- Public Reaction Preview (Tier 3)
REACTIONS_MODEL = "claude-opus-5"
REACTIONS_EFFORT = "low"
