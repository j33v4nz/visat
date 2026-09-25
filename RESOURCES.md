# VISAT resource pack (verified September 2026)

This is everything the team needs to get ready for HackMe'26: accounts, datasets, live weather, libraries, local Kochi data, costs and pitch facts. It is research only. All code gets written at the event.

---

## 1. Do this week (setup)

| Task | Who | Notes |
|---|---|---|
| **Google Earth Engine account** | All 4 | A Google Cloud project is required, and a **noncommercial** registration needs no billing. Since **27 Apr 2026** every noncommercial project runs on a quota tier (**Community** by default). Hitting the monthly limit slows you down rather than stopping you. Register now, because approval can take days. [Access guide](https://developers.google.com/earth-engine/guides/access) · [Noncommercial tiers](https://developers.google.com/earth-engine/guides/noncommercial_tiers) · [Quota explainer](https://spatialthoughts.com/2026/02/09/gee-quota-monitoring/) |
| Streamlit Community Cloud account | M3 | Free tier has a **~1 GB resource limit**, so the app must read small precomputed files. [Manage your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) |
| GitHub + repo access | All | Repo: github.com/j33v4nz/visat |
| Python 3.12 + `uv` on every laptop | All | Pin versions (section 4) and test the install before the event |
| CPCB CCR portal login | M4 | For station temperature data (section 3) |
| **NASA Earthdata login** (for AppEEARS) | M1 | Needed for **ECOSTRESS** LST, a PS1 input dataset. [AppEEARS ECOSTRESS tutorial (PDF)](https://ecostress.jpl.nasa.gov/downloads/tutorials/06-Downloading_from_AppEEARS.pdf) |
| Anthropic API access (Tier 3 Public Reaction Preview only) | M4 | Optional. An API key or an `ant auth login` profile. Budget a few dollars (see §2d). Skip it if Tier 3 isn't reached |

---

## 2. Satellite datasets (Google Earth Engine IDs)

| Use | Dataset ID | Key details |
|---|---|---|
| **Surface temperature (target)** | `LANDSAT/LC09/C02/T1_L2`, `LANDSAT/LC08/C02/T1_L2` | `ST_B10 × 0.00341802 + 149.0` = kelvin, then subtract 273.15 for °C. Mask clouds with `QA_PIXEL`. Drop pixels where `ST_QA × 0.01` > 2 K. Overpass is ~10:30 AM local time. Landsat 9 L2 is available through Sep 2026. [L9 catalog](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC09_C02_T1_L2) · [USGS scale factors](https://www.usgs.gov/faqs/how-do-i-use-a-scale-factor-landsat-level-2-science-products) · [Science product guide](https://www.usgs.gov/media/files/landsat-8-9-collection-2-level-2-science-product-guide) |
| Albedo | Same Landsat SR bands | Liang's formula on SR_B2–B7 |
| Greenery / concrete / water indices | `COPERNICUS/S2_SR_HARMONIZED` | NDVI, NDBI, MNDWI from Sentinel-2, because Landsat surface temperature already uses NDVI-based emissivity and would leak into the target. For clouds, use the SCL band or `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`. **2017 back-test exception:** the panel reports that S2 surface reflectance over India starts around Dec 2018 (check in GEE). For 2017, use **Landsat 8 SR NDVI** (or `COPERNICUS/S2_HARMONIZED` L1C) and say so |
| Land cover fractions | `ESA/WorldCover/v200` (2021) | Classes: 10 tree · 50 built · 80 water · **95 mangroves** |
| **Land-cover change (back-test)** | `GOOGLE/DYNAMICWORLD/V1` | 10 m, **2015 to present**, 9 class probabilities. Compare Feb–Apr 2017 with Feb–Apr 2024. [Catalog](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1) · [Change-monitoring workshop](https://courses.spatialthoughts.com/gee-dw-monitoring.html) |
| Population | `JRC/GHSL/P2023A/GHS_POP` | 100 m. Epochs every 5 years to 2020, plus 2025/2030 projections. P2023A is still the latest release. [Catalog](https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2023A_GHS_POP) |
| Building height / built surface | `JRC/GHSL/P2023A/GHS_BUILT_H`, `…/GHS_BUILT_S` | Morphology features. [Built surface](https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2023A_GHS_BUILT_S) |
| Elevation | `USGS/SRTMGL1_003` | Mangrove eligibility (low-lying land) |
| **Meteorological (PS1 input)** | `ECMWF/ERA5_LAND/HOURLY` | ~9 km. Bands: `temperature_2m`, `dewpoint_temperature_2m` (for humidity), `u/v_component_of_wind_10m`, `surface_solar_radiation_downwards`, `potential_evaporation`. **v5 use: the scene-panel model.** For each clean Landsat scene, take ERA5 values at the overpass hour, so each scene row gets its own weather. The physics feature (1 − albedo) × SSRD then **varies from scene to scene** and is really learned, not just a rescaled albedo. Also used for the heat index (the *when* part of the exposure index). Report n scenes and confidence intervals |
| Urban morphology | UT-GLOBUS building heights / urban canopy parameters | GEE community catalog ([page](https://gee-community-catalog.org/projects/utglobus/)). **Check only.** Record whether it covers Kochi so we can say so honestly. v5 uses GHSL + OSM buildings (PS1 says "if available") |
| **ECOSTRESS LST (PS1 input)** | `ECO_L2T_LSTE.002` via **NASA AppEEARS** (not in GEE for Kochi; GEE only has Los Angeles tiles) | 70 m, varying overpass times, so it gives the **afternoon** scenes Landsat can't. Output is GeoTIFF with a cloud mask. **v5 use:**
- Filter to **12:00–15:30 local time**, because the ISS overpass time drifts.
- Compare **patterns, not absolute °C**: Spearman correlation on ward means, plus top-decile overlap with the Landsat ranking.
- Check alignment against the coastline, since early scenes have geolocation errors.
- Submit the AppEEARS request at hour 0.

**Note:** the `lst_err` layer is missing for 16 Dec 2025 – 10 Jun 2026, so prefer Feb–Apr 2024–2025 scenes. [Product page](https://lpdaac.usgs.gov/products/eco_l2t_lstev002/) · [VITALS notebook](https://nasa.github.io/VITALS/python/Exploring_ECOSTRESS_L2T_LSTE.html) · [Quality-flag notice](https://www.earthdata.nasa.gov/data/alerts-outages/ecostress-version-2-level-2-quality-flags-action-required) |
| Mangrove reference | Global Mangrove Watch v4.1 (1985–2025) | In the community catalog. [GEE community catalog](https://gee-community-catalog.org/projects/mangrove/) |

---

## 2b. Live data: Open-Meteo weather API

| Item | Detail |
|---|---|
| Endpoint | `https://api.open-meteo.com/v1/forecast` ([docs](https://open-meteo.com/en/docs)) |
| Key / cost | **No API key**, free for non-commercial use. Limits: under **10,000 calls/day, 5,000/hour, 600/minute** ([terms](https://open-meteo.com/en/terms), [pricing](https://open-meteo.com/en/pricing)) |
| Licence | **CC-BY 4.0**. The app footer must say "Weather data: Open-Meteo" |
| Multiple points, one call | `latitude=9.965,9.958,9.968,9.997,10.024,9.968,10.016,10.055&longitude=76.242,76.259,76.284,76.291,76.308,76.320,76.352,76.321` (Fort Kochi, Mattancherry, Ernakulam South, Kaloor, Edappally, Vyttila, Kakkanad, Kalamassery; approximate centres, M1 checks them on a map) |
| Other params | `timezone=Asia/Kolkata&forecast_days=3` |
| `current=` | `temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m` |
| `hourly=` | `temperature_2m,relative_humidity_2m,apparent_temperature,wet_bulb_temperature_2m,uv_index,shortwave_radiation,wind_speed_10m` |
| Resolution | Several km. **Tested 25 Sep 2026:** all 8 points and all variables returned (72 hourly steps), but the 8 points snapped to only **4 distinct model cells** (~7 km apart). Treat it as **city-scale**; ward-level differences come from the satellite layer |

**Heat index**
- Compute it ourselves from temperature + humidity with the NWS (Rothfusz) formula, or use `pythermalcomfort`'s `heat_index`.
- Check: 32 °C at 70% humidity should come out ≈ **41 °C**.
- Open-Meteo's `apparent_temperature` uses a different "feels-like" formula (Steadman). Show it as "feels like", and use the heat index for the risk band.

**Heat-index bands (NWS)**
| Band | Range |
|---|---|
| Caution | 27–32 °C |
| Extreme caution | 32–39 °C |
| Danger | 39–51 °C |
| Extreme danger | ≥ 52 °C |

**Never-crash pattern**
- Wrap the fetch in `st.cache_data(ttl=900)` with a 3-second timeout, so it makes only ~4 calls/hour.
- On success, overwrite the runtime cache `data/live_cache.json` (gitignored).
- On any error, load the runtime cache if it exists, otherwise the **committed snapshot `data/app/live_snapshot.json`**, and show a "Live feed unavailable, showing data from <time>" banner.
- Commit that snapshot at data freeze. The deployed app on Streamlit Cloud only has files that are in git, so the fallback must be tracked.
- Test it with Wi-Fi off.

**"Act today" (one line on the Today screen)**
- Formula: `today_peak_heat_index × ward_exposure`, where `ward_exposure` = LST rank × population × site weight (construction sites, markets, schools, anganwadis, harbours from OSM).
- The live part is *when* and *how bad*; the satellite part is *where*.
- Link each ward to the actions officials already use (section 3b): the Labour Department's 12–3 PM rest period, and KSDMA advisories.

---

## 2c. Live Malayalam news alerts (RSS)

**v5 form (judge's ruling):**
- A **static chip** on the Today screen: "⚠ Heat reported by N Malayalam channels today". Clicking it opens an expander with the headlines, links and fetch time.
- Shown **next to an official KSDMA/IMD alert chip**, which is the authority.
- No scrolling ticker and no AI summaries.
- Falls back to the last cache; if there is none, the chip is hidden.
- Tier 2, owned by M4.
- **Official source:** M4 finds one before the event. Candidates to check: IMD district-wise warnings (mausam.imd.gov.in), NDMA's **Sachet** CAP alert feed, and KSDMA bulletins. None verified yet.

**Tested 25 Sep 2026**

| Feed | URL | Status |
|---|---|---|
| **Google News, Malayalam search** (aggregator) | `https://news.google.com/rss/search?q=<query>&hl=ml&gl=IN&ceid=IN:ml` | ✅ 64 Kerala weather items in 7 days, from Asianet News, 24 News, MediaOne, News18 Malayalam, Manorama Online, Kerala Kaumudi, Indian Express Malayalam, Samakalika Malayalam |
| Mathrubhumi | `https://www.mathrubhumi.com/rss` | ✅ 48 current items (general news, so filter with keywords) |
| 24 News | `https://www.twentyfournews.com/feed` | ✅ 10 current items |
| Mathrubhumi (Feedburner) | `https://feeds.feedburner.com/mathrubhumi` | ⚠️ Responds but looks stale. Don't use |
| Manorama, MediaOne, Kerala Kaumudi, Deshabhimani, Asianet (direct) | various | ❌ 403/404, no public RSS. They are covered via the Google News aggregator |

**Query we tested** (URL-encode it):
```
(ചൂട് OR താപനില OR ഉഷ്ണതരംഗം OR സൂര്യാതപം OR അലർട്ട്) (കേരളം OR എറണാകുളം OR കൊച്ചി) -യുഎഇ -ഗൾഫ് -സൗദി when:7d
```
Without the minus terms, Gulf heat stories (UAE 41–48 °C) leak in.

**Keywords** (a native Malayalam reader on the team should review this list)

| Group | Words |
|---|---|
| Heat | ചൂട് (heat), താപനില (temperature), ഉഷ്ണതരംഗം (heatwave), സൂര്യാതപം / സൂര്യാഘാതം (sunburn/sunstroke), ഉയർന്ന താപനില |
| Alert colours | യെല്ലോ അലർട്ട് (yellow), ഓറഞ്ച് അലർട്ട് (orange), റെഡ് അലർട്ട് (red), ജാഗ്രത (caution) |
| Place | കേരളം, സംസ്ഥാനത്ത്, the 14 district names (എറണാകുളം, തൃശൂർ, പാലക്കാട് …), കൊച്ചി |

**⚠️ Unicode pitfall:** real headlines spell "alert" two ways: അലർട്ട് (atomic chillu ർ, U+0D7C) and അലര്‍ട്ട് (ര + ് + ZWJ). Before matching:
- remove U+200D (ZWJ) and U+200C (ZWNJ)
- map chillu sequences to their atomic forms
- then apply NFC normalization

**Processing**
- Parse each item: title, source, pubDate, link.
- Keep Kerala weather items. Tag heat vs rain.
- Extract district(s) + alert colour with regex.
- Group items with the same (date, district, colour). **N sources = "confirmed by N channels"**; a single source = "unconfirmed".
- **Never empty:** if there are no heat items in 7 days, show "No heat alerts this week" plus the latest Kerala weather alerts. In September, all alerts were rain alerts.
- Cache: `st.cache_data(ttl=900)`, 5-second timeout. Fall back to the runtime `data/news_cache.json` (gitignored), then to the **committed `data/app/news_snapshot.json`**. If neither exists, hide the chip.

**Fair use:** show only headline, channel name, time and a link to the original. Never copy article text. Label it "from Malayalam news; official alerts: IMD / KSDMA". This is a non-commercial hackathon prototype; a production version would ask the channels for permission or use official IMD/KSDMA feeds.

**Library:** Python's built-in `xml.etree.ElementTree` is enough; `feedparser` is an optional alternative.

---

## 2d. Public Reaction Preview: Claude API notes (Tier 3)

These notes are from the current Claude API reference. They are for writing the code at the event; nothing is pre-built.

| Item | Guidance |
|---|---|
| SDK | Official `anthropic` Python SDK: `client = anthropic.Anthropic()`. Don't use raw HTTP |
| Model | Default **`claude-opus-5`** at `output_config: {"effort": "low"}` (simple, high-volume task). Switching to `claude-sonnet-5` or `claude-haiku-4-5` to save money is the team's choice; measure quality on a few sites first |
| Call shape | **One call per (site, use type)** returns **all personas at once** as JSON. That's 5–8 sites × 3–4 uses ≈ **15–32 calls in total**, not one call per persona |
| Structured output | `output_config: {"format": {...JSON schema...}}` on `messages.create()`, or `client.messages.parse()` with a Pydantic model. The old `output_format` parameter is deprecated. Schema per persona: `persona_id, stance ∈ {support, neutral, oppose}, top_concern, would_change_mind_if, quote_en, quote_ml (optional)` |
| Prompt caching | Put the **fixed system prompt + persona table** first and mark it with `cache_control: {"type": "ephemeral"}`. The varying proposal and numbers go after it. Check that `usage.cache_read_input_tokens > 0` on the second call. Keep timestamps and random IDs out of the cached prefix |
| Refusals | Check `stop_reason` before reading content. When writing `claude-opus-5` code, enable the server-side refusal fallback per the current docs |
| Batches | The Message Batches API costs **50% less** but runs asynchronously and can take a while. Use it only if precomputing early in the night; otherwise use normal calls |
| Rough cost | About 3k input + about 3k output tokens per call ≈ **$0.09/call** on `claude-opus-5` ($5 in / $25 out per million tokens) → **about $2–4 for all precomputed results**, less with caching or batches. Re-check prices on the day |
| Number guard | After parsing, reject any quote that contains a number not present in the VISAT input numbers, and regenerate or drop it |
| Demo safety | Precompute everything into **`data/app/reactions_cache.json` (tracked in git)**. The demo reads the cache; a live re-run is optional and falls back to the cache. The API key lives in Streamlit Cloud secrets, never in the repo |
| Disclosure | Mention this in the AI-use disclosure slide: which model, what it does, and that it never changes the numbers |

---

## 3. Kochi / Kerala local data

| Data | Source | Notes |
|---|---|---|
| **Ward boundaries** | [BharatLAS: Kochi 74 wards](https://bharatlas.com/view/wards_kochi) (Parquet / GeoJSON / Shapefile) | The 2025 delimitation raised the count to **76** ([Wikipedia](https://en.wikipedia.org/wiki/Kochi_Municipal_Corporation)). No open 76-ward GIS file was found, so use 74 and say so on stage |
| Schools, hospitals, markets, bus stops, parks, roads | OpenStreetMap via `osmnx` | Tags: `amenity=school/hospital/marketplace/bus_station`, `highway=bus_stop`, `leisure=park`. Anganwadis are often unmapped, so check `amenity=kindergarten` / name search |
| Station air temperature (independent check) | [CPCB CCR portal](https://app.cpcbccr.com/ccr/#/): Vyttila, Eloor (Udyogamandal) | Registration needed. Downloads are limited to about 1 week per query at 15-minute resolution, so pull **Jan–Apr** (to match the Landsat scene stack) in chunks. [How to access Indian AQ data](https://urbanemissions.info/blog-pieces/resources-how-to-access-aqdata-in-india/) |
| Coastal Regulation Zone | [KCZMA CZMP 2019, Ernakulam maps (PDF)](https://keralaczma.gov.in/index.php/zone-maps/coastal-zone-maps-2019) | PDF only, not GIS. Use it as a visual reference. The mangrove mask is a proxy: barren/grass cells within 200 m of water, below 3 m elevation, not built, near existing Global Mangrove Watch extent |
| Kawaki programme | [C-HED: Kawaki](https://c-hed.org/kawaki-project-inaugurated/) · [NbS4India case study](https://www.nbs4india.org/case-studies/the-kawaki-initiative/) | Launched in 2020 by Kochi Municipal Corporation with WRI-India and C-HED. Native-tree groves placed with data in heat-vulnerable areas |
| C-HED | [Climate change](https://c-hed.org/climate-change-2/) · [Designated climate-action cell](https://c-hed.org/workshop-on-advancing-climate-action-in-kochi-facilitating-c-heds-priorities-as-kochis-designated-cell-for-climate-action/) | Centre for Heritage, Environment & Development, **Kochi's designated cell for climate action**. This is our target user |
| **IURWTS canals (KMRL)** | [KMRL IURWTS](https://kochimetro.org/iurwts/) · [Swarajya](https://swarajyamag.com/news-brief/kochi-to-have-more-navigable-waterways-as-canals-set-for-transformation-under-rs-3716-crore-urban-revival-plan) | ₹3,716 crore; 6 canals (Edappally, Perandoor, Chilavannur, Thevara, Konthuruthy, Market — re-verified against Onmanorama/Swarajya, "Thevara–Perandoor" in an earlier draft of this doc read as one canal but was Thevara and Perandoor, two separate canals) to be widened to 16.5 m; land acquisition under way. Driven by flooding and transport. **v5:** shown as a committed overlay with 0 °C credit, plus canal-bank tree strips |

## 3b. Kerala rules and advisories (from panel research; M4 re-verifies before the event)

| Item | What it says | Use in VISAT | Source |
|---|---|---|---|
| Labour Commissioner order, 2026 | Outdoor workers rest **12–3 PM**, **13 Feb – 20 May 2026**; at most 8 hours between 7 AM and 7 PM | Linked from "Act today"; wards with construction sites ranked higher | [Kerala Kaumudi](https://keralakaumudi.com/en/news/news.php?id=1478856&u=govt-reschedules-working-hours-for-labourers-as-temperatures-soar-rest-from-12-3-pm) |
| KSDMA heat advisories | Avoid direct sun 11 AM–3 PM; water, ORS, cotton clothing; schools avoid assemblies and outdoor classes; local bodies run drinking-water kiosks (*thanneer pandal*); fire safety at markets and waste dumps; protect livestock | Action list on "Act today" and the Ward Card | KSDMA (find the current PDF) |
| KMBR 2019 | Government may grant extra FSI or relaxations for climate-mitigation and conservation projects | Heat-Neutral Check framed as a voluntary offset that could earn an FSI incentive | [Onmanorama](https://www.onmanorama.com/news/kerala/2020/09/24/building-rules-relaxations-details-kerala-cabinet.html) |
| SEIAA Kerala (EIA 8(a)) | Projects of 20,000–150,000 m² built-up area need state environmental clearance (Form-1A) | Heat-Neutral output could be attached to Form-1A for IT parks and malls | Verify with MoEFCC EIA 2006 schedule |
| Kochi Master Plan 2040 / nature-based solutions | Resilience guidance adopted | "Who signs" line for Ward Card actions | [WRI](https://www.wri.org/outcomes/kochi-india-adopts-nature-based-solutions-climate-resilience) |

**Framing rule:** the Heat-Neutral Check is a **screening tool and a policy proposal**, never an "approval" or a legal requirement.

---

## 4. Libraries (current versions to practise with)

| Library | Why | Gotchas |
|---|---|---|
| `earthengine-api` | Data export | `ee.Authenticate()` then `ee.Initialize(project="<cloud-project>")` |
| `pandas`, `pyarrow`, `numpy`, `scipy`, `scikit-learn` | Tables, focal filters, `NearestNeighbors`, `GroupKFold` | `scipy.ndimage.uniform_filter` for 300/500 m neighbourhood features |
| `xgboost` | Model | `monotone_constraints` per feature. Constrain all correlated partners |
| `shap` | Drivers | Use native TreeSHAP (`pred_contribs=True`), precomputed offline |
| `streamlit` + `pydeck` | Dashboard | `st.pydeck_chart(..., on_select="rerun")` returns **picked objects only**, not arbitrary lat/lon, and **every layer needs an `id`**. So the Check-a-Project sites are **5–8 pre-drawn pickable polygons**, the use type comes from `st.segmented_control`, and `view_state` is kept in `st.session_state` so reruns don't reset the map. The budget uses **preset buttons (₹1/10/50 crore)** with cached results instead of a laggy slider. Dark theme; hide the header with CSS. [Docs](https://docs.streamlit.io/develop/api-reference/charts/st.pydeck_chart) · [2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) |
| `streamlit-image-comparison` (Tier 3) | Before/after view | Compares two pre-rendered PNGs (e.g. 2017 vs 2024, before vs after the offset) |
| `osmnx` (2.1) | OSM features (buildings, roads, sites, canals) | **v2 API:** `graph_from_bbox(bbox=(left, bottom, right, top))`; features via `ox.features_from_bbox`. [User reference](https://osmnx.readthedocs.io/en/stable/user-reference.html) |
| `pythermalcomfort` (optional) | Heat index | `heat_index` as an alternative to coding the NWS formula ourselves. [Docs](https://pythermalcomfort.readthedocs.io/) |
| `anthropic` (Tier 3) | Public Reaction Preview | Structured outputs via `output_config.format` or `messages.parse()`; prompt caching; typed exceptions (`RateLimitError`, `APIConnectionError`). See §2d |
| `requests` | Live Open-Meteo fetch | Always pass `timeout=3`; never let an exception reach the UI |
| `pytest`, `ruff` | Tests and lint in CI | GitHub Actions, set up in hour 2. Tests to include:<br>• a mocked network failure loads the cache fallback<br>• the plan stays within budget<br>• no intervention warms a cell<br>• **joint re-prediction ≠ sum of separate ones is handled**<br>• **no double-counted spillover** |

---

## 4b. Deployment (Streamlit Community Cloud), from the repo cross-check

| Item | What to do at the event |
|---|---|
| Dependency file | Community Cloud **recommends `requirements.txt`**. It does **not** read `uv.lock`, and it treats `pyproject.toml` as Poetry format. So add an **app-only** `requirements.txt`: `streamlit`, `pydeck`, `pandas`, `pyarrow`, `numpy`, `requests` (+ `xgboost` only if the app re-predicts; + `anthropic` and `streamlit-image-comparison` only if Tier 3 ships). **No Earth Engine, geopandas/GDAL or training libraries** in the cloud build. [Streamlit docs: app dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) · [uv support request](https://github.com/streamlit/streamlit/issues/9502) |
| Reproducibility | Commit **`uv.lock`** (currently gitignored) for the full pipeline environment. Pin versions in `requirements.txt` |
| App data | The cloud app only sees files that are in git. Commit small, app-ready files to a tracked **`data/app/`** folder: parquet grid, heat PNG, ward GeoJSON, precomputed presets and Heat-Neutral results, `live_snapshot.json`, `news_snapshot.json`, `reactions_cache.json`. Keep `data/raw/`, `data/frozen/` and the runtime caches ignored. Aim for tens of MB, well under the ~1 GB app limit |
| Secrets | Add `.streamlit/secrets.toml` to `.gitignore`. Put any API key in the app's **Secrets** settings on Community Cloud and read it with `st.secrets` |
| Cold start | Open the app 10 minutes before judging. Keep the backup recording ready |

---

## 5. Resources per feature

| Feature | What to read / reuse |
|---|---|
| Heat map | Landsat ST scaling (above), [GEE Landsat guide](https://developers.google.com/earth-engine/guides/landsat), [Digital Earth Africa LST notebook](https://docs.digitalearthafrica.org/en/latest/sandbox/notebooks/Datasets/Landsat_Surface_Temperature.html) (same Collection 2 logic) |
| Model + honest validation | **Scene-panel:** rows = cells × scenes, with that scene's ERA5 values + (1 − albedo) × SSRD. XGBoost monotone constraints. `GroupKFold` on 2 km block IDs **across all scenes** (a block never appears in both train and test). Compare against a linear model and an unconstrained XGBoost; report n and CIs. Fallback: a single-composite model |
| Validity matrix | For each intervention: analog / energy-balance formula / no °C credit, plus within-support %. Formula interventions: ΔT ≈ Δα × S / h (cool roofs, cool pavements), latent-cooling estimate (green roofs) |
| Why (SHAP) | Group correlated features (greenery = NDVI + tree fraction) before showing bars |
| Analog transitions | `sklearn.neighbors.NearestNeighbors` (k=20) on context features, then move toward the neighbours' median. Cap at the observed 90th percentile |
| Back-test | Dynamic World 2017 vs 2024 (Feb–Apr) + Landsat LST for both periods. **Normalise each scene to its city median first**, so year-to-year weather doesn't dominate. Then plot predicted vs observed ΔLST |
| Optimizer | Greedy on (ΔT × people × vulnerability weight) / ₹, re-scoring neighbours via focal features. Precompute the ₹1–50 crore curve |
| Physics check | ΔT_roof ≈ Δα × S / h, with S ≈ 750 W/m² and h ≈ 25 W/m²K, scaled by roof fraction |
| **Heat-Neutral Development Check** | Reverse analog transition using **donors matched to the site's context** (inland vs port/industrial). Joint re-prediction of the site and its neighbours, then the cheapest offset to 0 **surface-°C (morning)**. Framed as a screening tool and policy proposal (section 3b). Precedent abroad: [ACEEE UHI policy database](https://database.aceee.org/city/mitigation-urban-heat-islands), [OCRAP model policy](https://ocrap.net/policies/urban-heat-model/) |
| Ward Heat Card | HTML template printed from the browser; Malayalam in **Noto Sans Malayalam** (Google Fonts), translated by a team member |

---

## 6. Intervention costs (re-verify before the event)

| Fix | Cost | Source |
|---|---|---|
| Street tree, incl. 5-year care | ₹3,100 / tree | BBMP tender ([Deccan Herald](https://www.deccanherald.com/amp/story/india%2Fkarnataka%2Fgreen-lessons-past-2227715)) |
| Cool roof | ₹300 / m² | [Telangana Cool Roof Policy 2023](https://telanganatoday.com/indias-first-cool-roof-policy-launched-in-telangana) |
| Cool roof recoat | ₹150 / m² every 3 years | Our estimate (humid-climate soiling) |
| Mangrove restoration | ₹1–8 lakh / ha | [CEEW](https://www.ceew.in/ecological-mangrove-restoration); [One Earth 2025](https://www.sciencedirect.com/science/article/pii/S259033222500168X) |
| Cool pavement | ₹350 / m² (range ₹190–500, ~3-year life) | Reflective coating ~₹186/m² material ([Flipkart LuminX](https://www.flipkart.com/luminx-cool-pavement-heat-reflective-coating-roads-walkways-parking-areas-white-resistance-elastomeric-emulsion-wall-paint/p/itmc4728e92353a1)) + labour (panel estimate) |
| Pond restoration | ~₹45 lakh / ha | Amrit Sarovar ~₹18 lakh/acre ([Vikaspedia](https://en.vikaspedia.in/viewcontent/schemesall/schemes-for-farmers/mission-amrit-sarovar?lgn=en)) |
| Canal-bank tree strip | ~₹1,000 / m | Estimate: ~1 tree per 3 m at ₹3,100/tree |
| IURWTS canals | ₹3,716 crore (committed; **not bought by our optimizer**) | [KMRL](https://kochimetro.org/iurwts/) |
| Green roof (simulated, rarely chosen) | ₹7,500 / m² | [IndiaSpend](https://www.indiaspend.com/explainers/explained-as-indoor-heat-rises-can-india-turn-to-green-roofs-867308) |

---

## 7. Fresh facts for the pitch (use 2026, not 2024)

- **April 2026:** IMD issued heatwave warnings for Palakkad, Thrissur and Kollam, with **Ernakulam forecast up to ~38 °C**. ([Onmanorama, 23 Apr 2026](https://www.onmanorama.com/news/kerala/2026/04/23/kerala-heatwave-warning-palakkad-thrissur-kollam.html))
- **24 April 2026:** orange alert in 3 districts, and **holidays declared for educational institutions** in Kollam and Thrissur. ([Onmanorama](https://www.onmanorama.com/news/kerala/2026/04/24/kerala-heatwave-alert-temperature-orange-holiday-kollam-thrissur-palakkad.amp.html))
- Yellow alerts in 12 districts through March–April 2026. ([Onmanorama, 25 Mar 2026](https://www.onmanorama.com/news/kerala/2026/03/25/maximum-temperature-go-up-in-kerala-weather-today.html))
- KSDMA advisory: highest risk for infants, the elderly, the chronically ill and **outdoor workers**. KSDMA also debunked a viral "55 °C" WhatsApp message ([Kerala Kaumudi](https://keralakaumudi.com/en/news/news.php?id=1731308&u=)). That's a good hook: *"people need real heat data, not rumours."*
- Kochi Corporation wards went from 74 to 76 in the 2025 delimitation.

---

## 8. New Q&A item: "Doesn't Kawaki already do this?"

> "Kawaki proves Kochi already wants data-driven cooling. It picks grove sites in heat-vulnerable areas. VISAT is the next layer. It compares trees against cool roofs and mangroves under a ₹ budget, checks new projects so they don't add heat, and verifies predictions against real 2017→2024 change. It gives C-HED a tool to plan the next Kawaki sites, not a replacement."

---

## 9. Pre-event checklist

- [ ] GEE noncommercial project working for **all 4** members (run one tiny export to confirm)
- [ ] Python 3.12 + `uv` + all libraries installed and importing on every laptop
- [ ] Streamlit Cloud hello-world deployed (M3)
- [ ] Open-Meteo test request for the 8 Kochi points works from a browser (M3), and the coordinates are checked on a map (M1)
- [ ] Malayalam news feeds open in a browser (Google News query, Mathrubhumi, 24 News), and a native reader reviews the keyword list (M4)
- [ ] Kochi 74-ward GeoJSON downloaded from BharatLAS (M1)
- [ ] CPCB Vyttila + Eloor temperature, Jan–Apr, downloaded (M4)
- [ ] **Team decision made** on the pre-event code/config files (`config.py`, tests, CI, `pyproject.toml`): move them to a `prep` branch or delete them before the event (PLAN §12)
- [ ] Costs re-verified; sources saved for slides (M4)
- [ ] Kerala rules re-verified: Labour order dates, KMBR FSI clause, SEIAA thresholds, IURWTS status (M4)
- [ ] An official KSDMA/IMD alert source found and tested (M4)
- [ ] Check in GEE whether S2 surface reflectance exists over Kochi in 2017, and whether Landsat NDVI is needed for the back-test (M1)
- [ ] NASA Earthdata account works; a test AppEEARS ECOSTRESS request for Kochi is done (M1)
- [ ] UT-GLOBUS Kochi coverage checked (M1)
- [ ] **PS1 compliance checklist (PLAN.md section 0) re-checked by the whole team**
- [ ] C-HED / councillor / KSDMA contacted (M4). **Use only genuine quotes.** If there's no reply, say "awaiting response"
- [ ] Slide template, pitch script and AI-use disclosure drafted (M4)
- [ ] Sketches of the 4 screens and the ward card, and a dark-theme test on a projector (M3)
- [ ] Practice run of the full pipeline (practice code stays off the event repo)
- [ ] Two phone hotspots with data packs

---

*Compiled by Jeevan George*
