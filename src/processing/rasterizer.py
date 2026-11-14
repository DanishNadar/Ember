"""Rasterize extracted polygon fronts to a documented common grid."""
from __future__ import annotations

import numpy as np
from matplotlib.path import Path as MatplotlibPath


def rasterize(polygons: list[list[list[list[float]]]], shape: tuple[int, int]) -> tuple[np.ndarray, dict]:
    if not polygons:
        return np.zeros(shape, dtype=np.uint8), {"bbox": None, "coordinate_units": "unknown"}
    points = [point for polygon in polygons for ring in polygon for point in ring]
    xmin, ymin = min(p[0] for p in points), min(p[1] for p in points)
    xmax, ymax = max(p[0] for p in points), max(p[1] for p in points)
    if xmin == xmax or ymin == ymax:
        raise ValueError("Cannot rasterize a zero-area bounding box")
    ys = np.linspace(ymin, ymax, shape[0], endpoint=False) + (ymax - ymin) / (2 * shape[0])
    xs = np.linspace(xmin, xmax, shape[1], endpoint=False) + (xmax - xmin) / (2 * shape[1])
    grid_x, grid_y = np.meshgrid(xs, ys)
    locations = np.column_stack((grid_x.ravel(), grid_y.ravel()))
    mask = np.zeros(len(locations), dtype=bool)
    for polygon in polygons:
        exterior = MatplotlibPath(np.asarray(polygon[0])[:, :2]).contains_points(locations, radius=1e-12)
        for hole in polygon[1:]:
            exterior &= ~MatplotlibPath(np.asarray(hole)[:, :2]).contains_points(locations, radius=1e-12)
        mask |= exterior
    return mask.reshape(shape).astype(np.uint8), {"bbox": [xmin, ymin, xmax, ymax], "coordinate_units": "source units"}
