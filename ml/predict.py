"""Predict one future burn mask from a numeric NPZ; y is optional."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from common import load_checkpoint, setup
from config import load_config
from dataset import normalize, read_sample


def predict(cfg, checkpoint_path, input_path):
    device = setup(cfg)
    model, norm, _ = load_checkpoint(checkpoint_path, cfg, device)
    x, _, metadata = read_sample(input_path, cfg, require_target=False)
    tensor = torch.from_numpy(normalize(x, norm)).unsqueeze(0).to(device)
    with torch.inference_mode():
        logits = model(tensor)
        if not torch.isfinite(logits).all():
            raise ValueError("Prediction produced nonfinite logits")
        probability = torch.sigmoid(logits)[0].cpu().numpy()
    prediction = (probability >= cfg["threshold"]).astype(np.uint8)
    out = Path(cfg["output_dir"]) / "predictions"
    if cfg["dataset_kind"] == "synthetic_mock":
        out = out / "synthetic_mock"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{Path(input_path).stem}_prediction.npz"
    metadata.update(dataset_kind=cfg["dataset_kind"], forecast_horizon_seconds=cfg["forecast_horizon_seconds"],
                    threshold=cfg["threshold"], source_path=str(Path(input_path).resolve()),
                    checkpoint=str(Path(checkpoint_path).resolve()))
    np.savez_compressed(path, probability=probability, predicted_mask=prediction,
                        metadata_json=np.asarray(json.dumps(metadata)))
    print(f"Saved {cfg['dataset_kind']} prediction {prediction.shape} to {path}", flush=True)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        predict(load_config(args.config), args.checkpoint, args.input)
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Prediction error: {exc}\n")


if __name__ == "__main__":
    main()
