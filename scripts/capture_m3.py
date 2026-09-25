"""Capture the four VISAT demo moments from a running local Streamlit app.

Run: python scripts/capture_m3.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("artifacts/m3")
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1)
    page.goto("http://localhost:8501", wait_until="networkidle", timeout=120_000)
    page.get_by_role("tab", name="① Where is heat dangerous today?").click()
    page.wait_for_timeout(2000)
    page.screenshot(path=str(OUT / "01_today.png"), animations="disabled")

    page.get_by_role("tab", name="② What should we do with ₹?").click()
    page.get_by_text("₹10 crore → about", exact=False).wait_for()
    page.wait_for_timeout(1500)
    assert not page.get_by_text("Error: Unexpected", exact=False).count()
    page.screenshot(path=str(OUT / "02_plan_10_crore.png"), animations="disabled")
    page.get_by_text("Show OSM canal-bank tree-strip candidates").click()
    page.get_by_text("Blue dots = 100 m cells near OSM canals", exact=False).wait_for()
    assert not page.get_by_text("Error: Unexpected", exact=False).count()

    page.get_by_role("tab", name="③ Will this project make it hotter?").click()
    page.get_by_text("Apply available offsets").click()
    page.get_by_text("Heat remains after these offsets", exact=False).wait_for()
    page.wait_for_timeout(1500)
    assert not page.get_by_text("Error: Unexpected", exact=False).count()
    page.screenshot(path=str(OUT / "03_kakkanad_it_park.png"), animations="disabled")
    page.get_by_text("Compare the modelled heat before and after offsets").click()
    page.get_by_text("Project + available offsets").wait_for()
    assert not page.get_by_text("Error: Unexpected", exact=False).count()

    page.get_by_role("tab", name="④ Can we trust it? · Ward Card").click()
    page.get_by_text("We predicted 2024 from 2017", exact=False).wait_for()
    page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / "04_proof_ward_card.png"), animations="disabled")
    browser.close()

print(f"Saved four screenshots to {OUT.resolve()}")
