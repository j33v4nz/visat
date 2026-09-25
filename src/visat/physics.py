"""Energy-balance formula for interventions without enough real-world
analogs in the Kochi data (cool roofs, cool pavements, green roofs).

ΔT ≈ Δalbedo × S / h

S = incoming solar irradiance (W/m²), h = surface-to-air heat-transfer
coefficient (W/m²K). Same formula used for the physics cross-check against
the scene-panel model's cool-roof output (PLAN.md, "physics check").
"""

from . import config


def delta_t_from_albedo_change(
    delta_albedo: float,
    *,
    solar_irradiance_w_m2: float = config.SOLAR_IRRADIANCE_W_M2,
    heat_transfer_coeff_w_m2k: float = config.HEAT_TRANSFER_COEFF_W_M2K,
) -> float:
    """Predicted surface-temperature drop (positive number = cooling) from
    raising a surface's albedo by `delta_albedo` (0-1 scale)."""
    if delta_albedo < 0:
        raise ValueError("delta_albedo must be >= 0 — this formula only cools, never warms")
    return delta_albedo * solar_irradiance_w_m2 / heat_transfer_coeff_w_m2k


# Typical albedo increases for each formula-based intervention, used as the
# default when a real measured value isn't available yet. Illustrative —
# replace with measured values from the scene stack when they exist.
DEFAULT_DELTA_ALBEDO = {
    "cool_roof": 0.35,  # dark roof (~0.15) to reflective coating (~0.50)
    "cool_pavement": 0.25,  # asphalt (~0.10) to reflective coating (~0.35)
    "green_roof": None,  # not an albedo effect — evapotranspiration/shading instead
}
