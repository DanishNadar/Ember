"""Portable experiment discovery; private machine paths stay in ignored config."""
import json
import os
from pathlib import Path


def local_config(root):
    path = Path(root) / "artifacts/local/observatory.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def configured_paths(root, key, defaults):
    root = Path(root).resolve()
    values = local_config(root).get(key, defaults)
    return [(root / value).resolve() for value in values]


def experiment_roots(root):
    override = os.environ.get("EMBER_RUNS_DIR")
    if override:
        return [Path(override).expanduser().resolve()]
    return configured_paths(root, "experiment_roots",
                            ["artifacts/experiments", "orchestration/fuzzball/runs"])


def find_histories(root):
    found = {p.resolve() for base in experiment_roots(root) if base.is_dir()
             for p in base.glob("**/history.csv")}
    return sorted(found, key=lambda p: (p.parent.name, str(p)))


def notebook_roots(root):
    return configured_paths(root, "notebook_roots", ["notebooks"])
