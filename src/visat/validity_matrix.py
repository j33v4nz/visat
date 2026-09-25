"""The intervention validity matrix (PLAN.md §5): every intervention type,
how it's modelled (real-data analog, energy-balance formula, or no °C
credit), where it's legally/physically allowed, and its cost function.

This is the single source of truth the optimizer and the Check-a-Project
screen both read from — never hardcode a cost or a method anywhere else.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import config


class Method(str, Enum):
    ANALOG = "analog"  # nearest-neighbour transition toward real Kochi cells
    FORMULA = "formula"  # energy-balance formula (physics.py)
    ANALOG_OR_FORMULA = "analog_or_formula"  # analog where data supports it, formula otherwise
    NO_CREDIT = "no_credit"  # shown as a committed overlay, never earns °C


@dataclass(frozen=True)
class Intervention:
    key: str
    label: str
    ps1_category: str
    method: Method
    where_allowed: str
    cost_fn_name: str  # name of the matching function in this module
    optimizer_eligible: bool  # False for green roofs (rarely cost-effective) and IURWTS (not bought)


INTERVENTIONS: dict[str, Intervention] = {
    "street_tree": Intervention(
        key="street_tree",
        label="Street trees",
        ps1_category="greening",
        method=Method.ANALOG,
        where_allowed="OSM roads, schools, parks (public land only)",
        cost_fn_name="cost_street_tree",
        optimizer_eligible=True,
    ),
    "canal_bank_strip": Intervention(
        key="canal_bank_strip",
        label="Canal-bank tree strips",
        ps1_category="greening_and_water",
        method=Method.ANALOG,
        where_allowed="Banks of the 6 canals in KMRL's IURWTS canal project",
        cost_fn_name="cost_canal_bank_strip",
        optimizer_eligible=True,
    ),
    "mangrove": Intervention(
        key="mangrove",
        label="Mangroves",
        ps1_category="greening",
        method=Method.ANALOG,
        where_allowed="CRZ / government shoreline only",
        cost_fn_name="cost_mangrove",
        optimizer_eligible=True,
    ),
    "green_roof": Intervention(
        key="green_roof",
        label="Green roofs",
        ps1_category="greening",
        method=Method.FORMULA,
        where_allowed="Buildings",
        cost_fn_name="cost_green_roof",
        optimizer_eligible=False,  # simulated and scored, rarely chosen on cost
    ),
    "cool_roof": Intervention(
        key="cool_roof",
        label="Cool roofs",
        ps1_category="cool_roofs",
        method=Method.FORMULA,
        where_allowed="Buildings",
        cost_fn_name="cost_cool_roof",
        optimizer_eligible=True,
    ),
    "cool_pavement": Intervention(
        key="cool_pavement",
        label="Cool pavements",
        ps1_category="albedo",
        method=Method.FORMULA,
        where_allowed="OSM road cells",
        cost_fn_name="cost_cool_pavement",
        optimizer_eligible=True,
    ),
    "pond_restoration": Intervention(
        key="pond_restoration",
        label="Pond restoration (>= 1 ha)",
        ps1_category="water_bodies",
        method=Method.ANALOG_OR_FORMULA,
        where_allowed="Low-lying public land",
        cost_fn_name="cost_pond_restoration",
        optimizer_eligible=True,
    ),
    "iurwts_canal": Intervention(
        key="iurwts_canal",
        label="IURWTS canals (KMRL)",
        ps1_category="water_bodies",
        method=Method.NO_CREDIT,
        where_allowed="6 canals: Edappally, Chilavannur, Thevara-Perandoor, Thevara, Konthuruthy, Market",
        cost_fn_name="cost_iurwts_canal",
        optimizer_eligible=False,  # committed project, 0 degC credit, shown as overlay only
    ),
}


def cost_street_tree(n_trees: int) -> float:
    return n_trees * config.COST_STREET_TREE_INCL_5YR_CARE


def cost_canal_bank_strip(length_m: float) -> float:
    return length_m * config.COST_CANAL_BANK_TREE_STRIP_PER_M


def cost_mangrove(hectares: float, *, high_estimate: bool = False) -> float:
    rate = config.COST_MANGROVE_PER_HECTARE_HIGH if high_estimate else config.COST_MANGROVE_PER_HECTARE_LOW
    return hectares * rate


def cost_green_roof(area_sqm: float) -> float:
    return area_sqm * config.COST_GREEN_ROOF_PER_SQM


def cost_cool_roof(area_sqm: float, *, years: int = 1) -> float:
    """Initial coat plus recoats every ~3 years, amortised over `years`."""
    recoats = max(0, (years - 1) // 3)
    return area_sqm * (config.COST_COOL_ROOF_PER_SQM + recoats * config.COST_COOL_ROOF_RECOAT_PER_SQM)


def cost_cool_pavement(area_sqm: float) -> float:
    return area_sqm * config.COST_COOL_PAVEMENT_PER_SQM


def cost_pond_restoration(hectares: float) -> float:
    return hectares * config.COST_POND_RESTORATION_PER_HECTARE


def cost_iurwts_canal() -> float:
    """Committed, not bought by the optimizer — returned for display only."""
    return config.COST_IURWTS_TOTAL_CRORE * 1e7  # crore -> rupees


def optimizer_eligible_interventions() -> list[Intervention]:
    return [i for i in INTERVENTIONS.values() if i.optimizer_eligible]
