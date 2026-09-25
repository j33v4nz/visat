"""Live weather strip: Open-Meteo, with the three-layer never-crash fallback
from RESOURCES.md §2b — runtime cache, then the committed snapshot, then a
"feed unavailable" banner. Never let a network exception reach the UI.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from . import config
from .heat_index import heat_index_band, heat_index_celsius

RUNTIME_CACHE_PATH = Path("data/live_cache.json")  # gitignored
COMMITTED_SNAPSHOT_PATH = Path("data/app/live_snapshot.json")  # tracked in git


@dataclass
class LiveWeatherResult:
    data: dict[str, Any]
    source: str  # "live", "runtime_cache", "committed_snapshot"
    fetched_at: float
    stale: bool


def _build_url() -> str:
    lats = ",".join(str(lat) for lat, _ in config.KOCHI_POINTS.values())
    lons = ",".join(str(lon) for _, lon in config.KOCHI_POINTS.values())
    return (
        f"{config.OPEN_METEO_ENDPOINT}"
        f"?latitude={lats}&longitude={lons}"
        f"&timezone={config.OPEN_METEO_TIMEZONE}"
        f"&forecast_days={config.OPEN_METEO_FORECAST_DAYS}"
        f"&current={','.join(config.OPEN_METEO_CURRENT_VARS)}"
        f"&hourly={','.join(config.OPEN_METEO_HOURLY_VARS)}"
    )


def _fetch_live() -> dict[str, Any]:
    response = requests.get(_build_url(), timeout=config.OPEN_METEO_TIMEOUT_SECONDS)
    response.raise_for_status()
    raw = response.json()
    return _summarise(raw)


def _summarise(raw: Any) -> dict[str, Any]:
    """Reduce the raw multi-point Open-Meteo response to what the Today
    screen needs: one city-scale current reading plus the heat-index band.

    Open-Meteo returns one object per point when queried with comma-joined
    lat/lon lists, so `raw` is a list here.
    """
    points = raw if isinstance(raw, list) else [raw]
    temps = [p["current"]["temperature_2m"] for p in points]
    rhs = [p["current"]["relative_humidity_2m"] for p in points]
    apparents = [p["current"]["apparent_temperature"] for p in points]
    winds = [p["current"]["wind_speed_10m"] for p in points]

    temp_c = sum(temps) / len(temps)
    rh_pct = sum(rhs) / len(rhs)
    hi_c = heat_index_celsius(temp_c, rh_pct)

    return {
        "temperature_c": round(temp_c, 1),
        "relative_humidity_pct": round(rh_pct, 1),
        "apparent_temperature_c": round(sum(apparents) / len(apparents), 1),
        "wind_speed_kmh": round(sum(winds) / len(winds), 1),
        "heat_index_c": hi_c,
        "heat_index_band": heat_index_band(hi_c),
        "n_points": len(points),
        "attribution": config.OPEN_METEO_ATTRIBUTION,
    }


def _load_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def get_live_weather(*, _now: float | None = None) -> LiveWeatherResult:
    """Fetch live weather, falling back through runtime cache then the
    committed snapshot on any failure. Caller (the Streamlit layer) should
    wrap this call in `st.cache_data(ttl=config.OPEN_METEO_CACHE_TTL_SECONDS)`
    so it isn't re-fetched on every rerun.
    """
    now = _now if _now is not None else time.time()

    try:
        data = _fetch_live()
        RUNTIME_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        RUNTIME_CACHE_PATH.write_text(json.dumps({"data": data, "fetched_at": now}))
        return LiveWeatherResult(data=data, source="live", fetched_at=now, stale=False)
    except (requests.RequestException, ValueError, KeyError):
        pass

    cached = _load_cache(RUNTIME_CACHE_PATH)
    if cached is not None:
        return LiveWeatherResult(
            data=cached["data"], source="runtime_cache", fetched_at=cached["fetched_at"], stale=True
        )

    snapshot = _load_cache(COMMITTED_SNAPSHOT_PATH)
    if snapshot is not None:
        return LiveWeatherResult(
            data=snapshot["data"], source="committed_snapshot", fetched_at=snapshot["fetched_at"], stale=True
        )

    raise RuntimeError(
        "No live weather available and no fallback found — commit "
        f"{COMMITTED_SNAPSHOT_PATH} at data freeze so this can never happen live."
    )
