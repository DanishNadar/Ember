"""Dependency-light geometry measurements for polygonal fire fronts."""
from __future__ import annotations

from typing import Iterable


def _closed(ring: list[list[float]]) -> list[list[float]]:
    if len(ring) < 3:
        return ring
    return ring if ring[0][:2] == ring[-1][:2] else [*ring, ring[0]]


def ring_area(ring: list[list[float]]) -> float:
    """Return unsigned shoelace area in the source coordinate system squared."""
    points = _closed(ring)
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:]))) / 2


def ring_perimeter(ring: list[list[float]]) -> float:
    """Return perimeter in source coordinate units (not automatically metres)."""
    points = _closed(ring)
    return sum(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for a, b in zip(points, points[1:]))


def polygon_area(coordinates: list[list[list[float]]]) -> float:
    if not coordinates:
        return 0.0
    return max(0.0, ring_area(coordinates[0]) - sum(ring_area(hole) for hole in coordinates[1:]))


def polygon_perimeter(coordinates: list[list[list[float]]]) -> float:
    return sum(ring_perimeter(ring) for ring in coordinates)


def geometry_metrics(polygons: Iterable[list[list[list[float]]]]) -> dict[str, float | int | None]:
    polygons = list(polygons)
    points = [point for polygon in polygons for ring in polygon for point in ring]
    if not points:
        return {"polygon_count": 0, "vertex_count": 0, "area_coordinate_squared": 0.0,
                "perimeter_coordinate_units": 0.0, "bbox": None}
    xs, ys = zip(*((float(point[0]), float(point[1])) for point in points))
    return {
        "polygon_count": len(polygons),
        "vertex_count": len(points),
        "area_coordinate_squared": sum(polygon_area(polygon) for polygon in polygons),
        "perimeter_coordinate_units": sum(polygon_perimeter(polygon) for polygon in polygons),
        "bbox": [min(xs), min(ys), max(xs), max(ys)],
    }
