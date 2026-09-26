import pytest

from uhi import config

pytestmark = pytest.mark.skipif(not (config.APP / "manifest.json").exists(),
                                reason="no data/app build")


def test_app_runs_all_workspaces_without_errors():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(config.ROOT / "app" / "streamlit_app.py"), default_timeout=180)
    at.run()
    assert not at.exception
    assert len(at.radio(key="workspace").options) == 5
    at.selectbox(key="today_ward").set_value("Island North").run()
    at.radio(key="workspace").set_value("plan").run()
    assert not at.exception
    at.segmented_control(key="budget").set_value(50).run()
    at.toggle(key="conservative").set_value(True).run()
    assert any("back-test error band" in info.value for info in at.info)
    at.radio(key="workspace").set_value("project").run()
    at.toggle(key="neutral").set_value(True).run()
    assert not at.exception
    assert any("does not pass the heat-neutral screen" in warning.value for warning in at.warning)
    at.radio(key="workspace").set_value("evidence").run()
    assert not at.exception


def test_scenario_workspace_renders_report_without_error():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(config.ROOT / "app" / "streamlit_app.py"), default_timeout=180)
    at.run()
    at.radio(key="workspace").set_value("simulation").run()
    assert not at.exception
    assert any(button.label == "Download scenario report" for button in at.get("download_button"))
    at.radio(key="sim_section").set_value("weather").run()
    at.selectbox(key="simulation_ward").set_value("Island North").run()
    assert not at.exception
    at.selectbox(key="simulation_fix").set_value(1).run()
    assert not at.exception


def test_simulation_catalog_selections_and_availability():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(config.ROOT / "app" / "streamlit_app.py"), default_timeout=180).run()
    at.radio(key="workspace").set_value("simulation").run()
    for option in at.selectbox(key="sim_intervention").options:
        at.selectbox(key="sim_intervention").set_value(option).run()
        assert not at.exception
        if option in ("Mangrove restoration", "Pond restoration (0.5 ha)"):
            assert any("Low support" in message.value for message in at.warning)
    at.radio(key="sim_section").set_value("budgets").run()
    at.segmented_control(key="sim_budget").set_value(50).run()
    assert not at.exception
    assert any("reaches more people" in message.value for message in at.info)
    at.radio(key="sim_section").set_value("projects").run()
    for site in at.selectbox(key="sim_site").options:
        at.selectbox(key="sim_site").set_value(site).run()
        for use in config.PROJECT_USES:
            at.selectbox(key="sim_use").set_value(use).run()
            assert not at.exception
    at.radio(key="sim_section").set_value("validation").run()
    assert not at.exception
    assert any("NOT RUN" in item.value for item in at.markdown)


def test_malayalam_mode_keeps_results_and_card_numbers():
    from streamlit.testing.v1 import AppTest

    from uhi import report

    at = AppTest.from_file(str(config.ROOT / "app" / "streamlit_app.py"), default_timeout=180)
    at.run()
    at.selectbox(key="language").set_value("മലയാളം").run()
    assert not at.exception
    assert "ഇന്നത്തെ ചൂട്" in at.radio(key="workspace").options[0]
    assert any("താപസൂചിക" in item.value for item in at.markdown)
    at.radio(key="workspace").set_value("project").run()
    at.toggle(key="neutral").set_value(True).run()
    assert any("ചൂട്-നിഷ്പക്ഷ പരിശോധനയിൽ വിജയിക്കുന്നില്ല" in warning.value
               for warning in at.warning)
    assert not at.exception
    row = {"ward": "Island North", "people_in_hotspots": 125, "lst_anom": 1.2,
           "schools": 2, "markets": 1, "hospitals": 1, "construction_sites": 0,
           "harbours": 0, "drv::Vegetation": 0.3}
    card = report.ward_card(row, 1, 74, [], "frozen", language="ml")
    assert "വാർഡിലെ ചൂട്" in card
    assert "125" in card
    assert "1.2 °C" in card
    assert "No eligible public-land actions" not in card


def test_optional_3d_preview_starts_and_updates():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(config.ROOT / "app" / "streamlit_app.py"), default_timeout=180).run()
    at.radio(key="workspace").set_value("simulation").run()
    at.selectbox(key="sim_intervention").set_value("Cool roofs").run()
    at.radio(key="sim_section").set_value("preview").run()
    assert at.selectbox(key="preview_fix").value == "Cool roofs"
    assert not any("ILLUSTRATIVE NEIGHBOURHOOD" in item.proto.srcdoc for item in at.get("iframe"))
    at.button(key="start_3d_simulation").click().run()
    assert not at.exception
    assert at.session_state["_preview_started"]
    assert any("ILLUSTRATIVE NEIGHBOURHOOD" in item.proto.srcdoc for item in at.get("iframe"))
    at.selectbox(key="preview_fix").set_value("IURWTS canals (KMRL)").run()
    assert not at.exception
    assert at.metric[0].value == "+0.00 °C"
    at.slider(key="preview_t2m_c").set_value(2.0).run()
    assert not at.exception
    assert any(metric.value == "+1.01 °C" for metric in at.metric)
