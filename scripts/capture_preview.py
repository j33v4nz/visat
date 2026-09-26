"""Exercise the optional 3D player in a real browser."""
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
    page.locator(".st-key-sim_section").get_by_text("3D Preview", exact=True).click()
    page.get_by_role("button", name="Start simulation", exact=True).click()
    player = page.frame_locator('iframe[srcdoc*="const scenario="]')
    player.get_by_text("SCENARIO READY", exact=True).wait_for()
    player.get_by_role("button", name="Before", exact=True).click()
    assert player.locator("canvas").get_attribute("data-progress") == "0"
    player.get_by_role("button", name="After", exact=True).click()
    assert player.locator("canvas").get_attribute("data-progress") == "1"
    player.locator("canvas").scroll_into_view_if_needed()
    page.screenshot(path=str(out / "simulation_3d_desktop.png"))
    page.get_by_role("combobox", name="Visualise a cooling measure").click()
    page.get_by_role("option", name="Cool roofs", exact=True).click()
    player.locator('canvas[data-treatment="Cool roofs"]').wait_for()
    player.get_by_text("SCENARIO READY", exact=True).wait_for()
    assert not page.locator('[data-testid="stException"]').count()
    page.set_viewport_size({"width": 390, "height": 844})
    player.locator("canvas").scroll_into_view_if_needed()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(out / "simulation_3d_mobile.png"))
    page.locator(".st-key-topbar").get_by_role("combobox").click()
    page.get_by_role("option", name="മലയാളം", exact=True).click()
    player.get_by_role("button", name="ശേഷം", exact=True).wait_for()
    assert not errors, errors
    browser.close()
print("3D preview passed: start, animation, before/after, selection update, mobile, Malayalam.")
