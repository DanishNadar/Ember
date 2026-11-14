"""Ember observatory: replay completed runs or poll Fuzzball CLI logs from Jupyter.

No cluster calls occur at import. All plots use actual events/history; unavailable
measurements stay absent rather than being filled with plausible-looking data.
"""
from pathlib import Path
from datetime import datetime, timezone
import csv
import json
import re
import shutil
import subprocess
import time
import os
import math

import matplotlib.pyplot as plt
import numpy as np

EVENT_MARKER = "EMBER_EVENT "
OLD_EPOCH = re.compile(
    r"epoch\s+(?P<epoch>\d+)/\d+\s+train_loss=(?P<train_loss>[\d.eE+-]+)"
    r"\s+val_loss=(?P<val_loss>[\d.eE+-]+)\s+IoU=(?P<val_iou>[\d.eE+-]+)",
    re.I,
)


def read_events(path, *, workflow_id=None, job=None):
    path = Path(path)
    return events_from_text(path.read_text(encoding="utf-8"), workflow_id=workflow_id,
                            job=job, source_id=str(path.resolve())) if path.exists() else []


def events_from_text(text, *, workflow_id=None, job=None, source_id=None):
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
        for field, value in (("workflow_id", workflow_id), ("job", job), ("source_id", source_id)):
            if value is not None:
                record[field] = value
        key = json.dumps(record, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        events.append(record)
    return events


def _identity(event):
    return (str(event.get("workflow_id") or event.get("experiment_id") or
                event.get("source_id") or "unknown"), str(event.get("job") or "unknown"))


def _timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # Naive node clocks cannot be compared safely across hosts.
        return result.astimezone(timezone.utc) if result.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def _ordered(events):
    first = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(events, key=lambda e: _timestamp(e.get("timestamp_utc")) or first)


def _label(identity):
    workflow, job = identity
    # Do not put private local source paths in plot labels.
    workflow = Path(workflow).name if "/" in workflow or "\\" in workflow else workflow[:12]
    return f"{workflow} / {job}"


def history_from_events(events):
    """Return sorted per-epoch records, preferring structured reports."""
    rows = {}
    structured = {}
    for e in _ordered(events):
        if e.get("event") != "epoch_finished":
            continue
        try:
            epoch = int(e.get("epoch", 0))
        except (ValueError, TypeError, OverflowError):
            continue
        if epoch <= 0:
            continue
        identity = _identity(e)
        record_key = (*identity, epoch)
        is_structured = isinstance(e.get("train"), dict) or isinstance(e.get("val"), dict)
        if structured.get(record_key) and not is_structured:
            continue
        row = {"epoch": epoch, "workflow_id": identity[0], "job": identity[1]}
        for group in ("train", "val"):
            if isinstance(e.get(group), dict):
                row.update({group + "_" + k: v for k, v in e[group].items()})
        for key in ("train_loss", "val_loss", "val_iou", "train_seconds",
                    "validation_seconds", "learning_rate"):
            if key in e:
                row[key] = e[key]
        rows[record_key] = row
        structured[record_key] = is_structured
    return [rows[k] for k in sorted(rows)]


def histories_from_events(events):
    result = {}
    for row in history_from_events(events):
        result.setdefault(_identity(row), []).append(row)
    return result


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
    if len({_identity(row) for row in rows}) > 1:
        raise ValueError("Select a single workflow/job history before plotting learning curves")
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
        else:
            ax.text(.5, .5, "Metric not recorded", transform=ax.transAxes, ha="center")
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
    for e in _ordered(events):
        kind = e.get("event", "")
        key = (*_identity(e), e.get("shard"), e.get("phase"))
        t = _timestamp(e.get("timestamp_utc"))
        if t is None:
            continue
        if kind in {"training_started", "cpu_shard_started", "ddp_finetune_started", "ddp_training_started", "test_evaluation_started"}:
            active[(key, kind)] = t
        elif kind in {"training_finished", "cpu_shard_finished", "ddp_finetune_finished", "ddp_training_finished", "test_evaluation_finished"}:
            start_type = {"training_finished": "training_started",
                          "cpu_shard_finished": "cpu_shard_started",
                          "ddp_finetune_finished": "ddp_finetune_started",
                          "ddp_training_finished": "ddp_training_started",
                          "test_evaluation_finished": "test_evaluation_started"}[kind]
            start = active.pop((key, start_type), None)
            if start is not None and t >= start:
                spans.append((_label(key[:2]) + " / " + str(key[3] or start_type.replace("_started", "")), start, t))
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
    rows = [(_timestamp(e.get("timestamp_utc")), _identity(e), e.get("resources", {}))
            for e in events if isinstance(e.get("resources"), dict)]
    rows = [(ts, job, data) for ts, job, data in rows if ts]
    if not rows:
        print("No hardware snapshots were recorded.")
        return None
    fig, axs = plt.subplots(1, 2, figsize=(12, 3.5), constrained_layout=True)
    base = min(t for t, _, _ in rows)
    for metric, ax, title in (
        ("gpu_utilization_percent_snapshot", axs[0], "GPU utilization snapshots"),
        ("host_cpu_percent_snapshot", axs[1], "Host CPU snapshots")):
        jobs = sorted({job for _, job, data in rows if isinstance(data.get(metric), (int, float))
                       and math.isfinite(data[metric])})
        for job in jobs:
            subset = sorted((t, data[metric]) for t, j, data in rows if j == job
                            and isinstance(data.get(metric), (int, float)) and math.isfinite(data[metric]))
            ax.plot([(t - base).total_seconds() for t, _ in subset], [v for _, v in subset],
                    marker="o", ms=3, label=_label(job))
        ax.set(title=title, xlabel="Seconds since first observed snapshot (shared clock)",
               ylabel="Instantaneous utilization (%)", ylim=(0, 105))
        if jobs:
            ax.legend(fontsize=8)
        else:
            ax.text(.5, .5, "No telemetry", transform=ax.transAxes, ha="center", va="center")
        ax.grid(alpha=.2)
    return fig



def progress_report(events):
    """Compact, directly observed job progress; no estimated finish times."""
    jobs, simulations = {}, set()
    for e in _ordered(events):
        identity = _identity(e)
        item = jobs.setdefault(identity, {"workflow_id": identity[0], "job": identity[1], "phase": "unknown",
                                    "last_epoch": None, "val_iou": None,
                                    "physics_completed": 0, "physics_excluded": 0, "physics_attempts": 0,
                                    "finished": False})
        kind = e.get("event")
        if kind in {"training_started", "cpu_shard_started", "ddp_finetune_started",
                    "ddp_training_started", "test_evaluation_started"}:
            item["phase"] = e.get("phase", kind)
            item["finished"] = False
        elif kind == "epoch_finished":
            if e.get("epoch", 0) >= (item["last_epoch"] or 0):
                item["last_epoch"] = e.get("epoch")
                item["val_iou"] = e.get("val", {}).get("iou", e.get("val_iou"))
        elif kind == "cpu_simulation_finished":
            key = (*identity, e.get("shard"), e.get("sample_id"))
            if key not in simulations:
                simulations.add(key)
                item["physics_attempts"] += 1
                if e.get("simulation_ok", e.get("status") == "complete"):
                    item["physics_completed"] += 1
                if e.get("status") != "complete":
                    item["physics_excluded"] += 1
        elif kind in {"training_finished", "cpu_shard_finished",
                      "ddp_finetune_finished", "ddp_training_finished",
                      "test_evaluation_finished"}:
            item["phase"] = kind
            item["finished"] = True
    return [jobs[j] for j in sorted(jobs)]

def bottleneck_report(events):
    epochs = history_from_events(events)
    paired = [e for e in epochs if all(isinstance(e.get(k), (int, float))
              and math.isfinite(e[k]) and e[k] >= 0 for k in ("train_seconds", "validation_seconds"))]
    train = [float(e["train_seconds"]) for e in paired]
    val = [float(e["validation_seconds"]) for e in paired]
    report = {"epochs_observed": len(epochs),
              "mean_train_epoch_s": round(np.mean(train), 3) if train else None,
              "mean_validation_epoch_s": round(np.mean(val), 3) if val else None,
              "timed_epoch_pairs": len(paired),
              "validation_fraction": sum(val)/(sum(val)+sum(train)) if sum(train)+sum(val) > 0 else None,
              "duration_scope": "Summed paired epoch work; not elapsed overlap or average hardware utilization",
              "gpu_utilization_average": None,
              "cpu_shards": [e.get("summary") for e in events
                             if e.get("event") == "cpu_shard_finished"
                             and isinstance(e.get("summary"), dict)]}
    # Without a continuous, calibrated interval sampling process, do not infer average GPU use.
    return report


def fuzzball_command():
    command = shutil.which("fuzzball")
    if command:
        return [command]
    local = Path.home() / ".local/bin/fuzzball"
    if local.is_file() and os.name != "nt":
        return [str(local)]
    if shutil.which("wsl.exe"):
        return ["wsl.exe", "--exec", "sh", "-lc", 'exec "$HOME/.local/bin/fuzzball" "$@"', "ember-fuzzball"]
    raise RuntimeError("Fuzzball CLI was not found; provide cli=[path_to_fuzzball] explicitly")


def fuzzball_log(workflow_id, job, *, cli=None, timeout=45):
    """Read a CLI log; wsl.exe wrapper works for a Windows notebook kernel."""
    if cli is None:
        cli = fuzzball_command()
    elif isinstance(cli, str):
        cli = [cli]
    if not workflow_id or not job:
        raise ValueError("Supply an actual workflow ID and job name")
    p = subprocess.run([*cli, "workflow", "log", workflow_id, job],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or "Fuzzball CLI failed")
    return p.stdout


def watch(workflows, *, cli=None, interval_s=8, cycles=45):
    """Bounded live notebook cell. Interrupt the kernel to stop watching."""
    from IPython.display import display, clear_output
    if not workflows:
        raise ValueError("Set workflows={workflow_id: [job_names]} before watching")
    if interval_s <= 0 or cycles < 1:
        raise ValueError("interval_s and cycles must be positive")
    deadline = time.monotonic() + cycles * interval_s + 45
    for _ in range(cycles):
        events, errors = [], []
        for workflow, jobs in workflows.items():
            for job in jobs:
                try:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return
                    new = events_from_text(fuzzball_log(workflow, job, cli=cli, timeout=min(45, remaining)),
                                           job=job, workflow_id=workflow)
                    events.extend(new)
                except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
                    errors.append(f"{job}: {exc}")
        clear_output(wait=True)
        print("Live Ember observatory | observed events:", len(events))
        if errors:
            print("Connection/log status:", "; ".join(errors))
        print("Per-job progress (observed):")
        for job_row in progress_report(events):
            print("  {job}: {phase}; epoch={last_epoch}; val_IoU={val_iou}; "
                  "physics_completed={physics_completed}, excluded={physics_excluded}".format(**job_row))
        for identity, rows in histories_from_events(events).items():
            fig = plot_learning(rows)
            if fig is not None:
                fig.suptitle(_label(identity))
                display(fig)
                plt.close(fig)
        if events:
            display(bottleneck_report(events))
            if any(e.get("event") in {"training_finished", "cpu_shard_finished", "ddp_finetune_finished"} for e in events):
                fig = plot_timeline(events)
                if fig is not None:
                    display(fig)
                    plt.close(fig)
        if not errors and events and all(any(e.get("event") in
                ("cpu_shard_finished", "ddp_finetune_finished", "ddp_training_finished", "test_evaluation_finished")
                for e in events if e.get("job") == job and e.get("workflow_id") == workflow)
                for workflow, jobs in workflows.items() for job in jobs):
            break
        time.sleep(max(0, min(interval_s, deadline - time.monotonic())))
