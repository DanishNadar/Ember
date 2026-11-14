"""Run real CLIs on a tiny CPU fixture; outputs are synthetic, never benchmarks."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np
import torch
import yaml
from common import load_checkpoint, setup
from config import load_config


def smoke_test(config_path):
    cfg = load_config(config_path)
    root = Path(__file__).resolve().parent
    staging = root / ".smoke_test"
    staging.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="run_", dir=staging))
    # Test fixture sizes, explicitly recorded in a complete derived configuration.
    cfg.update(data_dir=str(work / "data"), output_dir=str(work / "outputs"), dataset_kind="synthetic_mock",
               image_size=32, channel_names=["burned_mask"], channel_types=["binary"],
               current_burn_channel="burned_mask", split_group_key="scenario_family_id",
               device="cpu", num_workers=0, base_filters=4, depth=2, batch_size=2,
               epochs=2, save_frequency=1, mock_train_simulations=2, mock_val_simulations=1,
               mock_test_simulations=1, mock_steps_per_simulation=2)
    path = work / "config.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    print(f"Smoke configuration and retained artifacts: {work}", flush=True)

    def cli(script, *args):
        subprocess.run([sys.executable, str(root / script), "--config", str(path), *args], check=True, cwd=root)

    cli("mock_data.py")
    cli("train.py")
    checkpoint_path = work / "outputs" / "best.pt"
    cli("evaluate.py", "--checkpoint", str(checkpoint_path))
    sample = sorted((work / "data" / "test").glob("*.npz"))[0]
    # Exercise inference on an unlabeled NPZ, as a future simulator handoff would.
    with np.load(sample, allow_pickle=False) as sample_data:
        unlabeled = {key: sample_data[key] for key in sample_data.files if key != "y"}
    input_path = work / "unlabeled.npz"
    np.savez_compressed(input_path, **unlabeled)
    cli("predict.py", "--checkpoint", str(checkpoint_path), "--input", str(input_path))
    metrics = json.loads((work / "outputs/evaluation/synthetic_mock/metrics.json").read_text(encoding="utf-8"))
    assert metrics["samples"] == 2 and not metrics["is_real_benchmark"]
    for key in ("iou", "dice_f1", "precision", "recall"):
        assert 0 <= metrics[key] <= 1
    assert metrics["burned_area_mae_m2"] is not None
    assert metrics["latency"]["mean_ms_per_sample"] > 0
    assert (work / "outputs/evaluation/synthetic_mock/comparison.png").is_file()
    assert len(list((work / "outputs/evaluation/synthetic_mock/predictions").glob("*.npz"))) == 2
    prediction_path = work / "outputs/predictions/synthetic_mock/unlabeled_prediction.npz"
    with np.load(prediction_path, allow_pickle=False) as prediction:
        assert prediction["probability"].shape == (1, 32, 32)
        assert np.isfinite(prediction["probability"]).all()
        assert np.isin(prediction["predicted_mask"], [0, 1]).all()
    rows = list(csv.DictReader((work / "outputs/metrics.csv").open(encoding="utf-8")))
    assert len(rows) == cfg["epochs"]
    # Check two independent disk loads give identical deterministic CPU logits.
    device = setup(cfg)
    model_a, _, _ = load_checkpoint(checkpoint_path, cfg, device)
    model_b, _, _ = load_checkpoint(checkpoint_path, cfg, device)
    x = torch.from_numpy(unlabeled["x"]).unsqueeze(0)
    with torch.inference_mode():
        torch.testing.assert_close(model_a(x), model_b(x), rtol=0, atol=0)
    print(f"PASS: mock train/checkpoint/evaluate/unlabeled predict; no accuracy assertion. Artifacts: {work}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    smoke_test(parser.parse_args().config)
