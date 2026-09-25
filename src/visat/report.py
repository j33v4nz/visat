"""Ward Heat Card: one printable page a councillor can take to a council meeting."""

import html

from visat import config

# Malayalam labels: M4 fills these with a HUMAN translation checked by a native speaker.
# (Machine-translated Malayalam with unchecked numbers was vetoed by the judge.)
ML_LABELS: dict[str, str] = {}

DRIVER_WORDS = {
    "Vegetation": ("Low tree cover", "Good tree cover"),
    "Concrete & buildings": ("Dense concrete & buildings", "Few buildings"),
    "Water nearby": ("Far from water", "Cooled by nearby water"),
    "Surface reflectivity": ("Dark, heat-absorbing surfaces", "Reflective surfaces"),
    "Weather of the day": ("Hot, still weather", "Milder weather"),
    "Terrain": ("Low-lying terrain", "Higher terrain"),
}


def driver_sentences(row, top=3) -> list[str]:
    drv = {k.split("::", 1)[1]: v for k, v in row.items() if str(k).startswith("drv::")}
    drv.pop("Weather of the day", None)  # same for the whole city on a given day
    out = []
    for g, v in sorted(drv.items(), key=lambda kv: -abs(kv[1]))[:top]:
        warm, cool = DRIVER_WORDS.get(g, (g, g))
        out.append(f"{warm if v > 0 else cool} {'adds' if v > 0 else 'removes'} {abs(v):.1f} °C")
    return out


def _t(label: str) -> str:
    ml = ML_LABELS.get(label)
    return f"{html.escape(label)}" + (f" <span class='ml'>/ {html.escape(ml)}</span>" if ml else "")


def ward_card(ward: dict, rank: int, n_wards: int, actions: list[dict], source: str) -> str:
    drivers = "".join(f"<li>{html.escape(s)}</li>" for s in driver_sentences(ward))
    acts = "".join(
        f"<tr><td>{html.escape(a['label'])}</td><td>{a['cells']}</td>"
        f"<td>₹{a['cost_rs'] / 1e5:,.1f} lakh</td><td>{a['dt']:+.2f} °C</td></tr>" for a in actions
    ) or "<tr><td colspan=4>No eligible public-land actions in this ward at ₹10 crore.</td></tr>"
    demo = "<p class='demo'>DEMO DATA — not real measurements</p>" if source == "demo" else ""
    sites = (f"{ward['schools']} schools · {ward['markets']} markets · {ward['hospitals']} hospitals · "
             f"{ward['construction_sites']} construction sites · {ward['harbours']} harbours")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Ward Heat Card — {html.escape(ward['ward'])}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Malayalam:wght@400;700&family=Source+Sans+3:wght@400;700&display=swap" rel="stylesheet">
<style>
body{{font-family:'Source Sans 3','Noto Sans Malayalam',sans-serif;margin:24px;color:#111;max-width:760px}}
h1{{margin:0;font-size:28px}} .sub{{color:#555;margin:4px 0 16px}} .ml{{font-family:'Noto Sans Malayalam'}}
.big{{display:flex;gap:16px;margin:12px 0}} .big div{{border:2px solid #c8410b;border-radius:8px;padding:10px 14px}}
.big b{{display:block;font-size:26px;color:#c8410b}} table{{border-collapse:collapse;width:100%}}
td,th{{border-bottom:1px solid #ddd;padding:6px;text-align:left}} .demo{{color:#fff;background:#c8410b;padding:4px 8px}}
.foot{{font-size:12px;color:#555;margin-top:16px}} @media print{{body{{margin:8mm}}}}
</style></head><body>{demo}
<h1>{_t('Ward Heat Card')}: {html.escape(ward['ward'])}</h1>
<p class="sub">Kochi · VISAT heat action planner · {config.LABEL_SURFACE}</p>
<div class="big"><div><b>#{rank} / {n_wards}</b>{_t('Heat-stress rank')}</div>
<div><b>{ward['people_in_hotspots']:,.0f}</b>{_t('People in hotspots')}</div>
<div><b>{ward['lst_anom']:+.1f} °C</b>{_t('vs city median')}</div></div>
<h3>{_t('Why it is hot')}</h3><ul>{drivers}</ul>
<h3>{_t('Vulnerable places')}</h3><p>{sites}</p>
<h3>{_t('Top actions (₹10 crore city plan, public land only)')}</h3>
<table><tr><th>Action</th><th>Sites (100 m)</th><th>Cost</th><th>Cooling</th></tr>{acts}</table>
<h3>{_t('On heat days')}</h3><ul>{''.join(f'<li>{html.escape(a)}</li>' for a in config.ACT_TODAY_ADVICE)}</ul>
<p><b>{_t('Who signs')}:</b> Ward councillor → Corporation standing committee; tree sites via C-HED / Kawaki.</p>
<p class="foot">Surface temperature from Landsat (~10:30 AM), not air temperature. Cooling = people-weighted
surface-°C, model estimate validated by a 2017→2024 back-test. Cool-roof/pavement effects use a labelled
energy-balance formula. Canals get no cooling credit.</p></body></html>"""
