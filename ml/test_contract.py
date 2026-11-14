"""Contract/metric failure cases that would otherwise invalidate scientific results."""
import copy
from pathlib import Path
import tempfile
import unittest
import numpy as np
import torch
import yaml
from common import Metrics, SurrogateLoss, load_checkpoint, write_json
from config import load_config
from dataset import audit_splits, fit_normalization, normalize, read_sample
from evaluate import evaluate
from mock_data import generate
from model import build_model


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = load_config(Path(__file__).with_name("config.yaml"))
        self.cfg.update(data_dir=str(self.root / "data"), output_dir=str(self.root / "outputs"),
                        image_size=16, base_filters=2, depth=2, dataset_kind="synthetic_mock",
                        mock_train_simulations=1, mock_val_simulations=1, mock_test_simulations=1,
                        mock_steps_per_simulation=1)
        generate(self.cfg)
        self.splits, _ = audit_splits(self.cfg)
        self.path = self.splits["train"][0]

    def rewrite(self, path=None, **updates):
        path = path or self.path
        with np.load(path, allow_pickle=False) as data:
            values = {key: data[key] for key in data.files}
        values.update(updates)
        np.savez_compressed(path, **values)

    def test_reject_wrong_shape_dtype_nonfinite_and_target(self):
        with np.load(self.path, allow_pickle=False) as data:
            original = {key: data[key] for key in data.files}
        for updates, message in [({"x": np.zeros((1, 8, 8), np.float32)}, "x must"),
                                 ({"x": original["x"].astype(np.float64)}, "x must"),
                                 ({"x": np.full((1, 16, 16), np.nan, np.float32)}, "NaN/inf"),
                                 ({"x": np.full((1, 16, 16), np.inf, np.float32)}, "NaN/inf"),
                                 ({"x": np.full((1, 16, 16), 0.5, np.float32)}, "binary channel"),
                                 ({"y": np.full((1, 16, 16), 0.5, np.float32)}, "finite binary"),
                                 ({"y": original["y"].astype(np.uint8)}, "y must"),
                                 ({"y": np.zeros((1, 16, 16), np.float32)}, "cumulative target"),
                                 ({"channel_names": np.asarray(["wrong"])}, "channel_names/order"),
                                 ({"forecast_horizon_seconds": np.asarray(999)}, "horizon differs"),
                                 ({"dataset_kind": np.asarray("forefire")}, "never mix")]:
            with self.subTest(message=message):
                np.savez_compressed(self.path, **{**original, **updates})
                with self.assertRaisesRegex(ValueError, message):
                    read_sample(self.path, self.cfg)

    def test_missing_sample_and_target(self):
        with self.assertRaisesRegex(ValueError, "sample file is missing"):
            read_sample(self.root / "absent.npz", self.cfg)
        np.savez_compressed(self.path, x=np.zeros((1, 16, 16), np.float32), channel_names=np.asarray(["burned_mask"]))
        with self.assertRaisesRegex(ValueError, "missing 'y'"):
            read_sample(self.path, self.cfg)
        read_sample(self.path, self.cfg, require_target=False)

    def test_config_missing_or_unknown_options(self):
        path = self.root / "config.yaml"
        missing = {k: v for k, v in self.cfg.items() if k != "learning_rate"}
        path.write_text(yaml.safe_dump(missing), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing config options.*learning_rate"):
            load_config(path)
        path.write_text(yaml.safe_dump({**self.cfg, "learning_reate": 0.1}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unknown options.*learning_reate"):
            load_config(path)

    def test_simulation_and_family_leakage(self):
        for key in ("simulation_id", "scenario_family_id"):
            with self.subTest(key=key):
                with np.load(self.path, allow_pickle=False) as data:
                    identity = data[key]
                val = self.splits["val"][0]
                with np.load(val, allow_pickle=False) as data:
                    original = {name: data[name] for name in data.files}
                self.rewrite(val, **{key: identity})
                with self.assertRaisesRegex(ValueError, "leakage"):
                    audit_splits(self.cfg)
                np.savez_compressed(val, **original)

    def test_missing_split(self):
        self.splits["test"][0].unlink()
        with self.assertRaisesRegex(ValueError, "no .*npz samples"):
            audit_splits(self.cfg)

    def test_train_statistics_only_and_binary_one_hot_preservation(self):
        cfg = copy.deepcopy(self.cfg)
        cfg.update(channel_names=["burned_mask", "wind_u", "fuel_a", "fuel_b"],
                   channel_types=["binary", "continuous", "binary", "binary"])
        for split, files in self.splits.items():
            x, y, meta = read_sample(files[0], self.cfg)
            wind = np.tile(np.arange(16, dtype=np.float32), (16, 1))
            if split != "train":
                wind += 1000
            fuel_a = np.indices((16, 16))[0] % 2
            new_x = np.concatenate([x, wind[None], fuel_a[None], (1 - fuel_a)[None]]).astype(np.float32)
            meta["channel_names"] = np.asarray(cfg["channel_names"])
            np.savez_compressed(files[0], x=new_x, y=y, **meta)
        norm = fit_normalization(self.splits["train"], cfg)
        self.assertAlmostEqual(norm["mean"][1], 7.5)
        x, _, _ = read_sample(self.path, cfg)
        scaled = normalize(x, norm)
        self.assertAlmostEqual(float(scaled[1].mean()), 0.0, places=6)
        self.assertAlmostEqual(float(scaled[1].std()), 1.0, places=6)
        np.testing.assert_array_equal(scaled[[0, 2, 3]], x[[0, 2, 3]])
        logits = build_model(cfg)(torch.from_numpy(scaled).unsqueeze(0))
        self.assertEqual(tuple(logits.shape), (1, 1, 16, 16))

    def test_constant_continuous_channel(self):
        cfg = copy.deepcopy(self.cfg)
        cfg.update(channel_names=["burned_mask", "constant"], channel_types=["binary", "continuous"])
        x, y, meta = read_sample(self.path, self.cfg)
        meta["channel_names"] = np.asarray(cfg["channel_names"])
        np.savez_compressed(self.path, x=np.concatenate([x, np.full_like(x, 3)]), y=y, **meta)
        norm = fit_normalization([self.path], cfg)
        self.assertEqual(norm["std"][1], 1)

    def test_metrics_known_counts_and_empty_masks(self):
        metrics = Metrics(0.5)
        logits = torch.tensor([[[[10.0, 10.0], [-10.0, -10.0]]]])
        target = torch.tensor([[[[1.0, 0.0], [1.0, 0.0]]]])
        metrics.update(logits, target, [10])
        result = metrics.result()
        self.assertAlmostEqual(result["iou"], 1 / 3)
        self.assertEqual(result["dice_f1"], 0.5)
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 0.5)
        self.assertEqual(result["burned_area_mae_m2"], 0)
        empty = Metrics(0.5)
        empty.update(torch.full((1, 1, 2, 2), -10.), torch.zeros((1, 1, 2, 2)))
        self.assertEqual(empty.result()["iou"], 1)

    def test_logits_shape_and_monotonicity_gradient(self):
        model = build_model(self.cfg)
        x = torch.ones(2, 1, 16, 16)
        self.assertEqual(tuple(model(x).shape), (2, 1, 16, 16))
        logits = torch.zeros(2, 1, 16, 16, requires_grad=True)
        cfg = {**self.cfg, "monotonicity_weight": 1.0}
        baseline = SurrogateLoss(self.cfg)(logits, x, x)
        regularized = SurrogateLoss(cfg)(logits, x, x)
        self.assertAlmostEqual(float((regularized - baseline).detach()), 0.5, places=6)
        regularized.backward()
        self.assertTrue(torch.isfinite(logits.grad).all())
        self.assertTrue((logits.grad < 0).all())

    def make_checkpoint(self):
        out = Path(self.cfg["output_dir"])
        out.mkdir()
        norm = fit_normalization(self.splits["train"], self.cfg)
        write_json(out / "normalization.json", norm)
        _, metadata = audit_splits(self.cfg)
        write_json(out / "split_manifest.json", {split: [metadata[str(p)] for p in files]
                                                 for split, files in self.splits.items()})
        path = out / "fixture.pt"
        torch.save({"format_version": 1, "config": self.cfg, "normalization": norm, "epoch": 0,
                    "model_state_dict": build_model(self.cfg).state_dict()}, path)
        return path, norm

    def test_checkpoint_config_and_normalization_identity(self):
        path, norm = self.make_checkpoint()
        device = torch.device("cpu")
        load_checkpoint(path, self.cfg, device)
        with self.assertRaisesRegex(ValueError, "Checkpoint/config mismatch"):
            load_checkpoint(path, {**self.cfg, "forecast_horizon_seconds": 999}, device)
        write_json(path.parent / "normalization.json", {**norm, "training_samples": 999})
        with self.assertRaisesRegex(ValueError, "differs from the statistics"):
            load_checkpoint(path, self.cfg, device)
        (path.parent / "normalization.json").unlink()
        with self.assertRaisesRegex(ValueError, "ship normalization.json"):
            load_checkpoint(path, self.cfg, device)

    def test_checkpoint_heldout_audit_survives_new_data_root(self):
        path, _ = self.make_checkpoint()
        # Rename the live training identity to avoid current-directory leakage,
        # then reuse the ORIGINAL training family as a test family.
        _, _, original = read_sample(self.path, self.cfg)
        self.rewrite(scenario_family_id=np.asarray("new_train_family"))
        self.rewrite(self.splits["test"][0], scenario_family_id=np.asarray(original["scenario_family_id"]))
        audit_splits(self.cfg)  # The current directories alone appear disjoint.
        with self.assertRaisesRegex(ValueError, "Held-out leakage"):
            evaluate(self.cfg, path)


if __name__ == "__main__":
    unittest.main()
