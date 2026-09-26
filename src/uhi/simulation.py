"""Read saved scenario results without pretending to rerun the fitted model."""

from datetime import UTC, datetime
from html import escape

import pandas as pd


def plan_sites(preset, cells):
    """Match saved rounded coordinates to their original cells for ward filtering."""
    picks = pd.DataFrame(preset["picks"], columns=["lat", "lon", "fix", "dt", "cost"])
    locations = cells[["lat", "lon", "ward_id", "pop"]].copy()
    locations[["lat", "lon"]] = locations[["lat", "lon"]].round(5)
    return picks.merge(locations, on=["lat", "lon"], how="left", validate="many_to_one")


def weather_response(effects, changes):
    """Linear sensitivity preview. The summed endpoint range is not a joint CI."""
    steps = {"t2m_c": 1, "rh": 10, "wind_ms": 1, "ssrd_wm2": 100}
    rows = []
    for key, step in steps.items():
        factor = changes[key] / step
        effect = effects[key]
        endpoints = sorted([factor * effect["ci_low"], factor * effect["ci_high"]])
        rows.append({"variable": key, "change": changes[key],
                     "effect_c": factor * effect["effect_c"],
                     "low": endpoints[0], "high": endpoints[1]})
    return pd.DataFrame(rows)


def validation_inventory(metrics, reactions):
    """Status follows artifacts, not claims in a planning document."""
    return {
        "Spatial block validation": bool(metrics.get("cv", {}).get("spatial_cv")),
        "Atmospheric sensitivity": bool(metrics.get("atmospheric", {}).get("effects")),
        "2017 to 2024 back-test": bool(metrics.get("backtest", {}).get("n_changed_cells")),
        "Matched kNN back-test": bool(metrics.get("backtest", {}).get("matched")),
        "Cool-roof physics check": bool(metrics.get("physics_check")),
        "ECOSTRESS afternoon check": bool(metrics.get("ecostress")),
        "CPCB station check": bool(metrics.get("cpcb")),
        "Resident reaction preview": bool(reactions),
        "SOLWEIG pedestrian comfort": False,
        "InVEST Urban Cooling": False,
        "Vulnerability weighting sensitivity": False,
    }


def scenario_report(title, values, notes, manifest, language="en", tables=None):
    """Portable, printable report of the exact selection, with escaped user/data text."""
    rows = "".join(f"<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>"
                   for k, v in values.items())
    note_html = "".join(f"<p>{escape(str(note))}</p>" for note in notes)
    built = escape(str(manifest.get("built_at", "unknown")))
    source = escape(str(manifest.get("source", "unknown")))
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    table_html = "".join(f"<h2>{escape(str(name))}</h2>" + frame.to_html(index=False, escape=True, border=0)
                         for name, frame in (tables or {}).items())
    return f'''<!doctype html><html lang="{language}"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UHI: {escape(title)}</title><style>
body{{background:#080a09;color:#f2f1eb;font:15px/1.65 Consolas,"Noto Sans Malayalam",monospace;max-width:850px;margin:40px auto;padding:24px}}
h1{{font-size:28px}}header{{border-top:3px solid #ff7627;padding-top:18px}}small{{color:#abb6af}}table{{border-collapse:collapse;width:100%;margin:25px 0}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #39443e;overflow-wrap:anywhere}}th{{font-weight:400}}table:first-of-type th{{width:45%}}td{{font-weight:700}}p{{max-width:75ch}}@media print{{body{{color:#111;background:#fff}}small{{color:#444}}th,td{{border-color:#bbb}}}}
</style><header><small>UHI: Urban Heat Intelligence</small><h1>{escape(title)}</h1></header>
<table>{rows}</table>{note_html}{table_html}<footer><small>Source: {source} · Build: {built}<br>Report: {generated}</small></footer></html>'''
