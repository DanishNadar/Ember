"""Generate expanding synthetic circles ONLY to test plumbing, never fire accuracy."""
import argparse
from pathlib import Path
import numpy as np
from config import load_config


def generate(cfg):
    if cfg["dataset_kind"] != "synthetic_mock":
        raise ValueError("Mock generation requires dataset_kind: synthetic_mock and a separate data_dir/output_dir")
    if cfg["channel_names"] != [cfg["current_burn_channel"]] or cfg["channel_types"] != ["binary"]:
        raise ValueError("The mock generator only supports the current burn channel; it does not fabricate environmental fields")
    root = Path(cfg["data_dir"])
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"{root} is not empty; refusing to overwrite any dataset")
    size = cfg["image_size"]
    yy, xx = np.mgrid[:size, :size]
    rng = np.random.default_rng(cfg["random_seed"])
    count = 0
    for split in ("train", "val", "test"):
        directory = root / split
        directory.mkdir(parents=True, exist_ok=True)
        for simulation in range(cfg[f"mock_{split}_simulations"]):
            identity = f"synthetic_mock_{split}_{simulation:03d}"
            center_y, center_x = rng.uniform(size / 3, 2 * size / 3, size=2)
            distance = np.sqrt((yy - center_y) ** 2 + (xx - center_x) ** 2)
            # Fixed geometric fixture: nested circles, not a learned/physical spread model.
            for step in range(cfg["mock_steps_per_simulation"]):
                radius = size * (step + 1) / (4 * (cfg["mock_steps_per_simulation"] + 1))
                future_radius = size * (step + 2) / (4 * (cfg["mock_steps_per_simulation"] + 1))
                x = (distance <= radius).astype(np.float32)[None]
                y = (distance <= future_radius).astype(np.float32)[None]
                identities = {"simulation_id": np.asarray(identity), cfg["split_group_key"]: np.asarray(identity)}
                np.savez_compressed(directory / f"{identity}_{step:03d}.npz", x=x, y=y,
                                    channel_names=np.asarray(cfg["channel_names"]), **identities,
                                    dataset_kind=np.asarray("synthetic_mock"),
                                    time_t_seconds=np.asarray(step * cfg["forecast_horizon_seconds"], dtype=np.float64),
                                    forecast_horizon_seconds=np.asarray(cfg["forecast_horizon_seconds"], dtype=np.float64),
                                    cell_size_meters=np.asarray(cfg["mock_cell_size_meters"], dtype=np.float64))
                count += 1
    print(f"Generated {count} SYNTHETIC/MOCK samples at {root}; pipeline testing only", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    try:
        generate(load_config(args.config))
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Mock generation error: {exc}\n")


if __name__ == "__main__":
    main()
