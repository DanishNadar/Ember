"""Numeric arrival-time NPZ loader with split and geospatial-contract checks."""
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset


def load_pair(path, cfg):
    with np.load(path, allow_pickle=False) as z:
        required = {"x", "arrival_time_seconds", "channel_names", "simulation_id", "scenario_family_id",
                    "horizon_seconds", "cell_size_meters", "dataset_kind"}
        missing = required - set(z.files)
        if missing:
            raise ValueError(f"{path}: missing {sorted(missing)}")
        x = z["x"]
        arrival = z["arrival_time_seconds"]
        names = z["channel_names"].tolist()
        metadata = {k: z[k].item() for k in (
            "simulation_id", "scenario_family_id", "horizon_seconds",
            "cell_size_meters", "dataset_kind")}
    n = cfg["grid_size"]
    if x.dtype != np.float32 or x.shape != (len(cfg["channel_names"]), n, n):
        raise ValueError(f"{path}: x must be float32 [C,{n},{n}] in configured channel order")
    if arrival.dtype != np.float32 or arrival.shape not in ((n, n), (1, n, n)):
        raise ValueError(f"{path}: arrival_time_seconds must be float32 [{n},{n}]")
    arrival = arrival.reshape(n, n)
    if names != cfg["channel_names"] or not np.isfinite(x).all():
        raise ValueError(f"{path}: wrong channel_names/order or nonfinite x")
    if metadata["dataset_kind"] != "forefire":
        raise ValueError(f"{path}: real training must use dataset_kind='forefire' (mock excluded)")
    if any(not isinstance(metadata[k], str) or not metadata[k].strip() for k in
           ("simulation_id", "scenario_family_id")):
        raise ValueError(f"{path}: missing stable simulation and family IDs")
    if float(metadata["horizon_seconds"]) != cfg["horizon_seconds"]:
        raise ValueError(f"{path}: horizon mismatch with config")
    if float(metadata["cell_size_meters"]) <= 0:
        raise ValueError(f"{path}: cell_size_meters must be positive")
    for i, kind in enumerate(cfg["channel_types"]):
        if kind == "binary" and not np.isin(x[i], [0, 1]).all():
            raise ValueError(f"{path}: invalid binary channel {names[i]}")
    sentinel = cfg["unreached_sentinel"]
    unreached = arrival == sentinel
    valid = np.isfinite(arrival) & (arrival >= 0) & (arrival <= cfg["horizon_seconds"])
    if not np.all(unreached | valid):
        raise ValueError(f"{path}: arrival time outside [0,horizon] without configured sentinel")
    reached = valid.astype(np.float32)
    normalized = np.where(valid, arrival / cfg["horizon_seconds"], 0).astype(np.float32)
    return x, reached[None], normalized[None], metadata


def discover(cfg):
    paths, owner = {}, {}
    for split in ("train", "val", "test"):
        files = sorted((Path(cfg["data_dir"]) / split).glob("*.npz"))
        if not files:
            raise ValueError(f"No ForeFire NPZ files under {cfg['data_dir']}/{split}")
        paths[split] = files
        for file in files:
            _, _, _, meta = load_pair(file, cfg)
            for field in ("simulation_id", "scenario_family_id"):
                key = (field, meta[field])
                if key in owner and owner[key] != split:
                    raise ValueError(f"Leakage: {key} appears in {owner[key]} and {split}")
                owner[key] = split
    return paths


def fit_normalization(train_files, cfg):
    sums = np.zeros(len(cfg["channel_names"]), dtype=np.float64)
    sqs = sums.copy()
    count = 0
    for file in train_files:
        x, _, _, _ = load_pair(file, cfg)
        flat = x.reshape(len(sums), -1).astype(np.float64)
        sums += flat.sum(axis=1)
        sqs += np.square(flat).sum(axis=1)
        count += flat.shape[1]
    means = sums / count
    stds = np.sqrt(np.maximum(sqs / count - means ** 2, 0))
    for idx, kind in enumerate(cfg["channel_types"]):
        if kind == "binary":
            means[idx], stds[idx] = 0, 1
        elif stds[idx] < 1e-8:
            stds[idx] = 1
    return {"mean": means.tolist(), "std": stds.tolist(),
            "channel_names": cfg["channel_names"], "fit_split": "train"}


class ArrivalDataset(Dataset):
    def __init__(self, files, cfg, norm):
        self.files, self.cfg = files, cfg
        self.mean = np.asarray(norm["mean"], dtype=np.float32)[:, None, None]
        self.std = np.asarray(norm["std"], dtype=np.float32)[:, None, None]

    def __len__(self):
        return len(self.files)

    def __getitem__(self, index):
        x, reached, arrival, _ = load_pair(self.files[index], self.cfg)
        x = ((x - self.mean) / self.std).astype(np.float32)
        return torch.from_numpy(x), torch.from_numpy(reached), torch.from_numpy(arrival)
