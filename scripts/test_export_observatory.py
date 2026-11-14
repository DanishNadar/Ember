"""Offline export/integrity/privacy checks; fixtures are never training evidence."""
import base64
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nbformat
from scripts import export_observatory as exporter


class ExportTests(unittest.TestCase):
    def fixture(self, root):
        directory = root / "notebooks"; directory.mkdir()
        notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(
            "print('unit test fixture')", execution_count=1,
            outputs=[nbformat.v4.new_output("stream", name="stdout", text="Fixture completed\n")])])
        path = directory / "executed.ipynb"; nbformat.write(notebook, path)
        return path

    def test_redaction_preserves_numeric_metrics_and_image_payloads(self):
        image = "literal-base64-payload"
        value = {"iou": .758713, "token": "private-value", "image/png": image,
                 "path": r"C:\Users\example\project", "linux": "/home/example/project",
                 "text": "Bearer " + "secret" * 8 + " 192.168.1.20",
                 "pat": "ghp_" + "a" * 36, "assignment": 'api_key = "example-secret"'}
        safe = exporter.scrub(value)
        self.assertEqual(safe["iou"], value["iou"])
        self.assertEqual(safe["image/png"], image)
        self.assertNotIn("example", safe["path"])
        self.assertNotIn("192.168", safe["text"])
        self.assertEqual(safe["token"], "[REDACTED]")
        self.assertEqual(safe["pat"], "[REDACTED]")
        self.assertNotIn("example-secret", safe["assignment"])

    def test_export_normalizes_notebook_source_and_preserves_versions_and_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = self.fixture(root)
            original = exporter.sha(source)
            with patch.object(exporter, "run_metrics", return_value=[]):
                first = exporter.export(root, "fixture-experiment", notebook=source)
                second = exporter.export(root, "fixture-experiment", notebook=source)
            self.assertNotEqual(first["directory"], second["directory"])
            self.assertEqual(exporter.sha(source), original)
            report = Path(first["directory"]) / "report.html"
            self.assertIn("Fixture completed", report.read_text(encoding="utf-8"))
            self.assertNotIn("<script", report.read_text(encoding="utf-8").lower())
            nb = nbformat.read(Path(first["directory"]) / "Ember_Observatory.executed.ipynb", as_version=4)
            self.assertIsInstance(nb.cells[0].source, str)
            exporter.verify_manifest(first["manifest"], first["manifest_sha256"])
            report.write_text("changed after approval", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed"):
                exporter.verify_manifest(first["manifest"], first["manifest_sha256"])

    def test_refuses_unexecuted_notebook_and_publishing_to_main(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = self.fixture(root)
            notebook = nbformat.read(source, as_version=4)
            notebook.cells[0].outputs = []; notebook.cells[0].execution_count = None
            nbformat.write(notebook, source)
            with self.assertRaisesRegex(ValueError, "no saved execution"):
                exporter.export(root, "fixture-experiment", notebook=source)
            with self.assertRaisesRegex(ValueError, "new reports/observatory"):
                exporter.publish(root, "unused", "unused", "main")

    def test_manifest_traversal_is_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); outside = root / "outside.json"; outside.write_text("{}")
            snapshot = root / "snapshot"; snapshot.mkdir()
            manifest = snapshot / "manifest.json"
            manifest.write_text(json.dumps({"schema_version": 1, "experiment_id": "fixture", "version": "v1",
                "files": [{"path": "../outside.json", "sha256": exporter.sha(outside)}]}))
            with self.assertRaisesRegex(ValueError, "outside"):
                exporter.verify_manifest(manifest, exporter.sha(manifest))

    def test_gpu_utilization_survives_unsupported_memory_counters(self):
        module = importlib.import_module("ml.observability")
        result = type("QueryResult", (), {"returncode": 0, "stdout": "43, N/A, N/A\n"})()
        with patch.object(module.subprocess, "run", return_value=result):
            data = module.resources()
        self.assertEqual(data["gpu_utilization_percent_snapshot"], 43)
        self.assertNotIn("gpu_memory_used_mib_snapshot", data)


if __name__ == "__main__":
    unittest.main()
