import pytest

from visat import config

pytestmark = pytest.mark.skipif(not (config.APP / "manifest.json").exists(),
                                reason="no data/app build")


def test_app_runs_all_four_screens_without_errors():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(config.ROOT / "app" / "streamlit_app.py"), default_timeout=180)
    at.run()
    assert not at.exception
    assert len(at.tabs) == 4
    at.selectbox[0].set_value("Island North").run()
    at.selectbox[2].set_value("Island North").run()
    assert not at.exception
    at.segmented_control(key="budget").set_value("₹50 crore").run()
    at.toggle(key="conservative").set_value(True).run()
    assert any("back-test error band" in info.value for info in at.info)
    at.toggle(key="neutral").set_value(True).run()
    assert not at.exception
    assert any("does not pass the heat-neutral screen" in warning.value
               for warning in at.warning)
