"""Browser walkthrough and screenshots of the simulation catalogue."""
from pathlib import Path

from playwright.sync_api import sync_playwright

out = Path("artifacts/m3")
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://localhost:8501", wait_until="domcontentloaded")
    page.locator(".st-key-navigation").get_by_text("Simulation", exact=True).click()
    page.get_by_text("City scenario lab", exact=True).wait_for()
    panel = page.locator(".st-key-inspector")
    tabs = page.locator(".st-key-sim_section")
    for name, marker in [("Interventions", ".st-key-sim_intervention"),
                         ("Budgets", ".st-key-sim_budget"),
                         ("Development", ".st-key-sim_site"),
                         ("Ward lab", ".st-key-simulation_ward"),
                         ("Evidence", ".sim-inventory")]:
        tabs.get_by_text(name, exact=True).click()
        page.locator(marker).wait_for()
        panel.evaluate("el => el.scrollTop = 0")
        page.wait_for_timeout(600)
        assert not page.locator('[data-testid="stException"]').count()
        page.screenshot(path=str(out / f"simulation_{name.lower().replace(' ', '_')}.png"))
    with page.expect_download() as downloaded:
        page.get_by_role("button", name="Download scenario report", exact=True).click()
    downloaded.value.save_as(str(out / "simulation_evidence_report.html"))
    assert "Not available" in (out / "simulation_evidence_report.html").read_text(encoding="utf-8")
    tabs.get_by_text("Interventions", exact=True).click()
    page.get_by_role("combobox", name="Cooling intervention").click()
    page.get_by_role("option", name="Mangrove restoration", exact=True).click()
    page.get_by_text("Low support:", exact=False).wait_for()
    tabs.get_by_text("Ward lab", exact=True).click()
    page.locator(".st-key-simulation_temp").wait_for()
    page.set_viewport_size({"width": 390, "height": 844})
    panel.evaluate("el => el.scrollTop = 0")
    page.wait_for_timeout(600)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(out / "simulation_mobile.png"))
    page.get_by_role("button", name="Download scenario report", exact=True).scroll_into_view_if_needed()
    rect = page.get_by_role("button", name="Download scenario report", exact=True).bounding_box()
    assert rect and rect["y"] + rect["height"] <= 844
    page.locator(".st-key-topbar").get_by_role("combobox").click()
    page.get_by_role("option", name="മലയാളം", exact=True).click()
    page.get_by_text("നഗര സാഹചര്യ പരീക്ഷണം", exact=True).wait_for()
    panel.evaluate("el => el.scrollTop = 0")
    page.screenshot(path=str(out / "simulation_malayalam_mobile.png"))
    assert not page.locator('[data-testid="stException"]').count()
    assert not errors, errors
    browser.close()
print("Simulation walkthrough passed: all views, low-support warning, report download, mobile and Malayalam.")
