"""Live 'Today in Kochi' strip from Open-Meteo (free, no key, CC-BY 4.0), with a never-crash fallback."""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import requests

from uhi import config
from uhi.features import heat_band, heat_index_c

IST = ZoneInfo("Asia/Kolkata")
ATTRIBUTION = "Weather data: Open-Meteo (CC-BY 4.0)"


def fetch() -> list[dict]:
    lats = ",".join(str(p[0]) for p in config.KOCHI_POINTS.values())
    lons = ",".join(str(p[1]) for p in config.KOCHI_POINTS.values())
    params = {
        "latitude": lats, "longitude": lons, "timezone": "Asia/Kolkata", "forecast_days": 3,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m",
        "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,wet_bulb_temperature_2m",
    }
    r = requests.get(config.OPEN_METEO_URL, params=params, timeout=config.OPEN_METEO_TIMEOUT_S)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else [data]


def summarise(raw: list[dict]) -> dict:
    cur = [p["current"] for p in raw]
    t = float(np.median([c["temperature_2m"] for c in cur]))
    rh = float(np.median([c["relative_humidity_2m"] for c in cur]))
    feels = float(np.median([c["apparent_temperature"] for c in cur]))
    hi_now = float(heat_index_c(t, rh))
    hours = raw[0]["hourly"]["time"]
    temps = np.median([p["hourly"]["temperature_2m"] for p in raw], axis=0)
    hums = np.median([p["hourly"]["relative_humidity_2m"] for p in raw], axis=0)
    his = heat_index_c(temps, hums)
    today = cur[0]["time"][:10]
    today_idx = [i for i, h in enumerate(hours) if h.startswith(today)]
    peak_i = today_idx[int(np.argmax(his[today_idx]))] if today_idx else int(np.argmax(his))
    return {
        "time": cur[0]["time"], "temp_c": round(t, 1), "rh": round(rh), "feels_c": round(feels, 1),
        "heat_index_c": round(hi_now, 1), "band": heat_band(hi_now),
        "peak_heat_index_c": round(float(his[peak_i]), 1), "peak_time": hours[peak_i],
        "peak_band": heat_band(float(his[peak_i])),
        "forecast": [{"time": h, "heat_index_c": round(float(v), 1)} for h, v in zip(hours, his)],
        "label": config.LABEL_LIVE, "attribution": ATTRIBUTION,
    }


def get(cache: Path, snapshot: Path, fetcher=fetch) -> dict:
    """live → runtime cache → committed snapshot → unavailable. Never raises."""
    try:
        data = summarise(fetcher())
        data["status"] = "live"
        data["fetched_at"] = datetime.now(IST).isoformat(timespec="minutes")
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data))
        except OSError:
            pass
        return data
    except Exception:  # noqa: BLE001 — any fetch/pickle failure falls through to cache/snapshot
        for path, status in ((cache, "cached"), (snapshot, "snapshot")):
            try:
                data = json.loads(path.read_text())
                data["status"] = status
                return data
            except (OSError, ValueError):
                continue
    return {"status": "unavailable", "label": config.LABEL_LIVE, "attribution": ATTRIBUTION}
