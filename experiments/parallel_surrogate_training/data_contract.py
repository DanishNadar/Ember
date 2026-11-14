"""Completed-shard contract. NumPy-only validation; never runs a simulator."""
import hashlib
import json
from pathlib import Path
import numpy as np


def read_config(path):
    path = Path(path).resolve()
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["data_dir"] = str((path.parent / cfg["data_dir"]).resolve())
    if cfg["grid_size"] % 2 ** cfg["depth"]:
        raise ValueError("Grid must be divisible by 2**depth")
    if len(set(cfg["channel_names"])) != len(cfg["channel_names"]):
        raise ValueError("Channel names must be unique")
    if not set(cfg["binary_channels"]) <= set(cfg["channel_names"]):
        raise ValueError("Unknown binary channels")
    if cfg["dataset_kind"] not in ("forefire", "synthetic_mock"):
        raise ValueError("Unknown dataset provenance")
    for key in ("grid_size", "horizon_seconds", "cell_size_meters", "epochs", "batch_size", "base_filters", "depth", "learning_rate", "cpu_threads"):
        if not np.isfinite(cfg[key]) or cfg[key] <= 0:
            raise ValueError(f"{key} must be positive and finite")
    if not 0 < cfg["threshold"] < 1 or cfg["arrival_weight"] < 0 or cfg["dice_weight"] < 0:
        raise ValueError("Invalid threshold or loss weights")
    return cfg


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sample(path, cfg):
    with np.load(path, allow_pickle=False) as z:
        required = {"x", "arrival_time_seconds", "valid_mask", "reached_mask", "metadata_json"}
        if required - set(z.files):
            raise ValueError(f"{path}: missing {required - set(z.files)}")
        x, arrival, valid, reached = (z[k] for k in ("x", "arrival_time_seconds", "valid_mask", "reached_mask"))
        meta = json.loads(str(z["metadata_json"].item()))
    n = cfg["grid_size"]
    if x.shape != (len(cfg["channel_names"]), n, n) or x.dtype != np.float32 or not np.isfinite(x).all():
        raise ValueError(f"{path}: invalid input tensor")
    if arrival.shape != (n, n) or arrival.dtype != np.float32:
        raise ValueError(f"{path}: arrival must be float32 [H,W] in seconds")
    for a in (valid, reached):
        if a.shape != (n, n) or not np.isin(a, [0, 1]).all():
            raise ValueError(f"{path}: invalid binary masks")
    valid, reached = valid.astype(bool), reached.astype(bool)
    if not valid.any() or np.any(reached & ~valid):
        raise ValueError(f"{path}: invalid valid/reached relationship")
    if not np.isfinite(arrival[reached]).all() or np.any(arrival[reached] < 0) or np.any(arrival[reached] > cfg["horizon_seconds"]):
        raise ValueError(f"{path}: reached arrival outside horizon")
    if np.any(arrival[~reached] != -9999):
        raise ValueError(f"{path}: unreached/invalid cells must use -9999; masks distinguish them")
    for key in ("sample_id", "simulation_id", "scenario_family_id", "region", "engine_version"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise ValueError(f"{path}: missing {key}")
    expected = {"channel_names": cfg["channel_names"], "dataset_kind": cfg["dataset_kind"],
                "horizon_seconds": cfg["horizon_seconds"], "cell_size_meters": cfg["cell_size_meters"],
                "array_order": "CXY", "arrival_units": "seconds"}
    for key, value in expected.items():
        if meta.get(key) != value:
            raise ValueError(f"{path}: {key} mismatch")
    if meta.get("edge_hit") is not False:
        raise ValueError(f"{path}: edge_hit must be explicitly false")
    for name in cfg["binary_channels"]:
        if not np.isin(x[cfg["channel_names"].index(name)], [0, 1]).all():
            raise ValueError(f"{path}: {name} must be binary")
    if not x[cfg["channel_names"].index("ignition")].any():
        raise ValueError(f"{path}: empty ignition")
    return x, arrival, valid, reached, meta


def snapshot(cfg):
    """Only manifests published last are visible. Freeze paths AND hashes per round."""
    root = Path(cfg["data_dir"]).resolve()
    parts = {k: [] for k in ("train", "val", "test")}
    identities = {k: {} for k in ("sample_id", "simulation_id", "scenario_family_id")}
    seen_paths = set()
    for manifest in sorted(root.glob("*/complete.json")):
        m = json.loads(manifest.read_text(encoding="utf-8"))
        if m.get("status") != "complete":
            continue
        for entry in m["samples"]:
            split = entry["split"]
            if split not in parts:
                raise ValueError(f"Unknown split {split}; map OOD to a SEPARATE test experiment")
            path = (manifest.parent / entry["file"]).resolve()
            if not path.is_relative_to(manifest.parent.resolve()) or str(path) in seen_paths:
                raise ValueError("Unsafe or duplicate sample path")
            seen_paths.add(str(path))
            if digest(path) != entry["sha256"]:
                raise ValueError(f"{path}: hash mismatch")
            _, _, _, _, meta = sample(path, cfg)
            for key, owners in identities.items():
                identity = meta[key]
                if identity in owners and (key == "sample_id" or owners[identity] != split):
                    raise ValueError(f"Duplicate sample or split leakage: {key}={identity}")
                owners[identity] = split
            parts[split].append({"path": str(path), "sha256": entry["sha256"], "metadata": meta})
    if any(not paths for paths in parts.values()):
        raise ValueError("Need completed, nonempty train/val/test sets")
    return parts


def normalization(records, cfg):
    count = 0
    mean = np.zeros(len(cfg["channel_names"]), np.float64)
    m2 = mean.copy()
    for record in records:
        x, _, valid, _, _ = sample(record["path"], cfg)
        values = x[:, valid].astype(np.float64)
        n = values.shape[1]
        local = values.mean(1)
        delta = local - mean
        m2 += ((values - local[:, None]) ** 2).sum(1) + delta**2 * count * n / (count + n)
        mean += delta * n / (count + n)
        count += n
    std = np.sqrt(m2 / count)
    std[std < 1e-8] = 1
    for name in cfg["binary_channels"]:
        i = cfg["channel_names"].index(name)
        mean[i], std[i] = 0, 1
    return {"mean": mean.tolist(), "std": std.tolist(), "fit_split": "train"}


def verify_frozen(parts, cfg):
    """Revalidate a saved snapshot, independently of current shard discovery."""
    if set(parts) != {"train", "val", "test"} or any(not v for v in parts.values()):
        raise ValueError("Snapshot needs nonempty train/val/test")
    owners = {k: {} for k in ("sample_id", "simulation_id", "scenario_family_id")}
    for split, records in parts.items():
        for record in records:
            if digest(record["path"]) != record["sha256"]:
                raise ValueError("Frozen snapshot file hash changed")
            *_, meta = sample(record["path"], cfg)
            if meta != record["metadata"]:
                raise ValueError("Frozen metadata mismatch")
            for key, seen in owners.items():
                value = meta[key]
                if value in seen and (key == "sample_id" or seen[value] != split):
                    raise ValueError(f"Frozen snapshot leakage: {key}")
                seen[value] = split
    return parts


def inference_sample(path, cfg):
    """Unlabeled input contract; target arrays are neither required nor read."""
    with np.load(path, allow_pickle=False) as z:
        x, valid = z["x"], z["valid_mask"]
        meta = json.loads(str(z["metadata_json"].item()))
    n = cfg["grid_size"]
    if x.dtype != np.float32 or x.shape != (len(cfg["channel_names"]), n, n) or not np.isfinite(x).all():
        raise ValueError("Invalid inference inputs")
    if valid.shape != (n, n) or not np.isin(valid, [0, 1]).all() or not valid.any():
        raise ValueError("Invalid inference valid_mask")
    expected = {"channel_names": cfg["channel_names"], "dataset_kind": cfg["dataset_kind"],
                "horizon_seconds": cfg["horizon_seconds"], "cell_size_meters": cfg["cell_size_meters"],
                "array_order": "CXY", "arrival_units": "seconds"}
    for key, value in expected.items():
        if meta.get(key) != value:
            raise ValueError(f"Inference {key} mismatch")
    for key in ("sample_id", "region", "engine_version"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise ValueError(f"Missing inference {key}")
    for name in cfg["binary_channels"]:
        if not np.isin(x[cfg["channel_names"].index(name)], [0, 1]).all():
            raise ValueError(f"Nonbinary inference channel {name}")
    return x, valid.astype(bool), meta
