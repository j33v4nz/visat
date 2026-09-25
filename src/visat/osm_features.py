"""OpenStreetMap features on the 100 m grid → data/frozen/osm.parquet (M1, after gee_export).

    uv run python -m visat.osm_features

road_frac (public land for street trees / cool pavements), schools, markets, hospitals,
construction sites, harbours, parks, and canal-bank cells (for canal-bank tree strips).
"""

import numpy as np
import pandas as pd
from scipy.ndimage import binary_dilation

from visat import config

ROAD_WIDTH_M = 8.0
SITE_TAGS = {
    "n_school": {"amenity": ["school", "kindergarten", "college"]},
    "n_market": {"amenity": ["marketplace"]},
    "n_hospital": {"amenity": ["hospital", "clinic"]},
    "n_construction": {"landuse": ["construction"]},
    "n_harbour": {"landuse": ["harbour", "port"], "harbour": True, "industrial": ["port"]},
    "is_park": {"leisure": ["park", "garden", "playground"]},
}


def _bin(lat, lon, shape):
    lon0, _, _, lat1 = config.BBOX
    r = ((lat1 - np.asarray(lat)) / config.CELL_DEG).astype(int)
    c = ((np.asarray(lon) - lon0) / config.CELL_DEG).astype(int)
    ok = (r >= 0) & (r < shape[0]) & (c >= 0) & (c < shape[1])
    return r[ok], c[ok]


def _points_along(gdf, step_m=10.0):
    proj = gdf.to_crs(32643)  # UTM 43N covers Kochi
    pts = []
    for geom in proj.geometry:
        if geom is None or geom.length == 0:
            continue
        d = np.arange(0, geom.length, step_m)
        pts += [geom.interpolate(x) for x in d]
    import geopandas as gpd

    return gpd.GeoSeries(pts, crs=32643).to_crs(4326)


def run():
    import osmnx as ox
    from osmnx._errors import InsufficientResponseError

    from visat.gee_export import grid_shape

    shape = grid_shape()
    lon0, lat0, lon1, lat1 = config.BBOX
    bbox = (lon0, lat0, lon1, lat1)  # osmnx 2.x: (left, bottom, right, top)
    out = {}

    roads = ox.features_from_bbox(bbox, {"highway": True})
    roads = roads[roads.geom_type.isin(["LineString", "MultiLineString"])]
    pts = _points_along(roads.explode(index_parts=False))
    r, c = _bin(pts.y, pts.x, shape)
    length = np.zeros(shape)
    np.add.at(length, (r, c), 10.0)
    out["road_frac"] = np.clip(length * ROAD_WIDTH_M / config.GRID_RESOLUTION_M**2, 0, 0.4)
    print(f"roads: {len(roads)} ways")

    for col, tags in SITE_TAGS.items():
        grid = np.zeros(shape)
        try:
            g = ox.features_from_bbox(bbox, tags)
            cen = g.to_crs(32643).centroid.to_crs(4326)
            r, c = _bin(cen.y, cen.x, shape)
            np.add.at(grid, (r, c), 1)
        except InsufficientResponseError as e:  # no results for this tag
            print(f"{col}: none found ({type(e).__name__})")
        out[col] = (grid > 0).astype(int) if col == "is_park" else grid.astype(int)
        print(f"{col}: {int(grid.sum())}")

    canal = np.zeros(shape, bool)
    try:
        w = ox.features_from_bbox(bbox, {"waterway": ["canal", "drain", "ditch"]})
        pts = _points_along(w[w.geom_type.isin(["LineString", "MultiLineString"])].explode(index_parts=False))
        r, c = _bin(pts.y, pts.x, shape)
        canal[r, c] = True
    except InsufficientResponseError as e:
        print(f"canals: none found ({type(e).__name__})")
    out["canal_bank"] = binary_dilation(canal, iterations=1).astype(int)

    df = pd.DataFrame({k: v.ravel() for k, v in out.items()})
    df.insert(0, "cell_id", np.arange(len(df)))
    config.FROZEN.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.FROZEN / "osm.parquet", index=False)
    print("saved data/frozen/osm.parquet — next: python -m visat.pipeline --source frozen")


if __name__ == "__main__":
    run()
