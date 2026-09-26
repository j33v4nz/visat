"""The simulation workspace: saved joint runs, sensitivity previews and evidence."""

from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from uhi import config, i18n
from uhi.simulation import plan_sites, scenario_report, validation_inventory, weather_response
from uhi.simulation_preview import render_preview


def render_simulation(data, language):
    local = lambda en, ml: ml if language == "ml" else en
    t = lambda value: i18n.tr(value, language)
    m = data["metrics"]
    overlay = {}
    remembered = st.session_state.setdefault("_preview_defaults", {})
    for key in ("sim_intervention", "simulation_ward", "simulation_temp", "simulation_rh", "simulation_wind", "simulation_sun"):
        if key in st.session_state:
            remembered[key] = st.session_state[key]

    def html(text):
        st.markdown(text, unsafe_allow_html=True)

    def label(en, ml):
        html(f"<div class='sim-section-label'>{escape(local(en, ml))}</div>")

    def result(value, caption, detail="", warm=False):
        html(f"<div class='sim-result {'warming' if warm else ''}'>"
             f"<span>{escape(caption)}</span><strong>{escape(value)}</strong>"
             f"<p>{escape(detail)}</p></div>")

    def facts(items):
        html("<dl class='sim-facts'>" + "".join(
            f"<div><dt>{escape(str(k))}</dt><dd>{escape(str(v))}</dd></div>" for k, v in items) + "</dl>")

    def compare(rows, selected=None):
        maximum = max([abs(value) for _, value, _ in rows] + [0.001])
        html("<div class='sim-comparison'>" + "".join(
            f"<div class='sim-compare-row {'selected' if name == selected else ''}'>"
            f"<div><span>{escape(name)}</span><b>{escape(display)}</b></div>"
            f"<div class='sim-track'><i style='width:{100 * abs(value) / maximum:.2f}%;'></i></div></div>"
            for name, value, display in rows) + "</div>")

    def download(title, values, notes, tables=None):
        notes = [*notes, local("Morning surface temperature (~10:30 AM, Jan–Apr); not felt air temperature or a causal guarantee.",
                              "രാവിലെ 10:30-ലെ ഉപരിതല താപനില (ജനുവരി–ഏപ്രിൽ). അനുഭവപ്പെടുന്ന വായുചൂടോ കാരണഫല ഉറപ്പോ അല്ല.")]
        st.download_button(local("Download scenario report", "സാഹചര്യ റിപ്പോർട്ട് ഡൗൺലോഡ് ചെയ്യുക"),
                           scenario_report(title, values, notes, data["manifest"], language, tables),
                           file_name=f"uhi_{section}_report_{language}.html", mime="text/html", width="stretch")
        st.caption(local("Printable HTML report · includes your selection, results and limitations.",
                         "അച്ചടിക്കാവുന്ന HTML റിപ്പോർട്ട് · തിരഞ്ഞെടുപ്പും ഫലങ്ങളും പരിമിതികളും ഉൾപ്പെടുന്നു."))

    with st.container(key="simulation_workspace"):
        html(f"<div class='eyebrow'>{local('SIMULATION / KOCHI', 'സാഹചര്യ പരീക്ഷണം / കൊച്ചി')}</div>"
             f"<h2 class='sim-heading'>{local('City scenario lab', 'നഗര സാഹചര്യ പരീക്ഷണം')}</h2>"
             f"<p class='sim-intro'>{local('Compare cooling measures, budgets and development impacts.', 'ചൂട് കുറയ്ക്കാനുള്ള നടപടികളും ബജറ്റുകളും വികസന ഫലങ്ങളും താരതമ്യം ചെയ്യുക.')}</p>")
        html(f"<div class='sim-index'><span><b>{len(m['validity_matrix']):02}</b> {local('interventions', 'നടപടികൾ')}</span>"
             f"<span><b>{len(data['plans']['presets']):02}</b> {local('budgets', 'ബജറ്റുകൾ')}</span>"
             f"<span><b>{len(data['hn']['results']):02}</b> {local('project runs', 'പദ്ധതി പരീക്ഷണങ്ങൾ')}</span></div>")
        sections = {"interventions": local("Interventions", "നടപടികൾ"),
                    "budgets": local("Budgets", "ബജറ്റുകൾ"),
                    "projects": local("Development", "വികസനം"),
                    "weather": local("Ward lab", "വാർഡ് പരീക്ഷണം"),
                    "validation": local("Evidence", "തെളിവുകൾ"),
                    "preview": local("3D Preview", "3D ദൃശ്യം")}
        section = st.radio(local("Explore simulations", "പരീക്ഷണം തിരഞ്ഞെടുക്കുക"), list(sections),
                           format_func=sections.get, horizontal=True, key="sim_section", label_visibility="collapsed")
        st.caption(local("Saved joint runs + interactive sensitivity previews", "സംരക്ഷിച്ച സംയുക്ത ഫലങ്ങളും തത്സമയ സെൻസിറ്റിവിറ്റി കണക്കുകളും")
                   + f" · {m['n_scenes']} " + local("satellite scenes", "ഉപഗ്രഹ നിരീക്ഷണങ്ങൾ"))

        if section == "interventions":
            entries = m["validity_matrix"]
            by_name = {row["intervention"]: row for row in entries}
            selected = st.selectbox(local("Cooling intervention", "ചൂട് കുറയ്ക്കാനുള്ള നടപടി"), list(by_name),
                                    format_func=t, key="sim_intervention")
            row = by_name[selected]
            spec = next((s for s in config.INTERVENTIONS.values() if s["label"] == selected), None)
            method = spec["method"] if spec else "overlay"
            method_label = {"analog": local("ANALOG MODEL", "സമാനസ്ഥല മാതൃക"),
                            "formula": local("ENERGY BALANCE", "ഊർജസമതുലനം"),
                            "overlay": local("ZERO COOLING CREDIT", "ചൂടുകുറവ് കണക്കാക്കുന്നില്ല")}[method]
            html(f"<span class='sim-method'>{escape(method_label)}</span>")
            result(f"{row['median_dt_c']:+.2f} °C", local("Median effect per eligible cell", "യോഗ്യമായ സെല്ലുകളിലെ മധ്യക ഫലം"),
                   local("Saved study-wide result · 100 m cells", "പഠനപ്രദേശത്തെ സംരക്ഷിച്ച ഫലം · 100 മീ. സെല്ലുകൾ"))
            support = row.get("within_support_pct")
            facts([(local("Eligible cells", "യോഗ്യമായ സെല്ലുകൾ"), f"{row['eligible_cells']:,}" if row['eligible_cells'] is not None else local("Not applicable", "ബാധകമല്ല")),
                   (local("Category", "വിഭാഗം"), t(row["ps1_category"])),
                   (local("Within observed support", "നിരീക്ഷിച്ച പരിധിക്കുള്ളിൽ"), f"{support:.1f}%" if method == "analog" and support is not None else local("Not applicable", "ബാധകമല്ല"))])
            if method == "analog":
                st.caption(local("Matched to 20 similar Kochi cells. Changes are clipped to the observed 1st–99th percentile and constrained toward cooling.",
                                 "കൊച്ചിയിലെ 20 സമാനസ്ഥലങ്ങളുമായി താരതമ്യം ചെയ്യുന്നു. മാറ്റങ്ങൾ നിരീക്ഷിച്ച 1–99 ശതമാനക പരിധിയിലും ചൂട് കുറയുന്ന ദിശയിലുമാണ്."))
                if support is not None and support < 50:
                    st.warning(local(f"Low support: only {support:.1f}% remains within the observed range. This clipped extrapolation is indicative only.",
                                     f"കുറഞ്ഞ ഡാറ്റാ പിന്തുണ: {support:.1f}% മാത്രമാണ് നിരീക്ഷിച്ച പരിധിക്കുള്ളിൽ. ഈ കണക്ക് സൂചന മാത്രമാണ്."))
            elif method == "formula":
                formula = "ΔT = −8 K × treated roof share" if selected == "Green roofs" else "ΔT ≈ −Δα × S / h × treated area share"
                html(f"<div class='sim-equation'>{escape(formula)}</div>")
                st.caption(local("S = 750 W/m² · h = 25 W/m²K. Formula effects receive no neighbourhood spillover credit.",
                                 "S = 750 W/m² · h = 25 W/m²K. ഈ ഫലത്തിൽ സമീപപ്രദേശങ്ങളിലെ ചൂടുകുറവ് ഉൾപ്പെടുത്തിയിട്ടില്ല."))
            else:
                st.info(local("Canals are narrower than the 100 m grid. IURWTS receives 0 °C credit; canal-bank tree strips are a separate intervention.",
                              "കനാലുകൾ 100 മീ. ഗ്രിഡിനേക്കാൾ ഇടുങ്ങിയതാണ്. IURWTS-ന് 0 °C നേട്ടം; കനാൽക്കര വൃക്ഷനിരകൾ വേറൊരു നടപടിയാണ്."))
            if spec:
                st.caption(t(spec["cost_note"]))
            label("COMPARE ALL INTERVENTIONS / °C", "എല്ലാ നടപടികളുടെയും താരതമ്യം / °C")
            compare([(t(r["intervention"]), r["median_dt_c"], f"{r['median_dt_c']:+.2f} °C") for r in entries], t(selected))
            sites = plan_sites(data["plans"]["presets"]["50"], data["cells"])
            picks = sites[sites.fix == selected].copy()
            if len(picks):
                overlay = {"points": picks, "label": local("Selected sites in the saved ₹50 crore plan", "സംരക്ഷിച്ച ₹50 കോടി പദ്ധതിയിലെ സ്ഥലങ്ങൾ")}
                st.caption(local(f"Map: {len(picks)} selected sites from the ₹50 crore plan. These are not all eligible cells.",
                                 f"ഭൂപടം: ₹50 കോടി പദ്ധതിയിലെ {len(picks)} സ്ഥലങ്ങൾ. യോഗ്യമായ എല്ലാ സെല്ലുകളും ഇതിലില്ല."))
            else:
                st.caption(local("No selected sites for this intervention in the saved ₹50 crore plan. The city heat surface remains visible.",
                                 "സംരക്ഷിച്ച ₹50 കോടി പദ്ധതിയിൽ ഈ നടപടിക്ക് സ്ഥലങ്ങളില്ല. നഗരത്തിലെ ചൂട് ഭൂപടമാണ് കാണിക്കുന്നത്."))
            if method == "overlay" and not data["canals"].empty:
                show = st.toggle(local("Show unverified OSM canal-bank candidates", "പരിശോധിക്കാത്ത OSM കനാൽക്കര സ്ഥലങ്ങൾ കാണിക്കുക"), key="sim_canals")
                if show:
                    overlay = {"canals": True, "label": local("OSM candidates · not official IURWTS alignments", "OSM സാധ്യതകൾ · ഔദ്യോഗിക IURWTS പാതകളല്ല")}
            download(t(selected), {local("Median surface change", "മധ്യക ഉപരിതല മാറ്റം"): f"{row['median_dt_c']:+.2f} °C",
                                    local("Eligible cells", "യോഗ്യമായ സെല്ലുകൾ"): row["eligible_cells"],
                                    local("Method", "രീതി"): method_label,
                                    local("Observed support", "നിരീക്ഷിച്ച പിന്തുണ"): f"{support}%" if method == "analog" else local("Not applicable", "ബാധകമല്ല")},
                     [local("Study-wide saved summary, not a ward-specific rerun. Mangrove and pond results have low data support. Formula methods have no spillover credit. IURWTS cooling credit is zero.",
                            "പഠനപ്രദേശത്തെ സംരക്ഷിച്ച സംഗ്രഹമാണ്; പുതിയ വാർഡ് പ്രവചനമല്ല. കണ്ടൽക്കാടിനും കുളങ്ങൾക്കും ഡാറ്റാ പിന്തുണ കുറവാണ്. സൂത്രാധിഷ്ഠിത ഫലത്തിൽ സമീപപ്രദേശ നേട്ടമില്ല. IURWTS നേട്ടം പൂജ്യമാണ്.")])

        elif section == "budgets":
            amount = st.segmented_control(t("Budget"), [1, 10, 50], default=10,
                                          format_func=lambda x: f"₹{x} {t('crore')}", key="sim_budget")
            amount = amount or 10
            preset = data["plans"]["presets"][str(amount)]
            ours = preset["ours"]
            result(f"{ours['person_deg_cooling']:,.0f}", local("Person·°C of cooling", "ആളുകളുടെ എണ്ണം കണക്കിലെടുത്ത ചൂടുകുറവ് (person·°C)"),
                   local("Optimised for total cooling benefit per rupee", "ഓരോ രൂപയ്ക്കും പരമാവധി ചൂടുകുറവ് ലക്ഷ്യമാക്കുന്നു"))
            facts([(t("People cooled (≥0.1 °C)"), f"{ours['people_cooled']:,.0f}"),
                   (t("Avg cooling"), f"{ours['mean_dt_cooled']:+.2f} °C"),
                   (t("Sites (100 m)"), f"{ours['cells']:,}"),
                   (local("Actual spend", "യഥാർത്ഥ ചെലവ്"), f"₹{ours['cost_rs']/1e7:.2f} {t('crore')}")])
            label("SAME BUDGET / THREE STRATEGIES", "ഒരേ ബജറ്റ് / മൂന്ന് രീതികൾ")
            strategies = [ours, *preset["baselines"]]
            compare([(t(s["strategy"]), s["person_deg_cooling"], f"{s['person_deg_cooling']:,.0f} person·°C") for s in strategies], t(ours["strategy"]))
            table = pd.DataFrame([{t("Strategy"): t(s["strategy"]), t("People"): round(s["people_cooled"]),
                                   t("Avg cooling"): round(s["mean_dt_cooled"], 2)} for s in strategies])
            st.dataframe(table, hide_index=True, width="stretch")
            if any(s["people_cooled"] > ours["people_cooled"] for s in preset["baselines"]):
                st.info(local("Trees everywhere reaches more people at this budget. UHI delivers more total person·°C cooling; headcount is a different objective.",
                              "ഈ ബജറ്റിൽ എല്ലായിടത്തും മരങ്ങൾ എന്ന രീതി കൂടുതൽ ആളുകളിലെത്തുന്നു. UHI-യുടെ ആകെ person·°C നേട്ടം കൂടുതലാണ്; ആളുകളുടെ എണ്ണം വേറൊരു ലക്ഷ്യമാണ്."))
            with st.expander(local("Intervention mix & budget curve", "നടപടികളും ബജറ്റ് വക്രരേഖയും")):
                st.dataframe(pd.DataFrame([{t("Fix"): t(k), t("Sites"): v["cells"], t("₹ lakh"): round(v["cost_rs"]/1e5, 2)} for k,v in ours["mix"].items()]), hide_index=True)
                curve = pd.DataFrame(data["plans"]["curve"]).set_index("budget_cr")
                curve.columns = [t(c) for c in curve.columns]
                st.line_chart(curve, height=190)
                st.caption(local("Curve: sum of individual site effects. The three presets use joint evaluation, including recomputed neighbourhood effects.",
                                 "വക്രരേഖ ഓരോ സ്ഥലത്തിന്റെയും ഫലങ്ങളുടെ ആകെത്തുകയാണ്. മൂന്ന് ബജറ്റ് ഫലങ്ങൾ സമീപപ്രദേശ മാറ്റങ്ങൾ ഉൾപ്പെട്ട സംയുക്ത വിലയിരുത്തലാണ്."))
            points = plan_sites(preset, data["cells"])
            with st.expander(local("Selected locations", "തിരഞ്ഞെടുത്ത സ്ഥലങ്ങൾ")):
                display = points[["fix", "ward_id", "dt", "cost", "lat", "lon"]].copy()
                display["ward_id"] = display.ward_id.map(data["wards"].ward).fillna(t("Outside Kochi wards"))
                display["fix"] = display.fix.map(t)
                display.columns = [t("Fix"), t("Ward / area"), t("Surface ΔT (°C)"), local("Cost (₹)", "ചെലവ് (₹)"),
                                   local("Latitude", "അക്ഷാംശം"), local("Longitude", "രേഖാംശം")]
                st.dataframe(display, hide_index=True)
            overlay = {"points": points, "cooling": preset["cooling"], "label": local(f"₹{amount} crore · saved joint plan", f"₹{amount} കോടി · സംരക്ഷിച്ച സംയുക്ത പദ്ധതി")}
            download(local("Budget simulation", "ബജറ്റ് പരീക്ഷണം"),
                     {t("Budget"): f"₹{amount} {t('crore')}", t("People"): f"{ours['people_cooled']:,.0f}",
                      local("Person·°C cooling", "person·°C നേട്ടം"): f"{ours['person_deg_cooling']:,.0f}",
                      local("Actual spending", "യഥാർത്ഥ ചെലവ്"):f"₹{ours['cost_rs']:,.0f}",
                      t("Avg cooling"): f"{ours['mean_dt_cooled']:+.2f} °C", t("Sites"): ours["cells"],
                      **{t(s["strategy"]): f"{s['person_deg_cooling']:,.0f} person·°C; {s['people_cooled']:,.0f} " + t("People") for s in preset["baselines"]}},
                     [local("Saved joint plan evaluation. One fix per cell, public-land eligibility and vulnerability weighting. Optimisation targets person·°C, not headcount.",
                            "സംരക്ഷിച്ച സംയുക്ത വിലയിരുത്തൽ. ഒരു സെല്ലിൽ ഒരു നടപടി, പൊതുഭൂമി യോഗ്യത, അപകടസാധ്യതാ വെയിറ്റുകൾ. ലക്ഷ്യം person·°C നേട്ടമാണ്.")],
                     tables={local("Selected locations", "തിരഞ്ഞെടുത്ത സ്ഥലങ്ങൾ"):display})

        elif section == "projects":
            a,b = st.columns(2)
            site = a.selectbox(t("Proposed site"), [s["site"] for s in data["hn"]["sites"]], format_func=t, key="sim_site")
            use = b.selectbox(t("Proposed use"), list(config.PROJECT_USES), format_func=lambda k:t(config.PROJECT_USES[k]["label"]), key="sim_use")
            r = data["hn"]["results"][f"{site}|{use}"]
            apply = st.toggle(t("Apply available offsets"), value=True, key="sim_offsets")
            value = r["after"]["mean_dt_c"] if apply else r["before"]["mean_dt_c"]
            result(f"{value:+.2f} °C", local("People-weighted surface change", "ജനസംഖ്യ കണക്കിലെടുത്ത ഉപരിതല മാറ്റം"),
                   local("Within about 500 m of the proposed development", "നിർദിഷ്ട പദ്ധതിയുടെ ഏകദേശം 500 മീ. പരിധിയിൽ"), warm=value > .005)
            if apply:
                if r["after"]["heat_neutral"]:
                    st.success(local("Passes the saved heat-neutral screen", "സംരക്ഷിച്ച ചൂട്-നിഷ്പക്ഷ പരിശോധനയിൽ വിജയിച്ചു"))
                else:
                    st.warning(local("Heat remains after all available offsets", "ലഭ്യമായ എല്ലാ നടപടികൾക്കു ശേഷവും ചൂട് ശേഷിക്കുന്നു"))
            facts([(t("People"), f"{r['before']['people']:,}"),
                   (local("Offset cost", "ചൂടുകുറയ്ക്കൽ ചെലവ്"), f"₹{r['offset_cost_rs']/1e5:,.1f} {t('lakh')}")])
            label("BEFORE / AFTER OFFSETS", "നടപടികൾക്ക് മുൻപും ശേഷവും")
            chart = pd.DataFrame({"stage":[t("Project only"),t("Project + available offsets")],
                                  "change":[r["before"]["mean_dt_c"],r["after"]["mean_dt_c"]], "order":[0,1]})
            bars = alt.Chart(chart).mark_bar(size=23).encode(
                x=alt.X("change:Q", title="Δ °C", scale=alt.Scale(domain=[min(-.05,chart.change.min()),max(.1,chart.change.max())])),
                y=alt.Y("stage:N", sort=chart.stage.tolist(), title=None),
                color=alt.Color("order:N",scale=alt.Scale(domain=[0,1],range=["#ff7627","#70d9b3"]),legend=None),
                tooltip=["stage",alt.Tooltip("change:Q",format="+.2f")])
            st.altair_chart(bars, width="stretch")
            with st.expander(local("Offset measures & all 24 runs", "ചൂടുകുറയ്ക്കൽ നടപടികളും 24 പരീക്ഷണങ്ങളും")):
                st.dataframe(pd.DataFrame([{t("Fix"):t(k),t("Sites"):v["cells"],t("₹ lakh"):round(v["cost_rs"]/1e5,2)} for k,v in r["offset_mix"].items()]), hide_index=True)
                st.dataframe(pd.DataFrame([{t("Proposed site"):t(v["site"]),t("Proposed use"):t(v["use"]),
                                            local("Before °C", "മുൻപ് °C"):v["before"]["mean_dt_c"],local("After °C", "ശേഷം °C"):v["after"]["mean_dt_c"],
                                            t("₹ lakh"):round(v["offset_cost_rs"]/1e5,1),
                                            local("Heat-neutral screen", "ചൂട്-നിഷ്പക്ഷ പരിശോധന"):local("Pass" if v["after"]["heat_neutral"] else "Heat remains", "വിജയിച്ചു" if v["after"]["heat_neutral"] else "ചൂട് ശേഷിക്കുന്നു")}
                                           for v in data["hn"]["results"].values()]), hide_index=True)
            reaction = data["reactions"].get(f"{site}|{use}")
            with st.expander(t("How might residents react? (SIMULATED)")):
                if reaction:
                    st.caption(local("Simulated personas, not a resident survey. No effect on temperature or cost estimates.", "സാങ്കൽപ്പിക പ്രതികരണങ്ങൾ; സർവേയല്ല. താപനിലയെയും ചെലവിനെയും മാറ്റില്ല."))
                    st.dataframe(pd.DataFrame(reaction["personas"]), hide_index=True)
                else:
                    st.caption(local("No saved resident-reaction preview for this selection.", "ഈ തിരഞ്ഞെടുപ്പിന് സംരക്ഷിച്ച ജനപ്രതികരണ പരീക്ഷണമില്ല."))
            chosen = next(s for s in data["hn"]["sites"] if s["site"] == site)
            overlay = {"heat":r["heat_cells"],"offsets":r["offset_cells"] if apply else [],
                       "center":chosen["center"],"boundary":chosen["polygon"],
                       "label":local("Orange: added heat · mint: offset locations", "ഓറഞ്ച്: കൂടിയ ചൂട് · പച്ച: ചൂടുകുറയ്ക്കൽ സ്ഥലങ്ങൾ")}
            download(local("Development simulation", "വികസന പരീക്ഷണം"),
                     {t("Proposed site"):t(site),t("Proposed use"):t(config.PROJECT_USES[use]["label"]),
                      t("Project only"):f"{r['before']['mean_dt_c']:+.2f} °C",t("Apply available offsets"):str(apply),
                      local("Selected result", "തിരഞ്ഞെടുത്ത ഫലം"):f"{value:+.2f} °C",t("People"):r["before"]["people"],
                      local("Available offset cost", "ലഭ്യമായ നടപടികളുടെ ചെലവ്"):f"₹{r['offset_cost_rs']:,.0f}"},
                     [local("Screening tool and policy proposal, not planning approval. Saved development and offset simulations cover the local 500 m population. Available measures may not fully offset warming.",
                            "ഇത് പ്രാഥമിക പരിശോധനയും നയ നിർദ്ദേശവുമാണ്; പദ്ധതിക്കുള്ള അനുമതിയല്ല. പ്രാദേശിക 500 മീ. ജനസംഖ്യയെ അടിസ്ഥാനമാക്കിയതാണ് ഫലങ്ങൾ. ലഭ്യമായ നടപടികൾ മുഴുവൻ ചൂടും കുറയ്ക്കണമെന്നില്ല.")])

        elif section == "weather":
            names = data["wards"].sort_values("heat_stress",ascending=False).ward.tolist()
            choice = st.selectbox(t("Ward / area"), names, key="simulation_ward")
            st.session_state["today_ward"] = choice
            ward = data["wards"].loc[data["wards"].ward == choice].iloc[0]
            baseline = m["typical_atmosphere"]
            st.caption(local(f"Reference air: {baseline['t2m_c']:.1f} °C · humidity {baseline['rh']:.0f}% · wind {baseline['wind_ms']:.1f} m/s · sun {baseline['ssrd_wm2']:.0f} W/m²",
                             f"അടിസ്ഥാന വായു: {baseline['t2m_c']:.1f} °C · ആർദ്രത {baseline['rh']:.0f}% · കാറ്റ് {baseline['wind_ms']:.1f} മീ/സെ · സൂര്യപ്രകാശം {baseline['ssrd_wm2']:.0f} W/m²"))
            a,b=st.columns(2)
            with a:
                dt=st.slider(local("Air temperature change (°C)", "വായുതാപനില മാറ്റം (°C)"),-5.0,8.0,0.0,.5,key="simulation_temp")
                wind=st.slider(local("Wind change (m/s)", "കാറ്റിലെ മാറ്റം (മീ/സെ)"),-.5,3.0,0.0,.5,key="simulation_wind")
            with b:
                rh=st.slider(local("Humidity change (percentage points)", "ആർദ്രതാ മാറ്റം (ശതമാന പോയിന്റ്)"),-30,30,0,5,key="simulation_rh")
                sun=st.slider(local("Sunlight change (W/m²)", "സൂര്യപ്രകാശ മാറ്റം (W/m²)"),-200,200,0,25,key="simulation_sun")
            terms=weather_response(m["atmospheric"]["effects"],{"t2m_c":dt,"rh":rh,"wind_ms":wind,"ssrd_wm2":sun})
            weather_dt=terms.effect_c.sum()
            result(f"{weather_dt:+.2f} °C",local("Estimated weather-driven surface change", "കാലാവസ്ഥ മൂലമുള്ള ഉപരിതല മാറ്റത്തിന്റെ കണക്ക്"),
                   local("Immediate linear sensitivity preview", "ഉടൻ പുതുക്കുന്ന രേഖീയ സെൻസിറ്റിവിറ്റി കണക്ക്"),warm=weather_dt>0)
            facts([(local("Saved ward anomaly", "സംരക്ഷിച്ച വാർഡ് വ്യത്യാസം"),f"{ward.lst_anom:+.2f} °C"),
                   (local("Scenario vs fixed historical median", "സ്ഥിര ചരിത്ര മധ്യകവുമായുള്ള വ്യത്യാസം"),f"{ward.lst_anom+weather_dt:+.2f} °C")])
            label("WEATHER CONTRIBUTIONS", "കാലാവസ്ഥാ ഘടകങ്ങളുടെ ഫലം")
            change_labels={"t2m_c":local(f"Air {dt:+.1f} °C", f"വായു {dt:+.1f} °C"),
                           "rh":local(f"Humidity {rh:+d} pp", f"ആർദ്രത {rh:+d} pp"),
                           "wind_ms":local(f"Wind {wind:+.1f} m/s", f"കാറ്റ് {wind:+.1f} മീ/സെ"),
                           "ssrd_wm2":local(f"Sunlight {sun:+d} W/m²", f"സൂര്യപ്രകാശം {sun:+d} W/m²")}
            compare([(change_labels[r.variable],r.effect_c,f"{r.effect_c:+.2f} °C") for r in terms.itertuples()])
            st.caption(local(f"Summed sensitivity endpoints: {terms.low.sum():+.2f} to {terms.high.sum():+.2f} °C. This is not a joint confidence interval or a forecast. City-wide sensitivities are applied uniformly; humidity reducing surface temperature does not imply improved human comfort.",
                             f"സെൻസിറ്റിവിറ്റി പരിധികളുടെ ആകെത്തുക: {terms.low.sum():+.2f} മുതൽ {terms.high.sum():+.2f} °C. ഇത് സംയുക്ത വിശ്വാസപരിധിയോ പ്രവചനമോ അല്ല. നഗരതല സെൻസിറ്റിവിറ്റി ഒരേപോലെ പ്രയോഗിക്കുന്നു; ഉപരിതല ചൂട് കുറയുന്നത് മനുഷ്യർക്ക് ആശ്വാസം ലഭിക്കുന്നു എന്നല്ല."))
            points=plan_sites(data["plans"]["presets"]["10"],data["cells"])
            points=points[points.ward_id==ward.name]
            fixes=[None,*sorted(points.fix.unique())]
            fix=st.selectbox(local("Compare a saved cooling measure", "സംരക്ഷിച്ച ചൂടുകുറയ്ക്കൽ നടപടി താരതമ്യം ചെയ്യുക"),list(range(len(fixes))),
                             format_func=lambda i:local("No intervention", "ഇടപെടലില്ല") if i is None or not 0 < i < len(fixes) else t(fixes[i]), key="simulation_fix")
            fix=fix or 0
            selected=points[points.fix==fixes[fix]] if fix<len(fixes) and fix else points.iloc[:0]
            if len(selected):
                result(f"{selected.dt.mean():+.2f} °C",local("Saved effect at the selected treatment sites", "തിരഞ്ഞെടുത്ത നടപടി സ്ഥലങ്ങളിലെ സംരക്ഷിച്ച ഫലം"),
                       local(f"{len(selected)} sites · ₹{selected.cost.sum()/1e5:.1f} lakh · from the ₹10 crore joint plan", f"{len(selected)} സ്ഥലങ്ങൾ · ₹{selected.cost.sum()/1e5:.1f} ലക്ഷം · ₹10 കോടി സംയുക്ത പദ്ധതിയിൽ നിന്ന്"))
                st.caption(local("Shown separately from the weather preview. These site effects are not a ward-wide temperature change or a fresh joint simulation.",
                                 "കാലാവസ്ഥാ കണക്കിൽ നിന്ന് വേർതിരിച്ചാണ് കാണിക്കുന്നത്. സ്ഥലങ്ങളിലെ ഈ ഫലം വാർഡിന്റെ ആകെ താപമാറ്റമോ പുതിയ സംയുക്ത പരീക്ഷണമോ അല്ല."))
            ward_cells=data["cells"].loc[data["cells"].ward_id==ward.name]
            overlay={"points":selected,"label":local("Ward weather sensitivity · historical heat layer", "വാർഡ് കാലാവസ്ഥാ സെൻസിറ്റിവിറ്റി · ചരിത്ര ചൂട് പാളി")}
            if len(ward_cells): overlay["center"]=[float(ward_cells.lat.mean()),float(ward_cells.lon.mean())]
            download(local("Ward weather scenario", "വാർഡ് കാലാവസ്ഥാ പരീക്ഷണം"),
                     {t("Ward / area"):choice,local("Air change °C", "വായു മാറ്റം °C"):dt,local("Humidity change pp", "ആർദ്രതാ മാറ്റം pp"):rh,
                      local("Wind change m/s", "കാറ്റിലെ മാറ്റം മീ/സെ"):wind,local("Sunlight change W/m²", "സൂര്യപ്രകാശ മാറ്റം W/m²"):sun,
                      local("Weather surface response", "കാലാവസ്ഥയുടെ ഉപരിതല ഫലം"):f"{weather_dt:+.2f} °C",
                      local("Saved ward anomaly", "സംരക്ഷിച്ച വാർഡ് വ്യത്യാസം"):f"{ward.lst_anom:+.2f} °C",
                      local("Separate saved intervention", "വേറിട്ട സംരക്ഷിച്ച നടപടി"):t(fixes[fix]) if fix and fix<len(fixes) else local("None", "ഇല്ല"),
                      local("Saved site mean change", "സ്ഥലങ്ങളിലെ ശരാശരി മാറ്റം"):f"{selected.dt.mean():+.2f} °C" if len(selected) else local("Not selected", "തിരഞ്ഞെടുത്തിട്ടില്ല")},
                     [local("Linear preview from city-wide atmospheric sensitivities. Weather ranges are sums of bootstrap endpoints, not joint confidence intervals. The historical heat map is unchanged. Treatment effects are saved joint-plan site results and are not added to the ward anomaly.",
                            "നഗരതല കാലാവസ്ഥാ സെൻസിറ്റിവിറ്റിയിൽ നിന്നുള്ള രേഖീയ കണക്ക്. പരിധികൾ ബൂട്ട്സ്ട്രാപ്പ് അറ്റങ്ങളുടെ ആകെത്തുകയാണ്; സംയുക്ത വിശ്വാസപരിധിയല്ല. ചരിത്ര ചൂട് ഭൂപടം മാറുന്നില്ല. നടപടി ഫലങ്ങൾ സംരക്ഷിച്ച സംയുക്ത പദ്ധതിയിൽ നിന്നാണ്; വാർഡ് വ്യത്യാസവുമായി കൂട്ടുന്നില്ല.")])

        elif section == "preview":
            overlay = render_preview(data, language)

        else:
            inventory=validation_inventory(m,data["reactions"])
            label("THE EVIDENCE BEHIND EVERY SCENARIO", "ഓരോ പരീക്ഷണത്തിനും പിന്നിലെ തെളിവുകൾ")
            cv=m["cv"]["spatial_cv"]
            compare([(t(k),v["r2"],f"R² {v['r2']:.2f} · RMSE {v['rmse']:.2f} °C") for k,v in cv.items()])
            st.caption(local(f"Spatial validation across {m['cv']['n_blocks']} held-out blocks, approximately 2 km each. Random CV R²: {m['cv']['random_cv_ours']['r2']:.2f}.",
                             f"ഏകദേശം 2 കി.മീ. വീതമുള്ള {m['cv']['n_blocks']} വേർതിരിച്ച ബ്ലോക്കുകളിലെ പരിശോധന. റാൻഡം CV R²: {m['cv']['random_cv_ours']['r2']:.2f}."))
            bt=m["backtest"]
            facts([(local("2017–2024 back-test cells", "2017–2024 പരിശോധനാ സെല്ലുകൾ"),f"{bt['n_changed_cells']:,}"),
                   (local("Back-test MAE", "മുൻപരിശോധന പിശക്"),f"{bt['mae_c']:.2f} °C"),
                   (local("Correlation", "പരസ്പരബന്ധം"),f"{bt['pearson_r']:.2f}")])
            with st.expander(local("Saved weather sensitivity runs", "സംരക്ഷിച്ച കാലാവസ്ഥാ സെൻസിറ്റിവിറ്റി പരീക്ഷണങ്ങൾ")):
                st.dataframe(pd.DataFrame([{local("Weather change", "കാലാവസ്ഥാ മാറ്റം"):t(e["label"]),
                                            local("Surface effect °C", "ഉപരിതല ഫലം °C"):round(e["effect_c"],2),
                                            local("Bootstrap range °C", "ബൂട്ട്സ്ട്രാപ്പ് പരിധി °C"):f"{e['ci_low']:+.2f} to {e['ci_high']:+.2f}"}
                                           for e in m["atmospheric"]["effects"].values()]),hide_index=True)
                st.caption(local("Bootstrap over satellite days; small scene counts make these estimates uncertain.",
                                 "ഉപഗ്രഹ നിരീക്ഷണ ദിവസങ്ങളിലെ ബൂട്ട്സ്ട്രാപ്പ്; ചെറിയ സാമ്പിളുകൾ കാരണം അനിശ്ചിതത്വമുണ്ട്."))
            with st.expander(local("Observed vs predicted change", "നിരീക്ഷിച്ച മാറ്റവും പ്രവചിച്ച മാറ്റവും")):
                points=pd.DataFrame(bt.get("points",[]),columns=["predicted","observed"])
                if len(points):
                    scatter=alt.Chart(points).mark_circle(color="#70d9b3",size=12,opacity=.3).encode(x=alt.X("predicted:Q",title=local("Predicted °C", "പ്രവചിച്ച °C")),y=alt.Y("observed:Q",title=local("Observed °C", "നിരീക്ഷിച്ച °C")))
                    st.altair_chart(scatter,width="stretch")
            physics=m.get("physics_check")
            if physics:
                label("COOL-ROOF PHYSICS CROSS-CHECK", "മേൽക്കൂരകളിലെ ഭൗതിക പരിശോധന")
                facts([(local("ML model", "ML മാതൃക"),f"{physics['median_model_c']:+.2f} °C"),
                       (local("Energy balance", "ഊർജസമതുലനം"),f"{physics['median_formula_c']:+.2f} °C")])
                st.caption(local(f"{physics['n_cells']:,} cells. Albedo and built density correlate (r={physics['albedo_built_frac_corr']:.2f}), limiting the model's isolated roof signal; the roof intervention uses the formula.",
                                 f"{physics['n_cells']:,} സെല്ലുകൾ. പ്രകാശപ്രതിഫലനവും കെട്ടിട സാന്ദ്രതയും തമ്മിൽ ബന്ധമുണ്ട് (r={physics['albedo_built_frac_corr']:.2f}). അതിനാൽ മേൽക്കൂര നടപടിക്ക് ഭൗതിക സൂത്രം ഉപയോഗിക്കുന്നു."))
            label("RUN AVAILABILITY", "ഫലങ്ങളുടെ ലഭ്യത")
            labels_ml=["പ്രദേശതല പരിശോധന","കാലാവസ്ഥാ സെൻസിറ്റിവിറ്റി","2017–2024 മുൻപരിശോധന","സമാനസ്ഥല kNN പരിശോധന","മേൽക്കൂര ഭൗതിക പരിശോധന","ECOSTRESS ഉച്ചതിരിഞ്ഞുള്ള പരിശോധന","CPCB സ്റ്റേഷൻ പരിശോധന","ജനപ്രതികരണ പരീക്ഷണം","SOLWEIG കാൽനട സുഖാനുഭവം","InVEST നഗര തണുപ്പിക്കൽ","അപകടസാധ്യതാ വെയിറ്റുകളുടെ പരിശോധന"]
            html("<div class='sim-inventory'>"+"".join(f"<div><span>{escape(local(name,ml))}</span><b class='{'ready' if ready else 'pending'}'>{local('SAVED' if ready else 'NOT RUN', 'ലഭ്യം' if ready else 'ലഭ്യമല്ല')}</b></div>" for (name,ready),ml in zip(inventory.items(),labels_ml))+"</div>")
            st.caption(local("Status is checked against this build. ECOSTRESS needs an Earthdata download; CPCB needs station CSVs. Matched validation, resident previews and the unweighted sensitivity are only available when their results have been generated. SOLWEIG and InVEST remain optional future work.",
                             "ഈ ബിൽഡിലെ ഫലങ്ങളാണ് ലഭ്യത നിർണ്ണയിക്കുന്നത്. ECOSTRESS-ന് Earthdata ഡൗൺലോഡും CPCB-ക്ക് സ്റ്റേഷൻ CSV-കളും വേണം. മറ്റ് ഫലങ്ങൾ സൃഷ്ടിക്കുമ്പോൾ ലഭ്യമാകും. SOLWEIG, InVEST എന്നിവ ഭാവിയിലെ ഐച്ഛിക പ്രവർത്തനങ്ങളാണ്."))
            for key in ("ecostress","cpcb"):
                if m.get(key):
                    with st.expander(t(key.upper())): st.json(m[key])
            if bt.get("matched"):
                with st.expander(local("Matched kNN results", "സമാനസ്ഥല kNN ഫലങ്ങൾ")): st.json(bt["matched"])
            download(local("Simulation evidence report", "പരീക്ഷണ തെളിവുകളുടെ റിപ്പോർട്ട്"),
                     {local("Spatial R²", "പ്രദേശതല R²"):next(iter(cv.values()))["r2"],
                      local("Back-test MAE °C", "മുൻപരിശോധന പിശക് °C"):bt["mae_c"],
                      **{local(k,ml):local("Saved" if v else "Not available", "ലഭ്യം" if v else "ലഭ്യമല്ല") for (k,v),ml in zip(inventory.items(),labels_ml)}},
                     [local("Availability is derived from committed artifacts, not completion claims in the planning document. Model validation is exploratory and does not establish causality.",
                            "ലഭ്യത സംരക്ഷിച്ച ഫലങ്ങളിൽ നിന്നാണ്. പദ്ധതിരേഖയിലെ പൂർത്തീകരണ അവകാശവാദങ്ങളിൽ നിന്നല്ല. മാതൃകാ പരിശോധന കാരണബന്ധം തെളിയിക്കുന്നില്ല.")])
    return overlay
