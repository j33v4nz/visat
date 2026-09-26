"""UHI: Urban Heat Intelligence map workspace for Kochi."""

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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uhi import config, exposure, i18n, live, news, report
from uhi.ledger import heat_ledger

st.set_page_config(page_title="UHI · Urban Heat Intelligence", page_icon="U", layout="wide")
st.markdown(f"<style>{Path(__file__).with_name('dashboard.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)
lang = "ml" if st.session_state.get("language") == "മലയാളം" else "en"
t = lambda value: i18n.tr(value, lang)
local = lambda en, ml: ml if lang == "ml" else en
esc = lambda value: html.escape(str(value))
TEAL = [122, 227, 192]
ORANGE = [242, 163, 111]


@st.cache_data
def load():
    j = lambda name: json.loads((config.APP / name).read_text(encoding="utf-8"))
    return {
        "cells": pd.read_parquet(config.APP / "cells.parquet"),
        "wards": pd.read_parquet(config.APP / "wards.parquet").set_index("ward_id"),
        "geo": j("wards.geojson"), "plans": j("plans.json"), "hn": j("heat_neutral.json"),
        "metrics": j("metrics.json"), "manifest": j("manifest.json"),
        "image": "data:image/png;base64," + base64.b64encode(
            (config.APP / "heat.png").read_bytes()).decode(),
        "canals": pd.read_parquet(config.APP / "canal_banks.parquet")
        if (config.APP / "canal_banks.parquet").exists() else pd.DataFrame(),
        "reactions": j("reactions_cache.json")
        if (config.APP / "reactions_cache.json").exists() else {},
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
weather_placeholder = st.empty()
weather_placeholder.markdown(
    "<div class='weather-skeleton' aria-label='Loading weather'>" + "<span></span>" * 4 + "</div>",
    unsafe_allow_html=True)
LIVE = live_data()
IST = timezone(timedelta(hours=5, minutes=30), "IST")  # no DST, so a fixed offset is exact
weather_placeholder.empty()
names = wards.sort_values("heat_stress", ascending=False)["ward"].tolist()
mode = st.session_state.get("workspace", "heat")
budget = st.session_state.get("budget", 10)
P = D["plans"]["presets"][str(budget)]
site = st.session_state.get("site", D["hn"]["sites"][0]["site"])
use = st.session_state.get("use", "it_park")
R = D["hn"]["results"][f"{site}|{use}"]


def markup(value):
    st.markdown(value, unsafe_allow_html=True)


def title(kicker, heading, description=""):
    markup(f"<div class='eyebrow'>{esc(kicker)}</div><div class='context-title'>{esc(heading)}</div>"
           f"<div class='context-sub'>{esc(description)}</div>")


def hero(value, label, color=""):
    markup(f"<div class='hero-value {color}'>{esc(value)}</div>"
           f"<div class='hero-label'>{esc(label)}</div>")


def pair(left_value, left_label, right_value, right_label):
    markup("<div class='metric-pair'>" + "".join(
        f"<div><div class='mini-value'>{esc(value)}</div><div class='mini-label'>{esc(label)}</div></div>"
        for value, label in [(left_value, left_label), (right_value, right_label)]) + "</div>")


def validity_table():
    frame = pd.DataFrame(M["validity_matrix"])
    for column in ("intervention", "ps1_category", "method", "cost_note"):
        frame[column] = frame[column].map(t)
    st.dataframe(frame, hide_index=True)
    st.caption(local(config.CANAL_CREDIT_NOTE,
                     "കനാൽ പണിക്ക് 0 °C ചൂടുകുറവ് മാത്രമാണ് കണക്കാക്കിയത്. കനാൽക്കര വൃക്ഷനിരകൾ വേറെ പരിഗണിക്കുന്നു."))


@st.dialog("UHI · " + local("Detailed analysis", "വിശദമായ വിശകലനം"), width="large")
def details(section):
    if section == "plan":
        st.subheader(t("Site-by-site plan · fix, ward, people, surface °C and cost"))
        picks = pd.DataFrame(P["picks"], columns=["lat", "lon", "fix", "dt", "cost"])
        locations = cells[["lat", "lon", "ward_id", "pop"]].copy()
        locations[["lat", "lon"]] = locations[["lat", "lon"]].round(5)
        table = picks.merge(locations, on=["lat", "lon"], how="left", validate="many_to_one")
        display = pd.DataFrame({t("Ward / area"): table.ward_id.map(wards.ward).fillna(t("Outside Kochi wards")),
                                t("Fix"): table.fix.map(t), t("Surface ΔT (°C)"): table.dt,
                                t("People at site"): table["pop"].round(),
                                t("₹ lakh"): (table.cost / 1e5).round(2)})
        if st.session_state.get("conservative"):
            error = M["backtest"]["mae_c"]
            display[t("Back-test band (°C)")] = table.dt.map(
                lambda x: f"{x-error:+.2f} … {x+error:+.2f}")
        st.dataframe(display, hide_index=True)
        st.caption(local("Each row is a selected 100 m cell. GHSL 2020 population. Total plan results include spillover.",
                         "ഓരോ വരിയും തെരഞ്ഞെടുത്ത 100 മീ. സ്ഥലമാണ്. ജനസംഖ്യ GHSL 2020-ൽ നിന്ന്; ആകെ ഫലത്തിൽ സമീപപ്രദേശങ്ങളിലേക്കുള്ള സ്വാധീനവും ഉൾപ്പെടും."))
        st.subheader(local("Budget response", "ബജറ്റ് അനുസരിച്ചുള്ള ഫലം"))
        st.line_chart(pd.DataFrame(D["plans"]["curve"]).set_index("budget_cr"), height=220)
        st.caption(local("Curve sums per-site effects; presets use joint re-prediction.",
                         "വക്രരേഖ സ്ഥലങ്ങളുടെ ഫലം കൂട്ടിയ കണക്കാണ്; മൂന്ന് ബജറ്റുകൾക്ക് സംയുക്ത പ്രവചനം ഉപയോഗിക്കുന്നു."))
        validity_table()
    elif section == "evidence":
        bt = M["backtest"]
        st.subheader(t("2017 to 2024 back-test results"))
        if "points" in bt:
            x, y = t("Predicted Δ °C"), t("Observed Δ °C")
            points = pd.DataFrame(bt["points"], columns=[x, y])
            limits = [min(points.min()), max(points.max())]
            dots = alt.Chart(points).mark_circle(size=20, opacity=.4, color="#f2a36f").encode(x=x, y=y)
            line = alt.Chart(pd.DataFrame({"x": limits, "y": limits})).mark_line(color="#7ae3c0").encode(x="x", y="y")
            st.altair_chart(dots + line, width="stretch")
        st.caption(local("Exploratory validation, not a causal estimate. Surface temperature at ~10:30 AM is not felt air temperature.",
                         "ഈ പരിശോധന കാരണബന്ധം തെളിയിക്കുന്നതല്ല. രാവിലെ 10:30-ലെ ഉപരിതല താപനില അനുഭവപ്പെടുന്ന വായുചൂടല്ല."))
        st.dataframe(pd.DataFrame(M["cv"]["spatial_cv"]).T, width="stretch")
        ph = M.get("physics_check")
        if ph:
            st.info(f"{t('Cool roofs')}: {local('model', 'മാതൃക')} {ph['median_model_c']:+.2f} °C · "
                    f"{local('energy balance', 'ഊർജസമതുലനം')} {ph['median_formula_c']:+.2f} °C")
        st.caption(f"Random CV R²: {M['cv']['random_cv_ours']['r2']:.3f} · "
                   + local("The main result uses held-out spatial blocks.", "പ്രധാന ഫലം വേർതിരിച്ച പ്രദേശങ്ങളിലെ പരിശോധനയാണ്."))
        validity_table()
        st.json(D["manifest"], expanded=False)
    elif section == "card":
        choice = st.selectbox(t("Ward / area for the card"), names, key="card_ward")
        wid = wards.index[wards.ward == choice][0]
        actions = D["plans"]["presets"]["10"]["ward_actions"].get(str(wid), [])
        card = report.ward_card(wards.loc[wid].to_dict(), names.index(choice)+1, len(names),
                                actions, D["manifest"]["source"], language=lang)
        st.download_button(t("Download Ward Heat Card (open → print to PDF)"), card,
                           file_name=f"ward_heat_card_{choice.replace(' ', '_')}_{lang}.html", mime="text/html")
        st.iframe("data:text/html;charset=utf-8;base64," + base64.b64encode(card.encode()).decode(), height=590)
    elif section == "project":
        st.subheader(t("Compare the modelled heat before and after offsets"))
        chosen = next(s for s in D["hn"]["sites"] if s["site"] == site)
        camera = pdk.ViewState(latitude=chosen["center"][0], longitude=chosen["center"][1], zoom=13)
        heat = pd.DataFrame(R["heat_cells"], columns=["lat", "lon", "dt"])
        offsets = pd.DataFrame(R["offset_cells"], columns=["lat", "lon", "fix"])
        base = [pdk.Layer("BitmapLayer", image=f"'{D['image']}'", bounds=M["heat_png_bounds"], opacity=.35),
                pdk.Layer("ScatterplotLayer", data=heat, get_position=["lon", "lat"],
                          get_radius=45, get_fill_color=ORANGE+[170])]
        before, after = st.columns(2)
        for column, label, value, layer_set in [
            (before, "Project only", R["before"]["mean_dt_c"], base),
            (after, "Project + available offsets", R["after"]["mean_dt_c"], base + [
                pdk.Layer("ScatterplotLayer", data=offsets, get_position=["lon", "lat"],
                          get_radius=40, get_fill_color=TEAL+[230])])]:
            with column:
                st.metric(t(label), f"{value:+.2f} °C")
                st.pydeck_chart(pdk.Deck(layers=layer_set, initial_view_state=camera,
                                         map_provider="carto", map_style="dark"), height=330)
        st.caption(local("Same site and scale. Orange is added heat; mint marks cooling measures, not a simulated temperature surface.",
                         "ഒരേ സ്ഥലവും അളവും. ഓറഞ്ച് = കൂടുന്ന ചൂട്; പച്ച = ചൂട് കുറയ്ക്കൽ സ്ഥലങ്ങൾ."))
    elif section == "alerts":
        st.subheader(t("Official alerts"))
        for name, url in config.OFFICIAL_ALERT_LINKS.items():
            st.link_button(t(name), url)
        current_news = news_data()
        if current_news:
            st.caption(local("Malayalam news is supporting information, not an official alert.",
                             "മലയാളം വാർത്തകൾ അനുബന്ധ വിവരങ്ങൾ മാത്രം; ഔദ്യോഗിക മുന്നറിയിപ്പല്ല."))
            for item in current_news["items"]:
                st.markdown(f"[{item['title']}]({item['link']}) · {item['channel']}")
        else:
            st.caption(local("No recent news available. Check the official sources above.",
                             "പുതിയ വാർത്തകൾ ലഭ്യമല്ല. മുകളിലെ ഔദ്യോഗിക സ്രോതസ്സുകൾ പരിശോധിക്കുക."))
    elif section == "about":
        st.subheader(local("Terms of use", "ഉപയോഗ നിബന്ധനകൾ"))
        st.write(local(
            "UHI: Urban Heat Intelligence is a prototype for exploring city surface-temperature estimates and cooling scenarios. "
            "Its estimates are not air temperature, personal heat exposure, emergency warnings, or "
            "planning approvals. Check proposed sites, costs, permissions, and current official guidance "
            "before making a decision. For urgent heat guidance, use IMD or KSDMA alerts.",
            "നഗരത്തിലെ ഉപരിതല താപനിലയും ചൂട് കുറയ്ക്കാനുള്ള സാധ്യതകളും പരിശോധിക്കുന്ന മാതൃകാ ഉപകരണമാണിത്. "
            "ഇവിടത്തെ കണക്കുകൾ വായുതാപനിലയോ വ്യക്തിയുടെ ചൂട് അനുഭവമോ അടിയന്തര മുന്നറിയിപ്പോ "
            "പദ്ധതി അനുമതിയോ അല്ല. തീരുമാനത്തിന് മുൻപ് സ്ഥലവും ചെലവും അനുമതികളും ഔദ്യോഗിക നിർദ്ദേശങ്ങളും "
            "പരിശോധിക്കുക. അടിയന്തര ചൂട് നിർദ്ദേശങ്ങൾക്ക് IMD അല്ലെങ്കിൽ KSDMA അറിയിപ്പുകൾ കാണുക."))
        st.subheader(local("Privacy notice", "സ്വകാര്യതാ അറിയിപ്പ്"))
        st.write(local(
            "The app does not ask for your name, email, phone number, or device location. Ward and project "
            "choices are kept in the active app session and are not written to the project data files. "
            "Weather is requested for fixed Kochi locations from Open-Meteo. News headlines come from "
            "public feeds. The hosting provider may process technical connection logs. Do not enter "
            "sensitive personal information.",
            "പേര്, ഇമെയിൽ, ഫോൺ നമ്പർ, ഉപകരണത്തിന്റെ സ്ഥാനം എന്നിവ ആപ്പ് ചോദിക്കുന്നില്ല. വാർഡും "
            "പദ്ധതിസ്ഥലവും തിരഞ്ഞെടുക്കുന്നത് നിലവിലെ സെഷനിൽ മാത്രം സൂക്ഷിക്കുന്നു; പദ്ധതിയുടെ ഡാറ്റാ "
            "ഫയലുകളിൽ എഴുതുന്നില്ല. കൊച്ചിയിലെ നിശ്ചിത സ്ഥലങ്ങളിലെ കാലാവസ്ഥ Open-Meteo-യിൽ നിന്നും "
            "വാർത്തകൾ പൊതുവായ ഫീഡുകളിൽ നിന്നും ലഭിക്കുന്നു. സാങ്കേതിക കണക്ഷൻ വിവരങ്ങൾ ഹോസ്റ്റിംഗ് "
            "സേവനം കൈകാര്യം ചെയ്തേക്കാം. സ്വകാര്യ വിവരങ്ങൾ നൽകരുത്."))
        st.caption(local("Sources: Open-Meteo, public news feeds, Streamlit hosting.",
                         "സ്രോതസ്സുകൾ: Open-Meteo, പൊതുവാർത്താ ഫീഡുകൾ, Streamlit ഹോസ്റ്റിംഗ്."))


# The map stays mounted while the tools change. Native widgets sit in fixed floating containers.
with st.container(key="topbar"):
    brand, weather, language = st.columns([2.3, 4, 1])
    with brand:
        markup("<div class='brand'><div class='brand-mark'>UHI</div><div><div class='brand-name'>UHI: URBAN HEAT INTELLIGENCE</div>"
               f"<div class='brand-sub'>{local('KOCHI · URBAN CLIMATE WORKSPACE', 'കൊച്ചി · നഗര കാലാവസ്ഥാ വിശകലനം')}</div></div></div>")
    with weather:
        # Only this strip reruns each second: a real Kochi clock next to the (15-min) weather reading.
        @st.fragment(run_every=1)
        def weather_strip():
            live_now = live_data()
            if live_now.get("status") == "unavailable":
                return
            weather_status = live_now.get("status", "snapshot")
            weather_status_label = {
                "live": local("LIVE", "തത്സമയം"),
                "cached": local("CACHED", "കാഷ് ചെയ്തത്"),
                "snapshot": local("SNAPSHOT", "സംഭരിച്ച ചിത്രം"),
            }.get(weather_status, weather_status.upper())
            clock = datetime.now(IST).strftime("%H:%M:%S")
            observed = str(live_now.get("time", ""))[-5:] or "—"
            observed_note = esc(local(f"Weather observed at {observed} IST",
                                      f"കാലാവസ്ഥ രേഖപ്പെടുത്തിയത് {observed} IST"))
            markup(f"<div class='weather-strip' title='{observed_note}'>" + "".join(
                f"<div class='weather-stat'><small>{esc(label)}</small><b>{esc(value)}</b></div>"
                for label, value in [(local(f"KOCHI · {weather_status_label}", f"കൊച്ചി · {weather_status_label}"), f"{clock} IST"),
                                     (local("Air temperature", "വായുതാപനില"), f"{live_now['temp_c']}°"),
                                     (t("Feels like"), f"{live_now['feels_c']}°"),
                                     (t("Humidity"), f"{live_now['rh']}%"),
                                     (t("Heat index"), f"{live_now['heat_index_c']}°")]) + "</div>")

        weather_strip()
    language.selectbox("Language / ഭാഷ", ["English", "മലയാളം"], key="language", label_visibility="collapsed")

with st.container(key="navigation"):
    markup(f"<div class='eyebrow'>KOCHI / {local('WORKSPACE', 'വിശകലനം')}</div>")
    modes = {"heat": local("Heat overview", "ഇന്നത്തെ ചൂട്"),
             "plan": local("Cooling plan", "ബജറ്റ് പദ്ധതി"),
             "simulation": local("Simulation", "സാഹചര്യ പരീക്ഷണം"),
             "project": local("Project check", "പദ്ധതി പരിശോധന"),
             "evidence": local("Evidence", "തെളിവുകൾ")}
    st.radio("Workspace", list(modes), format_func=modes.get, key="workspace", label_visibility="collapsed")
    markup("<div class='section-rule'></div>")
    if st.button(local("Ward heat card", "വാർഡ് കാർഡ്"), width="stretch"):
        details("card")
    if st.button(local("Alerts and news", "മുന്നറിയിപ്പുകൾ"), width="stretch"):
        details("alerts")
    if st.button(local("About, privacy and use", "സ്വകാര്യതയും ഉപയോഗവും"), width="stretch"):
        details("about")
    source_status = local("Frozen satellite data", "സ്ഥിരപ്പെടുത്തിയ ഉപഗ്രഹ വിവരങ്ങൾ")
    if D["manifest"]["source"] == "demo":
        source_status = local("DEMO · synthetic data", "പരീക്ഷണ വിവരങ്ങൾ")
    markup(f"<div class='nav-footer'>{source_status}<br>"
           f"{len(wards)} {local('wards', 'വാർഡുകൾ')} · {M['n_scenes']} {local('scenes', 'നിരീക്ഷണങ്ങൾ')}<br>"
           f"{local('Weather', 'കാലാവസ്ഥ')}: {t(LIVE.get('status', 'unavailable'))}</div>")

with st.container(key="map_tools"):
    with st.popover(local("Map layers", "ഭൂപട പാളികൾ"), width="stretch"):
        st.toggle(local("Heat surface", "ഉപരിതല ചൂട്"), value=True, key="heat_visible")
        st.toggle(local("Ward boundaries", "വാർഡ് അതിരുകൾ"), value=True, key="wards_visible")
        st.slider(local("Opacity", "നിറത്തിന്റെ തീവ്രത"), .1, .9, .55, .05, key="heat_opacity")
    if st.button(local("Reset map", "ഭൂപടം പുനഃക്രമീകരിക്കുക"), width="stretch"):
        st.session_state["map_version"] = st.session_state.get("map_version", 0) + 1

with st.container(key="inspector"):
    if mode == "heat":
        title(local("HEAT OVERVIEW", "ഇന്നത്തെ ചൂട്"), local("Ward heat conditions", "വാർഡുകളിലെ ചൂട്"),
              local("Surface temperature across Kochi. Select a ward to inspect local drivers.",
                    "കൊച്ചിയിലെ ഉപരിതല താപനില. പ്രാദേശിക കാരണങ്ങൾ അറിയാൻ ഒരു വാർഡ് തിരഞ്ഞെടുക്കുക."))
        hot_people = cells.loc[cells.hotspot & (cells.ward_id >= 0), "pop"].sum()
        hero(f"{hot_people:,.0f}", local("people in the highest heat-stress cells", "ഏറ്റവും ചൂടുള്ള പ്രദേശങ്ങളിലെ ആളുകൾ"))
        markup("<div class='section-rule'></div>")
        choice = st.selectbox(t("Ward / area"), names, key="today_ward")
        if lang == "ml":
            st.caption("മാപ്പുമായി പൊരുത്തത്തിനായി വാർഡ് പേരുകൾ ഉറവിടത്തിലെ ലിപിയിൽ കാണിക്കുന്നു.")
        w = wards.loc[wards.ward == choice].iloc[0]
        pair(f"{w.lst_anom:+.1f} °C", t("vs city median"), f"{w.people:,.0f}", t("People"))
        st.markdown("**" + t("Why it's hot") + "**")
        drivers = {k.split("::")[1]: v for k, v in w.items() if k.startswith("drv::") and "Weather" not in k}
        for name, value in sorted(drivers.items(), key=lambda item: -abs(item[1]))[:3]:
            markup(f"<div class='driver-row'><span>{esc(t(name))}</span><span>{value:+.1f} °C</span></div>"
                   f"<div class='driver-track'><span style='width:{min(100,abs(value)/5*100):.1f}%;"
                   f"background:{'#eaa16d' if value > 0 else '#7ae3c0'}'></span></div>")
        with st.expander(t("Act today")):
            act = exposure.act_today(wards, LIVE.get("peak_heat_index_c") or M["season_heat_index_c"])
            st.caption(f"{t('Heat index')}: {act['peak_heat_index_c']} °C · {t(act['band'])}")
            st.write(", ".join(act["wards"]))
            for advice in act["advice"]:
                st.markdown("- " + t(advice))
        with st.expander(t("Next 72 hours: city heat index")):
            if LIVE.get("forecast"):
                fc = pd.DataFrame(LIVE["forecast"])
                fc["time"] = pd.to_datetime(fc.time)
                st.line_chart(fc.set_index("time")["heat_index_c"], height=150, color="#f2a36f")
            else:
                st.caption(local("Forecast unavailable.", "പ്രവചനം ലഭ്യമല്ല."))
        with st.expander(local("Weather effects & local facilities", "കാലാവസ്ഥയും പ്രാദേശിക സൗകര്യങ്ങളും")):
            st.caption(f"{int(w.schools)} {local('schools', 'സ്കൂളുകൾ')} · {int(w.markets)} {local('markets', 'ചന്തകൾ')} · "
                       f"{int(w.hospitals)} {local('hospitals', 'ആശുപത്രികൾ')}")
            st.dataframe(pd.DataFrame(M["atmospheric"]["effects"]).T, hide_index=True)
            st.caption(local("Bootstrap intervals over satellite days; small samples are uncertain.",
                             "ഉപഗ്രഹ നിരീക്ഷണ ദിവസങ്ങളിലെ പിശകിന്റെ പരിധി; ചെറിയ സാമ്പിളിൽ അനിശ്ചിതത്വമുണ്ട്."))
    elif mode == "plan":
        title(local("COOLING PLAN", "ചൂട് കുറയ്ക്കൽ പദ്ധതി"), local("Cooling investment plan", "ചൂട് കുറയ്ക്കാനുള്ള നിക്ഷേപ പദ്ധതി"))
        st.segmented_control(t("Budget"), [1, 10, 50], default=10,
                             format_func=lambda x: f"₹{x} {t('crore')}", key="budget")
        ours = P["ours"]
        hero(f"{ours['people_cooled']:,.0f}", t("People cooled (≥0.1 °C)"), "mint")
        pair(f"{ours['mean_dt_cooled']:.2f} °C", t("Avg cooling"), f"{ours['cells']:,}", t("Sites (100 m)"))
        comp = pd.DataFrame([{t("Strategy"): t(s["strategy"]), t("Person-°C"): s["person_deg_cooling"]}
                             for s in [ours, *P["baselines"]]])
        st.caption(t("Same money, three strategies"))
        st.bar_chart(comp.set_index(t("Strategy")), horizontal=True, color="#7ae3c0", height=140)
        st.toggle(t("Conservative mode · show back-test error band"), key="conservative")
        if st.session_state.get("conservative"):
            mae = M["backtest"]["mae_c"]
            st.info(local(f"Empirical back-test error band: {ours['mean_dt_cooled']-mae:+.2f} to "
                          f"{ours['mean_dt_cooled']+mae:+.2f} °C (±{mae:.2f} MAE). Not a confidence interval.",
                          f"മുൻപരിശോധന പിശക് ±{mae:.2f} °C. ഇത് വിശ്വാസപരിധിയോ ഉറപ്പുള്ള ചൂടുകുറവോ അല്ല."))
        st.toggle(t("Show OSM canal-bank tree-strip candidates"), key="canal_overlay")
        if st.session_state.get("canal_overlay"):
            st.caption(local("Blue = unverified canal-bank candidates, not IURWTS alignments. Canal credit: 0 °C.",
                             "നീല = പരിശോധിക്കേണ്ട കനാൽക്കര സാധ്യതകൾ; IURWTS പാതകളല്ല. കനാൽ നേട്ടം: 0 °C."))
        if st.button(local("Plan and site details", "പദ്ധതിയുടെയും സ്ഥലത്തിന്റെയും വിശദാംശങ്ങൾ"), type="primary", width="stretch"):
            details("plan")
        with st.expander(local("Intervention mix", "ഇടപെടലുകൾ")):
            st.dataframe(pd.DataFrame([{t("Fix"): t(k), t("Sites"): v["cells"],
                                        t("₹ lakh"): round(v["cost_rs"]/1e5, 1)}
                                       for k, v in ours["mix"].items()]), hide_index=True)
    elif mode == "project":
        title(local("PROJECT CHECK", "പദ്ധതി പരിശോധന"), local("Development impact", "പദ്ധതിയുടെ സ്വാധീനം"),
              local("Explore a proposed development and its available cooling measures.", "നിർദിഷ്ട പദ്ധതിയും ലഭ്യമായ ചൂട് കുറയ്ക്കൽ നടപടികളും പരിശോധിക്കുക."))
        st.selectbox(t("Proposed site"), [s["site"] for s in D["hn"]["sites"]], key="site", format_func=t)
        st.selectbox(t("Proposed use"), list(config.PROJECT_USES), key="use",
                     format_func=lambda x: t(config.PROJECT_USES[x]["label"]))
        st.toggle(t("Apply available offsets"), key="neutral")
        if st.session_state.get("neutral"):
            ledger = base64.b64encode(heat_ledger(R, t).encode()).decode()
            st.iframe(f"data:text/html;charset=utf-8;base64,{ledger}", height=185)
            if R["after"]["mean_dt_c"] > .005:
                st.warning(local("Heat remains. This proposal does not pass the heat-neutral screen.",
                                 "ചൂട് കൂടുതലാണ്. പദ്ധതി ചൂട്-നിഷ്പക്ഷ പരിശോധനയിൽ വിജയിക്കുന്നില്ല."))
            else:
                st.success(local("Passes the modelled heat-neutral screen.", "മാതൃകയിലെ ചൂട്-നിഷ്പക്ഷ പരിശോധനയിൽ വിജയിക്കുന്നു."))
            pair(f"₹{R['offset_cost_rs']/1e5:,.1f}", t("₹ lakh"), f"{R['before']['people']:,}", t("People"))
        else:
            hero(f"+{R['before']['mean_dt_c']:.2f} °C", t("Project adds"), "orange")
            st.caption(f"{R['before']['people']:,} {local('people within ~500 m', 'ആളുകൾ ഏകദേശം 500 മീ. പരിധിയിൽ')}")
        with st.expander(t("Compare the modelled heat before and after offsets")):
            pair(f"{R['before']['mean_dt_c']:+.2f} °C", t("Project only"),
                 f"{R['after']['mean_dt_c']:+.2f} °C", t("Project + available offsets"))
            for name, value in R["offset_mix"].items():
                st.caption(f"{t(name)} · {value['cells']} {t('Sites')} · ₹{value['cost_rs']/1e5:.1f} {t('lakh')}")
            if st.button(local("Open map comparison", "ഭൂപടങ്ങൾ താരതമ്യം ചെയ്യുക"), width="stretch"):
                details("project")
        with st.expander(local("Policy & limitations", "നയവും പരിമിതികളും")):
            st.caption(local(R["policy"], "ഇത് അനുമതിയല്ല; പ്രാഥമിക പരിശോധന മാത്രം. കോർപ്പറേഷന്റെ കെട്ടിടാനുമതി വിഭാഗമോ നഗരാസൂത്രണ സമിതിയോ അന്തിമ തീരുമാനം എടുക്കണം."))
            st.caption(local(R["label"], "രാവിലെ ഉപരിതല താപനില; ആളുകളുടെ എണ്ണം അനുസരിച്ചുള്ള കണക്ക്; ഏകദേശം 500 മീ. പരിധി."))
        reaction = D["reactions"].get(f"{site}|{use}")
        if reaction:
            with st.expander(t("How might residents react? (SIMULATED)")):
                st.warning(local("Simulated personas, not a survey. Never changes model results.", "സാങ്കൽപ്പിക പ്രതികരണങ്ങൾ; സർവേയല്ല. മാതൃകയിലെ കണക്കുകൾ മാറ്റില്ല."))
                st.dataframe(pd.DataFrame(reaction["personas"]), hide_index=True)
    elif mode == "simulation":
        title(local("SCENARIO LAB", "സാഹചര്യ പരീക്ഷണം"),
              local("Test a ward-level heat scenario", "വാർഡ് തലത്തിലെ ചൂട് സാഹചര്യം പരീക്ഷിക്കുക"),
              local("Adjust local weather and one available cooling measure. The estimate updates as you change inputs.",
                    "പ്രാദേശിക കാലാവസ്ഥയും ലഭ്യമായ ഒരു തണുപ്പിക്കൽ നടപടിയും ക്രമീകരിക്കുക. മാറ്റങ്ങൾക്കൊപ്പം കണക്കും പുതുക്കും."))
        choice = st.selectbox(t("Ward / area"), names, key="simulation_ward")
        st.session_state["today_ward"] = choice
        if lang == "ml":
            st.caption("മാപ്പുമായി പൊരുത്തത്തിനായി വാർഡ് പേരുകൾ ഉറവിടത്തിലെ ലിപിയിൽ കാണിക്കുന്നു.")
        wid = wards.index[wards.ward == choice][0]
        ward = wards.loc[wid]
        actions = D["plans"]["presets"]["10"]["ward_actions"].get(str(wid), [])
        st.caption(local(f"Baseline surface temperature anomaly: {ward.lst_anom:+.2f} °C vs city median",
                         f"അടിസ്ഥാന ഉപരിതല താപ വ്യത്യാസം: നഗര മധ്യകവുമായി താരതമ്യം ചെയ്യുമ്പോൾ {ward.lst_anom:+.2f} °C"))
        fixes = [None, *(action for action in actions if isinstance(action, dict) and action.get("label"))]
        def fix_label(index):
            try:
                index = int(index)
            except (TypeError, ValueError):
                index = 0
            if index <= 0 or index >= len(fixes) or fixes[index] is None:
                return local("No intervention", "ഇടപെടലില്ല")
            return t(fixes[index]["label"])
        fix_index = st.selectbox(local("Cooling measure", "തണുപ്പിക്കൽ നടപടി"), range(len(fixes)),
                                 format_func=fix_label, key="simulation_fix")
        try:
            fix_index = int(fix_index)
        except (TypeError, ValueError):
            fix_index = 0
        fix = fixes[fix_index] if 0 <= fix_index < len(fixes) else None
        if fix:
            max_sites = max(1, int(fix["cells"]))
            sites = st.slider(local("Treatment sites (100 m cells)", "നടപടി സ്ഥലങ്ങൾ (100 മീ. സെല്ലുകൾ)"),
                              1, max_sites, max_sites, key="simulation_sites")
            intervention_dt = float(fix["dt"]) * sites / max_sites
            cost = float(fix["cost_rs"]) * sites / max_sites
            person_deg = float(fix["person_deg"]) * sites / max_sites
        else:
            intervention_dt, cost, person_deg = 0.0, 0.0, 0.0
        st.markdown("**" + local("Weather scenario", "കാലാവസ്ഥാ സാഹചര്യം") + "**")
        temp_delta = st.slider(local("Air temperature change (°C)", "വായു താപനില മാറ്റം (°C)"), -5.0, 8.0, 0.0, .5, key="simulation_temp")
        humidity_delta = st.slider(local("Humidity change (percentage points)", "ആർദ്രതയിലെ മാറ്റം (ശതമാന പോയിന്റ്)"), -30, 30, 0, 5, key="simulation_rh")
        wind_delta = st.slider(local("Wind change (m/s)", "കാറ്റിലെ മാറ്റം (മീ/സെ)"), -3.0, 3.0, 0.0, .5, key="simulation_wind")
        sun_delta = st.slider(local("Sunlight change (W/m²)", "സൂര്യപ്രകാശത്തിലെ മാറ്റം (W/m²)"), -200, 200, 0, 25, key="simulation_sun")
        effects = M["atmospheric"]["effects"]
        weather_terms = [("t2m_c", temp_delta, 1.0), ("rh", humidity_delta, 10.0),
                         ("wind_ms", wind_delta, 1.0), ("ssrd_wm2", sun_delta, 100.0)]
        weather_dt = sum(effects[key]["effect_c"] * delta / unit for key, delta, unit in weather_terms)
        weather_low = sum((effects[key]["ci_low"] if delta >= 0 else effects[key]["ci_high"]) * delta / unit
                          for key, delta, unit in weather_terms)
        weather_high = sum((effects[key]["ci_high"] if delta >= 0 else effects[key]["ci_low"]) * delta / unit
                           for key, delta, unit in weather_terms)
        total_change = weather_dt + intervention_dt
        projected = float(ward.lst_anom) + total_change
        st.markdown("<div class='scenario-readout'>" +
                    f"<div><small>{local('PROJECTED WARD ANOMALY', 'കണക്കാക്കിയ വാർഡ് വ്യത്യാസം')}</small><strong>{projected:+.2f} °C</strong></div>"+
                    f"<div><small>{local('CHANGE FROM BASELINE', 'അടിസ്ഥാനത്തിൽ നിന്നുള്ള മാറ്റം')}</small><strong>{total_change:+.2f} °C</strong></div>"+
                    f"<div><small>{local('INTERVENTION COST', 'നടപടി ചെലവ്')}</small><strong>₹{cost/100000:.1f} lakh</strong></div></div>",
                    unsafe_allow_html=True)
        st.caption(local(f"Weather component: {weather_dt:+.2f} °C (combined sensitivity range {weather_low:+.2f} to {weather_high:+.2f} °C). Potential intervention: {intervention_dt:+.2f} °C; estimated {person_deg:,.0f} person·°C benefit.",
                         f"കാലാവസ്ഥാ ഘടകം: {weather_dt:+.2f} °C (സെൻസിറ്റിവിറ്റി പരിധി {weather_low:+.2f} മുതൽ {weather_high:+.2f} °C വരെ). സാധ്യതയുള്ള നടപടി: {intervention_dt:+.2f} °C; കണക്കാക്കിയ നേട്ടം {person_deg:,.0f} person·°C."))
        before_after = pd.DataFrame({local("Relative surface temperature", "ആപേക്ഷിക ഉപരിതല താപനില"): [float(ward.lst_anom), projected]},
                                    index=[local("Baseline", "അടിസ്ഥാനം"), local("Scenario", "സാഹചര്യം")])
        st.bar_chart(before_after, horizontal=True, color=["#ff7627"], height=120)
        report_text = (f"UHI: Urban Heat Intelligence — Ward scenario report\nWard: {choice}\n"
                       f"Baseline anomaly vs city median: {ward.lst_anom:+.2f} °C\n"
                       f"Cooling measure: {fix['label'] if fix else 'None'}\nSites: {sites if fix else 0}\n"
                       f"Weather deltas: air temperature {temp_delta:+.1f} °C; humidity {humidity_delta:+d} pp; "
                       f"wind {wind_delta:+.1f} m/s; sunlight {sun_delta:+d} W/m²\n"
                       f"Estimated weather effect: {weather_dt:+.2f} °C (sensitivity range {weather_low:+.2f} to {weather_high:+.2f})\n"
                       f"Estimated intervention effect: {intervention_dt:+.2f} °C; cost ₹{cost:,.0f}; person-degree benefit {person_deg:,.0f}\n"
                       f"Combined scenario anomaly: {projected:+.2f} °C\n\n"
                       "Exploratory scenario, not a forecast or causal estimate. Weather sensitivities are learned from satellite scenes; their intervals are bootstrap ranges. Intervention effects come from precomputed ward actions and scale linearly with selected sites. Validate local conditions, costs and permissions before use. Surface temperature is not felt air temperature.\n")
        st.download_button(local("Download scenario report", "സാഹചര്യ റിപ്പോർട്ട് ഡൗൺലോഡ് ചെയ്യുക"), report_text,
                           file_name=f"uhi_scenario_{wid}.txt", mime="text/plain", width="stretch")
        st.caption(local("Scenario math uses saved atmospheric sensitivities and ward action estimates. It updates instantly, but is not a weather forecast, causal promise or approval.",
                         "സംരക്ഷിച്ച കാലാവസ്ഥാ സെൻസിറ്റിവിറ്റിയും വാർഡ് നടപടി കണക്കുകളും ഉപയോഗിച്ചാണ് ഈ പരീക്ഷണം. ഉടൻ പുതുക്കുന്ന കണക്കാണിത്; കാലാവസ്ഥാ പ്രവചനമോ കാരണഫല ഉറപ്പോ അനുമതിയോ അല്ല."))
    else:
        title(local("EVIDENCE", "തെളിവുകൾ"), local("Model performance", "മാതൃകയുടെ കൃത്യത"),
              local("Real Kochi observations. Spatial validation. Transparent uncertainty.", "യഥാർത്ഥ കൊച്ചി നിരീക്ഷണങ്ങൾ. പ്രദേശങ്ങൾ വേർതിരിച്ച പരിശോധന."))
        ours_cv = next(v for k, v in M["cv"]["spatial_cv"].items() if "ours" in k)
        hero(f"{ours_cv['r2']:.2f}", local("Spatial validation R²", "പ്രദേശതല പരിശോധന R²"), "mint")
        pair(f"±{M['backtest']['mae_c']:.2f} °C", local("Back-test MAE", "മുൻപരിശോധന പിശക്"),
             f"{M['backtest']['pearson_r']:.2f}", local("Back-test correlation", "മുൻപരിശോധന ബന്ധം"))
        st.caption(local("Surface temperature, ~10:30 AM, Jan–Apr. Not the air temperature people feel. Population: GHSL 2020.",
                         "ജനുവരി–ഏപ്രിൽ, രാവിലെ 10:30-ലെ ഉപരിതല താപനില. അനുഭവപ്പെടുന്ന വായുചൂടല്ല. ജനസംഖ്യ: GHSL 2020."))
        if st.button(local("Validation details", "പരിശോധനാ വിശദാംശങ്ങൾ"), type="primary", width="stretch"):
            details("evidence")
        with st.expander(local("Additional validation", "കൂടുതൽ പരിശോധനകൾ")):
            for key, label in [("ecostress", "ECOSTRESS afternoon check"), ("cpcb", "CPCB station check")]:
                value = M.get(key)
                st.caption(t(label) + " · " + t("available" if value else "pending"))
                if value:
                    st.json(value)
            matched = M["backtest"].get("matched")
            st.caption(t("Matched back-test") + " · " + t("available" if matched else "pending"))
            if matched:
                st.json(matched)
    with st.container(key="mobile_actions"):
        card_action, alert_action, about_action = st.columns(3)
        if card_action.button(local("Ward card", "വാർഡ് കാർഡ്"), key="mobile_card"):
            details("card")
        if alert_action.button(local("Alerts", "മുന്നറിയിപ്പുകൾ"), key="mobile_alerts"):
            details("alerts")
        if about_action.button(local("About", "വിവരം"), key="mobile_about"):
            details("about")

# All mode-specific data is drawn on the same full-screen geographic canvas.
layers = []
if st.session_state.get("heat_visible", True):
    layers.append(pdk.Layer("BitmapLayer", id="heat", image=f"'{D['image']}'",
                            bounds=M["heat_png_bounds"], opacity=st.session_state.get("heat_opacity", .55)))
selected = st.session_state.get("today_ward", names[0])
if st.session_state.get("wards_visible", True):
    features = []
    for feature in D["geo"]["features"]:
        features.append({**feature, "properties": {**feature["properties"],
                         "selected": feature["properties"].get("name") == selected}})
    layers.append(pdk.Layer("GeoJsonLayer", id="wards", data={"type": "FeatureCollection", "features": features},
                            pickable=True, filled=True, stroked=True,
                            get_fill_color="properties.selected ? [122,227,192,30] : [0,0,0,0]",
                            get_line_color="properties.selected ? [122,227,192,230] : [160,190,210,70]",
                            line_width_min_pixels=1, auto_highlight=True))
view = pdk.ViewState(latitude=9.994, longitude=76.303, zoom=11.55, pitch=0)
if mode == "plan":
    cooling = pd.DataFrame(P["cooling"], columns=["lat", "lon", "dt"])
    layers.append(pdk.Layer("ScatterplotLayer", id="cooling", data=cooling,
                            get_position=["lon", "lat"], get_radius=45, get_fill_color=TEAL+[45]))
    picks = pd.DataFrame(P["picks"], columns=["lat", "lon", "fix", "dt", "cost"])
    picks["name"] = picks["fix"].map(t) + " · " + picks.dt.map(lambda x: f"{x:+.2f} °C")
    layers.append(pdk.Layer("ScatterplotLayer", id="picks", data=picks, get_position=["lon", "lat"],
                            get_radius=42, get_fill_color=TEAL+[210], pickable=True))
    if st.session_state.get("canal_overlay") and not D["canals"].empty:
        layers.append(pdk.Layer("ScatterplotLayer", id="canals", data=D["canals"], get_position=["lon", "lat"],
                                get_radius=22, get_fill_color=[90,160,255,150]))
elif mode == "project":
    chosen = next(s for s in D["hn"]["sites"] if s["site"] == site)
    view = pdk.ViewState(latitude=chosen["center"][0], longitude=chosen["center"][1]+.006, zoom=13.4)
    heat = pd.DataFrame(R["heat_cells"], columns=["lat", "lon", "dt"])
    heat["name"] = heat.dt.map(lambda x: f"+{x:.2f} °C")
    layers.append(pdk.Layer("ScatterplotLayer", id="project_heat", data=heat, get_position=["lon", "lat"],
                            get_radius=45, get_fill_color=ORANGE+[160], pickable=True))
    layers.append(pdk.Layer("PolygonLayer", id="site_boundary", data=[{"polygon": chosen["polygon"]}],
                            get_polygon="polygon", get_fill_color=[255,255,255,15],
                            get_line_color=[230,240,250,230], stroked=True, line_width_min_pixels=2))
    if st.session_state.get("neutral"):
        offsets = pd.DataFrame(R["offset_cells"], columns=["lat", "lon", "fix"])
        offsets["name"] = offsets.fix.map(t)
        layers.append(pdk.Layer("ScatterplotLayer", id="offsets", data=offsets, get_position=["lon", "lat"],
                                get_radius=40, get_fill_color=TEAL+[240], pickable=True))

labels = [{"name": t(name), "position": [lon, lat]} for name, (lat, lon) in config.KOCHI_POINTS.items()]
# deck.gl's TextLayer characterSet has no "auto" keyword: a plain string value is read
# literally as the exact set of characters to build glyphs for. "auto" therefore built a
# font atlas containing only the 4 letters a/u/t/o, so every other letter in "Kakkanad",
# "Kalamassery" etc. had no glyph and rendered blank. Use the real characters instead.
label_charset = "".join(sorted({ch for row in labels for ch in row["name"]}))
layers.append(pdk.Layer("TextLayer", id="place_labels", data=labels, get_position="position",
                        get_text="name", get_size=16, get_color=[235,240,245,255],
                        get_text_anchor="'middle'", get_alignment_baseline="'center'",
                        background=True, get_background_color=[12,24,32,170],
                        background_padding=[6,3], font_family="Arial",
                        character_set=f"'{label_charset}'"))


def select_ward():
    event = st.session_state.get(f"map_{mode}_{st.session_state.get('map_version', 0)}", {})
    picked = event.get("selection", {}).get("objects", {}).get("wards", [])
    if picked:
        name = picked[0].get("name") or picked[0].get("properties", {}).get("name")
        if name in names:
            st.session_state["today_ward"] = name


with st.container(key="map_canvas"):
    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view, map_provider="carto", map_style="dark",
                            tooltip={"text": "{name}"}), height=1000, on_select=select_ward,
                    selection_mode="single-object", key=f"map_{mode}_{st.session_state.get('map_version', 0)}")
with st.container(key="map_legend"):
    markup(f"<div class='legend-labels'><span>{local('SURFACE TEMPERATURE', 'ഉപരിതല താപനില')}</span>"
           "<span>~10:30 AM</span></div><div class='legend-gradient'></div>"
           f"<div class='legend-labels'><span>{local('Cooler', 'ചൂട് കുറവ്')}</span>"
           f"<span>{local('Warmer · relative to city median', 'നഗര മധ്യകണക്കിനേക്കാൾ കൂടുതൽ ചൂട്')}</span></div>")
markup("<div class='map-caption'>9.99° N &nbsp; 76.30° E &nbsp; · &nbsp; KOCHI, KERALA<br>"
       "Landsat · GHSL · ERA5 · Open-Meteo · © OpenStreetMap © CARTO</div>")
