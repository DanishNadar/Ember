"""Generate a bounded, region-held-out pilot using the existing real ForeFire wrapper.

Run on Linux with forefire==2.6.0, numpy, netCDF4 and PyYAML installed.
No synthetic targets or meteorological substitutions are used.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dataset"))
from ember_bench import initstates, runner

PLAN = {"train": [("corsica", "train", 24), ("socal_chaparral", "train", 24),
                  ("norcal_paradise", "train", 24), ("greatbasin_nv", "train", 24)],
        "val": [("texas_panhandle", "val", 24)],
        "test": [("montana_timber", "test", 24)]}
SENTINEL = -9999.0


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_arrays(x, arrival, names, horizon):
    if x.dtype != np.float32 or x.shape != (19, 320, 320) or not np.isfinite(x).all():
        raise ValueError("Invalid actual input tensor")
    if arrival.dtype != np.float32 or arrival.shape != (320, 320):
        raise ValueError("Invalid actual arrival grid")
    valid = np.isfinite(arrival) & (arrival >= 0) & (arrival <= horizon)
    if not np.all(valid | (arrival == SENTINEL)) or not valid.any():
        raise ValueError("Arrival grid has invalid values or no reached cells")
    for k in ("burnable", "ignition", "engine"):
        if not np.isin(x[names.index(k)], [0, 1]).all():
            raise ValueError(f"Invalid binary {k}")
    return valid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    source = ROOT / "dataset" / "ember_init_v2"
    names = [c[0] for c in initstates.CHANNELS]
    records = []
    regions = [r for entries in PLAN.values() for r, _, _ in entries]
    if len(set(regions)) != len(regions):
        raise ValueError("A whole region must belong to exactly one split")
    for split, entries in PLAN.items():
        (out / "data" / split).mkdir(parents=True)
        for region, source_split, count in entries:
            data = initstates.load_split(str(source), f"{region}/{source_split}")
            cfg = dict(data["meta"]["config"], _dir=initstates.ROOT)
            props = initstates.fuel_properties(initstates._p(cfg, cfg["landscape"]["fuel_table"]),
                                               cfg["landscape"].get("nonburnable", []),
                                               cfg["landscape"]["engine"])
            rows = sorted(data["rows"], key=lambda r: hashlib.sha256(
                ("ember-pilot-v1:" + r["sample_id"]).encode()).hexdigest())
            accepted = 0
            source_hashes = {"samples_csv": sha(source / region / source_split / "samples.csv"),
                             "meta_json": sha(source / region / source_split / "meta.json"),
                             "landscape": sha(initstates._p(cfg, cfg["landscape"]["path"]))}
            for offset in range(0, min(len(rows), count * 3), count + 4):
                batch = rows[offset:offset + count + 4]
                by_id = {r["sample_id"]: r for r in batch}
                scenarios = [initstates.to_scenario(r, cfg) for r in batch]
                results = list(runner.run_many(scenarios, workers=args.workers, progress=False))
                for result in sorted(results, key=lambda r: r["scenario"]["run_id"]):
                    sc = result["scenario"]
                    row = by_id[sc["run_id"]]
                    record = {"simulation_id": row["sample_id"], "split": split,
                              "scenario_family_id": "region:" + region,
                              "region": region, "source_split": source_split,
                              "source_hashes": source_hashes, "row": row, "scenario": sc,
                              **{k: v for k, v in result.items()
                                 if k not in {"arrival", "fuel", "alt", "scenario"}}}
                    if not result.get("ok") or result["edge_hit"]:
                        record["accepted"] = False
                        record["rejection"] = "simulation_failure" if not result.get("ok") else "edge_hit"
                        records.append(record)
                        continue
                    if accepted == count:
                        record.update(accepted=False, rejection="target_count_already_met")
                        records.append(record)
                        continue
                    ignition = initstates.ignition_mask(row, cfg)
                    x = initstates.input_tensor(row, result["fuel"], result["alt"], ignition,
                                                props, cfg["grid"]["dx_m"])
                    arrival = np.where(np.isfinite(result["arrival"]), result["arrival"], SENTINEL).astype(np.float32)
                    reached = validate_arrays(x, arrival, names, sc["horizon_s"])
                    for idx, angle in ((9, row["wind_dir_deg"]),
                                       (11, row["wind_dir_deg"] + row["wind_shift_deg"])):
                        expected = row["wind_speed"] * np.asarray([np.sin(np.deg2rad(angle)), np.cos(np.deg2rad(angle))])
                        if not np.allclose(x[idx:idx + 2, 0, 0], expected, rtol=1e-5, atol=1e-6):
                            raise ValueError("Input wind does not match the simulated schedule")
                    if not np.allclose(x[13], sc["wind_shift_t_s"] / sc["horizon_s"]):
                        raise ValueError("Input shift timing differs from simulation")
                    file = out / "data" / split / (row["sample_id"] + ".npz")
                    np.savez_compressed(file, x=x, arrival_time_seconds=arrival,
                                        channel_names=np.asarray(names),
                                        simulation_id=np.asarray(row["sample_id"]),
                                        scenario_family_id=np.asarray("region:" + region),
                                        dataset_kind=np.asarray("forefire"),
                                        horizon_seconds=np.asarray(sc["horizon_s"]),
                                        cell_size_meters=np.asarray(sc["dx"]),
                                        wind_shift_ramp_seconds=np.asarray(sc["wind_shift_ramp_s"]),
                                        array_index_order=np.asarray("[channel,x_east,y_north]"))
                    record.update(accepted=True, file=str(file.relative_to(out)),
                                  sha256=sha(file), reached_cells=int(reached.sum()),
                                  unreached_cells=int((~reached).sum()))
                    records.append(record)
                    accepted += 1
                if accepted == count:
                    break
            if accepted != count:
                raise RuntimeError(f"{region}: only {accepted}/{count} valid simulations; refusing incomplete dataset")
            print(f"DATASET {split}/{region}: {accepted} genuine ForeFire simulations", flush=True)
            (out / "simulation_records.json").write_text(json.dumps(records, indent=2))
    base = yaml.safe_load((ROOT / "ml" / "arrival_config.yaml").read_text())
    base.update(data_dir="data", output_dir="outputs_baseline", device="cuda",
                channel_names=names,
                channel_types=["binary" if n in {"burnable", "ignition", "engine"} else "continuous" for n in names],
                ignition_channel="ignition")
    (out / "baseline.yaml").write_text(yaml.safe_dump(base, sort_keys=False))
    variant = dict(base, learning_rate=0.0003, output_dir="outputs_lower_lr")
    (out / "lower_lr.yaml").write_text(yaml.safe_dump(variant, sort_keys=False))
    manifest = {"status": "complete", "dataset_kind": "forefire", "scope": "bounded pilot, not full 26000-scenario dataset",
                "source_commit": args.source_commit,
                "forefire_version": importlib.metadata.version("forefire"),
                "generator_sha256": sha(__file__), "sim_wrapper_sha256": sha(ROOT / "dataset/ember_bench/sim.py"),
                "plan": PLAN, "split_policy": "Entire regions are exclusive scenario families; Arizona remains unused",
                "channel_names": names, "grid_size": 320, "cell_size_meters": 40,
                "horizon_seconds": 3600, "unreached_sentinel": SENTINEL,
                "wind_shift_ramp_seconds": 1800, "array_index_order": "[channel,x_east,y_north]",
                "generation_wall_seconds": time.perf_counter() - started,
                "sample_counts": {s: sum(r["accepted"] and r["split"] == s for r in records) for s in PLAN},
                "known_limitations": ["Small pilot; very few independent region families",
                                      "ForeFire Farsite downslope behavior remains as documented upstream",
                                      "Prescribed future wind schedule is known to the model",
                                      "Metrics measure simulator agreement, not real-world accuracy"],
                "simulations": records}
    (out / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: v for k, v in manifest.items() if k != "simulations"}, indent=2))


if __name__ == "__main__":
    main()
