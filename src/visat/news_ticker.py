"""Live Malayalam news alert chip (RESOURCES.md §2c). A static chip on the
Today screen next to the official KSDMA/IMD alert — the official alert is
the authority, this is supporting evidence only. Shows headline, channel,
time and link, never article text.

Three-layer fallback, same pattern as live_weather: runtime cache, then the
committed snapshot, then the chip hides itself entirely (never shows a
broken or empty chip).
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from . import config

RUNTIME_CACHE_PATH = Path("data/news_cache.json")  # gitignored
COMMITTED_SNAPSHOT_PATH = Path("data/app/news_snapshot.json")  # tracked in git

# Malayalam chillu letters are ambiguous in real headlines: some encode the
# atomic chillu codepoint (U+0D7C ർ), others encode the decomposed sequence
# (ര + virama U+0D4D, sometimes plus a ZWJ U+200D). Normalise both to the
# atomic form before keyword matching, per RESOURCES.md §2c.
_ZERO_WIDTH_RE = re.compile("[‌‍]")
_CHILLU_DECOMPOSED_TO_ATOMIC = {
    "ര്": "ർ",  # ra + virama -> chillu rr
    "ല്": "ൽ",  # la + virama -> chillu l
    "ള്": "ൾ",  # lla + virama -> chillu ll
    "ണ്": "ണ്‌",  # left as-is; rare in this keyword set
    "ന്": "ൻ",  # na + virama -> chillu n
}


def normalise_malayalam(text: str) -> str:
    """Strip zero-width joiners, fold decomposed chillu sequences to their
    atomic form, then NFC-normalise. Must run on both the headline text and
    the keyword list before comparing, or real-world spelling variants get
    silently missed."""
    text = _ZERO_WIDTH_RE.sub("", text)
    for decomposed, atomic in _CHILLU_DECOMPOSED_TO_ATOMIC.items():
        text = text.replace(decomposed, atomic)
    return unicodedata.normalize("NFC", text)


@dataclass
class NewsItem:
    title: str
    source: str
    link: str
    published: str
    districts: list[str] = field(default_factory=list)
    alert_colour: str | None = None
    is_heat: bool = False


def _stem_match(keyword: str, text_norm: str, *, min_stem_len: int = 3) -> bool:
    """Malayalam is agglutinative: place and heat words almost always show
    up inflected in real headlines (locative/genitive suffixes — e.g.
    "എറണാകുളം" (Ernakulam) appears as "എറണാകുളത്ത്" (in Ernakulam)), not in
    their dictionary form. An exact substring match against the nominative
    form misses most real headlines, so match on a stem (keyword minus its
    last character) instead, for keywords long enough that this doesn't
    risk false positives on short words. This is a heuristic, not real
    morphological analysis — a native Malayalam reader should review it,
    per RESOURCES.md §2c."""
    kw_norm = normalise_malayalam(keyword)
    stem = kw_norm[:-1] if len(kw_norm) > min_stem_len else kw_norm
    return stem in text_norm


def _matches_any(text: str, keywords: tuple[str, ...] | dict[str, str]) -> bool:
    norm = normalise_malayalam(text)
    values = keywords.values() if isinstance(keywords, dict) else keywords
    return any(_stem_match(kw, norm) for kw in values)


def _extract_districts(text: str) -> list[str]:
    norm = normalise_malayalam(text)
    return [d for d in config.NEWS_PLACE_KEYWORDS if _stem_match(d, norm)]


def _extract_alert_colour(text: str) -> str | None:
    norm = normalise_malayalam(text)
    for colour, kw in config.NEWS_ALERT_COLOUR_KEYWORDS.items():
        if _stem_match(kw, norm):
            return colour
    return None


def _parse_rss(xml_text: str, source_name: str) -> list[NewsItem]:
    items: list[NewsItem] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    for item in root.iterfind(".//item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        link = (item.findtext("link") or "").strip()
        published = (item.findtext("pubDate") or "").strip()
        source_el = item.find("source")
        source = source_el.text.strip() if source_el is not None and source_el.text else source_name

        is_heat = _matches_any(title, config.NEWS_HEAT_KEYWORDS)
        items.append(
            NewsItem(
                title=title,
                source=source,
                link=link,
                published=published,
                districts=_extract_districts(title),
                alert_colour=_extract_alert_colour(title),
                is_heat=is_heat,
            )
        )
    return items


def _fetch_feed(name: str, url_template: str) -> list[NewsItem]:
    url = url_template.format(query=quote(config.NEWS_RSS_QUERY)) if "{query}" in url_template else url_template
    response = requests.get(url, timeout=config.NEWS_RSS_TIMEOUT_SECONDS)
    response.raise_for_status()
    return _parse_rss(response.text, name)


def fetch_all_feeds() -> list[NewsItem]:
    """Fetch every configured feed. A single feed failing doesn't take down
    the others — only a total failure should trigger the cache fallback in
    `get_news_chip`."""
    items: list[NewsItem] = []
    for name, url in config.NEWS_RSS_FEEDS.items():
        try:
            items.extend(_fetch_feed(name, url))
        except (requests.RequestException, ET.ParseError):
            continue
    return items


def group_confirmations(items: list[NewsItem]) -> list[dict[str, Any]]:
    """Group items reporting the same (district, alert colour): N distinct
    sources = "confirmed by N channels"; one source = "unconfirmed"."""
    groups: dict[tuple[str, str | None], dict[str, Any]] = {}
    for item in items:
        if not item.is_heat:
            continue
        district = item.districts[0] if item.districts else "Kerala"
        key = (district, item.alert_colour)
        group = groups.setdefault(
            key, {"district": district, "alert_colour": item.alert_colour, "sources": set(), "items": []}
        )
        group["sources"].add(item.source)
        group["items"].append(item)

    result = []
    for group in groups.values():
        result.append(
            {
                "district": group["district"],
                "alert_colour": group["alert_colour"],
                "n_channels": len(group["sources"]),
                "confirmed": len(group["sources"]) > 1,
                "items": group["items"],
            }
        )
    return sorted(result, key=lambda g: g["n_channels"], reverse=True)


def _serialise(items: list[NewsItem]) -> list[dict[str, Any]]:
    return [
        {
            "title": i.title,
            "source": i.source,
            "link": i.link,
            "published": i.published,
            "districts": i.districts,
            "alert_colour": i.alert_colour,
            "is_heat": i.is_heat,
        }
        for i in items
    ]


def _deserialise(raw: list[dict[str, Any]]) -> list[NewsItem]:
    return [NewsItem(**r) for r in raw]


def _load_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def get_news_chip(*, _now: float | None = None) -> dict[str, Any] | None:
    """Returns the chip payload, or None if the chip should be hidden
    entirely (no live feed and no cache at all — never show a broken chip).

    Caller wraps this in `st.cache_data(ttl=config.NEWS_RSS_CACHE_TTL_SECONDS)`.
    """
    now = _now if _now is not None else time.time()

    try:
        items = fetch_all_feeds()
        if not items:
            raise RuntimeError("all feeds returned nothing")
        groups = group_confirmations(items)
        payload = {"groups": groups, "all_items": _serialise(items), "fetched_at": now, "source": "live"}
        RUNTIME_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        RUNTIME_CACHE_PATH.write_text(
            json.dumps({"groups": groups, "all_items": _serialise(items), "fetched_at": now})
        )
        return _finalise(payload)
    except (requests.RequestException, RuntimeError):
        pass

    for path, source in ((RUNTIME_CACHE_PATH, "runtime_cache"), (COMMITTED_SNAPSHOT_PATH, "committed_snapshot")):
        cached = _load_cache(path)
        if cached is not None:
            cached["source"] = source
            return _finalise(cached)

    return None  # no live feed, no cache anywhere — hide the chip


def _finalise(payload: dict[str, Any]) -> dict[str, Any]:
    """Never-empty rule: if there are no heat items, say so explicitly and
    fall back to showing the latest general Kerala weather alerts instead."""
    heat_groups = [g for g in payload["groups"] if g.get("alert_colour") or g.get("district")]
    payload["has_heat_alerts"] = len(heat_groups) > 0
    payload["headline"] = (
        f"⚠ Heat reported by {heat_groups[0]['n_channels']} Malayalam channels today"
        if heat_groups
        else "No heat alerts this week"
    )
    return payload
