"""Small metadata-only checkpoint contract tests; no model training or GPU work."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


class ArrivalCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec("torch") is None:
            raise unittest.SkipTest("PyTorch is optional for offline report export")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
        from arrival_dataset import validate_checkpoint_contract
        cls.validate = staticmethod(validate_checkpoint_contract)

    def fixture(self, root):
        cfg = {"channel_names": ["ignition"], "channel_types": ["binary"], "grid_size": 8,
               "horizon_seconds": 3600, "unreached_sentinel": -9999, "base_filters": 4,
               "depth": 1, "dropout": 0, "ignition_channel": "ignition"}
        paths, recorded = {}, {}
        for part in ("train", "val", "test"):
            row = {"simulation_id": "fixture-" + part, "scenario_family_id": "family-" + part}
            p = root / (part + ".npz"); np.savez(p, **{k: np.asarray(v) for k, v in row.items()})
            paths[part], recorded[part] = [p], [row]
        checkpoint = {"config": copy.deepcopy(cfg), "normalization": {"mean": [0.], "std": [1.],
                      "fit_split": "train", "channel_names": cfg["channel_names"]}, "split_manifest": recorded}
        return cfg, paths, checkpoint

    def test_original_identity_and_normalization_contract_is_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            cfg, paths, checkpoint = self.fixture(Path(t))
            self.validate(checkpoint, cfg, paths)

    def test_changed_horizon_is_rejected_before_loading_model(self):
        with tempfile.TemporaryDirectory() as t:
            cfg, paths, checkpoint = self.fixture(Path(t)); cfg["horizon_seconds"] = 1800
            with self.assertRaisesRegex(ValueError, "horizon_seconds"):
                self.validate(checkpoint, cfg, paths)

    def test_historical_training_family_cannot_become_new_test_family(self):
        with tempfile.TemporaryDirectory() as t:
            cfg, paths, checkpoint = self.fixture(Path(t))
            np.savez(paths["test"][0], simulation_id=np.asarray("new-id"), scenario_family_id=np.asarray("family-train"))
            with self.assertRaisesRegex(ValueError, "Held-out test leakage"):
                self.validate(checkpoint, cfg, paths)

    def test_old_test_family_cannot_move_into_training(self):
        with tempfile.TemporaryDirectory() as t:
            cfg, paths, checkpoint = self.fixture(Path(t))
            np.savez(paths["train"][0], simulation_id=np.asarray("new-id"), scenario_family_id=np.asarray("family-test"))
            with self.assertRaisesRegex(ValueError, "Historical held-out test moved"):
                self.validate(checkpoint, cfg, paths)


if __name__ == "__main__":
    unittest.main()
