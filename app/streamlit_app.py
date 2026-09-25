"""VISAT — Kochi Heat Action Planner (HackMe'26, PS1). Four screens, one question each."""

import base64
import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from visat import config, exposure, live, news, report

st.set_page_config(page_title="VISAT · Kochi Heat Action Planner", page_icon="🌡️", layout="wide")
st.markdown(
    """<style>
    header[data-testid="stHeader"] {visibility:hidden;} #MainMenu, footer {visibility:hidden;}
    [data-testid="stMainBlockContainer"] {padding-top:1rem;}
    html, body, [class*="css"] {font-size:20px;}
    [data-testid="stMetricValue"] {font-size:44px;}
    .chip {display:inline-block;padding:4px 12px;border-radius:999px;margin-right:8px;font-size:17px;}
    .danger {background:#b8320b;color:#fff;} .warn {background:#e97a2e;color:#111;}
    .ok {background:#1f6f6d;color:#fff;} .demo {background:#e8c35a;color:#111;padding:6px 12px;
    border-radius:6px;font-weight:700;}
    .ledger {font-size:60px;font-weight:800;line-height:1.1;} .hot {color:#ff7a3d;} .cool {color:#46c4be;}
    [data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] li,
    [data-testid="stAppViewContainer"] label {font-size:1.05rem;}
    [data-baseweb="tab"] {font-size:1.05rem;}
    </style>""",
    unsafe_allow_html=True,
)
APP = config.APP
TEAL = [70, 196, 190]
HEAT = [255, 122, 61]
KOCHI_VIEW = pdk.ViewState(latitude=9.99, longitude=76.30, zoom=11.2, pitch=0)


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
left, right = st.columns([3, 2])
left.markdown("## VISAT · Kochi Heat Action Planner")
if D["manifest"]["source"] == "demo":
    right.markdown("<span class='demo'>DEMO DATA — synthetic Kochi, not real measurements</span>",
                   unsafe_allow_html=True)

band_cls = lambda b: "danger" if b in ("Danger", "Extreme danger") else "warn" if b else "ok"
if LIVE.get("status") != "unavailable":
    s1, s2, s3, s4, s5 = st.columns([1, 1, 1, 1, 2])
    s1.metric("Now in Kochi", f"{LIVE['temp_c']} °C")
    s2.metric("Humidity", f"{LIVE['rh']}%")
    s3.metric("Feels like", f"{LIVE['feels_c']} °C")
    s4.metric("Heat index", f"{LIVE['heat_index_c']} °C")
    status = {"live": "live", "cached": "cached", "snapshot": "saved snapshot"}[LIVE["status"]]
    s5.markdown(
        f"<span class='chip {band_cls(LIVE['band'])}'>{LIVE['band']}</span>"
        f"<br>Today's peak: <b>{LIVE['peak_heat_index_c']} °C</b> ({LIVE['peak_band']}) at "
        f"{LIVE['peak_time'][11:16]}<br><small>{config.LABEL_LIVE} · {status} · "
        f"{LIVE.get('fetched_at') or LIVE['time']}</small>", unsafe_allow_html=True)
else:
    st.info("Live weather unavailable right now — the rest of VISAT works offline.")

chips = st.columns([2, 3])
chips[0].markdown("Official alerts: " + " · ".join(
    f"[{name}]({url})" for name, url in config.OFFICIAL_ALERT_LINKS.items()))
NEWS = news_data()
if NEWS:
    with chips[1].popover(NEWS["text"]):
        st.caption(f"From Malayalam news (supporting evidence only; official alerts: IMD / KSDMA) · "
                   f"{NEWS['status']} · fetched {NEWS.get('fetched_at')}")
        for it in NEWS["items"]:
            st.markdown(f"- [{it['title']}]({it['link']}) — *{it['channel']}*, {it['time'][:16]}")

today, plan_tab, project_tab, proof_tab = st.tabs([
    "① Where is heat dangerous today?", "② What should we do with ₹?",
    "③ Will this project make it hotter?", "④ Can we trust it? · Ward Card",
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


def deck(layers, tooltip=None):
    return pdk.Deck(layers=layers, initial_view_state=KOCHI_VIEW, map_provider="carto",
                    map_style="dark", tooltip=tooltip or {"text": "{name}"})


def heat_ledger(result):
    """Animate the net number while preserving the actual saved before/after values."""
    before = float(result["before"]["mean_dt_c"])
    after = float(result["after"]["mean_dt_c"])
    removed = before - after
    scale = max(abs(before), abs(removed), abs(after), 0.01)
    rows = [
        ("Project adds", f"+{before:.2f} °C", before, "#ff7a3d"),
        ("Offsets remove", f"−{removed:.2f} °C", removed, "#46c4be"),
        ("Net change", f"{after:+.2f} °C", abs(after),
         "#ff7a3d" if after > 0.005 else "#46c4be"),
    ]
    markup = """<style>
    body {margin:0;background:#162020;color:#e4ebe9;font-family:Arial,sans-serif;}
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
    st.markdown(f"### {len(wards[wards['people_in_hotspots'] > 0])} {area_word} have people in the top-10% "
                f"heat-stress squares — about **{hot_people:,.0f} people**.")
    st.markdown(f"**Act today** (peak heat index {act['peak_heat_index_c']} °C, *{act['band']}*): "
                f"**{', '.join(act['wards'])}** — " + " · ".join(act["advice"]))
    mcol, pcol = st.columns([2, 1])
    with mcol:
        ev = st.pydeck_chart(deck([heat_layer(), ward_layer()]), on_select="rerun",
                             selection_mode="single-object", key="today_map", height=560)
        st.caption(f"Heat Stress Map · colour = {config.LABEL_SURFACE} vs city median "
                   f"(dark = cooler, yellow = hotter) · outlines = "
                   f"{'wards' if M['area_kind'] == 'wards' else '1 km zones (ward map not loaded)'}")
    picked = None
    try:
        objs = ev.selection["objects"].get("wards", [])
        picked = objs[0]["name"] if objs else None
    except (AttributeError, KeyError, TypeError):
        pass
    names = wards.sort_values("heat_stress", ascending=False)["ward"].tolist()
    with pcol:
        choice = st.selectbox("Ward / area", names, index=names.index(picked) if picked in names else 0)
        w = wards[wards["ward"] == choice].iloc[0]
        st.metric("People", f"{w['people']:,.0f}", f"{w['lst_anom']:+.1f} °C vs city", delta_color="inverse")
        st.markdown("**Why it's hot**")
        for s in report.driver_sentences(w):
            st.markdown(f"- {s}")
        drv = {k.split('::', 1)[1]: v for k, v in w.items() if str(k).startswith("drv::")}
        drv.pop("Weather of the day", None)
        st.bar_chart(pd.Series(drv, name="°C"), horizontal=True, color="#ff7a3d")
        st.caption(f"{int(w['schools'])} schools · {int(w['markets'])} markets · "
                   f"{int(w['construction_sites'])} construction sites")
    if LIVE.get("forecast"):
        fc = pd.DataFrame(LIVE["forecast"]).assign(time=lambda d: pd.to_datetime(d["time"]))
        st.markdown("**Next 72 hours — heat index (city)**")
        st.line_chart(fc.set_index("time")["heat_index_c"], color="#ff7a3d", height=180)
    with st.expander("Atmospheric drivers — how the day's weather changes Kochi's surface heat"):
        at = M["atmospheric"]
        st.dataframe(pd.DataFrame([{"Change": v["label"], "Surface °C": round(v["effect_c"], 2),
                                    "95% CI": f"{v['ci_low']:+.2f} to {v['ci_high']:+.2f}"}
                                   for v in at["effects"].values()]), hide_index=True)
        st.caption(f"From the scene-panel model across n = {at['n_scenes']} satellite days "
                   f"(bootstrap over days — small n, so read the intervals).")

# ------------------------------------------------------------------ ② Plan ₹
with plan_tab:
    budget = st.segmented_control("Budget", [f"₹{b} crore" for b in config.BUDGET_PRESETS_CR],
                                  default="₹10 crore", key="budget") or "₹10 crore"
    b = budget.split("₹")[1].split(" ")[0]
    P = D["plans"]["presets"][b]
    ours = P["ours"]
    best_base = max(P["baselines"], key=lambda s: s["person_deg_cooling"])
    gain = ours["person_deg_cooling"] / max(best_base["person_deg_cooling"], 1e-9)
    st.markdown(f"### {budget} → about **{ours['people_cooled']:,.0f} people** cooler by "
                f"**{abs(ours['mean_dt_cooled']):.2f} °C** on average — **{gain:.1f}×** the best simple "
                f"strategy.")
    conservative = st.toggle("Conservative mode · show back-test error band", key="conservative")
    show_canal_banks = st.toggle("Show OSM canal-bank tree-strip candidates", key="canal_overlay")
    backtest_mae = float(M["backtest"]["mae_c"])
    if conservative:
        lo = ours["mean_dt_cooled"] - backtest_mae
        hi = ours["mean_dt_cooled"] + backtest_mae
        st.info(f"Mean surface ΔT: {ours['mean_dt_cooled']:+.2f} °C, with an empirical "
                f"back-test error band of {lo:+.2f} to {hi:+.2f} °C "
                f"(±{backtest_mae:.2f} °C MAE). This is not a confidence interval or a "
                "guaranteed cooling range.")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("People cooled (≥0.1 °C)", f"{ours['people_cooled']:,.0f}")
    k2.metric("Avg cooling", f"{ours['mean_dt_cooled']:.2f} °C")
    k3.metric("₹ per person", f"{ours['cost_rs'] / max(ours['people_cooled'], 1):,.0f}")
    k4.metric("Sites (100 m)", f"{ours['cells']:,}")
    mc, sc = st.columns([2, 1])
    with mc:
        pal = {cfg["label"]: c for cfg, c in zip(config.INTERVENTIONS.values(), [
            [70, 196, 190], [40, 150, 120], [30, 110, 90], [80, 140, 255], [235, 235, 235],
            [180, 180, 180], [120, 200, 120]])}
        picks = pd.DataFrame(P["picks"], columns=["lat", "lon", "fix", "dt", "cost"])
        picks["color"] = picks["fix"].map(pal)
        cool = pd.DataFrame(P["cooling"], columns=["lat", "lon", "dt"])
        map_layers = [
            heat_layer(0.35),
            pdk.Layer("ScatterplotLayer", id="cooling", data=cool, get_position=["lon", "lat"],
                      get_radius=45, get_fill_color=TEAL + [70]),
            pdk.Layer("ScatterplotLayer", id="picks", data=picks, get_position=["lon", "lat"],
                      get_radius=40, get_fill_color="color", pickable=True),
        ]
        if show_canal_banks and not D["canal_banks"].empty:
            map_layers.append(pdk.Layer(
                "ScatterplotLayer", id="canal_banks", data=D["canal_banks"],
                get_position=["lon", "lat"], get_radius=18,
                get_fill_color=[70, 140, 255, 150], pickable=False))
        st.pydeck_chart(deck(map_layers, tooltip={"text": "{fix}: {dt} °C"}),
                        key="plan_map", height=520)
        st.caption("Coloured dots = where each fix goes (public land only). Teal haze = cells cooled "
                   f"≥0.05 °C, incl. spillover. {config.LABEL_SURFACE}. The plan covers the study area; "
                   "named wards cover Kochi municipality.")
        if show_canal_banks:
            st.caption("Blue dots = 100 m cells near OSM canals, drains or ditches where tree strips "
                       "could be checked on site. These are not verified IURWTS alignments; "
                       "canals receive 0 °C credit in this plan.")
    with sc:
        comp = pd.DataFrame([{"Strategy": s["strategy"], "People cooled": s["people_cooled"],
                              "Person-°C": s["person_deg_cooling"]} for s in [ours, *P["baselines"]]])
        st.markdown("**Same money, three strategies**")
        st.bar_chart(comp.set_index("Strategy")["Person-°C"], color="#46c4be", horizontal=True)
        st.dataframe(pd.DataFrame([{"Fix": k, "Sites": v["cells"], "₹ lakh": round(v["cost_rs"] / 1e5, 1)}
                                   for k, v in ours["mix"].items()]), hide_index=True)
    with st.expander("Budget curve & scenario evaluation (every intervention PS1 lists)"):
        curve = pd.DataFrame(D["plans"]["curve"]).set_index("budget_cr")
        st.line_chart(curve, height=260)
        st.caption("Estimated person-°C (sum of per-site effects); the three presets above use a full "
                   "joint re-prediction.")
        st.dataframe(pd.DataFrame(M["validity_matrix"]), hide_index=True)
        st.caption(config.CANAL_CREDIT_NOTE)
    with st.expander("Site-by-site plan · fix, ward, people, surface °C and cost"):
        locations = cells[["lat", "lon", "ward_id", "pop"]].copy()
        locations[["lat", "lon"]] = locations[["lat", "lon"]].round(5)
        site_table = picks.merge(locations, on=["lat", "lon"], how="left",
                                 validate="many_to_one")
        site_table["Ward / area"] = site_table["ward_id"].map(wards["ward"])
        site_table["Ward / area"] = site_table["Ward / area"].fillna("Outside Kochi wards")
        site_table["Surface ΔT (°C)"] = site_table["dt"].map(lambda x: f"{x:+.2f}")
        if conservative:
            site_table["Back-test band (°C)"] = site_table["dt"].map(
                lambda x: f"{x - backtest_mae:+.2f} to {x + backtest_mae:+.2f}")
        columns = ["Ward / area", "fix", "Surface ΔT (°C)"]
        if conservative:
            columns.append("Back-test band (°C)")
        site_table["People at site"] = site_table["pop"].round(0)
        site_table["₹ lakh"] = (site_table["cost"] / 1e5).round(2)
        st.dataframe(site_table[columns + ["People at site", "₹ lakh", "lat", "lon"]]
                     .rename(columns={"fix": "Fix", "lat": "Latitude", "lon": "Longitude"}),
                     hide_index=True)
        st.caption("Each row is one selected 100 m cell. People at site use GHSL 2020; the total plan "
                   "also counts spillover. Per-site surface ΔT is the saved joint prediction. "
                   "The empirical back-test MAE is not a statistical confidence interval.")

# ------------------------------------------------------------------ ③ Check a Project
with project_tab:
    sites = D["hn"]["sites"]
    site_geo = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": s["site"]},
         "geometry": {"type": "Polygon", "coordinates": [s["polygon"]]}} for s in sites]}
    c1, c2 = st.columns([1, 2])
    with c1:
        site_names = [s["site"] for s in sites]
        site = st.selectbox("Proposed site", site_names, key="site")
        uses = {v["label"]: k for k, v in config.PROJECT_USES.items()}
        use = st.segmented_control("Proposed use", list(uses), default="IT park", key="use") or "IT park"
        R = D["hn"]["results"][f"{site}|{uses[use]}"]
        neutral = st.toggle("Apply available offsets", key="neutral")
        if not neutral:
            st.markdown(f"<div class='ledger hot'>+{R['before']['mean_dt_c']:.1f} °C</div>"
                        f"<b>{R['before']['people']:,} people</b> within ~500 m", unsafe_allow_html=True)
        else:
            components.html(heat_ledger(R), height=160, scrolling=False)
            st.markdown(f"**Offset package: ₹{R['offset_cost_rs'] / 1e5:,.1f} lakh**")
            if R["after"]["mean_dt_c"] > 0.005:
                st.warning("Heat remains after these offsets. This proposal does not pass the "
                           "heat-neutral screen yet.")
            else:
                st.success("This proposal passes the modelled heat-neutral screen.")
            for k, v in R["offset_mix"].items():
                st.markdown(f"- {k}: {v['cells']} sites · ₹{v['cost_rs'] / 1e5:,.1f} lakh")
        st.caption(R["label"])
        st.info(R["policy"])
    with c2:
        heat = pd.DataFrame(R["heat_cells"], columns=["lat", "lon", "dt"])
        layers = [heat_layer(0.3),
                  pdk.Layer("GeoJsonLayer", id="sites", data=site_geo, stroked=True, filled=True,
                            get_fill_color=[255, 255, 255, 40], get_line_color=[255, 255, 255, 220],
                            line_width_min_pixels=2, pickable=True),
                  pdk.Layer("ScatterplotLayer", id="heatspread", data=heat, get_position=["lon", "lat"],
                            get_radius=45, get_fill_color=HEAT + [150])]
        if neutral:
            off = pd.DataFrame(R["offset_cells"], columns=["lat", "lon", "fix"])
            layers.append(pdk.Layer("ScatterplotLayer", id="offsets", data=off,
                                    get_position=["lon", "lat"], get_radius=40,
                                    get_fill_color=TEAL + [230], pickable=True))
        s0 = next(s for s in sites if s["site"] == site)
        view = pdk.ViewState(latitude=s0["center"][0], longitude=s0["center"][1], zoom=13.6)
        st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view, map_provider="carto",
                                 map_style="dark", tooltip={"text": "{name}{fix}"}),
                        key="project_map", height=560)
        st.caption("Orange = where the project adds surface heat. Teal = modelled offset sites "
                   "(trees nearby + cool/green roofs on the project).")
    with st.expander("Compare the modelled heat before and after offsets"):
        st.caption("Same site and map scale in both views. Orange marks added heat; teal marks "
                   "offset locations. The ledger above gives the net surface °C change.")
        before_map, after_map = st.columns(2)
        with before_map:
            st.markdown("**Project only**")
            st.pydeck_chart(pdk.Deck(layers=layers[:3], initial_view_state=view,
                                     map_provider="carto", map_style="dark"),
                            key="project_before_map", height=320)
        with after_map:
            st.markdown("**Project + available offsets**")
            comparison_layers = layers[:3] + [pdk.Layer(
                "ScatterplotLayer", id="comparison_offsets",
                data=pd.DataFrame(R["offset_cells"], columns=["lat", "lon", "fix"]),
                get_position=["lon", "lat"], get_radius=40,
                get_fill_color=TEAL + [230], pickable=True)]
            st.pydeck_chart(pdk.Deck(layers=comparison_layers, initial_view_state=view,
                                     map_provider="carto", map_style="dark"),
                            key="project_after_map", height=320)
    if D["reactions"]:
        rx = D["reactions"].get(f"{site}|{uses[use]}")
        if rx:
            with st.expander("How might residents react? (SIMULATED)"):
                st.warning("Simulated personas built from aggregate statistics — not real people or "
                           "survey data. For preparing public consultation only; never changes any number.")
                df = pd.DataFrame(rx["personas"])
                st.bar_chart(df["stance"].value_counts(), color="#46c4be")
                st.markdown("**Top concerns:** " + "; ".join(rx.get("top_concerns", [])))
                st.dataframe(df[["persona", "stance", "top_concern", "quote_en"]], hide_index=True)

# ------------------------------------------------------------------ ④ Proof & Ward Card
with proof_tab:
    bt = M["backtest"]
    a, b2 = st.columns([3, 2])
    with a:
        st.markdown("### We predicted 2024 from 2017 — here's how close we got")
        if "points" in bt:
            pts = pd.DataFrame(bt["points"], columns=["Predicted Δ °C", "Observed Δ °C"])
            lim = [min(pts.min()), max(pts.max())]
            chart = alt.Chart(pts).mark_circle(size=18, opacity=0.5, color="#ff7a3d").encode(
                x="Predicted Δ °C", y="Observed Δ °C")
            line = alt.Chart(pd.DataFrame({"x": lim, "y": lim})).mark_line(color="#46c4be").encode(
                x="x", y="y")
            st.altair_chart(chart + line, width="stretch")
            st.caption(f"{bt['label']} · {bt['n_changed_cells']:,} cells that really changed · "
                       f"r = {bt['pearson_r']:.2f} · error ±{bt['mae_c']:.2f} °C · teal = perfect match")
        else:
            st.info(bt.get("note", "Back-test unavailable."))
    with b2:
        cv = M["cv"]
        st.markdown("**Honest accuracy (areas the model never saw)**")
        st.dataframe(pd.DataFrame([{"Model": k, "R²": round(v["r2"], 3), "Error (°C)": round(v["rmse"], 2)}
                                   for k, v in cv["spatial_cv"].items()]), hide_index=True)
        st.caption(f"Grouped spatial-block CV (2 km blocks across {cv['n_scenes']} scenes). Random CV "
                   f"(easier, not what we report): R² {cv['random_cv_ours']['r2']:.3f}.")
        if M.get("ecostress"):
            e = M["ecostress"]
            st.metric("Afternoon check (ECOSTRESS 12:00–15:30)",
                      f"{e['top_decile_overlap_pct']:.0f}% of hotspots hold",
                      f"Spearman {e['spearman_cells']:.2f}", delta_color="off")
        if M.get("cpcb"):
            c = M["cpcb"]
            if "mae_heat_index_c" in c:
                st.metric("CPCB stations vs ERA5 heat index", f"±{c['mae_heat_index_c']:.1f} °C",
                          f"{c['n_days']} days", delta_color="off")
        matched = bt.get("matched")
        if matched and "mae_c" in matched:
            st.metric("Matched 2017→2024 check", f"±{matched['mae_c']:.2f} °C",
                      f"{matched['n_changed_matched']:,} changed cells", delta_color="off")
            st.caption("Changed cells vs k nearest unchanged cells on 2017 land features. "
                       "Exploratory comparison; not a causal estimate.")
    with st.expander("Physics check · validity matrix · data freshness · limits"):
        ph = M["physics_check"]
        if ph:
            st.markdown(f"**Cool roofs:** model {ph['median_model_c']:+.2f} °C vs energy-balance formula "
                        f"{ph['median_formula_c']:+.2f} °C per cell (median, n={ph['n_cells']}). "
                        f"{ph['note']}")
        st.dataframe(pd.DataFrame(M["validity_matrix"]), hide_index=True)
        st.dataframe(pd.DataFrame([
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
        ]), hide_index=True)
        st.markdown("**Limits:** surface temperature at ~10:30 AM is not the air people feel; weather is "
                    "city-scale (~9 km); population is GHSL 2020; we never call results causal; "
                    "Heat-Neutral Check is a screening tool, not an approval.")

    st.markdown("### Ward Heat Card")
    wc = st.selectbox("Ward / area for the card", names, key="card_ward")
    wid = wards.index[wards["ward"] == wc][0]
    rank = names.index(wc) + 1
    acts = D["plans"]["presets"]["10"]["ward_actions"].get(str(wid), [])
    card = report.ward_card(wards.loc[wid].to_dict(), rank, len(names), acts, D["manifest"]["source"])
    st.download_button("⬇ Download Ward Heat Card (open → print to PDF)", card,
                       file_name=f"ward_heat_card_{wc.replace(' ', '_')}.html", mime="text/html")
    st.iframe("data:text/html;base64," + base64.b64encode(card.encode()).decode(), height=520)

st.divider()
st.caption(f"{live.ATTRIBUTION} · Satellite: USGS Landsat, ESA Sentinel-2/WorldCover, Google Dynamic "
           "World, JRC GHSL, ECMWF ERA5-Land, NASA ECOSTRESS · Built at HackMe'26 with AI-assisted "
           "coding (disclosed in our presentation).")
