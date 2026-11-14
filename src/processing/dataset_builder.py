"""Build leakage-safe next-state datasets from completed Ember trajectories."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path

import numpy as np

from processing.feature_builder import write_json_atomic


def _split(scenario_id: str) -> str:
    # Stable scenario-level assignment prevents time-step leakage across splits.
    value = int(hashlib.sha256(scenario_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    return "train" if value < 70 else "validation" if value < 85 else "test"


def build_next_state_dataset(manifest_paths: list[Path], output_root: str | Path) -> dict:
    output_root = Path(output_root)
    by_scenario: dict[str, list[dict]] = defaultdict(list)
    rejected = []
    for path in manifest_paths:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        valid_at = manifest.get("source_metadata", {}).get("valid_at")
        if manifest.get("status") != "complete" or not valid_at:
            rejected.append({"manifest": str(path), "reason": "requires a completed state with valid_at"})
            continue
        try:
            datetime.fromisoformat(valid_at.replace("Z", "+00:00"))
        except ValueError:
            rejected.append({"manifest": str(path), "reason": f"invalid valid_at: {valid_at}"})
            continue
        by_scenario[manifest["scenario_id"]].append(manifest)
    samples, split_scenarios = {"train": [], "validation": [], "test": []}, {"train": [], "validation": [], "test": []}
    for scenario_id, states in by_scenario.items():
        states.sort(key=lambda item: item["source_metadata"]["valid_at"])
        split = _split(scenario_id)
        split_scenarios[split].append(scenario_id)
        for current, target in zip(states, states[1:]):
            current_mask = np.load(current["artifacts"]["state_npz"], allow_pickle=False)["burned_mask"]
            target_mask = np.load(target["artifacts"]["state_npz"], allow_pickle=False)["burned_mask"]
            if current_mask.shape != target_mask.shape:
                rejected.append({"scenario_id": scenario_id, "reason": "incompatible raster shapes"})
                continue
            samples[split].append((current_mask, target_mask, current["source_metadata"]["valid_at"], target["source_metadata"]["valid_at"]))
    dataset_dir = output_root / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for split, values in samples.items():
        if not values:
            continue
        inputs = np.stack([value[0] for value in values])
        targets = np.stack([value[1] for value in values])
        location = dataset_dir / f"{split}.npz"
        np.savez_compressed(location, current_burned_mask=inputs, next_burned_mask=targets)
        written[split] = str(location)
    manifest = {
        "schema_version": "1.0", "objective": "X_t -> burned_mask_(t+delta_t)",
        "status": "complete" if written else "blocked", "reason": None if written else "No temporal pairs: extract at least two timestamped states from one scenario.",
        "feature_definitions": {"current_burned_mask": "binary rasterized front/extent at t", "next_burned_mask": "binary rasterized front/extent at t + delta_t"},
        "split_policy": "SHA-256 scenario-id assignment, never time-step-level random splitting", "split_scenarios": split_scenarios,
        "sample_counts": {name: len(values) for name, values in samples.items()}, "artifacts": written, "rejected": rejected,
    }
    write_json_atomic(dataset_dir / "dataset_manifest.json", manifest)
    return manifest
