"""Fast, cluster-free checks of the Ember observability and scheduling contract."""
import json
import tempfile
from pathlib import Path
import unittest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from orchestration.observe.dashboard import (
    bottleneck_report, events_from_text, history_from_events, plot_learning,
    plot_timeline, read_events,
)
from orchestration.observe.build_workflow import make_workflow


class ObservatoryContractTests(unittest.TestCase):
    def test_parses_live_events_and_replay_csv(self):
        e1 = {"event": "epoch_finished", "epoch": 1, "timestamp_utc": "2026-11-14T20:00:01Z",
              "job": "train-baseline", "train": {"loss": 1.1, "iou": .2},
              "val": {"loss": 1.2, "iou": .15}, "train_seconds": 2, "validation_seconds": 1}
        e2 = dict(e1, epoch=2, timestamp_utc="2026-11-14T20:00:04Z",
                  train={"loss": .8, "iou": .4}, val={"loss": .9, "iou": .3})
        text = "noise\nEMBER_EVENT " + json.dumps(e1) + "\nEMBER_EVENT " + json.dumps(e2) + "\n"
        parsed = events_from_text(text)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(history_from_events(parsed)[-1]["val_iou"], .3)
        self.assertAlmostEqual(bottleneck_report(parsed)["validation_fraction"], 1 / 3)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "events.jsonl"
            p.write_text("\n".join(json.dumps(v) for v in [e1, e2]))
            self.assertEqual(len(read_events(p)), 2)
        fig = plot_learning(history_from_events(parsed), {"iou": .5})
        self.assertIsNotNone(fig)
        plt.close(fig)

    def test_parses_legacy_epochs_without_fabricated_train_iou(self):
        parsed = events_from_text("epoch 3/30 train_loss=0.47 val_loss=0.62 IoU=0.33")
        row = history_from_events(parsed)[0]
        self.assertEqual(row["epoch"], 3)
        self.assertEqual(row["val_iou"], .33)
        self.assertNotIn("train_iou", row)

    def test_timeline_only_for_observed_pairs(self):
        records = [
            {"event": "cpu_shard_started", "job": "physics-0", "shard": 0,
             "phase": "cpu_physics", "timestamp_utc": "2026-11-14T20:00:00Z"},
            {"event": "cpu_shard_finished", "job": "physics-0", "shard": 0,
             "phase": "cpu_physics", "timestamp_utc": "2026-11-14T20:00:07Z"},
            {"event": "ddp_finetune_started", "job": "ddp", "phase": "ddp_finetune",
             "timestamp_utc": "2026-11-14T20:00:06Z"},
        ]
        fig = plot_timeline(records)
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.axes[0].patches), 1)
        plt.close(fig)

    def test_cpu_shards_and_gpus_concurrent_but_isolated(self):
        wf = make_workflow(
            "fb://user/ember/source.tgz",
            "fb://user/ember/physics.tgz",
            "fb://user/ember/observatory/results",
        )
        self.assertEqual(wf["version"], "v4")
        self.assertEqual(set(wf["jobs"]),
                         {"physics-0", "physics-1", "train-baseline", "train-lower-lr"})
        outputs = [v["egress"][0]["destination"]["uri"] for v in wf["volumes"].values()]
        self.assertEqual(len(outputs), len(set(outputs)))
        for name, job in wf["jobs"].items():
            self.assertNotIn("depends-on", job)
            if name.startswith("physics"):
                self.assertEqual(job["resource"]["cpu"]["cores"], 16)
                self.assertNotIn("devices", job["resource"])
            else:
                self.assertEqual(job["resource"]["devices"]["nvidia.com/gpu"], 1)
                self.assertIn("EMBER_JOB", job["script"])
        self.assertIn("--shard 0", wf["jobs"]["physics-0"]["script"])
        self.assertIn("--shard 1", wf["jobs"]["physics-1"]["script"])


if __name__ == "__main__":
    unittest.main()
