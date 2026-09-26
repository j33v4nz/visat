"""Optional, dependency-free illustrative 3D scenario player."""

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from uhi import i18n
from uhi.simulation import plan_sites, weather_response


def preview_html(payload):
    """Embed data safely in the standalone canvas player."""
    template = Path(__file__).with_name("simulation_preview.html").read_text(encoding="utf-8")
    return template.replace("__SCENARIO__", json.dumps(payload, ensure_ascii=True).replace("<", "\\u003c"))


def render_preview(data, language):
    local = lambda en, ml: ml if language == "ml" else en
    t = lambda value: i18n.tr(value, language)
    remembered = st.session_state.get("_preview_defaults", {})
    st.caption(local("OPTIONAL / INTERACTIVE 3D", "ഐച്ഛികം / സംവേദനാത്മക 3D"))
    names = data["wards"].sort_values("heat_stress", ascending=False).ward.tolist()
    default_ward = remembered.get("simulation_ward", st.session_state.get("today_ward"))
    ward_name = st.selectbox(t("Ward / area"), names,
                             index=names.index(default_ward) if default_ward in names else 0,
                             key="preview_ward")
    entries = {r["intervention"]: r for r in data["metrics"]["validity_matrix"]}
    options = list(entries)
    default_fix = remembered.get("sim_intervention")
    fix = st.selectbox(local("Visualise a cooling measure", "ചൂടുകുറയ്ക്കൽ നടപടി കാണുക"), options,
                       index=options.index(default_fix) if default_fix in options else 0,
                       format_func=t, key="preview_fix")
    changes = {}
    with st.expander(local("Weather settings", "കാലാവസ്ഥാ ക്രമീകരണങ്ങൾ")):
        settings = [
            ("t2m_c", "simulation_temp", "Air temperature change (°C)", "വായുതാപനില മാറ്റം (°C)", -5.0, 8.0, 0.5),
            ("rh", "simulation_rh", "Humidity change (pp)", "ആർദ്രതാ മാറ്റം (pp)", -30.0, 30.0, 5.0),
            ("wind_ms", "simulation_wind", "Wind change (m/s)", "കാറ്റിലെ മാറ്റം (മീ/സെ)", -0.5, 3.0, 0.5),
            ("ssrd_wm2", "simulation_sun", "Sunlight change (W/m²)", "സൂര്യപ്രകാശ മാറ്റം (W/m²)", -200.0, 200.0, 25.0),
        ]
        for field, old_key, en, ml, low, high, step in settings:
            changes[field] = st.slider(local(en, ml), low, high,
                                       float(remembered.get(old_key, 0)), step,
                                       key=f"preview_{field}")
    ward = data["wards"].loc[data["wards"].ward == ward_name].iloc[0]
    sites = plan_sites(data["plans"]["presets"]["50"], data["cells"])
    selected = sites[(sites.ward_id == ward.name) & (sites.fix == fix)]
    row = entries[fix]
    treatment = float(selected.dt.mean()) if len(selected) else float(row["median_dt_c"])
    weather = float(weather_response(data["metrics"]["atmospheric"]["effects"], changes).effect_c.sum())
    if st.button(local("Start simulation", "പരീക്ഷണം ആരംഭിക്കുക"), type="primary",
                 width="stretch", key="start_3d_simulation"):
        st.session_state["_preview_started"] = True
        st.session_state["_preview_run"] = st.session_state.get("_preview_run", 0) + 1
    if not st.session_state.get("_preview_started"):
        st.info(local("Choose a ward and measure, then start. Drag to rotate the scene; compare before and after.",
                      "വാർഡും നടപടിയും തിരഞ്ഞെടുത്ത് ആരംഭിക്കുക. ദൃശ്യം വലിച്ച് തിരിക്കാം; മുൻപും ശേഷവും താരതമ്യം ചെയ്യാം."))
        return {}

    payload = {
        "ward": ward_name, "fix": fix, "fixLabel": t(fix), "treatment": treatment,
        "weather": weather, "anomaly": float(ward.lst_anom),
        "run": st.session_state.get("_preview_run", 1), "language": language,
        "labels": {
            "before": local("Before", "മുൻപ്"), "after": local("After", "ശേഷം"),
            "replay": local("Replay", "വീണ്ടും"), "rotate": local("Drag to rotate", "വലിച്ച് തിരിക്കുക"),
            "ready": local("SCENARIO READY", "ദൃശ്യം തയ്യാർ"),
            "playing": local("APPLYING CHANGES", "മാറ്റങ്ങൾ കാണിക്കുന്നു"),
            "schematic": local("ILLUSTRATIVE NEIGHBOURHOOD", "സാങ്കൽപ്പിക അയൽപ്രദേശം"),
            "progress": local("Before / after transition", "മുൻപ് / ശേഷം താരതമ്യം"),
            "cool": local("Cooler", "തണുപ്പ്"), "warm": local("Warmer", "ചൂട്"),
        },
    }
    components.html(preview_html(payload), height=445, scrolling=False)
    a, b = st.columns(2)
    a.metric(local("Treatment effect", "നടപടിയുടെ ഫലം"), f"{treatment:+.2f} °C")
    b.metric(local("Weather response", "കാലാവസ്ഥയുടെ ഫലം"), f"{weather:+.2f} °C")
    st.caption(local(
        f"Treatment: saved mean at {len(selected)} selected sites in this ward (₹50 crore plan)." if len(selected)
        else "Treatment: study-wide median; no selected sites for this measure in this ward's saved ₹50 crore plan.",
        f"നടപടി: ഈ വാർഡിലെ {len(selected)} സ്ഥലങ്ങളുടെ സംരക്ഷിച്ച ശരാശരി (₹50 കോടി പദ്ധതി)." if len(selected)
        else "നടപടി: പഠനപ്രദേശത്തിന്റെ മധ്യക ഫലം; ഈ വാർഡിലെ സംരക്ഷിച്ച പദ്ധതിയിൽ ഈ നടപടിക്ക് സ്ഥലങ്ങളില്ല."))
    if row.get("within_support_pct") is not None and row["within_support_pct"] < 50:
        st.warning(local("Low data support for this measure. Its cooling estimate is indicative only.",
                         "ഈ നടപടിക്ക് ഡാറ്റാ പിന്തുണ കുറവാണ്. ചൂടുകുറവിന്റെ കണക്ക് സൂചന മാത്രമാണ്."))
    st.caption(local(
        "Schematic buildings and planting, not surveyed geometry. Colours illustrate relative heat, not a calibrated map. Weather and treatment estimates are separate; animation shows a scenario transition, not elapsed years. Selections update the preview automatically after starting.",
        "കെട്ടിടങ്ങളും നടീലും സാങ്കൽപ്പികമാണ്; സർവേ ചെയ്ത രൂപരേഖയല്ല. നിറങ്ങൾ ആപേക്ഷിക ചൂടിന്റെ സൂചനയാണ്. കാലാവസ്ഥയുടെയും നടപടിയുടെയും കണക്കുകൾ വേറിട്ടതാണ്. ദൃശ്യത്തിലെ മാറ്റം വർഷങ്ങളുടെ പുരോഗതിയല്ല. ആരംഭിച്ച ശേഷം തിരഞ്ഞെടുപ്പുകൾ ദൃശ്യം സ്വയം പുതുക്കും."))
    cells = data["cells"].loc[data["cells"].ward_id == ward.name]
    overlay = {"points": selected, "label": local("3D preview / selected ward", "3D ദൃശ്യം / തിരഞ്ഞെടുത്ത വാർഡ്")}
    if len(cells):
        overlay["center"] = [float(cells.lat.mean()), float(cells.lon.mean())]
    return overlay
