"""Ward Heat Card: one printable page a councillor can take to a council meeting."""

import html

from visat import config, i18n

# Kept as a reviewable glossary for the event team's native-speaker copy review.
ML_LABELS = i18n.ML

DRIVER_WORDS = {
    "Vegetation": ("Low tree cover", "Good tree cover"),
    "Concrete & buildings": ("Dense concrete & buildings", "Few buildings"),
    "Water nearby": ("Far from water", "Cooled by nearby water"),
    "Surface reflectivity": ("Dark, heat-absorbing surfaces", "Reflective surfaces"),
    "Weather of the day": ("Hot, still weather", "Milder weather"),
    "Terrain": ("Low-lying terrain", "Higher terrain"),
}


def driver_sentences(row, top=3, language: str = "en") -> list[str]:
    if language == "ml":
        return i18n.drivers(row, language, top)
    drv = {k.split("::", 1)[1]: v for k, v in row.items() if str(k).startswith("drv::")}
    drv.pop("Weather of the day", None)  # same for the whole city on a given day
    out = []
    for g, v in sorted(drv.items(), key=lambda kv: -abs(kv[1]))[:top]:
        warm, cool = DRIVER_WORDS.get(g, (g, g))
        out.append(f"{warm if v > 0 else cool} {'adds' if v > 0 else 'removes'} {abs(v):.1f} °C")
    return out


def ward_card(ward: dict, rank: int, n_wards: int, actions: list[dict], source: str,
              language: str = "en") -> str:
    """Render a printable card in the selected language, preserving source numbers."""
    t = lambda label: i18n.tr(label, language)
    local = lambda en, ml: ml if language == "ml" else en
    drivers = "".join(f"<li>{html.escape(s)}</li>" for s in driver_sentences(ward, language=language))
    acts = "".join(
        f"<tr><td>{html.escape(t(a['label']))}</td><td>{a['cells']}</td>"
        f"<td>₹{a['cost_rs'] / 1e5:,.1f} {t('lakh')}</td><td>{a['dt']:+.2f} °C</td></tr>"
        for a in actions
    ) or f"<tr><td colspan=4>{local('No eligible public-land actions in this ward at ₹10 crore.', '₹10 കോടി പദ്ധതിയിൽ ഈ വാർഡിലെ പൊതുഭൂമിക്ക് യോഗ്യമായ ഇടപെടലുകളില്ല.')}</td></tr>"
    demo = (f"<p class='demo'>{local('DEMO DATA — not real measurements', 'പരീക്ഷണ വിവരങ്ങൾ — യഥാർത്ഥ അളവുകളല്ല')}</p>"
            if source == "demo" else "")
    sites = local(
        f"{ward['schools']} schools · {ward['markets']} markets · {ward['hospitals']} hospitals · "
        f"{ward['construction_sites']} construction sites · {ward['harbours']} harbours",
        f"{ward['schools']} സ്കൂളുകൾ · {ward['markets']} ചന്തകൾ · "
        f"{ward['hospitals']} ആശുപത്രികൾ · {ward['construction_sites']} നിർമാണ സ്ഥലങ്ങൾ · "
        f"{ward['harbours']} തുറമുഖങ്ങൾ")
    advice = "".join(f"<li>{html.escape(t(item))}</li>" for item in config.ACT_TODAY_ADVICE)
    note = local(
        "Surface temperature from Landsat (~10:30 AM), not air temperature. Cooling = people-weighted "
        "surface-°C, model estimate validated by a 2017→2024 back-test. Cool-roof/pavement effects "
        "use a labelled energy-balance formula. Canals get no cooling credit.",
        "ലാൻഡ്‌സാറ്റ് ഉപഗ്രഹത്തിൽ നിന്ന് രാവിലെ ഏകദേശം 10:30-ന് കണക്കാക്കിയ ഉപരിതല താപനിലയാണ്; "
        "ഇത് വായുതാപനിലയല്ല. ചൂടുകുറവ് ആളുകളുടെ എണ്ണം അനുസരിച്ച് തൂക്കിയ മാതൃകാ കണക്കാണ്; "
        "2017→2024 വിവരങ്ങളുമായുള്ള മുൻപരിശോധന നടത്തിയിട്ടുണ്ട്. മേൽക്കൂരയുടെയും നടപ്പാതയുടെയും "
        "ഫലത്തിൽ ഊർജസമതുലന സൂത്രവും ഉപയോഗിച്ചു. കനാൽ പണിക്ക് ചൂടുകുറവ് കണക്കാക്കിയിട്ടില്ല.")
    sign = local("Ward councillor → Corporation standing committee; tree sites via C-HED / Kawaki.",
                 "വാർഡ് കൗൺസിലർ → കോർപ്പറേഷൻ സ്റ്റാൻഡിങ് കമ്മിറ്റി; വൃക്ഷനടീൽ സ്ഥലങ്ങൾ C-HED / Kawaki വഴി.")
    return f"""<!doctype html><html lang="{language}"><head><meta charset="utf-8"><title>{t('Ward Heat Card')} — {html.escape(ward['ward'])}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Malayalam:wght@400;700&family=Source+Sans+3:wght@400;700&display=swap" rel="stylesheet">
<style>
body{{font-family:'Noto Sans Malayalam','Source Sans 3',sans-serif;margin:24px;color:#111;max-width:760px}}
h1{{margin:0;font-size:28px}} .sub{{color:#555;margin:4px 0 16px}} .ml{{font-family:'Noto Sans Malayalam'}}
.big{{display:flex;gap:16px;margin:12px 0}} .big div{{border:2px solid #c8410b;border-radius:8px;padding:10px 14px}}
.big b{{display:block;font-size:26px;color:#c8410b}} table{{border-collapse:collapse;width:100%}}
td,th{{border-bottom:1px solid #ddd;padding:6px;text-align:left}} .demo{{color:#fff;background:#c8410b;padding:4px 8px}}
.foot{{font-size:12px;color:#555;margin-top:16px}} @media print{{body{{margin:8mm}}}}
</style></head><body>{demo}
<h1>{t('Ward Heat Card')}: {html.escape(ward['ward'])}</h1>
<p class="sub">{local('Kochi · VISAT heat action planner · surface °C, ~10:30 AM, Jan–Apr', 'കൊച്ചി · VISAT ചൂട് പ്രതിരോധ പദ്ധതി · രാവിലെ ഏകദേശം 10:30-ലെ ഉപരിതല താപനില (ജനുവരി–ഏപ്രിൽ)')}</p>
<div class="big"><div><b>#{rank} / {n_wards}</b>{t('Heat-stress rank')}</div>
<div><b>{ward['people_in_hotspots']:,.0f}</b>{t('People in hotspots')}</div>
<div><b>{ward['lst_anom']:+.1f} °C</b>{t('vs city median')}</div></div>
<h3>{t('Why it is hot')}</h3><ul>{drivers}</ul>
<h3>{t('Vulnerable places')}</h3><p>{sites}</p>
<h3>{t('Top actions (₹10 crore city plan, public land only)')}</h3>
<table><tr><th>{t('Action')}</th><th>{t('Sites (100 m)')}</th><th>{t('Cost')}</th><th>{t('Cooling')}</th></tr>{acts}</table>
<h3>{t('On heat days')}</h3><ul>{advice}</ul>
<p><b>{t('Who signs')}:</b> {sign}</p>
<p class="foot">{note}</p></body></html>"""
