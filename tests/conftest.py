import pytest

from uhi import demo_data, exposure, model, optimize
from uhi.features import add_focal_features
from uhi.scenarios import Engine


@pytest.fixture(scope="session")
def world():
    """Small end-to-end world on DEMO data (fewer boosting rounds to keep CI fast)."""
    d = demo_data.build()
    cells = d["cells"]
    panel = model.build_panel(add_focal_features(cells), d["scenes"], d["scenes_meta"])
    fitted = model.fit(panel, rounds=60)
    ward, _ = exposure.assign_wards(cells, None)
    cells = cells.assign(ward_id=ward.to_numpy())
    cells = exposure.heat_stress(cells, exposure.composite_anomaly(d["scenes"], cells),
                                 exposure.season_heat_index(d["scenes_meta"]))
    engine = Engine(fitted, cells, model.typical_atmos(d["scenes_meta"]))
    cand = optimize.all_candidates(engine)
    return {"data": d, "model": fitted, "engine": engine, "cand": cand, "panel": panel}
