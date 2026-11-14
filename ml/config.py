"""Read the one human-editable configuration; reject typos and unsafe settings."""
from pathlib import Path
import math
import yaml


# Keys form the schema; numerical defaults live only in config.yaml. Do not use
# the editable YAML itself as the schema, or deleting a setting would go unnoticed.
REQUIRED_KEYS = set("""
data_dir output_dir dataset_kind image_size channel_names channel_types
current_burn_channel forecast_horizon_seconds split_policy split_group_key
batch_size learning_rate epochs optimizer weight_decay adam_betas optimizer_epsilon
sgd_momentum base_filters depth dropout random_seed device num_workers cpu_threads
deterministic threshold bce_weight dice_weight dice_smoothing monotonicity_weight
save_frequency early_stopping_patience early_stopping_min_delta latency_warmup_steps
latency_repeats mock_train_simulations mock_val_simulations mock_test_simulations
mock_steps_per_simulation mock_cell_size_meters
""".split())


def load_config(path):
    path = Path(path).resolve()
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise ValueError(f"{path}: configuration must be a YAML mapping")
    missing, extra = REQUIRED_KEYS - cfg.keys(), cfg.keys() - REQUIRED_KEYS
    if missing or extra:
        raise ValueError(f"{path}: missing config options {sorted(missing)}; unknown options {sorted(extra)}")
    for name in ("data_dir", "output_dir"):
        if not isinstance(cfg[name], str) or not cfg[name]:
            raise ValueError(f"{name} must be a nonempty path")
        cfg[name] = str((path.parent / cfg[name]).resolve())
    names, types = cfg["channel_names"], cfg["channel_types"]
    if (not isinstance(names, list) or not names or
            not all(isinstance(n, str) and n for n in names) or len(set(names)) != len(names)):
        raise ValueError("channel_names must be a nonempty list of unique channel names")
    if not isinstance(types, list) or len(types) != len(names) or any(t not in ("binary", "continuous") for t in types):
        raise ValueError("channel_types must match channel_names and contain only binary or continuous; one-hot encode fuel IDs")
    if cfg["current_burn_channel"] not in names or types[names.index(cfg["current_burn_channel"])] != "binary":
        raise ValueError("current_burn_channel must name a binary input channel")
    for name in ("image_size", "batch_size", "epochs", "base_filters", "depth", "cpu_threads",
                 "save_frequency", "early_stopping_patience", "latency_repeats",
                 "mock_train_simulations", "mock_val_simulations", "mock_test_simulations", "mock_steps_per_simulation"):
        if type(cfg[name]) is not int or cfg[name] <= 0:
            raise ValueError(f"{name} must be a positive integer")
    for name in ("num_workers", "latency_warmup_steps", "random_seed"):
        if type(cfg[name]) is not int or cfg[name] < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    if cfg["depth"] > 8 or cfg["image_size"] % (2 ** cfg["depth"]):
        raise ValueError("image_size must be divisible by 2**depth; depth must be <= 8")
    for name in ("forecast_horizon_seconds", "learning_rate", "optimizer_epsilon", "dice_smoothing", "mock_cell_size_meters"):
        _number(cfg, name, positive=True)
    for name in ("weight_decay", "bce_weight", "dice_weight", "monotonicity_weight", "early_stopping_min_delta"):
        _number(cfg, name)
    for name in ("threshold", "dropout", "sgd_momentum"):
        _number(cfg, name)
        if cfg[name] > 1 or (name != "threshold" and cfg[name] == 1):
            raise ValueError(f"{name} is outside its probability range")
    if cfg["bce_weight"] + cfg["dice_weight"] <= 0:
        raise ValueError("At least one supervised loss weight (BCE or Dice) must be positive")
    betas = cfg["adam_betas"]
    if not isinstance(betas, list) or len(betas) != 2 or any(type(b) not in (int, float) or not 0 <= b < 1 for b in betas):
        raise ValueError("adam_betas must contain two numbers in [0,1)")
    for name, allowed in {"optimizer": ("adam", "sgd"), "device": ("auto", "cpu", "cuda"),
                          "split_policy": ("precreated",), "dataset_kind": ("forefire", "synthetic_mock")}.items():
        if cfg[name] not in allowed:
            raise ValueError(f"{name} must be one of {allowed}")
    if not isinstance(cfg["split_group_key"], str) or not cfg["split_group_key"]:
        raise ValueError("split_group_key must be a nonempty metadata key")
    if cfg["split_group_key"] in ("x", "y", "channel_names", "dataset_kind", "time_t_seconds", "forecast_horizon_seconds", "cell_size_meters"):
        raise ValueError("split_group_key must name a scenario identity, not an array or measurement key")
    if type(cfg["deterministic"]) is not bool:
        raise ValueError("deterministic must be true or false")
    return cfg


def _number(cfg, name, positive=False):
    value = cfg[name]
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be a finite {'positive' if positive else 'nonnegative'} number")
