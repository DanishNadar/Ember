"""SYNTHETIC fixtures to verify publication and contracts, NOT fire physics."""
import json
import tempfile
from pathlib import Path
import numpy as np
from data_contract import read_config, snapshot, sample, normalization, digest


def main():
    root = Path(__file__).resolve().parent
    out = Path(tempfile.mkdtemp(prefix="smoke-", dir=make_runs(root)))
    cfg = read_config(root / "config.json")
    cfg.update(dataset_kind="synthetic_mock", grid_size=32, data_dir=str(out / "ready"), base_filters=4, depth=2, epochs=2)
    shard = out / "ready" / "batch_000"
    shard.mkdir(parents=True)
    entries = []
    X, Y = np.indices((32, 32))
    for split in ("train", "val", "test"):
        for i in range(2):
            identity = f"{split}-{i}"
            cx, cy = 10 + 8 * i, 15
            radius = np.sqrt((X-cx)**2 + (Y-cy)**2)
            x = np.zeros((19, 32, 32), np.float32)
            x[0] = 1
            x[17, cx, cy] = 1
            valid = np.ones((32, 32), np.uint8)
            reached = (radius < 9).astype(np.uint8)
            arrival = np.where(reached, radius * 300, -9999).astype(np.float32)
            meta = dict(sample_id=identity, simulation_id=identity, scenario_family_id=identity,
                        region="MOCK", engine_version="synthetic-fixture", edge_hit=False,
                        channel_names=cfg["channel_names"], dataset_kind="synthetic_mock",
                        horizon_seconds=3600, cell_size_meters=40, array_order="CXY", arrival_units="seconds")
            path = shard / f"{identity}.npz"
            np.savez_compressed(path, x=x, arrival_time_seconds=arrival, valid_mask=valid,
                                reached_mask=reached, metadata_json=np.asarray(json.dumps(meta)))
            entries.append(dict(split=split, file=path.name, sha256=digest(path)))
    # Before publication no samples may be consumed.
    try:
        snapshot(cfg)
    except ValueError:
        pass
    else:
        raise AssertionError("Unpublished shard was consumed")
    manifest = shard / "complete.json"
    manifest.write_text(json.dumps(dict(status="complete", samples=entries)))
    parts = snapshot(cfg)
    norm = normalization(parts["train"], cfg)
    assert norm["mean"][17] == 0 and norm["std"][17] == 1
    # Exercise a true family leak with distinct sample/simulation IDs.
    target = shard / "val-0.npz"
    with np.load(target, allow_pickle=False) as z:
        arrays = {k: z[k] for k in z.files}
    meta = json.loads(str(arrays["metadata_json"].item()))
    original = dict(meta)
    meta["scenario_family_id"] = "train-0"
    arrays["metadata_json"] = np.asarray(json.dumps(meta))
    np.savez_compressed(target, **arrays)
    entries[2]["sha256"] = digest(target)
    manifest.write_text(json.dumps(dict(status="complete", samples=entries)))
    try:
        snapshot(cfg)
    except ValueError:
        pass
    else:
        raise AssertionError("Cross-split family leak accepted")
    meta = dict(original, edge_hit=True)
    arrays["metadata_json"] = np.asarray(json.dumps(meta))
    np.savez_compressed(target, **arrays)
    try:
        sample(target, cfg)
    except ValueError:
        pass
    else:
        raise AssertionError("Edge-hit label accepted")
    arrays["metadata_json"] = np.asarray(json.dumps(original))
    np.savez_compressed(target, **arrays)
    entries[2]["sha256"] = digest(target)
    # A manifest that assigns the same scenario to train and validation must fail.
    entries[2]["split"] = "train"
    entries.append(dict(entries[2], split="val"))
    manifest.write_text(json.dumps(dict(status="complete", samples=entries)))
    try:
        snapshot(cfg)
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate sample accepted")
    entries.pop()
    entries[2]["split"] = "val"
    manifest.write_text(json.dumps(dict(status="complete", samples=entries)))
    (out / "config.json").write_text(json.dumps(cfg, indent=2))
    print("PASS: shard publication, shapes, masks, provenance, normalization, duplicate/family-leak/edge rejection")
    print("SYNTHETIC ONLY. No ForeFire, training, CUDA, or cluster performance verified.")
    print(f"Optional training: python experiments/parallel_surrogate_training/train.py --config \"{out / 'config.json'}\" --output \"{out / 'training'}\" --device cpu")
    return out


def make_runs(root):
    path = root / "runs"
    path.mkdir(exist_ok=True)
    return path


if __name__ == "__main__":
    main()
