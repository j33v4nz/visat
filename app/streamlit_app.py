"""UHI: Urban Heat Intelligence — Kochi Climate Terrain Intelligence Platform."""

import base64
import html
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uhi import config, exposure, i18n, live, news, report
from uhi.ledger import heat_ledger
from uhi.simulation_ui import render_simulation

st.set_page_config(
    page_title="UHI · Kochi Climate Terrain Intelligence",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    f"<style>{Path(__file__).with_name('dashboard.css').read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)

# Single source of truth for view projection and camera
st.session_state.setdefault("view_mode", "2D")
st.session_state.setdefault("zoom_level", 11.55)
st.session_state.setdefault("camera_center", (9.994, 76.303))
st.session_state.setdefault("zoom_step", 0)

lang = "ml" if st.session_state.get("language") == "മലയാളം" else "en"
t = lambda value: i18n.tr(value, lang)
local = lambda en, ml: ml if lang == "ml" else en
esc = lambda value: html.escape(str(value))

TEAL = [0, 230, 118]
ORANGE = [255, 87, 34]


@st.cache_data
def load():
    j = lambda name: json.loads((config.APP / name).read_text(encoding="utf-8"))
    return {
        "cells": pd.read_parquet(config.APP / "cells.parquet"),
        "wards": pd.read_parquet(config.APP / "wards.parquet").set_index("ward_id"),
        "geo": j("wards.geojson"),
        "plans": j("plans.json"),
        "hn": j("heat_neutral.json"),
        "metrics": j("metrics.json"),
        "manifest": j("manifest.json"),
        "image": "data:image/png;base64,"
        + base64.b64encode((config.APP / "heat.png").read_bytes()).decode(),
        "canals": (
            pd.read_parquet(config.APP / "canal_banks.parquet")
            if (config.APP / "canal_banks.parquet").exists()
            else pd.DataFrame()
        ),
        "reactions": (
            j("reactions_cache.json")
            if (config.APP / "reactions_cache.json").exists()
            else {}
        ),
    }


@st.cache_data(ttl=config.LIVE_TTL_S, show_spinner=False)
def live_data():
    return live.get(config.DATA / "live_cache.json", config.APP / "live_snapshot.json")


@st.cache_data(ttl=config.LIVE_TTL_S, show_spinner=False)
def news_data():
    return news.get(config.DATA / "news_cache.json", config.APP / "news_snapshot.json")


if not (config.APP / "manifest.json").exists():
    st.error("No app data. Run python -m uhi.pipeline --source frozen.")
    st.stop()

D = load()
M, wards, cells = D["metrics"], D["wards"], D["cells"]
LIVE = live_data()
IST = timezone(timedelta(hours=5, minutes=30), "IST")  # no DST, so a fixed offset is exact
names = wards.sort_values("heat_stress", ascending=False)["ward"].tolist()


@st.cache_data
def kochi_search_index():
    geo = D["geo"]
    index = {}
    for feature in geo["features"]:
        props = feature["properties"]
        name = props.get("name")
        code = props.get("sourcewardcode") or ""
        geom = feature["geometry"]
        coords = (
            geom["coordinates"][0]
            if geom["type"] == "Polygon"
            else geom["coordinates"][0][0]
        )
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        lat = sum(lats) / len(lats)
        lon = sum(lons) / len(lons)
        if name:
            label = f"Ward {code} · {name}" if code else name
            index[label] = (name, lat, lon)
    for landmark, (lat, lon) in config.KOCHI_POINTS.items():
        closest_ward = min(
            index.values(),
            key=lambda item: (item[1] - lat) ** 2 + (item[2] - lon) ** 2,
        )[0]
        index[f"📍 {landmark}"] = (closest_ward, lat, lon)
    return index


SEARCH_INDEX = kochi_search_index()

mode = st.session_state.get("workspace", "heat")
budget = st.session_state.get("budget", 10)
P = D["plans"]["presets"][str(budget)]
site = st.session_state.get("site", D["hn"]["sites"][0]["site"])
use = st.session_state.get("use", "it_park")
R = D["hn"]["results"][f"{site}|{use}"]


def markup(value):
    st.markdown(value, unsafe_allow_html=True)


def title(kicker, heading, description=""):
    markup(
        f"<div class='eyebrow'>{esc(kicker)}</div>"
        f"<div class='context-title'>{esc(heading)}</div>"
        f"<div class='context-sub'>{esc(description)}</div>"
    )


def hero(value, label, color=""):
    markup(
        f"<div class='hero-box'>"
        f"<div class='hero-value {color}'>{esc(value)}</div>"
        f"<div class='hero-label'>{esc(label)}</div>"
        f"</div>"
    )


def pair(left_value, left_label, right_value, right_label):
    markup(
        "<div class='metric-pair'>"
        + "".join(
            f"<div class='stat-cell'><div class='mini-value'>{esc(value)}</div><div class='mini-label'>{esc(label)}</div></div>"
            for value, label in [
                (left_value, left_label),
                (right_value, right_label),
            ]
        )
        + "</div>"
    )


def validity_table():
    frame = pd.DataFrame(M["validity_matrix"])
    for column in ("intervention", "ps1_category", "method", "cost_note"):
        frame[column] = frame[column].map(t)
    st.dataframe(frame, hide_index=True)
    st.caption(
        local(
            config.CANAL_CREDIT_NOTE,
            "കനാൽ പണിക്ക് 0 °C ചൂടുകുറവ് മാത്രമാണ് കണക്കാക്കിയത്. കനാൽക്കര വൃക്ഷനിരകൾ വേറെ പരിഗണിക്കുന്നു.",
        )
    )


@st.dialog("UHI · " + local("Detailed Analysis", "വിശദമായ വിശകലനം"), width="large")
def details(section):
    if section == "plan":
        st.subheader(t("Site-by-site plan · fix, ward, people, surface °C and cost"))
        picks = pd.DataFrame(P["picks"], columns=["lat", "lon", "fix", "dt", "cost"])
        locations = cells[["lat", "lon", "ward_id", "pop"]].copy()
        locations[["lat", "lon"]] = locations[["lat", "lon"]].round(5)
        table = picks.merge(locations, on=["lat", "lon"], how="left", validate="many_to_one")
        display = pd.DataFrame(
            {
                t("Ward / area"): table.ward_id.map(wards.ward).fillna(t("Outside Kochi wards")),
                t("Fix"): table.fix.map(t),
                t("Surface ΔT (°C)"): table.dt,
                t("People at site"): table["pop"].round(),
                t("₹ lakh"): (table.cost / 1e5).round(2),
            }
        )
        if st.session_state.get("conservative"):
            error = M["backtest"]["mae_c"]
            display[t("Back-test band (°C)")] = table.dt.map(
                lambda x: f"{x-error:+.2f} … {x+error:+.2f}"
            )
        st.dataframe(display, hide_index=True)
        st.caption(
            local(
                "Each row is a selected 100 m cell. GHSL 2020 population. Total plan results include spillover.",
                "ഓരോ വരിയും തെരഞ്ഞെടുത്ത 100 മീ. സ്ഥലമാണ്. ജനസംഖ്യ GHSL 2020-ൽ നിന്ന്; ആകെ ഫലത്തിൽ സമീപപ്രദേശങ്ങളിലേക്കുള്ള സ്വാധീനവും ഉൾപ്പെടും.",
            )
        )
        st.subheader(local("Budget response", "ബജറ്റ് അനുസരിച്ചുള്ള ഫലം"))
        st.line_chart(pd.DataFrame(D["plans"]["curve"]).set_index("budget_cr"), height=220)
        validity_table()
    elif section == "evidence":
        bt = M["backtest"]
        st.subheader(t("2017 to 2024 back-test results"))
        if "points" in bt:
            x, y = t("Predicted Δ °C"), t("Observed Δ °C")
            points = pd.DataFrame(bt["points"], columns=[x, y])
            limits = [min(points.min()), max(points.max())]
            dots = (
                alt.Chart(points)
                .mark_circle(size=24, opacity=0.45, color="#ff5722")
                .encode(x=x, y=y)
            )
            line = (
                alt.Chart(pd.DataFrame({"x": limits, "y": limits}))
                .mark_line(color="#00e676", strokeWidth=2)
                .encode(x="x", y="y")
            )
            st.altair_chart(dots + line, use_container_width=True)
        st.caption(
            local(
                "Exploratory validation, not a causal estimate. Surface temperature at ~10:30 AM is not felt air temperature.",
                "ഈ പരിശോധന കാരണബന്ധം തെളിയിക്കുന്നതല്ല. രാവിലെ 10:30-ലെ ഉപരിതല താപനില അനുഭവപ്പെടുന്ന വായുചൂടല്ല.",
            )
        )
        st.dataframe(pd.DataFrame(M["cv"]["spatial_cv"]).T, use_container_width=True)
        ph = M.get("physics_check")
        if ph:
            st.info(
                f"{t('Cool roofs')}: {local('model', 'മാതൃക')} {ph['median_model_c']:+.2f} °C · "
                f"{local('energy balance', 'ഊർജസമതുലനം')} {ph['median_formula_c']:+.2f} °C"
            )
        validity_table()
        st.json(D["manifest"], expanded=False)
    elif section == "card":
        choice = st.selectbox(t("Ward / area for the card"), names, key="card_ward")
        wid = wards.index[wards.ward == choice][0]
        actions = D["plans"]["presets"]["10"]["ward_actions"].get(str(wid), [])
        card = report.ward_card(
            wards.loc[wid].to_dict(),
            names.index(choice) + 1,
            len(names),
            actions,
            D["manifest"]["source"],
            language=lang,
        )
        st.download_button(
            t("Download Ward Heat Card (open → print to PDF)"),
            card,
            file_name=f"ward_heat_card_{choice.replace(' ', '_')}_{lang}.html",
            mime="text/html",
        )
        st.iframe(
            "data:text/html;charset=utf-8;base64,"
            + base64.b64encode(card.encode()).decode(),
            height=590,
        )
    elif section == "project":
        st.subheader(t("Compare the modelled heat before and after offsets"))
        chosen = next(s for s in D["hn"]["sites"] if s["site"] == site)
        camera = pdk.ViewState(
            latitude=chosen["center"][0], longitude=chosen["center"][1], zoom=13
        )
        heat = pd.DataFrame(R["heat_cells"], columns=["lat", "lon", "dt"])
        offsets = pd.DataFrame(R["offset_cells"], columns=["lat", "lon", "fix"])
        base = [
            pdk.Layer(
                "BitmapLayer",
                image=f"'{D['image']}'",
                bounds=M["heat_png_bounds"],
                opacity=0.35,
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=heat,
                get_position=["lon", "lat"],
                get_radius=45,
                get_fill_color=ORANGE + [170],
            ),
        ]
        before, after = st.columns(2)
        for column, label, value, layer_set in [
            (before, "Project only", R["before"]["mean_dt_c"], base),
            (
                after,
                "Project + available offsets",
                R["after"]["mean_dt_c"],
                base
                + [
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=offsets,
                        get_position=["lon", "lat"],
                        get_radius=40,
                        get_fill_color=TEAL + [230],
                    )
                ],
            ),
        ]:
            with column:
                st.metric(t(label), f"{value:+.2f} °C")
                st.pydeck_chart(
                    pdk.Deck(
                        layers=layer_set,
                        initial_view_state=camera,
                        map_provider="carto",
                        map_style="dark",
                    ),
                    height=330,
                )
    elif section == "alerts":
        st.subheader(t("Official alerts"))
        for name, url in config.OFFICIAL_ALERT_LINKS.items():
            st.link_button(t(name), url)
        current_news = news_data()
        if current_news:
            for item in current_news["items"]:
                st.markdown(f"[{item['title']}]({item['link']}) · {item['channel']}")
    elif section == "about":
        st.subheader(local("Scope & Scientific Honesty", "പരിധിയും നിബന്ധനകളും"))
        st.write(
            local(
                "UHI: Urban Heat Intelligence is an analytical decision-support system for exploring surface temperature and cooling interventions across Kochi. "
                "Satellite values are radiometric skin surface temperature (~10:30 AM), not ambient felt air temperature. "
                "Canal banks receive 0 °C cooling credit pending ground verification. Heat-Neutral Check is a municipal screening tool, not an approval.",
                "കൊച്ചിയിലെ ഉപരിതല താപനിലയും ചൂട് കുറയ്ക്കാനുള്ള സാധ്യതകളും പരിശോധിക്കുന്ന വിശകലന സംവിധാനം. "
                "ഇവിടത്തെ കണക്കുകൾ ഉപരിതല താപനിലയാണ്; അനുഭവപ്പെടുന്ന വായുചൂടല്ല. പദ്ധതി പരിശോധന അനുമതിയല്ല.",
            )
        )
        st.caption(
            "Sources: Landsat 8/9, Sentinel-2, GHSL 2020, ERA5-Land, Open-Meteo, OpenStreetMap contributors."
        )


# TOPBAR
with st.container(key="topbar"):
    b_col, w_col, l_col = st.columns([2.5, 4.5, 1])
    with b_col:
        markup(
            "<div class='brand-row'>"
            "<div class='brand-badge'>UHI</div>"
            "<div>"
            "<div class='brand-title'>URBAN HEAT INTELLIGENCE</div>"
            f"<div class='brand-sub'>{local('KOCHI CLIMATE TERRAIN', 'കൊച്ചി നഗര താപ നിരീക്ഷണം')}</div>"
            "</div></div>"
        )
    with w_col:
        @st.fragment(run_every=1)
        def weather_telemetry():
            live_now = live_data()
            clock = datetime.now(IST).strftime("%H:%M:%S")
            temp = live_now.get("temp_c", LIVE.get("temp_c", 27.1))
            feels = live_now.get("feels_c", LIVE.get("feels_c", 30.1))
            rh = live_now.get("rh", LIVE.get("rh", 83))
            hi = live_now.get(
                "peak_heat_index_c",
                live_now.get(
                    "heat_index_c", LIVE.get("peak_heat_index_c", 32.3)
                ),
            )
            markup(
                f"<div class='weather-telemetry'>"
                f"<div class='weather-metric'><small>DATA STREAM</small><b><span class='live-indicator'><span class='live-dot'></span>LIVE</span></b></div>"
                f"<div class='weather-metric'><small>{local('KOCHI TIME', 'കൊച്ചി സമയം')}</small><b>{clock} IST</b></div>"
                f"<div class='weather-metric'><small>{local('AIR TEMP', 'വായുതാപനില')}</small><b>{temp}°C</b></div>"
                f"<div class='weather-metric'><small>{t('Feels like')}</small><b>{feels}°C</b></div>"
                f"<div class='weather-metric'><small>{t('Humidity')}</small><b>{rh}%</b></div>"
                f"<div class='weather-metric'><small>{t('Heat index')}</small><b>{hi}°C</b></div>"
                f"</div>"
            )

        weather_telemetry()
    with l_col:
        st.selectbox(
            "Language / ഭാഷ",
            ["English", "മലയാളം"],
            key="language",
            label_visibility="collapsed",
        )

# LEFT NAVIGATION PANEL
with st.container(key="navigation"):
    markup(f"<div class='eyebrow'>{local('WORKSPACES', 'വിശകലനം')}</div>")
    modes = {
        "heat": local("Heat overview", "ഇന്നത്തെ ചൂട്"),
        "plan": local("Cooling plan", "ബജറ്റ് പദ്ധതി"),
        "simulation": local("Simulation", "സാഹചര്യ പരീക്ഷണം"),
        "project": local("Project check", "പദ്ധതി പരിശോധന"),
        "evidence": local("Evidence", "തെളിവുകൾ"),
    }
    st.radio(
        "Workspace",
        list(modes),
        format_func=modes.get,
        key="workspace",
        label_visibility="collapsed",
    )
    markup("<div class='section-rule'></div>")
    if st.button(local("Ward heat card (PDF)", "വാർഡ് കാർഡ്"), width="stretch"):
        details("card")
    if st.button(local("Alerts and news", "മുന്നറിയിപ്പുകൾ"), width="stretch"):
        details("alerts")
    if st.button(local("Methodology & scope", "വിവരം"), width="stretch"):
        details("about")

    markup(
        f"<div class='nav-scope'>"
        f"<b>{local('Kochi Urban Scope', 'കൊച്ചി പരിധി')}</b><br>"
        f"{len(wards)} {local('wards analyzed', 'വാർഡുകൾ')}<br>"
        f"{M['n_scenes']} {local('satellite scenes', 'നിരീക്ഷണങ്ങൾ')}<br>"
        f"{local('Live stream sync', 'തത്സമയ ഡാറ്റ')}</div>"
    )

# FLOATING MAP CONTROLS (Left side under navigation)
with st.container(key="map_tools"):
    markup(f"<div class='gis-label'>{local('MAP CONTROLS', 'ഭൂപടം')}</div>")
    z1, z2 = st.columns(2)
    if z1.button("➕", help="Zoom In", key="btn_zoom_in", width="stretch"):
        st.session_state["zoom_level"] = min(
            15.5, st.session_state.get("zoom_level", 11.55) + 0.6
        )
        st.session_state["zoom_step"] = st.session_state.get("zoom_step", 0) + 1
        st.rerun()
    if z2.button("➖", help="Zoom Out", key="btn_zoom_out", width="stretch"):
        st.session_state["zoom_level"] = max(
            10.2, st.session_state.get("zoom_level", 11.55) - 0.6
        )
        st.session_state["zoom_step"] = st.session_state.get("zoom_step", 0) + 1
        st.rerun()

    # Guaranteed single-click 2D/3D state transition
    is_3d = st.session_state.get("view_mode", "2D") == "3D"
    toggle_target = "2D" if is_3d else "3D"
    btn_text = (
        local("Switch to 2D", "2D കാഴ്ച്ച")
        if is_3d
        else local("Switch to 3D", "3D കാഴ്ച്ച")
    )
    if st.button(btn_text, key="btn_toggle_3d", width="stretch"):
        st.session_state["view_mode"] = toggle_target
        st.session_state["zoom_step"] = st.session_state.get("zoom_step", 0) + 1
        st.rerun()

    with st.popover(local("Map layers", "പാളികൾ"), width="stretch"):
        st.toggle(
            local("Heat surface", "ഉപരിതല ചൂട്"), value=True, key="heat_visible"
        )
        st.toggle(
            local("Ward boundaries", "വാർഡ് അതിരുകൾ"),
            value=True,
            key="wards_visible",
        )
        st.slider(
            local("Opacity", "തീവ്രത"), 0.1, 0.9, 0.55, 0.05, key="heat_opacity"
        )

# FLOATING SEARCH BAR (Bottom of map)
with st.container(key="map_search"):
    search_options = [
        local("🔍 Search Kochi wards or areas...", "🔍 കൊച്ചി വാർഡുകൾ തിരയുക...")
    ] + list(SEARCH_INDEX.keys())
    s_choice = st.selectbox(
        "Kochi Search",
        search_options,
        key="search_input",
        label_visibility="collapsed",
    )
    if s_choice != search_options[0]:
        target_name, t_lat, t_lon = SEARCH_INDEX[s_choice]
        if st.session_state.get("today_ward") != target_name:
            st.session_state["today_ward"] = target_name
            st.session_state["camera_center"] = (t_lat, t_lon)
            st.session_state["zoom_level"] = 13.2
            st.session_state["zoom_step"] = (
                st.session_state.get("zoom_step", 0) + 1
            )
            st.rerun()

simulation_overlay = {}

# RIGHT ANALYTICS / INSPECTOR PANEL
with st.container(key="inspector"):
    if mode == "heat":
        choice = st.selectbox(
            t("Ward / area"), names, key="today_ward"
        )
        w = wards.loc[wards.ward == choice].iloc[0]
        rank_idx = names.index(choice) + 1
        total_wards = len(names)

        title(
            local(f"WARD {rank_idx:02d} / {total_wards:02d} · KOCHI", f"വാർഡ് {rank_idx:02d}"),
            f"{choice}",
            local("Surface temperature anomaly and driver attribution.", "ഉപരിതല ചൂട് വ്യതിയാനം."),
        )

        hero(f"{w.lst_anom:+.1f} °C", local("SURFACE HEAT ANOMALY", "ഉപരിതല ചൂട് വ്യതിയാനം"), "orange")
        st.caption(
            f"{w.people_in_hotspots:,.0f} {local('people in heat-stress hotspots', 'ആളുകൾ ഉയർന്ന ചൂടിൽ')}"
        )

        markup(
            f"<div class='stat-grid-4'>"
            f"<div class='stat-cell'><div class='stat-cell-value'>{w.people:,.0f}</div><div class='stat-cell-label'>{t('Population')}</div></div>"
            f"<div class='stat-cell'><div class='stat-cell-value'>{LIVE.get('peak_heat_index_c') or M['season_heat_index_c']} °C</div><div class='stat-cell-label'>{t('Heat index')}</div></div>"
            f"<div class='stat-cell'><div class='stat-cell-value'>{w['drv::Vegetation']:+.1f} °C</div><div class='stat-cell-label'>{t('Vegetation')}</div></div>"
            f"<div class='stat-cell'><div class='stat-cell-value'>{w['drv::Concrete & buildings']:+.1f} °C</div><div class='stat-cell-label'>{t('Built-up')}</div></div>"
            f"</div>"
        )

        st.markdown(
            "**" + local("Thermal Drivers Attribution", "ചൂടിന്റെ പ്രധാന കാരണങ്ങൾ") + "**"
        )
        drivers = {
            k.split("::")[1]: v
            for k, v in w.items()
            if k.startswith("drv::") and "Weather" not in k
        }
        for d_name, d_val in sorted(drivers.items(), key=lambda it: -abs(it[1]))[:4]:
            track_color = "#ff5722" if d_val > 0 else "#00e676"
            markup(
                f"<div class='driver-row'><span>{esc(t(d_name))}</span><span>{d_val:+.2f} °C</span></div>"
                f"<div class='driver-track'><span style='width:{min(100, abs(d_val)/5*100):.1f}%;"
                f"background:{track_color}'></span></div>"
            )

        st.markdown(
            "**" + local("72-Hour City Heat Index Forecast Trend", "അടുത്ത 72 മണിക്കൂർ താപസൂചിക") + "**"
        )
        if LIVE.get("forecast"):
            fc = pd.DataFrame(LIVE["forecast"])
            fc["time"] = pd.to_datetime(fc.time)
            fc_chart = (
                alt.Chart(fc)
                .mark_area(
                    line={"color": "#ff5722", "strokeWidth": 2},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[
                            alt.GradientStop(color="#ff572244", offset=0),
                            alt.GradientStop(color="#ff572205", offset=1),
                        ],
                        x1=1,
                        x2=1,
                        y1=1,
                        y2=0,
                    ),
                )
                .encode(
                    x=alt.X(
                        "time:T",
                        title=None,
                        axis=alt.Axis(
                            format="%a %H:%M",
                            gridColor="#1c2738",
                            labelColor="#8494ab",
                        ),
                    ),
                    y=alt.Y(
                        "heat_index_c:Q",
                        title="°C",
                        scale=alt.Scale(zero=False),
                        axis=alt.Axis(gridColor="#1c2738", labelColor="#8494ab"),
                    ),
                )
                .properties(height=130)
            )
            caution_line = (
                alt.Chart(pd.DataFrame({"y": [32]}))
                .mark_rule(color="#f59e0b", strokeDash=[4, 4], strokeWidth=1.5)
                .encode(y="y:Q")
            )
            st.altair_chart(fc_chart + caution_line, use_container_width=True)

        with st.expander(t("Act today")):
            act = exposure.act_today(
                wards, LIVE.get("peak_heat_index_c") or M["season_heat_index_c"]
            )
            st.caption(
                f"{t('Heat index')}: {act['peak_heat_index_c']} °C · {t(act['band'])}"
            )
            st.write(", ".join(act["wards"]))
            for advice in act["advice"]:
                st.markdown("- " + t(advice))

        with st.expander(local("Weather effects & facilities", "കാലാവസ്ഥയും സൗകര്യങ്ങളും")):
            st.caption(
                f"{int(w.schools)} {local('schools', 'സ്കൂളുകൾ')} · {int(w.markets)} {local('markets', 'ചന്തകൾ')} · "
                f"{int(w.hospitals)} {local('hospitals', 'ആശുപത്രികൾ')}"
            )
            st.dataframe(pd.DataFrame(M["atmospheric"]["effects"]).T, hide_index=True)

    elif mode == "plan":
        title(
            local("COOLING PLAN", "ചൂട് കുറയ്ക്കൽ പദ്ധതി"),
            local("Optimized investment plan", "നിക്ഷേപ പദ്ധതി"),
            local("Algorithmic budget allocation.", "ബജറ്റ് അനുസരിച്ചുള്ള പദ്ധതി."),
        )
        st.segmented_control(
            t("Budget"),
            [1, 10, 50],
            default=10,
            format_func=lambda x: f"₹{x} {t('crore')}",
            key="budget",
        )
        ours = P["ours"]
        hero(f"{ours['people_cooled']:,.0f}", t("People cooled (≥0.1 °C)"), "mint")
        pair(f"{ours['mean_dt_cooled']:.2f} °C", t("Avg cooling"), f"{ours['cells']:,}", t("Sites (100 m)"))

        comp = pd.DataFrame(
            [
                {
                    t("Strategy"): t(s["strategy"]),
                    t("Person-°C"): s["person_deg_cooling"],
                }
                for s in [ours, *P["baselines"]]
            ]
        )
        st.markdown("**" + t("Same money, three strategies") + "**")
        st.bar_chart(
            comp.set_index(t("Strategy")),
            horizontal=True,
            color="#00e676",
            height=140,
        )

        st.toggle(
            t("Conservative mode · show back-test error band"),
            key="conservative",
        )
        if st.session_state.get("conservative"):
            mae = M["backtest"]["mae_c"]
            st.info(
                local(
                    f"Empirical back-test error band: {ours['mean_dt_cooled']-mae:+.2f} to "
                    f"{ours['mean_dt_cooled']+mae:+.2f} °C (±{mae:.2f} MAE). Not a confidence interval.",
                    f"മുൻപരിശോധന പിശക് ±{mae:.2f} °C. ഇത് വിശ്വാസപരിധിയോ ഉറപ്പുള്ള ചൂടുകുറവോ അല്ല.",
                )
            )

        st.toggle(
            t("Show OSM canal-bank tree-strip candidates"),
            key="canal_overlay",
        )
        if st.session_state.get("canal_overlay"):
            st.caption(
                local(
                    "Canal-bank candidate strips. Disclaimer: 0 °C credit (unverified field status).",
                    "കനാൽക്കര സാധ്യതകൾ. കനാൽ നേട്ടം: 0 °C.",
                )
            )

        if st.button(
            local("Plan and site details", "പദ്ധതിയുടെ വിശദാംശങ്ങൾ"),
            type="primary",
            width="stretch",
        ):
            details("plan")

        with st.expander(local("Intervention mix", "ഇടപെടലുകൾ")):
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            t("Fix"): t(k),
                            t("Sites"): v["cells"],
                            t("₹ lakh"): round(v["cost_rs"] / 1e5, 1),
                        }
                        for k, v in ours["mix"].items()
                    ]
                ),
                hide_index=True,
            )

    elif mode == "project":
        title(
            local("PROJECT CHECK", "പദ്ധതി പരിശോധന"),
            local("Development impact & heat-neutral check", "പദ്ധതിയുടെ സ്വാധീനവും പരിശോധനയും"),
            local("Screen development proposals and compute offsets.", "പദ്ധതിയും ആവശ്യമായ നടപടികളും."),
        )
        st.selectbox(
            t("Proposed site"),
            [s["site"] for s in D["hn"]["sites"]],
            key="site",
            format_func=t,
        )
        st.selectbox(
            t("Proposed use"),
            list(config.PROJECT_USES),
            key="use",
            format_func=lambda x: t(config.PROJECT_USES[x]["label"]),
        )
        st.toggle(t("Apply available offsets"), key="neutral")

        if st.session_state.get("neutral"):
            ledger = base64.b64encode(heat_ledger(R, t).encode()).decode()
            st.iframe(
                f"data:text/html;charset=utf-8;base64,{ledger}", height=185
            )
            if R["after"]["mean_dt_c"] > 0.005:
                st.warning(
                    local(
                        "Heat remains. This proposal does not pass the heat-neutral screen.",
                        "ചൂട് കൂടുതലാണ്. പദ്ധതി ചൂട്-നിഷ്പക്ഷ പരിശോധനയിൽ വിജയിക്കുന്നില്ല.",
                    )
                )
            else:
                st.success(
                    local(
                        "Passes the modelled heat-neutral screen.",
                        "മാതൃകയിലെ ചൂട്-നിഷ്പക്ഷ പരിശോധനയിൽ വിജയിക്കുന്നു.",
                    )
                )
            pair(
                f"₹{R['offset_cost_rs']/1e5:,.1f} L",
                t("₹ lakh"),
                f"{R['before']['people']:,}",
                t("People"),
            )
        else:
            hero(f"+{R['before']['mean_dt_c']:.2f} °C", t("Project adds"), "orange")
            st.caption(
                f"{R['before']['people']:,} {local('people within ~500 m perimeter', 'ആളുകൾ 500 മീ. പരിധിയിൽ')}"
            )

        with st.expander(t("Compare the modelled heat before and after offsets")):
            pair(
                f"{R['before']['mean_dt_c']:+.2f} °C",
                t("Project only"),
                f"{R['after']['mean_dt_c']:+.2f} °C",
                t("Project + available offsets"),
            )
            if st.button(
                local("Open map comparison", "ഭൂപടങ്ങൾ താരതമ്യം ചെയ്യുക"),
                width="stretch",
            ):
                details("project")

        with st.expander(local("Policy & limitations", "നയവും പരിമിതികളും")):
            st.caption(
                local(
                    R["policy"],
                    "ഇത് അനുമതിയല്ല; പ്രാഥമിക പരിശോധന മാത്രം. കോർപ്പറേഷന്റെ കെട്ടിടാനുമതി വിഭാഗമോ നഗരാസൂത്രണ സമിതിയോ അന്തിമ തീരുമാനം എടുക്കണം.",
                )
            )

        reaction = D["reactions"].get(f"{site}|{use}")
        if reaction:
            with st.expander(t("How might residents react? (SIMULATED)")):
                st.dataframe(pd.DataFrame(reaction["personas"]), hide_index=True)

    elif mode == "simulation":
        simulation_overlay = render_simulation(D, lang)

    else:
        title(
            local("EVIDENCE", "തെളിവുകൾ"),
            local("Model performance & validation", "മാതൃകയുടെ കൃത്യതയും വിശ്വാസ്യതയും"),
            local("Independent spatial holdout validation.", "പ്രദേശങ്ങൾ വേർതിരിച്ച പരിശോധന."),
        )
        ours_cv = next(v for k, v in M["cv"]["spatial_cv"].items() if "ours" in k)
        hero(f"{ours_cv['r2']:.2f}", local("Spatial block validation R²", "പ്രദേശതല പരിശോധന R²"), "mint")
        pair(
            f"±{M['backtest']['mae_c']:.2f} °C",
            local("Back-test MAE", "മുൻപരിശോധന പിശക്"),
            f"{M['backtest']['pearson_r']:.2f}",
            local("Back-test correlation", "മുൻപരിശോധന ബന്ധം"),
        )

        bt = M["backtest"]
        if "points" in bt:
            x, y = t("Predicted Δ °C"), t("Observed Δ °C")
            points = pd.DataFrame(bt["points"], columns=[x, y])
            limits = [min(points.min()), max(points.max())]
            scatter_chart = (
                alt.Chart(points)
                .mark_circle(size=20, opacity=0.45, color="#ff5722")
                .encode(x=x, y=y)
                .properties(height=130)
            )
            diag_line = (
                alt.Chart(pd.DataFrame({"x": limits, "y": limits}))
                .mark_line(color="#00e676", strokeWidth=1.5)
                .encode(x="x", y="y")
            )
            st.altair_chart(scatter_chart + diag_line, use_container_width=True)

        st.caption(
            local(
                "Skin surface temperature (~10:30 AM overpass, Jan–Apr). Not personal felt air temperature.",
                "രാവിലെ 10:30-ലെ ഉപരിതല താപനില. അനുഭവപ്പെടുന്ന വായുചൂടല്ല.",
            )
        )
        if st.button(
            local("Validation details", "പരിശോധനാ വിശദാംശങ്ങൾ"),
            type="primary",
            width="stretch",
        ):
            details("evidence")

    with st.container(key="mobile_actions"):
        m1, m2, m3 = st.columns(3)
        if m1.button(local("Ward card", "വാർഡ് കാർഡ്"), key="mobile_card"):
            details("card")
        if m2.button(local("Alerts", "മുന്നറിയിപ്പുകൾ"), key="mobile_alerts"):
            details("alerts")
        if m3.button(local("About", "വിവരം"), key="mobile_about"):
            details("about")


# AUTOMATIC KOCHI BOUNDS MANAGEMENT
cam_center = st.session_state.get("camera_center", (9.994, 76.303))
cam_zoom = st.session_state.get("zoom_level", 11.55)

# Strictly clamp camera to Kochi analysis region
lat = max(9.85, min(10.18, cam_center[0]))
lon = max(76.12, min(76.48, cam_center[1]))
zoom = max(10.2, min(16.0, cam_zoom))

is_3d = st.session_state.get("view_mode", "2D") == "3D"
pitch = 52 if is_3d else 0
bearing = -20 if is_3d else 0

view = pdk.ViewState(
    latitude=lat,
    longitude=lon,
    zoom=zoom,
    pitch=pitch,
    bearing=bearing,
    min_zoom=10.0,
    max_zoom=16.0,
)

layers = []
if st.session_state.get("heat_visible", True):
    layers.append(
        pdk.Layer(
            "BitmapLayer",
            id="heat",
            image=f"'{D['image']}'",
            bounds=M["heat_png_bounds"],
            opacity=st.session_state.get("heat_opacity", 0.55),
        )
    )

selected = st.session_state.get("today_ward", names[0])

if st.session_state.get("wards_visible", True):
    if is_3d and mode == "heat":
        # 3D Extruded Ward Polygons
        features_3d = []
        for feature in D["geo"]["features"]:
            props = dict(feature["properties"])
            anom = float(props.get("lst_anom", 0))
            hot_pop = float(props.get("people_in_hotspots", 0))
            is_sel = props.get("name") == selected
            elev = max(80, min(2500, (anom * 150) + (hot_pop / 12)))
            props["elev"] = elev
            props["fill"] = (
                [255, 87, 34, 195] if is_sel else [175, 45, 20, 110]
            )
            props["line_color"] = (
                [255, 255, 255, 230] if is_sel else [110, 155, 185, 75]
            )
            features_3d.append({**feature, "properties": props})
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                id="wards_3d",
                data={"type": "FeatureCollection", "features": features_3d},
                stroked=True,
                filled=True,
                extruded=True,
                wireframe=True,
                get_elevation="properties.elev",
                get_fill_color="properties.fill",
                get_line_color="properties.line_color",
                line_width_min_pixels=1,
                pickable=True,
                auto_highlight=True,
            )
        )
    else:
        # Standard 2D Ward Polygons
        features = []
        for feature in D["geo"]["features"]:
            features.append(
                {
                    **feature,
                    "properties": {
                        **feature["properties"],
                        "selected": feature["properties"].get("name") == selected,
                    },
                }
            )
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                id="wards",
                data={"type": "FeatureCollection", "features": features},
                pickable=True,
                filled=True,
                stroked=True,
                get_fill_color="properties.selected ? [255,87,34,50] : [0,0,0,0]",
                get_line_color="properties.selected ? [255,87,34,245] : [130,165,190,75]",
                line_width_min_pixels=2,
                auto_highlight=True,
            )
        )

if mode == "plan":
    cooling = pd.DataFrame(P["cooling"], columns=["lat", "lon", "dt"])
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            id="cooling",
            data=cooling,
            get_position=["lon", "lat"],
            get_radius=45,
            get_fill_color=TEAL + [45],
        )
    )
    picks = pd.DataFrame(P["picks"], columns=["lat", "lon", "fix", "dt", "cost"])
    picks["name"] = picks["fix"].map(t) + " · " + picks.dt.map(lambda x: f"{x:+.2f} °C")
    if is_3d:
        picks["elev"] = picks["dt"].abs().clip(upper=8) * 120 + 60
        layers.append(
            pdk.Layer(
                "ColumnLayer",
                id="picks",
                data=picks,
                get_position=["lon", "lat"],
                radius=42,
                get_elevation="elev",
                elevation_scale=1,
                extruded=True,
                get_fill_color=TEAL + [225],
                pickable=True,
                auto_highlight=True,
            )
        )
    else:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="picks",
                data=picks,
                get_position=["lon", "lat"],
                get_radius=42,
                get_fill_color=TEAL + [225],
                pickable=True,
            )
        )
    if st.session_state.get("canal_overlay") and not D["canals"].empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="canals",
                data=D["canals"],
                get_position=["lon", "lat"],
                get_radius=22,
                get_fill_color=[0, 180, 216, 150],
            )
        )

elif mode == "simulation":
    overlay = simulation_overlay
    if overlay.get("center"):
        view = pdk.ViewState(
            latitude=overlay["center"][0],
            longitude=overlay["center"][1] + 0.009,
            zoom=13,
            min_zoom=10.0,
            max_zoom=16.0,
        )
    if "points" in overlay and len(overlay["points"]):
        points = overlay["points"].copy()
        points["name"] = (
            points.fix.map(t) + " · " + points.dt.map(lambda value: f"{value:+.2f} °C")
        )
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="simulation_sites",
                data=points,
                get_position=["lon", "lat"],
                get_radius=48,
                get_fill_color=TEAL + [230],
                pickable=True,
            )
        )
    if overlay.get("cooling"):
        cooling = pd.DataFrame(overlay["cooling"], columns=["lat", "lon", "dt"])
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="simulation_cooling",
                data=cooling,
                get_position=["lon", "lat"],
                get_radius=45,
                get_fill_color=TEAL + [40],
            )
        )
    if overlay.get("heat"):
        heat = pd.DataFrame(overlay["heat"], columns=["lat", "lon", "dt"])
        heat["name"] = heat.dt.map(lambda value: f"{value:+.2f} °C")
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="simulation_heat",
                data=heat,
                get_position=["lon", "lat"],
                get_radius=45,
                get_fill_color=ORANGE + [200],
                pickable=True,
            )
        )
    if overlay.get("offsets"):
        offsets = pd.DataFrame(overlay["offsets"], columns=["lat", "lon", "fix"])
        offsets["name"] = offsets.fix.map(t)
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="simulation_offsets",
                data=offsets,
                get_position=["lon", "lat"],
                get_radius=42,
                get_fill_color=TEAL + [240],
                pickable=True,
            )
        )
    if overlay.get("boundary"):
        layers.append(
            pdk.Layer(
                "PolygonLayer",
                id="simulation_boundary",
                data=[{"polygon": overlay["boundary"]}],
                get_polygon="polygon",
                get_fill_color=[255, 255, 255, 10],
                get_line_color=[240, 240, 235, 230],
                stroked=True,
                line_width_min_pixels=2,
            )
        )
    if overlay.get("canals"):
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="simulation_canals",
                data=D["canals"],
                get_position=["lon", "lat"],
                get_radius=25,
                get_fill_color=[0, 180, 216, 170],
            )
        )
    if overlay.get("label"):
        with st.container(key="simulation_map_note"):
            markup(
                f"<div class='eyebrow'>{local('MAP / SCENARIO', 'ഭൂപടം / പരീക്ഷണം')}</div><p>{esc(overlay['label'])}</p>"
            )

elif mode == "project":
    chosen = next(s for s in D["hn"]["sites"] if s["site"] == site)
    view = pdk.ViewState(
        latitude=chosen["center"][0],
        longitude=chosen["center"][1] + 0.006,
        zoom=13.4,
        pitch=48 if is_3d else 0,
        bearing=-20 if is_3d else 0,
        min_zoom=10.0,
        max_zoom=16.0,
    )
    heat = pd.DataFrame(R["heat_cells"], columns=["lat", "lon", "dt"])
    heat["name"] = heat.dt.map(lambda x: f"+{x:.2f} °C")
    if is_3d:
        heat["elev"] = heat["dt"].clip(lower=0) * 180 + 50
        layers.append(
            pdk.Layer(
                "ColumnLayer",
                id="project_heat",
                data=heat,
                get_position=["lon", "lat"],
                radius=42,
                get_elevation="elev",
                get_fill_color=ORANGE + [185],
                extruded=True,
                pickable=True,
            )
        )
    else:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="project_heat",
                data=heat,
                get_position=["lon", "lat"],
                get_radius=45,
                get_fill_color=ORANGE + [160],
                pickable=True,
            )
        )
    layers.append(
        pdk.Layer(
            "PolygonLayer",
            id="site_boundary",
            data=[{"polygon": chosen["polygon"]}],
            get_polygon="polygon",
            get_fill_color=[255, 255, 255, 15],
            get_line_color=[230, 240, 250, 230],
            stroked=True,
            line_width_min_pixels=2,
        )
    )
    if st.session_state.get("neutral"):
        offsets = pd.DataFrame(R["offset_cells"], columns=["lat", "lon", "fix"])
        offsets["name"] = offsets.fix.map(t)
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="offsets",
                data=offsets,
                get_position=["lon", "lat"],
                get_radius=40,
                get_fill_color=TEAL + [240],
                pickable=True,
            )
        )

labels = [
    {"name": t(name), "position": [lon, lat]}
    for name, (lat, lon) in config.KOCHI_POINTS.items()
]
label_charset = "".join(sorted({ch for row in labels for ch in row["name"]}))
layers.append(
    pdk.Layer(
        "TextLayer",
        id="place_labels",
        data=labels,
        get_position="position",
        get_text="name",
        get_size=13,
        get_color=[240, 246, 252, 240],
        get_text_anchor="'middle'",
        get_alignment_baseline="'center'",
        background=True,
        get_background_color=[10, 16, 26, 195],
        background_padding=[6, 4],
        font_family="Outfit",
        character_set=f"'{label_charset}'",
    )
)


def select_ward():
    event = st.session_state.get(
        f"map_{mode}_{st.session_state.get('view_mode', '2D')}_{st.session_state.get('zoom_step', 0)}",
        {},
    )
    picked = event.get("selection", {}).get("objects", {}).get("wards", [])
    if not picked:
        picked = event.get("selection", {}).get("objects", {}).get("wards_3d", [])
    if picked:
        name = picked[0].get("name") or picked[0].get("properties", {}).get("name")
        if name in names:
            st.session_state["today_ward"] = name
            if (
                mode == "simulation"
                and st.session_state.get("sim_section") == "weather"
            ):
                st.session_state["simulation_ward"] = name


with st.container(key="map_canvas"):
    st.pydeck_chart(
        pdk.Deck(
            layers=layers,
            initial_view_state=view,
            map_provider="carto",
            map_style="dark",
            tooltip={"text": "{name}"},
        ),
        height=1000,
        on_select=select_ward,
        selection_mode="single-object",
        key=f"map_{mode}_{st.session_state.get('view_mode', '2D')}_{st.session_state.get('zoom_step', 0)}",
    )

with st.container(key="map_legend"):
    markup(
        f"<div class='legend-labels'><span>{local('SURFACE TEMPERATURE', 'ഉപരിതല താപനില')}</span>"
        "<span>~10:30 AM</span></div><div class='legend-gradient'></div>"
        f"<div class='legend-labels'><span>{local('Cooler', 'ചൂട് കുറവ്')}</span>"
        f"<span>{local('Warmer · relative to median', 'കൂടുതൽ ചൂട്')}</span></div>"
    )

markup(
    "<div class='map-caption'>9.99° N &nbsp; 76.30° E · KOCHI TERRAIN<br>"
    "Landsat 8/9 · Sentinel-2 · GHSL · ERA5 · © CARTO</div>"
)

# Client-side 5-second auto-recenter observer
components.html(
    """
<script>
(function() {
  const BOUNDS = { minLat: 9.85, maxLat: 10.20, minLon: 76.10, maxLon: 76.50 };
  let recenterTimer = null;
  let countdownSec = 5;

  function getBanner() {
    let b = window.parent.document.getElementById('uhi-recenter-banner');
    if (!b) {
      b = window.parent.document.createElement('div');
      b.id = 'uhi-recenter-banner';
      b.style.cssText = 'position:fixed;top:76px;left:50%;transform:translateX(-50%);z-index:99999;background:rgba(12,20,32,0.96);border:1px solid #ff5722;color:#ff8a65;padding:8px 16px;border-radius:4px;font-family:"JetBrains Mono",monospace;font-size:11px;font-weight:700;letter-spacing:0.04em;box-shadow:0 8px 24px rgba(0,0,0,0.8);display:none;pointer-events:none;';
      window.parent.document.body.appendChild(b);
    }
    return b;
  }

  function startRecenter() {
    if (recenterTimer) return;
    const b = getBanner();
    countdownSec = 5;
    b.innerText = '⌖ Outside Kochi analysis bounds · Returning in ' + countdownSec + 's...';
    b.style.display = 'block';

    recenterTimer = setInterval(() => {
      countdownSec -= 1;
      if (countdownSec > 0) {
        b.innerText = '⌖ Outside Kochi analysis bounds · Returning in ' + countdownSec + 's...';
      } else {
        clearInterval(recenterTimer);
        recenterTimer = null;
        b.innerText = '⌖ Returning to Kochi analysis area...';
        setTimeout(() => { b.style.display = 'none'; }, 1000);
      }
    }, 1000);
  }

  function cancelRecenter() {
    if (recenterTimer) {
      clearInterval(recenterTimer);
      recenterTimer = null;
      const b = getBanner();
      b.style.display = 'none';
    }
  }
})();
</script>
""",
    height=0,
)
