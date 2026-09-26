"""Walk the map-first UHI dashboard and save desktop, scenario and mobile screenshots."""
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("artifacts/m3")
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://localhost:8501", wait_until="domcontentloaded", timeout=60000)
    page.locator(".st-key-inspector").wait_for(timeout=30000)
    page.wait_for_timeout(2500)
    canvas = page.locator(".st-key-map_canvas").bounding_box()
    assert canvas["width"] == 1600 and canvas["height"] == 1000
    page.screenshot(path=str(OUT / "dashboard_desktop.png"))

    nav = page.locator(".st-key-navigation")
    nav.get_by_text("Cooling plan", exact=False).click()
    page.get_by_text("People cooled", exact=False).wait_for()
    page.screenshot(path=str(OUT / "dashboard_plan.png"))

    nav.get_by_text("Project check", exact=False).click()
    page.get_by_text("Development impact", exact=False).wait_for()
    page.screenshot(path=str(OUT / "dashboard_project.png"))

    nav.get_by_text("Simulation", exact=False).click()
    page.get_by_text("Test a ward-level heat scenario", exact=False).wait_for()
    page.get_by_role("button", name="Download scenario report").wait_for()
    page.screenshot(path=str(OUT / "dashboard_simulation.png"))

    nav.get_by_text("Evidence", exact=False).click()
    page.get_by_text("Model performance", exact=False).wait_for()
    page.screenshot(path=str(OUT / "dashboard_evidence.png"))

    nav.get_by_text("Heat overview", exact=False).click()
    page.get_by_role("combobox").first.click()
    page.get_by_role("option").nth(1).click()
    page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / "dashboard_malayalam.png"))
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(800)
    layer_options = page.locator(".st-key-map_tools").get_by_text("Heat surface", exact=False)
    if layer_options.count() and layer_options.first.is_visible():
        page.locator(".st-key-map_tools").get_by_role("button").first.click()
        page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / "dashboard_mobile.png"))
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert not errors, errors
    assert not page.locator('[data-testid="stException"]').count()
    browser.close()

print("Dashboard capture passed: five workspaces, English/Malayalam and mobile.")
