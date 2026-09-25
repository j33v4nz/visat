"""VISAT: Kochi Heat Action Planner — Streamlit entry point.

Four screens (PLAN.md §2): Today / Plan (rupee) / Check a Project / Proof &
Ward Card. Dark theme, screen names as questions, key numbers large.

Run locally:  streamlit run app.py
Deploy: Streamlit Community Cloud reads requirements.txt (not pyproject.toml
— see RESOURCES.md §4b), so keep this file's imports limited to what's in
that lean file: streamlit, pydeck, pandas, numpy, requests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from visat import config
from visat.live_weather import get_live_weather
from visat.news_ticker import get_news_chip
from visat.validity_matrix import INTERVENTIONS

st.set_page_config(page_title="VISAT — Kochi Heat Action Planner", layout="wide", page_icon="🌡️")

# --- Dark theme / hide chrome (PLAN.md UX rules: dark, red/orange = heat, teal = fixes) ---
st.markdown(
    """
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background-color: #0b0b0f; color: #f2f2f2; }
    .visat-big-number { font-size: 3rem; font-weight: 700; }
    .visat-heat { color: #ff6a3d; }
    .visat-fix { color: #2dd4bf; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=config.OPEN_METEO_CACHE_TTL_SECONDS)
def cached_live_weather():
    return get_live_weather()


@st.cache_data(ttl=config.NEWS_RSS_CACHE_TTL_SECONDS)
def cached_news_chip():
    return get_news_chip()


def live_strip() -> None:
    """Shown on every screen: temperature, humidity, heat index and danger
    band, plus the news chip next to an official-alert placeholder."""
    try:
        weather = cached_live_weather()
    except RuntimeError as exc:
        st.error(str(exc))
        return

    cols = st.columns([1, 1, 1, 1, 2])
    d = weather.data
    cols[0].metric("Temperature", f"{d['temperature_c']} °C")
    cols[1].metric("Humidity", f"{d['relative_humidity_pct']}%")
    cols[2].metric("Feels like", f"{d['apparent_temperature_c']} °C")
    band = (d["heat_index_band"] or "—").replace("_", " ").title()
    cols[3].metric("Heat index", f"{d['heat_index_c']} °C", band)

    if weather.stale:
        cols[4].warning(f"Live feed unavailable — showing data from cache ({weather.source})")
    else:
        cols[4].caption(f"{config.OPEN_METEO_ATTRIBUTION} · city-scale, updated just now")

    news = cached_news_chip()
    if news is not None:
        with st.expander(news["headline"]):
            for item in news.get("all_items", [])[:10]:
                st.markdown(f"- **{item['source']}** · {item['published']} · [{item['title']}]({item['link']})")
            st.caption("From Malayalam news; official alerts: IMD / KSDMA are the authority.")


def screen_today() -> None:
    st.header("Where is heat dangerous today?")
    live_strip()
    st.info(
        "Heat Exposure Map goes here once the scene-panel model and ward roll-up are wired in "
        "(src/visat/model.py + the frozen scene stack from ee_export.py). "
        "Placeholder until data freeze."
    )


def screen_plan() -> None:
    st.header("What should we do with our money?")
    live_strip()

    st.write("Preset budgets (cached, no drag slider — RESOURCES.md pydeck note):")
    cols = st.columns(len(config.BUDGET_PRESETS_CRORE))
    for col, crore in zip(cols, config.BUDGET_PRESETS_CRORE):
        col.button(f"₹{crore} crore", key=f"preset_{crore}")

    st.info(
        "Wire this to optimizer.precompute_presets(candidates) once real "
        "candidate cells (cost, delta_c, people_protected per cell x "
        "intervention) exist from the model + validity matrix."
    )

    with st.expander("Interventions considered (validity matrix)"):
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Intervention": i.label,
                        "PS1 category": i.ps1_category,
                        "Method": i.method.value,
                        "Where allowed": i.where_allowed,
                        "In optimizer": i.optimizer_eligible,
                    }
                    for i in INTERVENTIONS.values()
                ]
            ),
            hide_index=True,
        )


def screen_check_a_project() -> None:
    st.header("Will this new project make it hotter?")
    live_strip()
    st.info(
        "Check-a-Project: pick one of 5-8 pre-drawn pydeck polygons "
        "(st.pydeck_chart(..., on_select='rerun') returns picked objects "
        "only — see RESOURCES.md §4), then st.segmented_control for the "
        "proposed use. Wire to the reverse-transition + offset optimizer "
        "once the model is trained."
    )


def screen_proof() -> None:
    st.header("Can we trust it? What do I take to council?")
    live_strip()
    st.info(
        "Back-test chart (predicted vs observed 2017->2024 delta-LST), "
        "spatial-block CV vs baselines, CPCB check and ECOSTRESS rank "
        "agreement go here once model.cross_validated_rmse has real data. "
        "Ward Card PDF download button goes here."
    )


PAGES = {
    "Today": screen_today,
    "Plan ₹": screen_plan,
    "Check a Project": screen_check_a_project,
    "Proof & Ward Card": screen_proof,
}

st.title("VISAT — Kochi Heat Action Planner")
tab_names = list(PAGES.keys())
tabs = st.tabs(tab_names)
for tab, name in zip(tabs, tab_names):
    with tab:
        PAGES[name]()
