"""Ember observatory: replay completed runs or poll Fuzzball CLI logs from Jupyter.

No cluster calls occur at import. All plots use actual events/history; unavailable
measurements stay absent rather than being filled with plausible-looking data.
"""
from pathlib import Path
from datetime import datetime
import csv
import json
import re
import shutil
import subprocess
import time

import matplotlib.pyplot as plt
import numpy as np

EVENT_MARKER = "EMBER_EVENT "
OLD_EPOCH = re.compile(
    r"epoch\s+(?P<epoch>\d+)/\d+\s+train_loss=(?P<train_loss>[\d.eE+-]+)"
    r"\s+val_loss=(?P<val_loss>[\d.eE+-]+)\s+IoU=(?P<val_iou>[\d.eE+-]+)",
    re.I,
)


def read_events(path):
    path = Path(path)
    return events_from_text(path.read_text(encoding="utf-8")) if path.exists() else []


def events_from_text(text):
    """Accept JSONL events or EMBER_EVENT lines mixed into Fuzzball stdout."""
    events, seen = [], set()
    for line in text.splitlines():
        segment = line.split(EVENT_MARKER, 1)[-1] if EVENT_MARKER in line else line.strip()
        if not segment.startswith("{"):
            m = OLD_EPOCH.search(line)
            if m:
                record = {"event": "epoch_finished", **{k: float(v) for k, v in m.groupdict().items()}}
                record["epoch"] = int(record["epoch"])
            else:
                continue
        else:
            try:
                record = json.loads(segment)
            except (ValueError, TypeError):
                continue
            if not isinstance(record, dict) or "event" not in record:
                continue
        # Cluster logs may include duplicates when retried; preserve distinct jobs.
        key = (record.get("timestamp_utc"), record.get("job"), record.get("event"),
               record.get("epoch"), record.get("workflow_id"))
        if key in seen:
            continue
        seen.add(key)
        events.append(record)
    return events


def history_from_events(events):
    """Return sorted per-epoch records, preferring structured reports."""
    rows = {}
    for e in events:
        if e.get("event") != "epoch_finished":
            continue
        epoch = int(e.get("epoch", 0))
        if epoch <= 0:
            continue
        row = {"epoch": epoch}
        for group in ("train", "val"):
            if isinstance(e.get(group), dict):
                row.update({group + "_" + k: v for k, v in e[group].items()})
        for key in ("train_loss", "val_loss", "val_iou", "train_seconds",
                    "validation_seconds", "learning_rate"):
            if key in e:
                row[key] = e[key]
        rows[epoch] = row
    return [rows[k] for k in sorted(rows)]


def read_history(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return [dict(row, epoch=int(row["epoch"])) for row in csv.DictReader(f)]


def _numeric(row, key):
    try:
        value = row.get(key)
        return float(value) if value is not None and value != "" else np.nan
    except (TypeError, ValueError):
        return np.nan


def plot_learning(rows, test=None):
    """Live train/val curves; the held-out test is shown only as a final annotation."""
    if not rows:
        print("No epoch metrics yet. Select a finished history.csv or poll an active workflow.")
        return None
    fig, axs = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for ax, keys, name, ylabel in [
        (axs[0, 0], ["train_loss", "val_loss"], "Learning curves", "Loss (BCE + arrival)"),
        (axs[0, 1], ["train_iou", "val_iou"], "Burned-area overlap", "IoU"),
        (axs[1, 0], ["train_dice", "val_dice"], "Segmentation quality", "Dice / F1"),
        (axs[1, 1], ["train_arrival_mae_seconds_on_reached", "val_arrival_mae_seconds_on_reached"],
         "Conditional arrival-time error", "MAE, seconds")]:
        epochs = [int(r["epoch"]) for r in rows]
        for key in keys:
            vals = [_numeric(r, key) for r in rows]
            if not np.isnan(vals).all():
                ax.plot(epochs, vals, marker=".", label=key.replace("_", " ").title())
        ax.set(xlabel="Epoch", ylabel=ylabel, title=name)
        ax.grid(alpha=0.2)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(fontsize=8)
    if test:
        v = test.get("iou")
        mae = test.get("arrival_mae_seconds_on_reached")
        fig.suptitle("Final held-out test (NOT evaluated each epoch): IoU={}  |  arrival MAE={} s".format(
            f"{v:.3f}" if isinstance(v, (int, float)) else "unavailable",
            f"{mae:.1f}" if isinstance(mae, (int, float)) else "unavailable"))
    return fig


def plot_timeline(events):
    """Use observed timestamps only; stage transitions are never inferred."""
    spans, active = [], {}
    for e in sorted(events, key=lambda p: p.get("timestamp_utc") or ""):
        kind = e.get("event", "")
        key = (e.get("job"), e.get("shard"), e.get("phase"))
        ts = e.get("timestamp_utc")
        if not ts:
            continue
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if kind in {"training_started", "cpu_shard_started", "ddp_finetune_started", "test_evaluation_started"}:
            active[(key, kind)] = t
        elif kind in {"training_finished", "cpu_shard_finished", "ddp_finetune_finished", "test_evaluation_finished"}:
            start_type = {"training_finished": "training_started",
                          "cpu_shard_finished": "cpu_shard_started",
                          "ddp_finetune_finished": "ddp_finetune_started",
                          "test_evaluation_finished": "test_evaluation_started"}[kind]
            start = active.pop((key, start_type), None)
            if start is not None and t >= start:
                spans.append((str(key[0] or "job") + " · " + start_type.replace("_started", ""), start, t))
    if not spans:
        print("No complete, timestamped phase intervals yet. DDP is not assumed.")
        return None
    base = min(start for _, start, _ in spans)
    fig, ax = plt.subplots(figsize=(12, max(3, len(spans) * 0.55 + 1)))
    for i, (label, start, end) in enumerate(spans):
        x = (start - base).total_seconds()
        duration = (end - start).total_seconds()
        ax.barh(i, duration, left=x, height=0.62)
        ax.text(x + duration + 0.5, i, f"{duration:.1f}s", va="center", fontsize=8)
    ax.set_yticks(range(len(spans)), [v[0] for v in spans])
    ax.invert_yaxis()
    ax.set(xlabel="Elapsed seconds since first recorded stage", title="Observed CPU/GPU job phase overlap")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    return fig


def plot_resources(events):
    """Plots individual GPU/CPU snapshots; no average utilization is claimed."""
    rows = [(e.get("timestamp_utc"), e.get("job", "unknown"), e.get("resources", {}))
            for e in events if isinstance(e.get("resources"), dict)]
    rows = [(ts, job, data) for ts, job, data in rows if ts]
    if not rows:
        print("No hardware snapshots were recorded.")
        return None
    fig, axs = plt.subplots(1, 2, figsize=(12, 3.5), constrained_layout=True)
    for metric, ax, title in (
        ("gpu_utilization_percent_snapshot", axs[0], "GPU utilization snapshots"),
        ("host_cpu_percent_snapshot", axs[1], "Host CPU snapshots")):
        jobs = sorted({job for _, job, data in rows if metric in data})
        for job in jobs:
            subset = [(datetime.fromisoformat(t.replace("Z", "+00:00")), data[metric])
                      for t, j, data in rows if j == job and metric in data]
            start = min(t for t, _ in subset)
            ax.plot([(t - start).total_seconds() for t, _ in subset], [v for _, v in subset],
                    marker="o", ms=3, label=job)
        ax.set(title=title, xlabel="Seconds since this job's first snapshot",
               ylabel="Instantaneous utilization (%)", ylim=(0, 105))
        if jobs:
            ax.legend(fontsize=8)
        else:
            ax.text(.5, .5, "No telemetry", transform=ax.transAxes, ha="center", va="center")
        ax.grid(alpha=.2)
    return fig


def bottleneck_report(events):
    epochs = [e for e in events if e.get("event") == "epoch_finished"]
    train = [float(e["train_seconds"]) for e in epochs if isinstance(e.get("train_seconds"), (int, float))]
    val = [float(e["validation_seconds"]) for e in epochs if isinstance(e.get("validation_seconds"), (int, float))]
    report = {"epochs_observed": len(epochs),
              "mean_train_epoch_s": round(np.mean(train), 3) if train else None,
              "mean_validation_epoch_s": round(np.mean(val), 3) if val else None,
              "validation_fraction": sum(val)/(sum(val)+sum(train)) if train and val else None,
              "gpu_utilization_average": None}
    # Without a continuous, calibrated interval sampling process, do not infer average GPU use.
    return report


def fuzzball_log(workflow_id, job, *, cli=None, timeout=45):
    """Read a CLI log; wsl.exe wrapper works for a Windows notebook kernel."""
    if cli is None:
        cli = ["fuzzball"] if shutil.which("fuzzball") else [
            "wsl.exe", "--exec", "/home/caden/.local/bin/fuzzball"]
    elif isinstance(cli, str):
        cli = [cli]
    if not workflow_id or not job:
        raise ValueError("Supply an actual workflow ID and job name")
    p = subprocess.run([*cli, "workflow", "log", workflow_id, job],
                       capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or "Fuzzball CLI failed")
    return p.stdout


def watch(workflows, *, cli=None, interval_s=8, cycles=45):
    """Bounded live notebook cell. Interrupt the kernel to stop watching."""
    from IPython.display import display, clear_output
    if not workflows:
        raise ValueError("Set workflows={workflow_id: [job_names]} before watching")
    for _ in range(cycles):
        events, errors = [], []
        for workflow, jobs in workflows.items():
            for job in jobs:
                try:
                    new = events_from_text(fuzzball_log(workflow, job, cli=cli))
                    events.extend([dict(e, job=job, workflow_id=workflow) for e in new])
                except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
                    errors.append(f"{job}: {exc}")
        clear_output(wait=True)
        print("Live Ember observatory | observed events:", len(events))
        if errors:
            print("Connection/log status:", "; ".join(errors))
        rows = history_from_events(events)
        if rows:
            display(plot_learning(rows))
            plt.show()
        if events:
            display(bottleneck_report(events))
            if any(e.get("event") in {"training_finished", "cpu_shard_finished", "ddp_finetune_finished"} for e in events):
                display(plot_timeline(events))
                plt.show()
        if not errors and events and all(any(e.get("event") in
                ("training_finished", "cpu_shard_finished", "ddp_finetune_finished", "test_evaluation_finished")
                for e in events if e.get("job") == job) for jobs in workflows.values() for job in jobs):
            break
        time.sleep(interval_s)
