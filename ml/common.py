"""Shared seeding, losses, metrics and portable checkpoint loading."""
import json
import random
from pathlib import Path
import numpy as np
import torch
from torch import nn
from dataset import validate_normalization
from model import build_model


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def setup(cfg):
    random.seed(cfg["random_seed"])
    np.random.seed(cfg["random_seed"] % (2 ** 32))
    torch.manual_seed(cfg["random_seed"])
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(cfg["random_seed"])
    torch.set_num_threads(cfg["cpu_threads"])
    torch.use_deterministic_algorithms(cfg["deterministic"])
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = cfg["deterministic"]
    requested = cfg["device"]
    if requested == "cuda" and not torch.cuda.is_available():
        raise ValueError("device=cuda requested but CUDA is unavailable in this PyTorch environment; use auto or cpu")
    return torch.device("cuda" if requested == "auto" and torch.cuda.is_available() else "cpu" if requested == "auto" else requested)


def synchronize(device):
    if device.type == "cuda":
        torch.cuda.synchronize(device)


class SurrogateLoss(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.bce = nn.BCEWithLogitsLoss()
        self.burn_index = cfg["channel_names"].index(cfg["current_burn_channel"])

    def forward(self, logits, target, x):
        # BCE consumes RAW logits. Sigmoid below is only for differentiable auxiliary losses.
        bce = self.bce(logits, target)
        probability = torch.sigmoid(logits)
        axes = (1, 2, 3)
        smooth = self.cfg["dice_smoothing"]
        dice = (1 - (2 * (probability * target).sum(axes) + smooth) /
                (probability.sum(axes) + target.sum(axes) + smooth)).mean()
        monotonicity = torch.relu(x[:, self.burn_index:self.burn_index + 1] - probability).mean()
        return (self.cfg["bce_weight"] * bce + self.cfg["dice_weight"] * dice +
                self.cfg["monotonicity_weight"] * monotonicity)


class Metrics:
    """Micro pixel confusion metrics and mean per-sample absolute burned-area error."""
    def __init__(self, threshold):
        self.threshold = threshold
        self.tp = self.fp = self.fn = self.tn = 0
        self.area_errors = []
        self.physical_errors = []

    def update(self, logits, target, cell_sizes=None):
        predicted = (torch.sigmoid(logits.detach()) >= self.threshold).cpu().numpy()
        truth = target.detach().cpu().numpy().astype(bool)
        self.tp += int(np.count_nonzero(predicted & truth))
        self.fp += int(np.count_nonzero(predicted & ~truth))
        self.fn += int(np.count_nonzero(~predicted & truth))
        self.tn += int(np.count_nonzero(~predicted & ~truth))
        errors = np.abs(predicted.sum(axis=(1, 2, 3)).astype(float) - truth.sum(axis=(1, 2, 3)))
        self.area_errors.extend(errors.tolist())
        if cell_sizes is not None:
            self.physical_errors.extend(None if size is None else float(error * size ** 2)
                                        for error, size in zip(errors, cell_sizes))

    def result(self):
        def ratio(numerator, denominator):
            return numerator / denominator if denominator else 1.0
        result = {
            "iou": ratio(self.tp, self.tp + self.fp + self.fn),
            "dice_f1": ratio(2 * self.tp, 2 * self.tp + self.fp + self.fn),
            "precision": ratio(self.tp, self.tp + self.fp),
            "recall": ratio(self.tp, self.tp + self.fn),
            "burned_area_mae_pixels": float(np.mean(self.area_errors)),
            "tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn,
            "samples": len(self.area_errors),
        }
        complete = len(self.physical_errors) == len(self.area_errors) and all(e is not None for e in self.physical_errors)
        result["burned_area_mae_m2"] = float(np.mean(self.physical_errors)) if complete else None
        return result


def load_checkpoint(path, cfg, device):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"Checkpoint missing: {path}; run train.py first")
    # weights_only supports state dictionaries + plain metadata, without arbitrary object loading.
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if checkpoint.get("format_version") != 1:
        raise ValueError(f"{path}: unsupported Ember checkpoint format")
    saved = checkpoint["config"]
    for key in ("channel_names", "channel_types", "current_burn_channel", "forecast_horizon_seconds",
                "image_size", "base_filters", "depth", "dropout", "dataset_kind"):
        if saved[key] != cfg[key]:
            raise ValueError(f"Checkpoint/config mismatch for {key}: trained={saved[key]!r}, requested={cfg[key]!r}")
    norm_path = path.parent / "normalization.json"
    if not norm_path.is_file():
        raise ValueError(f"Missing {norm_path}; ship normalization.json with the checkpoint")
    normalization = json.loads(norm_path.read_text(encoding="utf-8"))
    validate_normalization(normalization, cfg)
    if normalization != checkpoint["normalization"]:
        raise ValueError("normalization.json differs from the statistics embedded in this checkpoint")
    model = build_model(cfg).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, normalization, checkpoint
