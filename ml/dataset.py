"""Strict numeric NPZ contract, simulation/family split auditing, train-only scaling."""
from pathlib import Path
from zipfile import BadZipFile
import numpy as np
import torch
from torch.utils.data import Dataset


def read_sample(path, cfg, require_target=True):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"{path}: sample file is missing; export numeric NPZ arrays, not PNGs")
    try:
        with np.load(path, allow_pickle=False) as data:
            arrays = {key: data[key] for key in data.files}
    except (ValueError, OSError, EOFError, BadZipFile, TypeError) as exc:
        raise ValueError(f"{path}: unreadable NPZ (use numeric arrays and Unicode metadata; no pickled objects): {exc}") from exc
    for key in ("x", "channel_names") + (("y",) if require_target else ()):
        if key not in arrays:
            raise ValueError(f"{path}: missing '{key}'; expected x float32 [C,H,W], y float32 [1,H,W] and channel_names")
    expected = (len(cfg["channel_names"]), cfg["image_size"], cfg["image_size"])
    x = arrays["x"]
    if x.shape != expected or x.dtype != np.float32:
        raise ValueError(f"{path}: x must be float32 {expected}, got {x.dtype} {x.shape}; resample on the export side")
    channels = arrays["channel_names"]
    if channels.ndim != 1 or channels.dtype.kind != "U" or channels.tolist() != cfg["channel_names"]:
        raise ValueError(f"{path}: channel_names/order must exactly equal {cfg['channel_names']}; got {channels.tolist()}")
    if not np.isfinite(x).all():
        raise ValueError(f"{path}: x contains NaN/inf; resolve missing environmental data before export")
    for i, kind in enumerate(cfg["channel_types"]):
        if kind == "binary" and not np.isin(x[i], [0, 1]).all():
            raise ValueError(f"{path}: binary channel {cfg['channel_names'][i]} must contain only 0 or 1")
    y = arrays.get("y")
    if y is not None:
        if y.dtype != np.float32 or y.shape != (1, *expected[1:]):
            raise ValueError(f"{path}: y must be float32 {(1, *expected[1:])}, got {y.dtype} {y.shape}")
        if not np.isfinite(y).all() or not np.isin(y, [0, 1]).all():
            raise ValueError(f"{path}: y must be a finite binary mask (exactly 0 or 1)")
        burn = x[cfg["channel_names"].index(cfg["current_burn_channel"])]
        if np.any(y[0] < burn):
            raise ValueError(f"{path}: cumulative target y loses previously burned pixels; check time ordering/alignment")
    metadata = {}
    for key, value in arrays.items():
        if key in ("x", "y", "channel_names"):
            continue
        if value.ndim != 0 or value.dtype.kind not in "Uifb":
            raise ValueError(f"{path}: metadata '{key}' must be a scalar string or number")
        metadata[key] = value.item()
    metadata["channel_names"] = channels.tolist()
    for key in ("time_t_seconds", "forecast_horizon_seconds", "cell_size_meters"):
        if key in metadata:
            value = metadata[key]
            if type(value) not in (int, float) or not np.isfinite(value) or value < 0 or (key != "time_t_seconds" and value == 0):
                raise ValueError(f"{path}: {key} must be a finite {'nonnegative' if key == 'time_t_seconds' else 'positive'} number")
    if "forecast_horizon_seconds" in metadata and metadata["forecast_horizon_seconds"] != cfg["forecast_horizon_seconds"]:
        raise ValueError(f"{path}: forecast horizon differs from config ({cfg['forecast_horizon_seconds']} seconds)")
    if "dataset_kind" in metadata and metadata["dataset_kind"] != cfg["dataset_kind"]:
        raise ValueError(f"{path}: dataset_kind conflicts with config; never mix synthetic_mock and ForeFire results")
    return x, y, metadata


def audit_splits(cfg):
    """Always audit all three directories, including test, before fitting anything."""
    root = Path(cfg["data_dir"])
    splits, metadata = {}, {}
    owners = {"simulation_id": {}, cfg["split_group_key"]: {}}
    for split in ("train", "val", "test"):
        files = sorted((root / split).glob("*.npz"))
        if not files:
            raise ValueError(f"{root / split}: no *.npz samples; create train/, val/, test/ grouped by entire scenario family")
        splits[split] = files
        for path in files:
            _, _, meta = read_sample(path, cfg)
            for key in ("simulation_id", cfg["split_group_key"], "dataset_kind"):
                if not isinstance(meta.get(key), str) or not meta[key].strip():
                    raise ValueError(f"{path}: '{key}' string metadata is required for split/provenance auditing")
            for key, seen in owners.items():
                group = meta[key]
                if group in seen and seen[group] != split:
                    raise ValueError(f"Temporal/scenario leakage: {key}={group!r} appears in both {seen[group]} and {split}")
                seen[group] = split
            metadata[str(path)] = meta
    return splits, metadata


def fit_normalization(paths, cfg):
    """Stable, pixel-weighted population moments; no validation/test pixels are used."""
    count = 0
    means = np.zeros(len(cfg["channel_names"]), dtype=np.float64)
    m2 = np.zeros_like(means)
    for path in paths:
        x, _, _ = read_sample(path, cfg)
        flat = x.astype(np.float64).reshape(len(means), -1)
        n = flat.shape[1]
        local_mean = flat.mean(axis=1)
        local_m2 = ((flat - local_mean[:, None]) ** 2).sum(axis=1)
        delta = local_mean - means
        m2 += local_m2 + delta ** 2 * count * n / (count + n)
        means += delta * n / (count + n)
        count += n
    if not count:
        raise ValueError("Cannot normalize an empty training split")
    stds = np.sqrt(m2 / count)
    for i, kind in enumerate(cfg["channel_types"]):
        if kind == "binary":
            means[i], stds[i] = 0, 1
        elif stds[i] == 0:
            stds[i] = 1  # Constant channels are centered with unit scale; no arbitrary epsilon.
    return {"version": 1, "fit_split": "train", "channel_names": cfg["channel_names"],
            "channel_types": cfg["channel_types"], "mean": means.tolist(), "std": stds.tolist(),
            "training_samples": len(paths), "pixels_per_channel": count}


def validate_normalization(norm, cfg):
    if (norm.get("version") != 1 or norm.get("fit_split") != "train" or
            norm.get("channel_names") != cfg["channel_names"] or norm.get("channel_types") != cfg["channel_types"]):
        raise ValueError("normalization.json has incompatible channel definitions or was not fit on train")
    mean, std = np.asarray(norm["mean"]), np.asarray(norm["std"])
    if mean.shape != (len(cfg["channel_names"]),) or std.shape != mean.shape or not np.isfinite(mean).all() or not np.isfinite(std).all() or np.any(std <= 0):
        raise ValueError("normalization.json must contain finite means and positive standard deviations")
    for i, kind in enumerate(cfg["channel_types"]):
        if kind == "binary" and (mean[i] != 0 or std[i] != 1):
            raise ValueError("Binary masks must not be normalized")


def normalize(x, norm):
    result = (x.astype(np.float64) - np.asarray(norm["mean"])[:, None, None]) / np.asarray(norm["std"])[:, None, None]
    result = result.astype(np.float32)
    if not np.isfinite(result).all():
        raise ValueError("Normalization produced NaN/inf; check input scale and training statistics")
    return result


class BurnDataset(Dataset):
    def __init__(self, paths, cfg, normalization):
        self.paths, self.cfg, self.normalization = paths, cfg, normalization
        validate_normalization(normalization, cfg)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        x, y, _ = read_sample(self.paths[index], self.cfg)
        return torch.from_numpy(normalize(x, self.normalization)), torch.from_numpy(y)
