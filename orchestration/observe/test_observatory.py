"""Fast, cluster-free checks of the Ember observability and scheduling contract."""
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from orchestration.observe.dashboard import (
    bottleneck_report, events_from_text, history_from_events, plot_learning,
    plot_timeline, read_events,
    histories_from_events, progress_report, plot_resources,
)
from orchestration.observe.build_workflow import make_workflow


class ObservatoryContractTests(unittest.TestCase):
    def test_progress_estimates_use_observed_epochs_and_keep_metrics(self):
        events = [{"event":"training_started", "job":"a", "workflow_id":"w",
                   "timestamp_utc":"2026-11-14T00:00:00Z", "epochs_requested":4, "sample_counts":{"train":8}},
                  {"event":"epoch_finished", "job":"a", "workflow_id":"w", "epoch":1,
                   "timestamp_utc":"2026-11-14T00:00:10Z", "train_seconds":2,
                   "train":{"loss":.4}, "val":{"loss":.5, "iou":.2}, "learning_rate":.001}]
        row = progress_report(events)[0]
        self.assertEqual(row["remaining_seconds_estimate"],30)
        self.assertEqual(row["training_samples_per_second"],4)
        self.assertEqual(row["val_loss"],.5)

    def test_windows_cli_logs_are_decoded_as_utf8(self):
        from orchestration.observe.dashboard import fuzzball_log
        result = type("LogResult", (), {"returncode": 0, "stdout": "ForeFire ✓", "stderr": ""})()
        with patch("orchestration.observe.dashboard.subprocess.run", return_value=result) as run:
            self.assertEqual(fuzzball_log("workflow", "physics-0", cli=["fuzzball"]), "ForeFire ✓")
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")

    def test_identical_epoch_and_job_names_stay_separate_across_workflows(self):
        events = [{"event": "epoch_finished", "epoch": 1, "job": "baseline",
                   "workflow_id": workflow, "val": {"loss": loss}}
                  for workflow, loss in [("workflow-a", 1.0), ("workflow-b", 2.0)]]
        self.assertEqual(len(history_from_events(events)), 2)
        self.assertEqual(len(histories_from_events(events)), 2)
        self.assertEqual(len(progress_report(events)), 2)
        with self.assertRaisesRegex(ValueError, "single workflow/job"):
            plot_learning(history_from_events(events))

    def test_collection_context_overrides_unknown_emitter_job(self):
        text = 'EMBER_EVENT {"event":"epoch_finished","epoch":1,"job":"unknown"}'
        record = events_from_text(text, workflow_id="actual-workflow", job="actual-job")[0]
        self.assertEqual((record["workflow_id"], record["job"]), ("actual-workflow", "actual-job"))

    def test_resource_times_share_one_clock_and_skip_bad_timestamps(self):
        events = [{"job": "a", "workflow_id": "w", "timestamp_utc": "2026-11-14T20:00:00Z",
                   "resources": {"gpu_utilization_percent_snapshot": 10}},
                  {"job": "b", "workflow_id": "w", "timestamp_utc": "2026-11-14T21:00:05+01:00",
                   "resources": {"gpu_utilization_percent_snapshot": 20}},
                  {"job": "bad", "timestamp_utc": "not a clock", "resources": {"gpu_utilization_percent_snapshot": 99}}]
        fig = plot_resources(events)
        self.assertEqual([line.get_xdata()[0] for line in fig.axes[0].lines], [0, 5])
        plt.close(fig)

    def test_timeline_does_not_pair_different_workflows_or_naive_clocks(self):
        events = [{"event": "training_started", "job": "same", "workflow_id": "one",
                   "timestamp_utc": "2026-11-14T20:00:00Z"},
                  {"event": "training_finished", "job": "same", "workflow_id": "two",
                   "timestamp_utc": "2026-11-14T20:00:05Z"}]
        self.assertIsNone(plot_timeline(events))
        events[1]["workflow_id"] = "one"
        events[1]["timestamp_utc"] = "2026-11-14T20:00:05"
        self.assertIsNone(plot_timeline(events))

    def test_bottleneck_uses_paired_unique_work_not_unmatched_durations(self):
        event = {"event": "epoch_finished", "epoch": 1, "job": "a", "workflow_id": "w",
                 "train_seconds": 2, "validation_seconds": 1}
        report = bottleneck_report([event, event, dict(event, epoch=2, train_seconds=None, validation_seconds=100)])
        self.assertEqual(report["timed_epoch_pairs"], 1)
        self.assertAlmostEqual(report["validation_fraction"], 1 / 3)

    def test_progress_reopens_test_phase_after_training_and_counts_unique_simulations(self):
        events = [{"event": "training_finished", "job": "gpu", "workflow_id": "w"},
                  {"event": "test_evaluation_started", "job": "gpu", "workflow_id": "w"}]
        self.assertFalse(progress_report(events)[0]["finished"])
        event = {"event": "cpu_simulation_finished", "workflow_id": "w", "job": "cpu",
                 "sample_id": "real-id", "simulation_ok": True, "status": "excluded"}
        row = progress_report([event, event])[0]
        self.assertEqual((row["physics_attempts"], row["physics_completed"], row["physics_excluded"]), (1, 1, 1))

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
