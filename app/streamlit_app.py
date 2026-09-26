"""VISAT — Kochi Heat Action Planner (HackMe'26, PS1). Four screens, one question each."""

import base64
import json
import sys
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from visat import config, exposure, i18n, live, news, report

st.set_page_config(page_title="VISAT · Kochi Heat Action Planner", page_icon="🌡️", layout="wide")
st.markdown(
    """<link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Malayalam:wght@400;600;800&display=swap"
          rel="stylesheet">
    <style>
    header[data-testid="stHeader"] {visibility:hidden;} #MainMenu, footer {visibility:hidden;}
    [data-testid="stMainBlockContainer"] {padding-top:1rem;}
    html, body, [class*="css"] {font-size:20px;}
    [data-testid="stMetric"] {background:linear-gradient(160deg,#182524 0%,#121b1a 100%);
        border:1px solid #2a3d3b;border-radius:14px;padding:12px 16px;}
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] * {font-size:40px!important;
        font-weight:800!important;letter-spacing:-0.5px;}
    [data-testid="stMetricLabel"] p {color:#9fb3b0;font-size:0.9rem!important;text-transform:uppercase;
        letter-spacing:0.6px;}
    .hero {display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin:0 0 4px;}
    .hero .title {font-size:2.2rem;white-space:nowrap;line-height:1.2;font-weight:800;margin:0;padding:0;
        background:linear-gradient(90deg,#fcffa4 0%,#f57d15 45%,#46c4be 100%);
        -webkit-background-clip:text;background-clip:text;color:transparent;}
    .hero span {color:#9fb3b0;font-size:1rem;}
    .legend {font-size:15px;color:#b9c8c5;margin:6px 0 2px;}
    .legend .bar {height:12px;border-radius:6px;margin:4px 0;}
    .legend .ends {display:flex;justify-content:space-between;}
    .swatch {display:inline-block;width:12px;height:12px;border-radius:50%;margin:0 5px 0 12px;
        vertical-align:middle;}
    .gauge {position:relative;height:16px;border-radius:8px;margin:28px 0 22px;
        background:linear-gradient(90deg,#e8c35a 0%,#e97a2e 25%,#d4483f 55%,#8e1b3a 100%);}
    .gauge .mark {position:absolute;top:-24px;transform:translateX(-50%);font-size:14px;
        white-space:nowrap;font-weight:700;}
    .gauge .mark::after {content:'';position:absolute;left:50%;top:20px;width:3px;height:24px;
        background:#fff;transform:translateX(-50%);border-radius:2px;}
    .gauge .tick {position:absolute;top:20px;font-size:12px;color:#8aa09c;transform:translateX(-50%);}
    .bigstat {font-size:54px;font-weight:800;line-height:1.05;}
    .sub {color:#9fb3b0;font-size:0.95rem;}
    .chip {display:inline-block;padding:4px 12px;border-radius:999px;margin-right:8px;font-size:17px;}
    .danger {background:#b8320b;color:#fff;} .warn {background:#e97a2e;color:#111;}
    .ok {background:#1f6f6d;color:#fff;} .demo {background:#e8c35a;color:#111;padding:6px 12px;
    border-radius:6px;font-weight:700;}
    .ledger {font-size:60px;font-weight:800;line-height:1.1;} .hot {color:#ff7a3d;} .cool {color:#46c4be;}
    [data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] li,
    [data-testid="stAppViewContainer"] label {font-size:1.05rem;}
    [data-baseweb="tab"] {font-size:1.05rem;}
    .ml-ui, .ml-ui p, .ml-ui label {font-family:'Noto Sans Malayalam',sans-serif;}
    </style>""",
    unsafe_allow_html=True,
)
APP = config.APP
language = st.session_state.get("language", "English")
lang = "ml" if language == "മലയാളം" else "en"
t = lambda value: i18n.tr(value, lang)
local = lambda en, ml: ml if lang == "ml" else en
if lang == "ml":
    st.markdown("""<style>
    [data-testid="stAppViewContainer"] {font-family:'Noto Sans Malayalam',sans-serif;}
    [data-testid="stAppViewContainer"] h2 {font-size:2rem;line-height:1.35;}
    [data-testid="stAppViewContainer"] h3 {font-size:1.65rem;line-height:1.4;}
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {
        font-size:0.92rem!important;white-space:normal!important;
        overflow:visible!important;text-overflow:clip!important;
    }
    </style>""", unsafe_allow_html=True)
TEAL = [70, 196, 190]
HEAT = [255, 122, 61]
KOCHI_VIEW = pdk.ViewState(latitude=9.99, longitude=76.30, zoom=12.3, pitch=0)
KOCHI_3D = pdk.ViewState(latitude=9.935, longitude=76.285, zoom=11.9, pitch=50, bearing=-15)
# Same inferno stops as pipeline.colorize, so legends and 3D colours match the heat image.
INFERNO = [(0, 0, 4), (40, 11, 84), (101, 21, 110), (159, 42, 99), (212, 72, 66), (245, 125, 21),
           (250, 193, 39), (252, 255, 164)]
FIX_COLORS = ["#46c4be", "#2c9678", "#1d6b58", "#5a8cff", "#b5ece8", "#7fa9a5", "#8fd18f"]
AXIS = {"labelColor": "#b9c8c5", "titleColor": "#b9c8c5", "gridColor": "#24403c",
        "domainColor": "#36504d", "labelFontSize": 13, "titleFontSize": 13}


def inferno(x: float) -> list[int]:
    """0–1 → RGB on the same ramp as the heat image."""
    pos = min(max(x, 0.0), 1.0) * (len(INFERNO) - 1)
    i = min(int(pos), len(INFERNO) - 2)
    f = pos - i
    return [round(a * (1 - f) + b * f) for a, b in zip(INFERNO[i], INFERNO[i + 1])]


def hexcolor(rgb) -> str:
    return "#" + "".join(f"{int(v):02x}" for v in rgb[:3])


def styled(chart):
    return chart.configure_axis(**AXIS, labelLimit=220).configure_view(stroke=None).configure(background="transparent")


def legend(left_label, right_label, stops=None):
    stops = stops or [f"rgb{c}" for c in INFERNO]
    return (f"<div class='legend'><div class='bar' style='background:linear-gradient(90deg,"
            f"{','.join(stops)})'></div><div class='ends'><span>{left_label}</span>"
            f"<span>{right_label}</span></div></div>")


def swatches(items):
    return "<div class='legend'>" + "".join(
        f"<span class='swatch' style='background:{c}'></span>{name}" for name, c in items) + "</div>"


@st.cache_data
def load():
    j = lambda n: json.loads((APP / n).read_text())
    return {
        "cells": pd.read_parquet(APP / "cells.parquet"),
        "canal_banks": pd.read_parquet(APP / "canal_banks.parquet")
        if (APP / "canal_banks.parquet").exists() else pd.DataFrame(),
        "wards": pd.read_parquet(APP / "wards.parquet"),
        "wards_geo": j("wards.geojson"), "plans": j("plans.json"), "hn": j("heat_neutral.json"),
        "metrics": j("metrics.json"), "manifest": j("manifest.json"),
        "heat_png": "data:image/png;base64," + base64.b64encode((APP / "heat.png").read_bytes()).decode(),
        "reactions": j("reactions_cache.json") if (APP / "reactions_cache.json").exists() else None,
    }


@st.cache_data(ttl=config.LIVE_TTL_S, show_spinner="Fetching live Kochi weather…")
def live_data():
    return live.get(config.DATA / "live_cache.json", APP / "live_snapshot.json")


@st.cache_data(ttl=config.LIVE_TTL_S, show_spinner="Checking Malayalam news…")
def news_data():
    return news.get(config.DATA / "news_cache.json", APP / "news_snapshot.json")


if not (APP / "manifest.json").exists():
    st.error("No app data yet. Run `uv run python -m visat.pipeline --source demo` (or `--source frozen`).")
    st.stop()
D = load()
M = D["metrics"]
cells, wards = D["cells"], D["wards"]
wards = wards.set_index("ward_id")
LIVE = live_data()

# ------------------------------------------------------------------ header + live strip
left, right, language_col = st.columns([5, 1, 1])
left.markdown(f"<div class='hero'><div class='title'>VISAT · {t('Kochi Heat Action Planner')}</div>"
              f"<span>{local('Satellite + weather + physics-informed ML · Kochi Corporation, C-HED',
                             'ഉപഗ്രഹ ചിത്രങ്ങൾ + കാലാവസ്ഥ + ഭൗതികശാസ്ത്രാധിഷ്ഠിത ML · കൊച്ചി കോർപ്പറേഷൻ')}"
              "</span></div>", unsafe_allow_html=True)
language_col.selectbox("Language / ഭാഷ", ["English", "മലയാളം"], key="language")
if D["manifest"]["source"] == "demo":
    right.markdown("<span class='demo'>DEMO DATA — synthetic Kochi, not real measurements</span>",
                   unsafe_allow_html=True)

band_cls = lambda b: ("danger" if b in ("Danger", "Extreme danger")
                      else "warn" if b in ("Caution", "Extreme caution") else "ok")
if LIVE.get("status") != "unavailable":
    s1, s2, s3, s4, s5 = st.columns([1, 1, 1, 1, 2])
    s1.metric(t("Now in Kochi"), f"{LIVE['temp_c']} °C")
    s2.metric(t("Humidity"), f"{LIVE['rh']}%")
    s3.metric(t("Feels like"), f"{LIVE['feels_c']} °C")
    s4.metric(t("Heat index"), f"{LIVE['heat_index_c']} °C")
    status = {"live": "live", "cached": "cached", "snapshot": "saved snapshot"}[LIVE["status"]]
    peak_label = t("Today's peak")
    pos = lambda c: min(max((float(c) - 26) / (54 - 26) * 100, 1), 99)
    ticks = "".join(f"<span class='tick' style='left:{pos(v)}%'>{v}</span>" for v in (27, 32, 39, 51))
    s5.markdown(
        f"<div class='gauge'>{ticks}"
        f"<span class='mark' style='left:{pos(LIVE['heat_index_c'])}%'>{local('now', 'ഇപ്പോൾ')}</span>"
        f"<span class='mark' style='left:{pos(LIVE['peak_heat_index_c'])}%;color:#ff7a3d'>"
        f"{local('peak', 'ഉയർന്നത്')}</span></div>"
        f"<span class='chip {band_cls(LIVE['band'])}'>{t(LIVE['band'])}</span>"
        f"{peak_label}: <b>{LIVE['peak_heat_index_c']} °C</b> "
        f"({t(LIVE['peak_band'])}) {local('at', 'സമയം')} "
        f"{LIVE['peak_time'][11:16]}<br><small>{t(config.LABEL_LIVE)} · {t(status)} · "
        f"{LIVE.get('fetched_at') or LIVE['time']}</small>", unsafe_allow_html=True)
else:
    st.info(local("Live weather unavailable right now — the rest of VISAT works offline.",
                  "തത്സമയ കാലാവസ്ഥാ വിവരം ഇപ്പോൾ ലഭ്യമല്ല. ബാക്കി വിവരങ്ങൾ ഇന്റർനെറ്റ് ഇല്ലാതെയും കാണാം."))

chips = st.columns([2, 3])
chips[0].markdown(f"{t('Official alerts')}: " + " · ".join(
    f"[{t(name)}]({url})" for name, url in config.OFFICIAL_ALERT_LINKS.items()))
NEWS = news_data()
if NEWS:
    with chips[1].popover(NEWS["text"]):
        st.caption(local("From Malayalam news (supporting evidence only; official alerts: IMD / KSDMA)",
                         "മലയാളം വാർത്തകൾ അനുബന്ധ വിവരങ്ങൾ മാത്രം; ഔദ്യോഗിക മുന്നറിയിപ്പുകൾ IMD / KSDMA")
                   + f" · {t(NEWS['status'])} · {NEWS.get('fetched_at')}")
        for it in NEWS["items"]:
            st.markdown(f"- [{it['title']}]({it['link']}) — *{it['channel']}*, {it['time'][:16]}")

today, plan_tab, project_tab, proof_tab = st.tabs([
    "① " + t("Where is heat dangerous today?"), "② " + t("What should we do with ₹?"),
    "③ " + t("Will this project make it hotter?"), "④ " + t("Can we trust it? · Ward Card"),
])


def ward_layer(selectable=True):
    return pdk.Layer("GeoJsonLayer", id="wards", data=D["wards_geo"], stroked=True, filled=True,
                     get_fill_color=[0, 0, 0, 0], get_line_color=[220, 220, 220, 90],
                     line_width_min_pixels=1, pickable=selectable, auto_highlight=True)


def heat_layer(opacity=0.85):
    b = M["heat_png_bounds"]
    # pydeck 0.9 treats an unquoted data URL as an accessor expression.
    return pdk.Layer("BitmapLayer", id="heat", image=f"'{D['heat_png']}'",
                     bounds=b, opacity=opacity)


def mask_layer():
    """Dim everything outside the modelled study area so panning/zooming past the data's
    edge reads as leaving a labelled study area, not a broken map cutting off."""
    lon0, lat0, lon1, lat1 = M["heat_png_bounds"]
    outer = [[-180, -85], [180, -85], [180, 85], [-180, 85]]
    inner = [[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1]]
    return [
        pdk.Layer("PolygonLayer", id="mask", data=[{"polygon": [outer, inner]}],
                 get_polygon="polygon", get_fill_color=[13, 17, 17, 225],
                 stroked=False, filled=True, pickable=False),
        pdk.Layer("PathLayer", id="mask_border", data=[{"path": inner + [inner[0]]}],
                 get_path="path", get_color=[70, 196, 190, 160], get_width=2,
                 width_min_pixels=1.5, pickable=False),
    ]


def deck(layers, tooltip=None, view=None):
    return pdk.Deck(layers=mask_layer() + layers, initial_view_state=view or KOCHI_VIEW,
                    map_provider="carto", map_style="dark", tooltip=tooltip or {"text": "{name}"})


@st.cache_data
def wards_3d_geo():
    """Ward polygons coloured by surface heat and raised by people living in hotspots."""
    lo, hi = M["heat_png_range"]
    geo = json.loads(json.dumps(D["wards_geo"]))
    by_name = wards.set_index("ward")
    max_hot = max(float(wards["people_in_hotspots"].max()), 1.0)
    for f in geo["features"]:
        p = f["properties"]
        row = by_name.loc[p["name"]] if p["name"] in by_name.index else None
        hot = float(row["people_in_hotspots"]) if row is not None else 0.0
        p["fill"] = inferno((float(p.get("lst_anom") or 0) - lo) / (hi - lo)) + [235]
        p["elev"] = 40 + hot / max_hot * 1500
        p["hot_people"] = f"{hot:,.0f}"
        p["anom"] = f"{float(p.get('lst_anom') or 0):+.1f}"
    return geo


def ward_3d_layer():
    return pdk.Layer("GeoJsonLayer", id="wards", data=wards_3d_geo(), stroked=True, filled=True,
                     extruded=True, wireframe=True, get_elevation="properties.elev",
                     get_fill_color="properties.fill", get_line_color=[255, 255, 255, 60],
                     pickable=True, auto_highlight=True, highlight_color=[70, 196, 190, 200],
                     material={"ambient": 0.55, "diffuse": 0.6, "shininess": 40})


def heat_ledger(result):
    """Animate the net number while preserving the actual saved before/after values."""
    before = float(result["before"]["mean_dt_c"])
    after = float(result["after"]["mean_dt_c"])
    removed = before - after
    scale = max(abs(before), abs(removed), abs(after), 0.01)
    rows = [
        (t("Project adds"), f"+{before:.2f} °C", before, "#ff7a3d"),
        (t("Offsets remove"), f"−{removed:.2f} °C", removed, "#46c4be"),
        (t("Net change"), f"{after:+.2f} °C", abs(after),
         "#ff7a3d" if after > 0.005 else "#46c4be"),
    ]
    markup = """<style>
    body {margin:0;background:#162020;color:#e4ebe9;font-family:Arial,'Noto Sans Malayalam',sans-serif;}
    .heat-ledger {padding:12px 16px;border:1px solid #36504d;border-radius:12px;}
    .heat-ledger-row {display:flex;justify-content:space-between;gap:12px;
                      font-size:20px;margin:5px 0;}
    .heat-ledger-track {height:9px;background:#29403d;border-radius:10px;overflow:hidden;}
    .heat-ledger-fill {height:100%;width:var(--ledger-width);background:var(--ledger-color);
                       animation:ledger-fill .9s ease-out both;}
    @keyframes ledger-fill {from {width:0;} to {width:var(--ledger-width);}}
    </style><div class='heat-ledger'>"""
    for i, (label, value, amount, color) in enumerate(rows):
        width = min(100, max(0, amount / scale * 100))
        number_id = " id='net-number'" if i == 2 else ""
        markup += (f"<div class='heat-ledger-row'><span>{label}</span>"
                   f"<strong{number_id} style='color:{color}'>{value}</strong></div>"
                   f"<div class='heat-ledger-track'><div class='heat-ledger-fill' "
                   f"style='--ledger-width:{width:.1f}%;--ledger-color:{color}'></div></div>")
    markup += f"""</div><script>
    const start = {before:.4f}, end = {after:.4f}, duration = 900;
    const output = document.getElementById('net-number');
    const format = value => `${{value >= 0 ? '+' : ''}}${{value.toFixed(2)}} °C`;
    let began;
    function tick(now) {{
      if (began === undefined) began = now;
      const p = Math.min(1, (now - began) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      output.textContent = format(start + (end - start) * eased);
      if (p < 1) requestAnimationFrame(tick);
    }}
    requestAnimationFrame(tick);
    </script>"""
    return markup


# ------------------------------------------------------------------ ① Today
with today:
    peak = LIVE.get("peak_heat_index_c") or M["season_heat_index_c"]
    act = exposure.act_today(wards, peak)
    hot_people = cells.loc[cells["hotspot"] & (cells["ward_id"] >= 0), "pop"].sum()
    area_word = "wards" if M["area_kind"] == "wards" else "areas"
    n_hot_wards = len(wards[wards["people_in_hotspots"] > 0])
    st.markdown(local(
        f"### {n_hot_wards} {area_word} have people in the top-10% heat-stress squares — "
        f"about **{hot_people:,.0f} people**.",
        f"### ഏറ്റവും കൂടുതൽ ചൂട് അനുഭവിക്കുന്ന 10% പ്രദേശങ്ങളിൽ {n_hot_wards} വാർഡുകളിലായി "
        f"ഏകദേശം **{hot_people:,.0f} ആളുകൾ** താമസിക്കുന്നു."))
    advice = " · ".join(t(item) for item in act["advice"])
    st.markdown(local(
        f"**Act today** (peak heat index {act['peak_heat_index_c']} °C, *{act['band']}*): "
        f"**{', '.join(act['wards'])}** — {advice}",
        f"**ഇന്ന് ചെയ്യേണ്ടത്** (ഉയർന്ന താപസൂചിക {act['peak_heat_index_c']} °C, "
        f"*{t(act['band'])}*): **{', '.join(act['wards'])}** — {advice}"))
    mcol, pcol = st.columns([2, 1])
    with mcol:
        three_d = st.toggle(local("3D wards · height = people in hotspots",
                                  "3D വാർഡുകൾ · ഉയരം = ചൂടേറിയ സ്ഥലങ്ങളിലെ ആളുകൾ"), key="today_3d")
        if three_d:
            today_deck = deck([heat_layer(0.25), ward_3d_layer()], view=KOCHI_3D, tooltip={
                "html": "<b>{name}</b><br>{anom} °C vs city<br>{hot_people} people in hotspots"})
        else:
            today_deck = deck([heat_layer(), ward_layer()])
        ev = st.pydeck_chart(today_deck, on_select="rerun",
                             selection_mode="single-object", key="today_map", height=560)
        lo, hi = M["heat_png_range"]
        st.markdown(legend(f"{lo:+.1f} °C · {local('cooler', 'തണുപ്പ്')}",
                           f"{local('hotter', 'ചൂട്')} · {hi:+.1f} °C"), unsafe_allow_html=True)
        st.caption(local(
            f"Heat Stress Map · colour = {config.LABEL_SURFACE} vs city median "
            f"(dark = cooler, yellow = hotter) · outlines = "
            f"{'wards' if M['area_kind'] == 'wards' else '1 km zones (ward map not loaded)'}",
            "ചൂട് ഭൂപടം · നിറങ്ങൾ നഗരത്തിലെ ശരാശരിയുമായി താരതമ്യപ്പെടുത്തിയ രാവിലെ ഏകദേശം 10:30-ലെ "
            "ഉപരിതല താപനിലയാണ് (ഇരുണ്ടത് = തണുപ്പ്; മഞ്ഞ = കൂടുതൽ ചൂട്) · "
            "അതിരുകൾ = വാർഡുകൾ" if M["area_kind"] == "wards" else
            "ചൂട് ഭൂപടം · അതിരുകൾ = 1 കി.മീ. മേഖലകൾ (വാർഡ് ഭൂപടം ലഭ്യമല്ല)"))
    picked = None
    try:
        objs = ev.selection["objects"].get("wards", [])
        picked = objs[0]["name"] if objs else None
    except (AttributeError, KeyError, TypeError):
        pass
    names = wards.sort_values("heat_stress", ascending=False)["ward"].tolist()
    with pcol:
        choice = st.selectbox(t("Ward / area"), names,
                              index=names.index(picked) if picked in names else 0,
                              key="today_ward")
        w = wards[wards["ward"] == choice].iloc[0]
        st.metric(t("People"), f"{w['people']:,.0f}",
                  local(f"{w['lst_anom']:+.1f} °C vs city",
                        f"നഗര ശരാശരിയേക്കാൾ {w['lst_anom']:+.1f} °C"), delta_color="inverse")
        why_hot_label = t("Why it's hot")
        st.markdown(f"**{why_hot_label}**")
        for s in i18n.drivers(w, lang):
            st.markdown(f"- {s}")
        drv = {k.split('::', 1)[1]: v for k, v in w.items() if str(k).startswith("drv::")}
        drv.pop("Weather of the day", None)
        dd = pd.DataFrame({"driver": [t(k) for k in drv], "c": [float(v) for v in drv.values()]})
        dd["label"] = dd["c"].map(lambda v: f"{v:+.1f} °C")
        base = alt.Chart(dd).encode(
            y=alt.Y("driver:N", sort="-x", title=None),
            x=alt.X("c:Q", title=local("°C added (+) or removed (−)", "°C കൂട്ടുന്നു (+) / കുറയ്ക്കുന്നു (−)")))
        bars = base.mark_bar(cornerRadius=4).encode(color=alt.condition(
            "datum.c > 0", alt.value("#ff7a3d"), alt.value("#46c4be")))
        text = base.mark_text(align="left", dx=4, color="#e4ebe9", fontSize=13).encode(text="label")
        st.altair_chart(styled((bars + text).properties(height=210)), width="stretch")
        st.caption(local(f"{int(w['schools'])} schools · {int(w['markets'])} markets · "
                         f"{int(w['construction_sites'])} construction sites",
                         f"{int(w['schools'])} സ്കൂളുകൾ · {int(w['markets'])} ചന്തകൾ · "
                         f"{int(w['construction_sites'])} നിർമാണ സ്ഥലങ്ങൾ"))
    if LIVE.get("forecast"):
        fc = pd.DataFrame(LIVE["forecast"]).assign(time=lambda d: pd.to_datetime(d["time"]))
        st.markdown(f"**{t('Next 72 hours — heat index (city)')}**")
        bands = pd.DataFrame([{"band": t(n), "lo": a, "hi": min(b, 56)}
                              for n, a, b in config.HEAT_INDEX_BANDS_C])
        y_lo = min(26.0, float(fc["heat_index_c"].min()) - 1)
        y_hi = max(42.0, float(fc["heat_index_c"].max()) + 2)
        bands = bands[bands["lo"] < y_hi].assign(hi=lambda d: d["hi"].clip(upper=y_hi))
        shade = alt.Chart(bands).mark_rect(opacity=0.16).encode(
            y=alt.Y("lo:Q", scale=alt.Scale(domain=[y_lo, y_hi]), title="°C"), y2="hi:Q",
            color=alt.Color("band:N", scale=alt.Scale(
                domain=[t(n) for n, *_ in config.HEAT_INDEX_BANDS_C],
                range=["#e8c35a", "#e97a2e", "#d4483f", "#8e1b3a"]),
                legend=alt.Legend(orient="top", title=None, labelColor="#b9c8c5")))
        curve = alt.Chart(fc).encode(x=alt.X("time:T", title=None,
                                             axis=alt.Axis(format="%a %H:%M")),
                                     y=alt.Y("heat_index_c:Q", title="°C"))
        area = curve.mark_area(line={"color": "#ff7a3d", "strokeWidth": 2.5}, opacity=0.35,
                               color=alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0, stops=[
                                   alt.GradientStop(color="rgba(22,32,32,0)", offset=0),
                                   alt.GradientStop(color="#ff7a3d", offset=1)]))
        pk = fc.loc[[fc["heat_index_c"].idxmax()]].assign(
            label=lambda d: d["heat_index_c"].map(lambda v: f"{local('peak', 'ഉയർന്നത്')} {v:.1f} °C"))
        peak_dot = alt.Chart(pk).mark_point(size=120, filled=True, color="#fcffa4").encode(
            x="time:T", y="heat_index_c:Q")
        peak_txt = alt.Chart(pk).mark_text(dy=-14, color="#fcffa4", fontSize=13, fontWeight="bold").encode(
            x="time:T", y="heat_index_c:Q", text="label:N")
        st.altair_chart(styled((shade + area + peak_dot + peak_txt).properties(height=230)),
                        width="stretch")
    with st.expander(t("Atmospheric drivers — how the day's weather changes Kochi's surface heat")):
        at = M["atmospheric"]
        ae = pd.DataFrame([{"change": t(v["label"]), "effect": v["effect_c"], "lo": v["ci_low"],
                            "hi": v["ci_high"]} for v in at["effects"].values()])
        enc = alt.Chart(ae).encode(y=alt.Y("change:N", title=None, sort="-x"))
        forest = (enc.mark_rule(strokeWidth=3, color="#6f8784").encode(
                      x=alt.X("lo:Q", title=local("Surface °C effect (95% CI)", "ഉപരിതല °C മാറ്റം (95% CI)")),
                      x2="hi:Q")
                  + enc.mark_point(size=160, filled=True).encode(x="effect:Q", color=alt.condition(
                      "datum.effect > 0", alt.value("#ff7a3d"), alt.value("#46c4be")))
                  + alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(strokeDash=[4, 4], color="#9fb3b0")
                  .encode(x="x:Q"))
        st.altair_chart(styled(forest.properties(height=40 * len(ae) + 40)), width="stretch")
        st.dataframe(pd.DataFrame([{t("Change"): t(v["label"]), t("Surface °C"): round(v["effect_c"], 2),
                                    "95% CI": f"{v['ci_low']:+.2f} to {v['ci_high']:+.2f}"}
                                   for v in at["effects"].values()]), hide_index=True)
        st.caption(local(f"From the scene-panel model across n = {at['n_scenes']} satellite days "
                         "(bootstrap over days — small n, so read the intervals).",
                         f"{at['n_scenes']} ഉപഗ്രഹ നിരീക്ഷണ ദിവസങ്ങളെ അടിസ്ഥാനമാക്കിയ കണക്ക്. "
                         "ദിവസങ്ങളുടെ എണ്ണം കുറവായതിനാൽ പിശകിന്റെ പരിധിയും പരിഗണിക്കുക."))

# ------------------------------------------------------------------ ② Plan ₹
with plan_tab:
    budget = st.segmented_control(t("Budget"), [f"₹{b} {t('crore')}" for b in config.BUDGET_PRESETS_CR],
                                  default=f"₹10 {t('crore')}", key="budget") or f"₹10 {t('crore')}"
    b = budget.split("₹")[1].split(" ")[0]
    P = D["plans"]["presets"][b]
    ours = P["ours"]
    best_base = max(P["baselines"], key=lambda s: s["person_deg_cooling"])
    gain = ours["person_deg_cooling"] / max(best_base["person_deg_cooling"], 1e-9)
    st.markdown(local(
        f"### {budget} → about **{ours['people_cooled']:,.0f} people** cooler by "
        f"**{abs(ours['mean_dt_cooled']):.2f} °C** on average — **{gain:.1f}×** the best simple strategy.",
        f"### {budget} ബജറ്റിൽ ഏകദേശം **{ours['people_cooled']:,.0f} ആളുകൾക്ക്** "
        f"ശരാശരി **{abs(ours['mean_dt_cooled']):.2f} °C** ഉപരിതല ചൂടുകുറവ് — "
        f"ലളിതമായ മികച്ച രീതിയേക്കാൾ **{gain:.1f} മടങ്ങ്** ഫലം."))
    conservative = st.toggle(t("Conservative mode · show back-test error band"), key="conservative")
    show_canal_banks = st.toggle(t("Show OSM canal-bank tree-strip candidates"), key="canal_overlay")
    backtest_mae = float(M["backtest"]["mae_c"])
    if conservative:
        lo = ours["mean_dt_cooled"] - backtest_mae
        hi = ours["mean_dt_cooled"] + backtest_mae
        st.info(local(
            f"Mean surface ΔT: {ours['mean_dt_cooled']:+.2f} °C, with an empirical "
            f"back-test error band of {lo:+.2f} to {hi:+.2f} °C "
            f"(±{backtest_mae:.2f} °C MAE). This is not a confidence interval or a "
            "guaranteed cooling range.",
            f"ശരാശരി ഉപരിതല താപമാറ്റം: {ours['mean_dt_cooled']:+.2f} °C. "
            f"മുൻപരിശോധനയിലെ ശരാശരി പിശക് (±{backtest_mae:.2f} °C) ചേർത്താൽ "
            f"{lo:+.2f} മുതൽ {hi:+.2f} °C വരെ. ഇത് വിശ്വാസപരിധിയോ ഉറപ്പുള്ള ചൂടുകുറവോ അല്ല."))
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(t("People cooled (≥0.1 °C)"), f"{ours['people_cooled']:,.0f}")
    k2.metric(t("Avg cooling"), f"{ours['mean_dt_cooled']:.2f} °C")
    k3.metric(t("₹ per person"), f"{ours['cost_rs'] / max(ours['people_cooled'], 1):,.0f}")
    k4.metric(t("Sites (100 m)"), f"{ours['cells']:,}")
    mc, sc = st.columns([2, 1])
    with mc:
        hexrgb = lambda h: [int(h[i:i + 2], 16) for i in (1, 3, 5)]
        pal = {cfg["label"]: hexrgb(c) for cfg, c in zip(config.INTERVENTIONS.values(), FIX_COLORS)}
        picks = pd.DataFrame(P["picks"], columns=["lat", "lon", "fix", "dt", "cost"])
        picks["color"] = picks["fix"].map(pal)
        picks["elev"] = picks["dt"].abs().clip(upper=8) * 90 + 40
        cool = pd.DataFrame(P["cooling"], columns=["lat", "lon", "dt"])
        plan_3d = st.toggle(local("3D view · column height = cooling at the site",
                                  "3D കാഴ്ച · ഉയരം = ആ സ്ഥലത്തെ ചൂടുകുറവ്"), value=True, key="plan_3d")
        pick_layer = (
            pdk.Layer("ColumnLayer", id="picks", data=picks, get_position=["lon", "lat"], radius=42,
                      get_elevation="elev", elevation_scale=1, extruded=True, get_fill_color="color",
                      pickable=True, auto_highlight=True)
            if plan_3d else
            pdk.Layer("ScatterplotLayer", id="picks", data=picks, get_position=["lon", "lat"],
                      get_radius=55, get_fill_color="color", stroked=True, get_line_color=[0, 0, 0, 180],
                      line_width_min_pixels=1, pickable=True))
        map_layers = [
            heat_layer(0.35),
            pdk.Layer("ScatterplotLayer", id="cooling", data=cool, get_position=["lon", "lat"],
                      get_radius=50, get_fill_color=TEAL + [60]),
            pick_layer,
        ]
        if show_canal_banks and not D["canal_banks"].empty:
            map_layers.append(pdk.Layer(
                "ScatterplotLayer", id="canal_banks", data=D["canal_banks"],
                get_position=["lon", "lat"], get_radius=18,
                get_fill_color=[70, 140, 255, 150], pickable=False))
        st.pydeck_chart(deck(map_layers, tooltip={"text": "{fix}: {dt} °C"},
                             view=KOCHI_3D if plan_3d else None),
                        key="plan_map", height=540)
        used = [cfg["label"] for cfg in config.INTERVENTIONS.values() if cfg["label"] in ours["mix"]]
        st.markdown(swatches([(t(n), hexcolor(pal[n])) for n in used]
                             + [(local("cooled by spillover", "സമീപ സ്വാധീനം"), "#46c4be66")]),
                    unsafe_allow_html=True)
        st.caption(local(
            "Coloured dots = where each fix goes (public land only). Teal haze = cells cooled "
            f"≥0.05 °C, incl. spillover. {config.LABEL_SURFACE}. The plan covers the study area; "
            "named wards cover Kochi municipality.",
            "നിറമുള്ള ബിന്ദുക്കൾ = ഓരോ ഇടപെടലിന്റെയും സ്ഥലം (പൊതുഭൂമിയിൽ മാത്രം). "
            "നീലപ്പച്ച ഭാഗങ്ങൾ = ചുറ്റുപാടിലേക്കുള്ള സ്വാധീനമുൾപ്പെടെ ≥0.05 °C ഉപരിതല ചൂടുകുറവ്. "
            "പദ്ധതി പഠനപ്രദേശം മുഴുവൻ ഉൾക്കൊള്ളുന്നു; പേരുള്ള വാർഡുകൾ കൊച്ചി കോർപ്പറേഷനിൽ മാത്രം."))
        if show_canal_banks:
            st.caption(local(
                "Blue dots = 100 m cells near OSM canals, drains or ditches where tree strips "
                "could be checked on site. These are not verified IURWTS alignments; "
                "canals receive 0 °C credit in this plan.",
                "നീല ബിന്ദുക്കൾ = OSM രേഖകളിലെ കനാൽ, ഓട, ചാൽ എന്നിവയ്ക്ക് സമീപമുള്ള 100 മീ. സ്ഥലങ്ങൾ. "
                "വൃക്ഷനിര നടാൻ നേരിട്ട് പരിശോധിക്കേണ്ട സാധ്യതകളാണിവ; സ്ഥിരീകരിച്ച IURWTS പാതകളല്ല. "
                "കനാലിന് ഈ പദ്ധതിയിൽ 0 °C ചൂടുകുറവ് മാത്രമാണ് കണക്കാക്കിയത്."))
    with sc:
        comp = pd.DataFrame([{"Strategy": t(s["strategy"]), "People cooled": s["people_cooled"],
                              "Person-°C": s["person_deg_cooling"]} for s in [ours, *P["baselines"]]])
        st.markdown(f"**{t('Same money, three strategies')}**")
        comp["ours"] = [True] + [False] * (len(comp) - 1)
        comp["label"] = comp["Person-°C"].map(lambda v: f"{v:,.0f}")
        cb = alt.Chart(comp).encode(
            y=alt.Y("Strategy:N", sort=None, title=None),
            x=alt.X("Person-°C:Q", title=local("person-°C of cooling", "ആൾ-°C ചൂടുകുറവ്")))
        st.altair_chart(styled((
            cb.mark_bar(cornerRadius=5).encode(color=alt.condition(
                "datum.ours", alt.value("#46c4be"), alt.value("#4a5f5c")))
            + cb.mark_text(align="left", dx=5, color="#e4ebe9", fontSize=13).encode(text="label")
        ).properties(height=170)), width="stretch")
        st.markdown(f"<div class='sub'>{local('VISAT plan', 'VISAT പദ്ധതി')}: "
                    f"<b style='color:#46c4be;font-size:1.4rem'>{gain:.1f}×</b> "
                    f"{local('the best simple strategy', 'ലളിതമായ മികച്ച രീതി')}</div>",
                    unsafe_allow_html=True)
        mix = pd.DataFrame([{"fix": t(k), "lakh": round(v["cost_rs"] / 1e5, 1), "sites": v["cells"],
                             "color": hexcolor(pal.get(k, TEAL))}
                            for k, v in ours["mix"].items()])
        donut = alt.Chart(mix).mark_arc(innerRadius=58, outerRadius=100, stroke="#0e1514",
                                        strokeWidth=2).encode(
            theta="lakh:Q", color=alt.Color("fix:N", scale=alt.Scale(
                domain=mix["fix"].tolist(), range=mix["color"].tolist()),
                legend=alt.Legend(orient="bottom", columns=2, title=None, labelColor="#b9c8c5")),
            tooltip=["fix", "sites", alt.Tooltip("lakh:Q", title="₹ lakh")])
        centre = alt.Chart(pd.DataFrame({"t": [f"₹{b} Cr"]})).mark_text(
            fontSize=20, fontWeight="bold", color="#e4ebe9").encode(text="t:N")
        st.markdown(f"**{local('Where the money goes', 'പണം എവിടേക്ക്')}**")
        st.altair_chart(styled((donut + centre).properties(height=280)), width="stretch")
        st.dataframe(pd.DataFrame([{t("Fix"): t(k), t("Sites"): v["cells"],
                                    t("₹ lakh"): round(v["cost_rs"] / 1e5, 1)}
                                   for k, v in ours["mix"].items()]), hide_index=True)
    with st.expander(t("Budget curve & scenario evaluation (every intervention PS1 lists)")):
        curve = pd.DataFrame(D["plans"]["curve"]).melt("budget_cr", var_name="strategy",
                                                        value_name="person_deg")
        cl = alt.Chart(curve).mark_line(point=True, strokeWidth=3).encode(
            x=alt.X("budget_cr:Q", title=local("Budget (₹ crore)", "ബജറ്റ് (₹ കോടി)")),
            y=alt.Y("person_deg:Q", title=local("person-°C of cooling", "ആൾ-°C ചൂടുകുറവ്")),
            color=alt.Color("strategy:N", scale=alt.Scale(
                domain=["VISAT plan", "Trees everywhere", "Spread evenly"],
                range=["#46c4be", "#e8c35a", "#8a9e9b"]),
                legend=alt.Legend(orient="top", title=None, labelColor="#b9c8c5")),
            tooltip=["strategy", "budget_cr", alt.Tooltip("person_deg:Q", format=",.0f")])
        now_rule = alt.Chart(pd.DataFrame({"x": [float(b)]})).mark_rule(
            strokeDash=[5, 4], color="#fcffa4").encode(x="x:Q")
        st.altair_chart(styled((cl + now_rule).properties(height=280)), width="stretch")
        st.caption(local(
            "Estimated person-°C (sum of per-site effects); the three presets above use a full "
            "joint re-prediction.",
            "ആൾ-°C ഒരു ഏകദേശ കണക്കാണ്. മുകളിലെ മൂന്ന് ബജറ്റ് പദ്ധതികൾക്കായി എല്ലാ ഇടപെടലുകളും "
            "ഒരുമിച്ച് ചേർത്ത് വീണ്ടും പ്രവചിച്ചിട്ടുണ്ട്."))
        validity = pd.DataFrame(M["validity_matrix"])
        if lang == "ml":
            for column in ("intervention", "ps1_category", "method", "cost_note"):
                validity[column] = validity[column].map(t)
            validity = validity.rename(columns={"intervention": "ഇടപെടൽ", "ps1_category": "വിഭാഗം",
                                                "method": "രീതി", "eligible_cells": "യോഗ്യമായ സ്ഥലങ്ങൾ",
                                                "median_dt_c": "മധ്യ താപമാറ്റം (°C)",
                                                "within_support_pct": "സമാനസ്ഥല പിന്തുണ (%)",
                                                "cost_note": "ചെലവിന്റെ അടിസ്ഥാനം"})
        st.dataframe(validity, hide_index=True)
        st.caption(local(config.CANAL_CREDIT_NOTE,
                         "IURWTS-ലെ ആറു കനാലുകൾ KMRL-ന്റെ നിലവിലുള്ള പദ്ധതിയാണ്. "
                         "100 മീ. ഗ്രിഡിനെക്കാൾ ഇടുങ്ങിയതിനാൽ കനാൽ പണിക്ക് 0 °C ചൂടുകുറവ് മാത്രം "
                         "കണക്കാക്കുന്നു; കനാൽക്കര വൃക്ഷനിരകൾ വേറെ പരിഗണിക്കുന്നു."))
    with st.expander(t("Site-by-site plan · fix, ward, people, surface °C and cost")):
        locations = cells[["lat", "lon", "ward_id", "pop"]].copy()
        locations[["lat", "lon"]] = locations[["lat", "lon"]].round(5)
        site_table = picks.merge(locations, on=["lat", "lon"], how="left",
                                 validate="many_to_one")
        site_table["Ward / area"] = site_table["ward_id"].map(wards["ward"])
        site_table["Ward / area"] = site_table["Ward / area"].fillna(t("Outside Kochi wards"))
        site_table["Surface ΔT (°C)"] = site_table["dt"].map(lambda x: f"{x:+.2f}")
        if conservative:
            site_table["Back-test band (°C)"] = site_table["dt"].map(
                lambda x: f"{x - backtest_mae:+.2f} to {x + backtest_mae:+.2f}")
        columns = ["Ward / area", "fix", "Surface ΔT (°C)"]
        if conservative:
            columns.append("Back-test band (°C)")
        site_table["People at site"] = site_table["pop"].round(0)
        site_table["₹ lakh"] = (site_table["cost"] / 1e5).round(2)
        display_sites = site_table[columns + ["People at site", "₹ lakh", "lat", "lon"]].copy()
        display_sites["fix"] = display_sites["fix"].map(t)
        display_sites = display_sites.rename(columns={
            "fix": "Fix", "lat": "Latitude", "lon": "Longitude"})
        if lang == "ml":
            display_sites = display_sites.rename(columns={column: t(column) for column in display_sites})
        st.dataframe(display_sites, hide_index=True)
        st.caption(local(
            "Each row is one selected 100 m cell. People at site use GHSL 2020; the total plan "
            "also counts spillover. Per-site surface ΔT is the saved joint prediction. "
            "The empirical back-test MAE is not a statistical confidence interval.",
            "ഓരോ വരിയും തെരഞ്ഞെടുത്ത 100 മീ. സ്ഥലമാണ്. ഇവിടത്തെ ആളുകളുടെ കണക്ക് GHSL 2020-ൽ നിന്നാണ്; "
            "ആകെ പദ്ധതിയിൽ സമീപപ്രദേശങ്ങളിലേക്കുള്ള സ്വാധീനവും ഉൾപ്പെടും. സ്ഥലത്തെ താപമാറ്റം "
            "എല്ലാ ഇടപെടലുകളും ചേർത്തുള്ള പ്രവചനമാണ്. മുൻപരിശോധനയിലെ ശരാശരി പിശക് വിശ്വാസപരിധിയല്ല."))

# ------------------------------------------------------------------ ③ Check a Project
with project_tab:
    sites = D["hn"]["sites"]
    site_geo = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": s["site"]},
         "geometry": {"type": "Polygon", "coordinates": [s["polygon"]]}} for s in sites]}
    c1, c2 = st.columns([1, 2])
    with c1:
        site_names = [s["site"] for s in sites]
        site = st.selectbox(t("Proposed site"), site_names, key="site", format_func=t)
        uses = {v["label"]: k for k, v in config.PROJECT_USES.items()}
        use = st.segmented_control(t("Proposed use"), list(uses), default="IT park",
                                   key="use", format_func=t) or "IT park"
        R = D["hn"]["results"][f"{site}|{uses[use]}"]
        neutral = st.toggle(t("Apply available offsets"), key="neutral")
        if not neutral:
            st.markdown(f"<div class='ledger hot'>+{R['before']['mean_dt_c']:.1f} °C</div>"
                        f"<b>{R['before']['people']:,} {local('people', 'ആളുകൾ')}</b> "
                        f"{local('within ~500 m', 'ഏകദേശം 500 മീ. പരിധിയിൽ')}",
                        unsafe_allow_html=True)
        else:
            components.html(heat_ledger(R), height=160, scrolling=False)
            st.markdown(f"**{t('Offset package')}: ₹{R['offset_cost_rs'] / 1e5:,.1f} {t('lakh')}**")
            if R["after"]["mean_dt_c"] > 0.005:
                st.warning(local("Heat remains after these offsets. This proposal does not pass the "
                                 "heat-neutral screen yet.",
                                 "ഈ നടപടികൾക്കുശേഷവും ചൂട് കൂടുതലാണ്. നിർദിഷ്ട പദ്ധതി നിലവിൽ "
                                 "ചൂട്-നിഷ്പക്ഷ പരിശോധനയിൽ വിജയിക്കുന്നില്ല."))
            else:
                st.success(local("This proposal passes the modelled heat-neutral screen.",
                                 "മാതൃക കണക്കനുസരിച്ച് ഈ പദ്ധതി ചൂട്-നിഷ്പക്ഷ പരിശോധനയിൽ വിജയിക്കുന്നു."))
            for k, v in R["offset_mix"].items():
                st.markdown(f"- {t(k)}: {v['cells']} {t('Sites').lower()} · "
                            f"₹{v['cost_rs'] / 1e5:,.1f} {t('lakh')}")
        st.caption(local(R["label"], "രാവിലെ അളക്കുന്ന, ഏകദേശം 500 മീ. പരിധിയിലെ ആളുകളുടെ എണ്ണം "
                         "അനുസരിച്ച് തൂക്കിയ ഉപരിതല താപമാറ്റം (°C)"))
        st.info(local(R["policy"],
                      "ഇത് അനുമതിയല്ല; പ്രാഥമിക പരിശോധനയ്ക്കും നയ നിർദ്ദേശത്തിനുമുള്ള ഉപകരണം മാത്രം. "
                      "സാധ്യമായ വഴി: KMBR 2019-ലെ അധിക FSI പ്രോത്സാഹനത്തിന് സ്വമേധയാ ചൂട് കുറയ്ക്കൽ; "
                      "20,000–150,000 ച.മീ. പദ്ധതികളുടെ SEIAA Form-1A-യിൽ ചേർക്കൽ; "
                      "കൊച്ചി മാസ്റ്റർ പ്ലാൻ 2040-ലെ കാലാവസ്ഥാ പ്രതിരോധ മാർഗ്ഗനിർദ്ദേശം. "
                      "അവസാന തീരുമാനം കോർപ്പറേഷന്റെ കെട്ടിടാനുമതി വിഭാഗത്തിനോ നഗരാസൂത്രണ സമിതിക്കോ."))
    with c2:
        heat = pd.DataFrame(R["heat_cells"], columns=["lat", "lon", "dt"])
        layers = [heat_layer(0.3),
                  pdk.Layer("GeoJsonLayer", id="sites", data=site_geo, stroked=True, filled=True,
                            get_fill_color=[255, 255, 255, 40], get_line_color=[255, 255, 255, 220],
                            line_width_min_pixels=2, pickable=True),
                  pdk.Layer("ScatterplotLayer", id="heatspread", data=heat, get_position=["lon", "lat"],
                            get_radius=45, get_fill_color=HEAT + [150])]
        s0 = next(s for s in sites if s["site"] == site)
        view = pdk.ViewState(latitude=s0["center"][0], longitude=s0["center"][1], zoom=13.6)
        project_3d = st.toggle(local("3D heat dome · column height = added surface °C",
                                     "3D ചൂട് ഗോപുരം · ഉയരം = കൂടുന്ന ഉപരിതല °C"),
                               value=True, key="project_3d")
        if project_3d:
            # Heat dome: the project's added heat rises as columns; offsets pull it down in teal.
            dmax = max(float(heat["dt"].max()) if len(heat) else 0.0, 0.01)
            dome = heat.assign(
                elev=lambda d: d["dt"].clip(lower=0) / dmax * 900 + 20,
                color=lambda d: [inferno(0.45 + 0.55 * v / dmax) + [230] for v in d["dt"].clip(lower=0)],
                name=lambda d: d["dt"].map(lambda v: f"+{v:.2f} °C"), fix="")
            shown = [layers[0], layers[1], pdk.Layer(
                "ColumnLayer", id="heatspread", data=dome, get_position=["lon", "lat"], radius=40,
                get_elevation="elev", get_fill_color="color", extruded=True, pickable=True,
                auto_highlight=True)]
            if neutral:
                off = pd.DataFrame(R["offset_cells"], columns=["lat", "lon", "fix"]).assign(name="")
                shown.append(pdk.Layer("ColumnLayer", id="offsets", data=off, get_position=["lon", "lat"],
                                       radius=40, get_elevation=260, get_fill_color=TEAL + [240],
                                       extruded=True, pickable=True))
            view = pdk.ViewState(latitude=s0["center"][0] - 0.004, longitude=s0["center"][1],
                                 zoom=14.2, pitch=55, bearing=-25)
        else:
            shown = list(layers)
            if neutral:
                off = pd.DataFrame(R["offset_cells"], columns=["lat", "lon", "fix"])
                shown.append(pdk.Layer("ScatterplotLayer", id="offsets", data=off,
                                       get_position=["lon", "lat"], get_radius=40,
                                       get_fill_color=TEAL + [230], pickable=True))
        st.pydeck_chart(pdk.Deck(layers=mask_layer() + shown, initial_view_state=view, map_provider="carto",
                                 map_style="dark", tooltip={"text": "{name}{fix}"}),
                        key="project_map", height=560)
        st.markdown(swatches([(local("added surface heat", "കൂടുന്ന ചൂട്"), "#f57d15"),
                              (local("offset sites", "ചൂട് കുറയ്ക്കൽ സ്ഥലങ്ങൾ"), "#46c4be"),
                              (local("project site", "പദ്ധതി സ്ഥലം"), "#ffffff")]),
                    unsafe_allow_html=True)
        view = pdk.ViewState(latitude=s0["center"][0], longitude=s0["center"][1], zoom=13.6)
        st.caption(local(
            "Orange = where the project adds surface heat. Teal = modelled offset sites "
            "(trees nearby + cool/green roofs on the project).",
            "ഓറഞ്ച് = പദ്ധതി ഉപരിതല ചൂട് കൂട്ടുന്ന സ്ഥലം. നീലപ്പച്ച = മാതൃകയിൽ കണക്കാക്കിയ "
            "ചൂട് കുറയ്ക്കൽ സ്ഥലങ്ങൾ (സമീപത്തെ മരങ്ങളും പദ്ധതിയിലെ മേൽക്കൂര നടപടികളും)."))
    with st.expander(t("Compare the modelled heat before and after offsets")):
        st.caption(local(
            "Same site and map scale in both views. Orange marks added heat; teal marks "
            "offset locations. The ledger above gives the net surface °C change.",
            "രണ്ട് ഭൂപടങ്ങളിലും ഒരേ സ്ഥലവും അളവുമാണ്. ഓറഞ്ച് = കൂടുന്ന ചൂട്; "
            "നീലപ്പച്ച = ചൂട് കുറയ്ക്കൽ നടപടികൾ. മുകളിലെ പട്ടികയിൽ അവസാന ഉപരിതല താപമാറ്റം കാണാം."))
        before_map, after_map = st.columns(2)
        with before_map:
            st.markdown(f"**{t('Project only')}**")
            st.pydeck_chart(pdk.Deck(layers=mask_layer() + layers[:3], initial_view_state=view,
                                     map_provider="carto", map_style="dark"),
                            key="project_before_map", height=320)
        with after_map:
            st.markdown(f"**{t('Project + available offsets')}**")
            comparison_layers = layers[:3] + [pdk.Layer(
                "ScatterplotLayer", id="comparison_offsets",
                data=pd.DataFrame(R["offset_cells"], columns=["lat", "lon", "fix"]),
                get_position=["lon", "lat"], get_radius=40,
                get_fill_color=TEAL + [230], pickable=True)]
            st.pydeck_chart(pdk.Deck(layers=mask_layer() + comparison_layers, initial_view_state=view,
                                     map_provider="carto", map_style="dark"),
                            key="project_after_map", height=320)
    if D["reactions"]:
        rx = D["reactions"].get(f"{site}|{uses[use]}")
        if rx:
            with st.expander(t("How might residents react? (SIMULATED)")):
                st.warning(local("Simulated personas built from aggregate statistics — not real people or "
                                 "survey data. For preparing public consultation only; never changes any number.",
                                 "ഇവ യഥാർത്ഥ ആളുകളുടെയോ സർവേകളുടെയോ അഭിപ്രായങ്ങളല്ല. "
                                 "പൊതുചർച്ചയ്ക്ക് തയ്യാറാകാൻ കണക്കുകൾ അടിസ്ഥാനമാക്കി സൃഷ്ടിച്ച "
                                 "സാങ്കൽപ്പിക പ്രതികരണങ്ങൾ മാത്രം; ഇവ ഒരു കണക്കും മാറ്റുന്നില്ല."))
                df = pd.DataFrame(rx["personas"])
                st.bar_chart(df["stance"].value_counts(), color="#46c4be")
                st.markdown(f"**{t('Top concerns')}:** " + "; ".join(rx.get("top_concerns", [])))
                st.dataframe(df[["persona", "stance", "top_concern", "quote_en"]], hide_index=True)

# ------------------------------------------------------------------ ④ Proof & Ward Card
with proof_tab:
    bt = M["backtest"]
    a, b2 = st.columns([3, 2])
    with a:
        st.markdown("### " + t("We predicted 2024 from 2017 — here's how close we got"))
        if "points" in bt:
            predicted, observed = t("Predicted Δ °C"), t("Observed Δ °C")
            pts = pd.DataFrame(bt["points"], columns=[predicted, observed])
            lim = [min(pts.min()), max(pts.max())]
            q1, q2, q3 = st.columns(3)
            q1.metric(local("Changed cells", "മാറിയ സ്ഥലങ്ങൾ"),
                      f"{bt['n_changed_cells']:,}")
            q2.metric(local("Correlation r", "ബന്ധം r"), f"{bt['pearson_r']:.2f}")
            q3.metric(local("Typical error", "ശരാശരി പിശക്"), f"±{bt['mae_c']:.2f} °C")
            chart = alt.Chart(pts).mark_circle(size=16, opacity=0.35).encode(
                x=alt.X(predicted, scale=alt.Scale(domain=lim)),
                y=alt.Y(observed, scale=alt.Scale(domain=lim)),
                color=alt.Color(observed, scale=alt.Scale(scheme="inferno", domainMid=0), legend=None))
            line = alt.Chart(pd.DataFrame({"x": lim, "y": lim})).mark_line(
                color="#46c4be", strokeWidth=2.5, strokeDash=[6, 4]).encode(
                x=alt.X("x:Q", title=predicted), y=alt.Y("y:Q", title=observed))
            slope, icpt = np.polyfit(pts[predicted], pts[observed], 1)
            trend = alt.Chart(pd.DataFrame({"x": lim, "y": [icpt + slope * v for v in lim]})).mark_line(
                color="#fcffa4", strokeWidth=3, clip=True).encode(x="x:Q", y="y:Q")
            st.altair_chart(styled((chart + line + trend).properties(height=420)), width="stretch")
            st.caption(local(
                f"{bt['label']} · {bt['n_changed_cells']:,} cells that really changed · "
                f"r = {bt['pearson_r']:.2f} · error ±{bt['mae_c']:.2f} °C · teal dashes = perfect "
                "match · yellow = fitted trend",
                f"2017→2024 ഉപരിതല താപമാറ്റം · യഥാർത്ഥത്തിൽ മാറിയ {bt['n_changed_cells']:,} സ്ഥലങ്ങൾ · "
                f"ബന്ധം r = {bt['pearson_r']:.2f} · ശരാശരി പിശക് ±{bt['mae_c']:.2f} °C · "
                "നീലപ്പച്ച രേഖ = കൃത്യമായ പ്രവചനം"))
        else:
            st.info(local(bt.get("note", "Back-test unavailable."),
                          "മുൻകാല വിവരങ്ങളുമായുള്ള പരിശോധന ഇപ്പോൾ ലഭ്യമല്ല."))
    with b2:
        cv = M["cv"]
        st.markdown(f"**{t('Honest accuracy (areas the model never saw)')}**")
        cvd = pd.DataFrame([{"model": k.replace(" (ours)", ""), "r2": v["r2"], "ours": "(ours)" in k,
                             "label": f"R² {v['r2']:.2f}"} for k, v in cv["spatial_cv"].items()])
        cve = alt.Chart(cvd).encode(y=alt.Y("model:N", sort=None, title=None),
                                    x=alt.X("r2:Q", scale=alt.Scale(domain=[0, 1]), title="R²"))
        st.altair_chart(styled((
            cve.mark_bar(cornerRadius=5).encode(color=alt.condition(
                "datum.ours", alt.value("#46c4be"), alt.value("#4a5f5c")))
            + cve.mark_text(align="left", dx=5, color="#e4ebe9", fontSize=13).encode(text="label")
        ).properties(height=160)), width="stretch")
        st.dataframe(pd.DataFrame([{t("Model"): k, "R²": round(v["r2"], 3),
                                    t("Error (°C)"): round(v["rmse"], 2)}
                                   for k, v in cv["spatial_cv"].items()]), hide_index=True)
        st.caption(local(
            f"Grouped spatial-block CV (2 km blocks across {cv['n_scenes']} scenes). Random CV "
            f"(easier, not what we report): R² {cv['random_cv_ours']['r2']:.3f}.",
            f"{cv['n_scenes']} ഉപഗ്രഹ നിരീക്ഷണങ്ങളിലെ 2 കി.മീ. പ്രദേശങ്ങൾ വേർതിരിച്ച് കൃത്യത "
            f"പരിശോധിച്ചു. ലളിതമായ റാൻഡം പരിശോധനയിൽ R² = {cv['random_cv_ours']['r2']:.3f}; "
            "അതാണ് ഇവിടെ പ്രധാന കൃത്യതയായി കാണിക്കാത്തത്."))
        if M.get("ecostress"):
            e = M["ecostress"]
            st.metric(t("Afternoon check (ECOSTRESS 12:00–15:30)"),
                      f"{e['top_decile_overlap_pct']:.0f}% of hotspots hold",
                      f"Spearman {e['spearman_cells']:.2f}", delta_color="off")
        if M.get("cpcb"):
            c = M["cpcb"]
            if "mae_heat_index_c" in c:
                st.metric(t("CPCB stations vs ERA5 heat index"), f"±{c['mae_heat_index_c']:.1f} °C",
                          f"{c['n_days']} days", delta_color="off")
        matched = bt.get("matched")
        if matched and "mae_c" in matched:
            st.metric(t("Matched 2017→2024 check"), f"±{matched['mae_c']:.2f} °C",
                      local(f"{matched['n_changed_matched']:,} changed cells",
                            f"മാറിയ {matched['n_changed_matched']:,} സ്ഥലങ്ങൾ"), delta_color="off")
            st.caption(local("Changed cells vs k nearest unchanged cells on 2017 land features. "
                             "Exploratory comparison; not a causal estimate.",
                             "2017-ലെ ഭൂപ്രകൃതിയിൽ സമാനമായ, മാറ്റമില്ലാത്ത സ്ഥലങ്ങളുമായുള്ള താരതമ്യം. "
                             "ഇത് കാരണബന്ധത്തിന്റെ തെളിവല്ല."))
    with st.expander(t("Physics check · validity matrix · data freshness · limits")):
        ph = M["physics_check"]
        if ph:
            st.markdown(local(
                f"**Cool roofs:** model {ph['median_model_c']:+.2f} °C vs energy-balance formula "
                f"{ph['median_formula_c']:+.2f} °C per cell (median, n={ph['n_cells']}). {ph['note']}",
                f"**ചൂട് കുറയ്ക്കുന്ന മേൽക്കൂരകൾ:** ഓരോ സ്ഥലത്തും മാതൃകയുടെ മധ്യകണക്ക് "
                f"{ph['median_model_c']:+.2f} °C; ഊർജസമതുലന സൂത്രത്തിന്റെ കണക്ക് "
                f"{ph['median_formula_c']:+.2f} °C (സ്ഥലങ്ങൾ: {ph['n_cells']}). "
                "ഇരു രീതികളിലും വ്യത്യാസമുണ്ട്; അതുകൊണ്ട് സൂത്രത്തിന്റെ കണക്കും പ്രത്യേകം കാണിക്കുന്നു."))
        validity = pd.DataFrame(M["validity_matrix"])
        if lang == "ml":
            for column in ("intervention", "ps1_category", "method", "cost_note"):
                validity[column] = validity[column].map(t)
            validity = validity.rename(columns={"intervention": "ഇടപെടൽ", "ps1_category": "വിഭാഗം",
                                                "method": "രീതി", "eligible_cells": "യോഗ്യമായ സ്ഥലങ്ങൾ",
                                                "median_dt_c": "മധ്യ താപമാറ്റം (°C)",
                                                "within_support_pct": "സമാനസ്ഥല പിന്തുണ (%)",
                                                "cost_note": "ചെലവിന്റെ അടിസ്ഥാനം"})
        st.dataframe(validity, hide_index=True)
        freshness = pd.DataFrame([
            {"Layer": "Satellite heat (Landsat 8/9)", "Status": "frozen",
             "Detail": f"{M['n_scenes']} scenes, Jan–Apr {config.SCENE_YEARS[0]}–{config.SCENE_YEARS[1]}"},
            {"Layer": "ECOSTRESS afternoon check", "Status": "available" if M.get("ecostress") else "pending",
             "Detail": "Requires AppEEARS scenes" if not M.get("ecostress") else "see metric above"},
            {"Layer": "CPCB station check", "Status": "available" if M.get("cpcb") else "pending",
             "Detail": "Requires station CSVs" if not M.get("cpcb") else "see metric above"},
            {"Layer": "Matched back-test", "Status": "available" if matched else "pending",
             "Detail": "Requires raw back-test export" if not matched else "see metric above"},
            {"Layer": "Weather per scene (ERA5-Land)", "Status": "frozen", "Detail": "at overpass hour"},
            {"Layer": "Live weather (Open-Meteo)", "Status": LIVE.get("status"),
             "Detail": LIVE.get("fetched_at") or LIVE.get("time", "")},
            {"Layer": "Malayalam news", "Status": (NEWS or {}).get("status", "hidden"),
             "Detail": (NEWS or {}).get("fetched_at") or ""},
            {"Layer": "Built", "Status": D["manifest"]["source"], "Detail": D["manifest"]["built_at"]},
            {"Layer": "Ward rollup", "Status": M["area_kind"],
             "Detail": D["manifest"].get("ward_rollup_built_at", "from full pipeline")},
        ])
        if lang == "ml":
            freshness = freshness.rename(columns={column: t(column) for column in freshness})
            freshness[t("Status")] = freshness[t("Status")].map(t)
            freshness[t("Layer")] = freshness[t("Layer")].map(t)
            freshness[t("Detail")] = freshness[t("Detail")].map(t)
        st.dataframe(freshness, hide_index=True)
        st.markdown(local(
            "**Limits:** surface temperature at ~10:30 AM is not the air people feel; weather is "
            "city-scale (~9 km); population is GHSL 2020; we never call results causal; "
            "Heat-Neutral Check is a screening tool, not an approval.",
            "**പരിമിതികൾ:** രാവിലെ ഏകദേശം 10:30-ലെ ഉപരിതല താപനില ശരീരത്തിന് അനുഭവപ്പെടുന്ന "
            "വായുചൂടല്ല. കാലാവസ്ഥാ വിവരം ഏകദേശം 9 കി.മീ. നഗരതലത്തിലാണ്; ജനസംഖ്യ GHSL 2020-ൽ "
            "നിന്നാണ്. ഈ ഫലങ്ങൾ കാരണബന്ധം തെളിയിക്കുന്നതല്ല. ചൂട്-നിഷ്പക്ഷ പരിശോധന അനുമതിയല്ല."))

    st.markdown("### " + t("Ward Heat Card"))
    wc = st.selectbox(t("Ward / area for the card"), names, key="card_ward")
    wid = wards.index[wards["ward"] == wc][0]
    rank = names.index(wc) + 1
    acts = D["plans"]["presets"]["10"]["ward_actions"].get(str(wid), [])
    card = report.ward_card(wards.loc[wid].to_dict(), rank, len(names), acts,
                            D["manifest"]["source"], language=lang)
    st.download_button("⬇ " + t("Download Ward Heat Card (open → print to PDF)"), card,
                       file_name=f"ward_heat_card_{wc.replace(' ', '_')}.html", mime="text/html")
    preview = card.replace("</head>", "<style>html,body{background:#fff;color:#111;}</style></head>", 1)
    st.iframe("data:text/html;base64," + base64.b64encode(preview.encode()).decode(), height=560)

st.divider()
st.caption(local(
    f"{live.ATTRIBUTION} · Satellite: USGS Landsat, ESA Sentinel-2/WorldCover, Google Dynamic "
    "World, JRC GHSL, ECMWF ERA5-Land, NASA ECOSTRESS · Built at HackMe'26 with AI-assisted "
    "coding (disclosed in our presentation).",
    "കാലാവസ്ഥ: Open-Meteo · ഉപഗ്രഹ / ഭൂപട വിവരങ്ങൾ: USGS Landsat, ESA Sentinel-2/WorldCover, "
    "Google Dynamic World, JRC GHSL, ECMWF ERA5-Land. HackMe'26-ൽ AI സഹായത്തോടെ നിർമിച്ചത്; "
    "അത് അവതരണത്തിൽ വെളിപ്പെടുത്തുന്നു."))
