"""What-if engine: validity matrix, analog transitions, energy-balance formulas, joint re-prediction.

Honesty rules enforced here:
- analog fixes only move a cell toward REAL Kochi cells that already look like the fix (k=20 donors),
  never beyond the observed range (1st–99th percentile), and only in the cooling direction;
- fixes with no data analog (cool roofs, cool pavements, green roofs) use a labelled
  energy-balance formula, with no spillover credit;
- every reported ΔT comes from ONE joint re-prediction of all changed cells together.
"""

import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter
from sklearn.neighbors import NearestNeighbors

from visat import config
from visat.features import add_focal_features
from visat.model import predict, with_atmos

FOCAL_BASES = ("tree_frac", "water_frac")


def eligible(cells: pd.DataFrame, key: str) -> pd.Series:
    c = cells
    land = c["water_frac"] < 0.3
    if key == "street_trees":
        public = (c["road_frac"] > 0.05) | (c["is_park"] > 0) | (c["n_school"] > 0)
        return land & public & (c["built_frac"] > 0.05) & (c["tree_frac"] < 0.6)
    if key == "canal_bank_trees":
        return land & (c["canal_bank"] > 0) & (c["tree_frac"] < 0.6)
    if key == "mangroves":  # CRZ / shoreline proxy: next to water, low-lying, not built
        return ((c["dist_water_m"] <= 200) & (c["elevation"] < 3) & (c["built_frac"] < 0.2)
                & (c["water_frac"] < 0.5) & (c["mangrove_frac"] < 0.5))
    if key == "pond":
        return (land & (c["elevation"] < 3) & (c["built_frac"] < 0.2)
                & (c["grass_bare_frac"] > 0.3) & (c["dist_water_m"] > 100))
    if key in ("cool_roofs", "green_roofs"):
        return c["building_frac"] > 0.1
    if key == "cool_pavements":
        return c["road_frac"] > 0.05
    raise KeyError(key)


def donors(cells: pd.DataFrame, key: str) -> pd.Series:
    c = cells
    if key in ("street_trees", "canal_bank_trees"):
        m = (c["tree_frac"] >= 0.5) & c["built_frac"].between(0.1, 0.6)
        return m if m.sum() >= 50 else (c["tree_frac"] >= 0.5) & (c["water_frac"] < 0.3)
    if key == "mangroves":
        return c["mangrove_frac"] >= 0.3
    if key == "pond":
        return (c["water_frac"] >= 0.7) & (c["dist_water_m"] == 0)
    raise KeyError(key)


class Engine:
    def __init__(self, model, cells: pd.DataFrame, atmos: dict):
        self.model = model
        self.atmos = atmos
        self.cells = add_focal_features(cells.sort_values("cell_id").reset_index(drop=True))
        self.shape = (int(self.cells["row"].max()) + 1, int(self.cells["col"].max()) + 1)
        self.base = predict(model, with_atmos(self.cells, atmos))
        land = self.cells[self.cells["water_frac"] <= 0.5]
        lo, hi = config.SUPPORT_QUANTILES
        self.support = {f: (float(land[f].quantile(lo)), float(land[f].quantile(hi)))
                        for f in config.LC_FEATURES}
        self._sens = None

    # ------------------------------------------------------------ transitions
    def _knn_target(self, idx: np.ndarray, donor_mask: pd.Series) -> pd.DataFrame:
        ctx = config.CONTEXT_FEATURES
        pool = self.cells.loc[donor_mask, ctx + config.LC_FEATURES]
        scale = self.cells[ctx].std().replace(0, 1)
        k = min(config.KNN_DONORS, len(pool))
        nn = NearestNeighbors(n_neighbors=k).fit(pool[ctx] / scale)
        _, nbr = nn.kneighbors(self.cells.loc[idx, ctx] / scale)
        vals = pool[config.LC_FEATURES].to_numpy()[nbr]  # (n, k, f)
        return pd.DataFrame(np.median(vals, axis=1), columns=config.LC_FEATURES, index=idx)

    def _clip(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
        inside = np.ones(len(frame), bool)
        for f, (lo, hi) in self.support.items():
            v = frame[f].to_numpy()
            inside &= (v >= lo - 1e-9) & (v <= hi + 1e-9)
            frame[f] = np.clip(v, lo, hi)
        return frame, inside

    def analog_transition(self, idx: np.ndarray, key: str, intensity: float | None = None,
                          cooling_only: bool = True, target=None):
        """New land-cover values for cells `idx`, moved toward context-matched real donors."""
        intensity = config.INTERVENTIONS.get(key, {}).get("intensity", 1.0) if intensity is None else intensity
        cur = self.cells.loc[idx, config.LC_FEATURES]
        tgt = self._knn_target(idx, donors(self.cells, key)) if target is None else target
        new = cur + intensity * (tgt - cur)
        if cooling_only:  # only move each feature in its cooling direction
            for f in config.LC_FEATURES:
                sign = config.FEATURES.get(f, 0)
                if sign < 0:
                    new[f] = np.maximum(new[f], cur[f])
                elif sign > 0:
                    new[f] = np.minimum(new[f], cur[f])
                else:
                    new[f] = cur[f]
        water = new["water_frac"]
        new["tree_frac"] = np.minimum(new["tree_frac"], 1 - water)
        new["mangrove_frac"] = np.minimum(new["mangrove_frac"], 1 - water)
        return self._clip(new)

    # ------------------------------------------------------------ formulas (no data analog)
    def formula_delta(self, idx: np.ndarray, key: str, building_frac=None) -> tuple[np.ndarray, np.ndarray]:
        spec = config.INTERVENTIONS[key]
        c = self.cells.loc[idx]
        bf = c["building_frac"].to_numpy() if building_frac is None else np.asarray(building_frac)
        if key == "cool_roofs":
            area_frac = bf * spec["coverage"]
            dt = -spec["delta_albedo"] * config.SOLAR_SHORTWAVE_WM2 / config.HEAT_LOSS_WM2K * area_frac
        elif key == "cool_pavements":
            area_frac = c["road_frac"].to_numpy() * spec["coverage"]
            dt = -spec["delta_albedo"] * config.SOLAR_SHORTWAVE_WM2 / config.HEAT_LOSS_WM2K * area_frac
        elif key == "green_roofs":
            area_frac = bf * spec["coverage"]
            dt = -spec["surface_cooling_k"] * area_frac
        else:
            raise KeyError(key)
        cost = area_frac * config.GRID_RESOLUTION_M**2 * spec["cost_per_m2"]
        return dt, cost

    # ------------------------------------------------------------ joint re-prediction
    def joint(self, changes: dict[int, pd.Series] | None = None, formula_dt: pd.Series | None = None,
              overrides: pd.DataFrame | None = None) -> np.ndarray:
        """ΔT (°C) for EVERY cell after applying all changes together (focal features recomputed)."""
        frame = self.cells.copy()
        if overrides is not None and len(overrides):
            frame.loc[overrides.index, overrides.columns] = overrides.to_numpy()
        frame = add_focal_features(frame)
        dt = predict(self.model, with_atmos(frame, self.atmos)) - self.base
        if formula_dt is not None and len(formula_dt):
            dt[formula_dt.index.to_numpy()] += formula_dt.to_numpy()
        return dt

    # ------------------------------------------------------------ fast per-candidate estimates
    def _sensitivity(self):
        """d(LST)/d(neighbourhood fraction) per cell, for linear spillover estimates."""
        if self._sens is None:
            frame = with_atmos(self.cells, self.atmos)
            sens = {}
            for base in FOCAL_BASES:
                for tag in config.FOCAL_SIZES:
                    bumped = frame.copy()
                    bumped[f"{base}_{tag}"] += 0.1
                    sens[(base, tag)] = (predict(self.model, bumped) - self.base) / 0.1
            self._sens = sens
        return self._sens

    def _spill(self, idx: np.ndarray, deltas: pd.DataFrame, weights: np.ndarray) -> np.ndarray:
        rows, cols = self.cells.loc[idx, "row"].to_numpy(), self.cells.loc[idx, "col"].to_numpy()
        total = np.zeros(len(idx))
        for (base, tag), s in self._sensitivity().items():
            size = config.FOCAL_SIZES[tag]
            sw = (s * weights).reshape(self.shape)
            box = uniform_filter(sw, size=size, mode="constant") * size**2  # sum over window
            own = sw[rows, cols]
            total += deltas[base].to_numpy() / size**2 * (box[rows, cols] - own)
        return total

    def candidates(self, key: str, weights: np.ndarray | None = None) -> pd.DataFrame:
        """One row per eligible cell: cost (₹), own ΔT, estimated person-°C cooling benefit."""
        spec = config.INTERVENTIONS[key]
        weights = self.cells["pop"].to_numpy() if weights is None else weights
        idx = self.cells.index[eligible(self.cells, key)].to_numpy()
        if len(idx) == 0:
            return pd.DataFrame()
        out = pd.DataFrame({"cell_id": self.cells.loc[idx, "cell_id"].to_numpy(), "intervention": key,
                            "method": spec["method"]}, index=idx)
        if spec["method"] == "formula":
            dt, cost = self.formula_delta(idx, key)
            out["own_dt"], out["cost"], out["within_support"] = dt, cost, True
            out["benefit"] = -dt * weights[idx]
            return out[out["cost"] > 0]
        new, inside = self.analog_transition(idx, key)
        delta = new - self.cells.loc[idx, config.LC_FEATURES]
        frame = with_atmos(self.cells.loc[idx], self.atmos)
        frame[config.LC_FEATURES] = new
        for base in FOCAL_BASES:  # the cell's own neighbourhood features include itself
            for tag, size in config.FOCAL_SIZES.items():
                frame[f"{base}_{tag}"] += delta[base] / size**2
        frame = with_atmos(frame, self.atmos)
        own = predict(self.model, frame) - self.base[idx]
        spill = self._spill(idx, delta, weights)
        out["own_dt"], out["cost"], out["within_support"] = own, spec["cost_per_cell"], inside
        out["benefit"] = -(own * weights[idx] + spill)
        out["new_lc"] = [row for row in new.to_dict("records")]
        return out[out["benefit"] > 0]

    def evaluate(self, selection: pd.DataFrame) -> dict:
        """Joint evaluation of a set of chosen fixes (one per cell)."""
        overrides, formula = [], []
        for key, grp in selection.groupby("intervention"):
            idx = grp.index.to_numpy()
            if config.INTERVENTIONS[key]["method"] == "formula":
                dt, _ = self.formula_delta(idx, key)
                formula.append(pd.Series(dt, index=idx))
            else:
                overrides.append(pd.DataFrame(list(grp["new_lc"]), index=idx))
        ov = pd.concat(overrides) if overrides else None
        fd = pd.concat(formula).groupby(level=0).sum() if formula else None
        dt = self.joint(overrides=ov, formula_dt=fd)
        pop = self.cells["pop"].to_numpy()
        cooled = dt <= -0.1
        person_deg = float((dt * pop).sum())
        people = float(pop[cooled].sum())
        return {"dt": dt, "person_deg": person_deg, "people_cooled": people,
                "mean_dt_cooled": float(np.average(dt[cooled], weights=pop[cooled])) if people else 0.0,
                "cost": float(selection["cost"].sum()), "n_cells": len(selection)}


def validity_matrix(engine: Engine) -> list[dict]:
    rows = []
    for key, spec in config.INTERVENTIONS.items():
        cand = engine.candidates(key)
        n_elig = int(eligible(engine.cells, key).sum())
        support = float(cand["within_support"].mean() * 100) if len(cand) else None
        rows.append({
            "intervention": spec["label"], "ps1_category": spec["ps1"],
            "method": "Analog (real Kochi cells)" if spec["method"] == "analog"
            else "Energy-balance formula (labelled)",
            "eligible_cells": n_elig,
            "median_dt_c": round(float(cand["own_dt"].median()), 2) if len(cand) else None,
            "within_support_pct": None if support is None else round(support, 1),
            "cost_note": spec["cost_note"],
        })
    rows.append({"intervention": "IURWTS canals (KMRL)", "ps1_category": "Water bodies",
                 "method": "Committed overlay — 0 °C credit", "eligible_cells": None,
                 "median_dt_c": 0.0, "within_support_pct": None,
                 "cost_note": config.CANAL_CREDIT_NOTE})
    return rows
