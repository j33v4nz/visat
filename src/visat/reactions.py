"""Public Reaction Preview (Tier 3) — SIMULATED resident personas react to a heat-neutral proposal.

Synthetic resident TYPES built from aggregate ward statistics — never real or identifiable people.
Output prepares C-HED for public consultation; it never changes any °C, ₹ or ranking number.
Precomputed (no live AI call in the demo):

    uv sync --extra reactions
    ANTHROPIC_API_KEY=... uv run python -m visat.reactions      # writes data/app/reactions_cache.json
"""

import json
import re

import pandas as pd

from visat import config

PERSONAS = [  # (id, persona, where they are picked from, outdoor hours/day, typical concerns)
    ("fisher", "Fisher, Fort Kochi", "harbours", 8, "catch, harbour access, heat on the water"),
    ("migrant_worker", "Migrant construction worker (Hindi/Odia/Bengali speaker)", "construction_sites", 9,
     "work hours, shade, drinking water, wages"),
    ("auto_driver", "Autorickshaw driver", "people", 10, "shade at stands, traffic, fuel"),
    ("market_vendor", "Broadway market vendor", "markets", 10, "shade, customers, fire risk"),
    ("it_employee", "Kakkanad IT employee", "people", 1, "commute, traffic, green space"),
    ("elderly", "Elderly resident, Mattancherry", "heat_stress", 2, "health, heat at home, water"),
    ("parent", "School parent", "schools", 1, "children's safety, school timing"),
    ("anganwadi", "Anganwadi worker", "schools", 4, "children under 6, water, shade"),
    ("councillor", "Ward councillor", "heat_stress", 3, "budget, votes, visible results"),
    ("builder", "Builder / developer", "construction_sites", 3, "cost, approvals, FSI"),
    ("rwa", "Residents' association secretary", "people", 2, "parking, trees, maintenance"),
    ("volunteer", "Environmental volunteer", "heat_stress", 4, "native trees, mangroves, canals"),
    ("shopkeeper", "Shopkeeper", "markets", 8, "footfall, parking, construction dust"),
    ("student", "College student", "schools", 3, "bus stops, heat while walking"),
    ("asha", "ASHA health worker", "hospitals", 6, "heat illness, elderly visits"),
    ("fish_seller", "Fish seller (woman), market", "markets", 8, "ice, shade, stall space"),
    ("security_guard", "Security guard, IT park", "construction_sites", 12, "night shifts, heat, shade"),
    ("hospital_staff", "Hospital staff", "hospitals", 2, "heat admissions, ambulance access"),
    ("home_worker", "Home-based worker", "people", 1, "heat indoors, electricity bills"),
    ("delivery_rider", "Delivery rider", "people", 10, "shade, water points, routes"),
]

SCHEMA = {
    "type": "object",
    "properties": {
        "personas": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "persona_id": {"type": "string"},
                "stance": {"type": "string", "enum": ["support", "neutral", "oppose"]},
                "top_concern": {"type": "string"},
                "would_change_mind_if": {"type": "string"},
                "quote_en": {"type": "string"},
            },
            "required": ["persona_id", "stance", "top_concern", "would_change_mind_if", "quote_en"],
            "additionalProperties": False,
        }},
        "top_concerns": {"type": "array", "items": {"type": "string"}},
        "consult_first": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["personas", "top_concerns", "consult_first"],
    "additionalProperties": False,
}

SYSTEM = (
    "You simulate how types of Kochi residents might react to an urban-heat proposal, to help the "
    "city's climate cell prepare for public consultation. The personas are synthetic TYPES built from "
    "aggregate ward statistics, not real people. Be realistic and varied: include support, doubts and "
    "opposition where plausible. Keep quotes to one short sentence in plain English. Do not invent any "
    "numbers: only use numbers that appear in the proposal facts, or none. Return one entry per persona "
    "in the table, then the 5 most common concerns and the 3 groups to consult first.\n\nPersona table:\n"
)


def persona_table(wards: pd.DataFrame) -> list[dict]:
    rows = []
    for pid, label, pick, hours, concerns in PERSONAS:
        col = pick if pick in wards else "people"
        w = wards.sort_values(col, ascending=False).iloc[0]
        rows.append({"persona_id": pid, "persona": label, "ward": w["ward"],
                     "outdoor_hours_per_day": hours, "typical_concerns": concerns})
    return rows


def facts(result: dict) -> str:
    mix = "; ".join(f"{k}: {v['cells']} sites" for k, v in result["offset_mix"].items())
    return (f"Proposal: a new {result['use']} at {result['site']}. VISAT estimate: it would add "
            f"{result['before']['mean_dt_c']} °C of morning surface heat for about "
            f"{result['before']['people']} people within 500 m. Heat-neutral offset: {mix}, costing "
            f"₹{result['offset_cost_rs'] / 1e5:.0f} lakh. The city would ask the developer to fund the "
            f"offset in exchange for a building-rule incentive.")


_NUM = re.compile(r"\d[\d,]*\.?\d*")


def number_guard(data: dict, fact_text: str) -> dict:
    """Drop any persona reply that quotes a number not present in the proposal facts."""
    allowed = {n.replace(",", "").rstrip(".") for n in _NUM.findall(fact_text)}
    kept, dropped = [], 0
    for p in data.get("personas", []):
        text = " ".join(str(p.get(k, "")) for k in ("top_concern", "would_change_mind_if", "quote_en"))
        nums = {n.replace(",", "").rstrip(".") for n in _NUM.findall(text)}
        if nums <= allowed:
            kept.append(p)
        else:
            dropped += 1
    return {**data, "personas": kept, "guard_dropped": dropped}


def simulate(client, table: list[dict], result: dict) -> dict | None:
    fact_text = facts(result)
    resp = client.beta.messages.create(
        model=config.REACTIONS_MODEL,
        max_tokens=8000,
        betas=["server-side-fallback-2026-07-01"],
        extra_body={"fallbacks": "default"},
        output_config={"effort": config.REACTIONS_EFFORT,
                       "format": {"type": "json_schema", "schema": SCHEMA}},
        system=[{"type": "text", "text": SYSTEM + json.dumps(table, ensure_ascii=False),
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": fact_text}],
    )
    if resp.stop_reason in ("refusal", "max_tokens"):
        return None
    text = next((b.text for b in resp.content if b.type == "text"), "")
    data = number_guard(json.loads(text), fact_text)
    by_id = {r["persona_id"]: r for r in table}
    for p in data["personas"]:
        p["persona"] = by_id.get(p["persona_id"], {}).get("persona", p["persona_id"])
    data["facts"] = fact_text
    data["model"] = config.REACTIONS_MODEL
    return data


def run():
    import anthropic

    client = anthropic.Anthropic()
    wards = pd.read_parquet(config.APP / "wards.parquet")
    hn = json.loads((config.APP / "heat_neutral.json").read_text())
    table = persona_table(wards)
    out_path = config.APP / "reactions_cache.json"
    cache = json.loads(out_path.read_text()) if out_path.exists() else {}
    for key, result in hn["results"].items():
        if key in cache:
            continue
        try:
            data = simulate(client, table, result)
        except anthropic.APIError as e:
            print(f"{key}: API error {type(e).__name__} — skipped")
            continue
        if data:
            cache[key] = data
            out_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
            print(f"{key}: {len(data['personas'])} personas (guard dropped {data['guard_dropped']})")
    print(f"saved {len(cache)} results to {out_path}")


if __name__ == "__main__":
    run()
