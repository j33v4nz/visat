"""Malayalam news heat chip: headline + channel + time + link only (never article text).
Supporting evidence next to the official KSDMA/IMD alert — the official alert is the authority."""

import json
import re
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from visat import config

IST = ZoneInfo("Asia/Kolkata")
CHILLU = {"ണ്‍": "ൺ", "ന്‍": "ൻ", "ര്‍": "ർ", "ല്‍": "ൽ", "ള്‍": "ൾ", "ക്‍": "ൿ"}
HEAT = ["ചൂട്", "താപനില", "ഉഷ്ണതരംഗ", "സൂര്യാതപ", "സൂര്യാഘാത", "heat", "temperature"]
RAIN = ["മഴ", "rain"]
PLACE = ["കേരള", "സംസ്ഥാന", "എറണാകുളം", "കൊച്ചി", "kerala", "kochi", "ernakulam",
         "തിരുവനന്തപുരം", "കൊല്ലം", "പത്തനംതിട്ട", "ആലപ്പുഴ", "കോട്ടയം", "ഇടുക്കി", "തൃശൂർ",
         "പാലക്കാട്", "മലപ്പുറം", "കോഴിക്കോട്", "വയനാട്", "കണ്ണൂർ", "കാസർകോട്"]
GULF = ["യുഎഇ", "ഗൾഫ്", "സൗദി", "ദുബായ്", "ഖത്തർ", "കുവൈത്ത്", "ഒമാൻ", "uae", "dubai", "saudi"]
COLOURS = {"റെഡ്": "Red", "ഓറഞ്ച്": "Orange", "യെല്ലോ": "Yellow", "red": "Red", "orange": "Orange",
           "yellow": "Yellow"}


def normalize(text: str) -> str:
    for seq, atomic in CHILLU.items():
        text = text.replace(seq, atomic)
    text = text.replace("‍", "").replace("‌", "")
    return unicodedata.normalize("NFC", text).lower()


def classify(title: str) -> dict | None:
    t = normalize(title)
    if any(normalize(g) in t for g in GULF) or not any(normalize(p) in t for p in PLACE):
        return None
    heat = any(normalize(k) in t for k in HEAT)
    rain = any(normalize(k) in t for k in RAIN)
    if not (heat or rain or "അലർട്ട്" in t or "alert" in t):
        return None
    colour = next((v for k, v in COLOURS.items() if normalize(k) in t), None)
    return {"kind": "heat" if heat else "weather", "colour": colour}


def parse_rss(xml_text: str, feed: str) -> list[dict]:
    items = []
    for it in ET.fromstring(xml_text).iter("item"):
        title = (it.findtext("title") or "").strip()
        src = it.find("source")
        channel = src.text.strip() if src is not None and src.text else feed
        try:
            when = parsedate_to_datetime(it.findtext("pubDate")).astimezone(IST)
        except (TypeError, ValueError):
            continue
        tag = classify(title)
        if tag:
            title = re.sub(r"\s+-\s+[^-]+$", "", title) if feed == "google_news_ml" else title
            items.append({"title": title, "channel": channel, "link": it.findtext("link"),
                          "time": when.isoformat(timespec="minutes"), **tag})
    return items


def fetch() -> list[dict]:
    items = []
    for name, url in config.NEWS_FEEDS.items():
        if "{query}" in url:
            url = url.format(query=urllib.parse.quote(config.NEWS_QUERY))
        try:
            r = requests.get(url, timeout=config.NEWS_TIMEOUT_S, headers={"User-Agent": "VISAT/0.1"})
            r.raise_for_status()
            items += parse_rss(r.text, name)
        except (requests.RequestException, ET.ParseError):
            continue
    if not items:
        raise RuntimeError("no news items")
    return items


def chip(items: list[dict], today: str | None = None) -> dict:
    today = today or datetime.now(IST).strftime("%Y-%m-%d")
    items = sorted(items, key=lambda i: i["time"], reverse=True)
    heat_today = [i for i in items if i["kind"] == "heat" and i["time"][:10] == today]
    heat_week = [i for i in items if i["kind"] == "heat"]
    channels = sorted({i["channel"] for i in heat_today})
    if heat_today:
        text = f"⚠ Heat reported by {len(channels)} Malayalam channel{'s' * (len(channels) != 1)} today"
        shown = heat_today
    elif heat_week:
        text, shown = "Heat mentioned in Malayalam news this week", heat_week
    else:
        text, shown = "No heat alerts this week — latest Kerala weather alerts", items
    return {"text": text, "n_channels": len(channels), "items": shown[:8],
            "confirmed": len(channels) >= 2}


def get(cache: Path, snapshot: Path, fetcher=fetch) -> dict | None:
    """live → runtime cache → committed snapshot → None (chip hidden). Never raises."""
    try:
        items = fetcher()
        data = {"items": items, "fetched_at": datetime.now(IST).isoformat(timespec="minutes"),
                "status": "live"}
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data, ensure_ascii=False))
        except OSError:
            pass
    except Exception:  # noqa: BLE001 — any fetch/parse failure falls through to cache/snapshot
        data = None
        for path, status in ((cache, "cached"), (snapshot, "snapshot")):
            try:
                data = json.loads(path.read_text())
                data["status"] = status
                break
            except (OSError, ValueError):
                continue
        if data is None:
            return None
    return {**chip(data["items"]), "status": data["status"], "fetched_at": data.get("fetched_at")}
