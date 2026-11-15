"""Tiny SYNTHETIC integration verification. Not production training or fire evaluation."""
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
from smoke import main as fixtures


def run(script, *args):
    result = subprocess.run([sys.executable, str(Path(__file__).parent / script), *map(str, args)],
                            capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise AssertionError(f"{script} failed\n{result.stdout}\n{result.stderr}")
    return result.stdout


if __name__ == "__main__":
    out = fixtures()
    cfg = out / "config.json"
    run("preflight.py", "--allow-cpu")
    run("check_data.py", "--config", cfg)
    run("prepare_configs.py", "--base", cfg, "--data", out / "ready", "--output", out / "prepared")
    frozen = out / "prepared/snapshot.json"
    run("train.py", "--config", cfg, "--output", out / "round1", "--snapshot", frozen, "--device", "cpu")
    for name in ("best.pt", "last.pt", "events.jsonl", "snapshot.json"):
        assert (out / "round1" / name).is_file(), name
    events = [json.loads(line) for line in (out / "round1/events.jsonl").read_text().splitlines()]
    assert events[-1]["event"] == "finished"
    assert all(e["train"]["optimizer_steps"] > 0 for e in events if e["event"] == "epoch")
    run("train.py", "--config", cfg, "--output", out / "round2", "--resume", out / "round1/last.pt", "--device", "cpu")
    run("predict.py", "--checkpoint", out / "round1/best.pt", "--config", cfg,
        "--split", "test", "--output", out / "evaluation", "--device", "cpu", "--repeats", "2", "--warmup", "1")
    report = json.loads((out / "evaluation/report.json").read_text())
    assert report["dataset_kind"] == "synthetic_mock" and "MOCK" in report["by_region"]
    sample_path = out / "ready/batch_000/test-0.npz"
    with np.load(sample_path, allow_pickle=False) as z:
        x, valid, metadata = z["x"], z["valid_mask"], z["metadata_json"]
        arrival = z["arrival_time_seconds"]
    unlabeled = out / "unlabeled.npz"
    np.savez_compressed(unlabeled, x=x, valid_mask=valid, metadata_json=metadata)
    run("predict.py", "--checkpoint", out / "round1/best.pt", "--input", unlabeled,
        "--output", out / "inference", "--device", "cpu", "--repeats", "2", "--warmup", "1")
    # Explicit minutes/+inf -> seconds/-9999 conversion, then manifest publication.
    raw = np.where(arrival == -9999, np.inf, arrival/60).astype(np.float32)
    np.save(out / "arrival_minutes.npy", raw)
    converted = out / "exported/sample.npz"
    run("export_sample.py", "--config", cfg, "--inputs", unlabeled, "--arrival", out / "arrival_minutes.npy",
        "--source-units", "minutes", "--source-unreached", "inf", "--split", "test", "--output", converted)
    with np.load(converted, allow_pickle=False) as z:
        np.testing.assert_allclose(z["arrival_time_seconds"], arrival, atol=.001)
    run("publish_shard.py", "--config", cfg, "--shard", converted.parent)
    assert (converted.parent / "complete.json").is_file()
    # Verify frozen snapshots detect later file mutation.
    with sample_path.open("ab") as f:
        f.write(b"changed")
    from data_contract import read_config, verify_frozen
    try:
        verify_frozen(json.loads(frozen.read_text()), read_config(cfg))
    except ValueError:
        pass
    else:
        raise AssertionError("Mutated frozen file accepted")
    print("PASS: synthetic train/backward/checkpoints/resume/evaluate/unlabeled inference/export/publish/hash protection")
    print("No ForeFire, CUDA, PGX placement, Fuzzball submission or cluster benchmark verified.")
