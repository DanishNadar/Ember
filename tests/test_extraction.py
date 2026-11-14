from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from processing.geometry_processor import geometry_metrics
from simulation.state_extractor import extract_state


class ExtractionTests(unittest.TestCase):
    def test_geometry_metrics_for_unit_square(self) -> None:
        metrics = geometry_metrics([[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]])
        self.assertEqual(metrics["area_coordinate_squared"], 1.0)
        self.assertEqual(metrics["perimeter_coordinate_units"], 4.0)

    def test_geojson_extraction_is_resume_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "front.geojson"
            source.write_text(json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}}]}), encoding="utf-8")
            manifest = extract_state(source, root / "output", "unit", (16, 16))
            self.assertEqual(manifest["status"], "complete")
            self.assertEqual(manifest["validation"]["burned_cells"], 256)
            resumed = extract_state(source, root / "output", "unit", (16, 16), resume=True)
            self.assertTrue(resumed["resumed"])


if __name__ == "__main__":
    unittest.main()
