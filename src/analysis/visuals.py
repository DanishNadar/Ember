"""Presentation-oriented graphics derived only from recorded Ember artifacts."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _plot_extent(bbox: np.ndarray) -> list[float]:
    return [float(bbox[0]), float(bbox[2]), float(bbox[1]), float(bbox[3])]


def _arrival_crop(valid: np.ndarray, padding: int = 20) -> tuple[slice, slice]:
    rows, columns = np.where(valid)
    return (slice(max(0, rows.min() - padding), min(valid.shape[0], rows.max() + padding + 1)),
            slice(max(0, columns.min() - padding), min(valid.shape[1], columns.max() + padding + 1)))


def create_reference_visuals(state_manifest_path: str | Path, arrival_manifest_path: str | Path, output_root: str | Path) -> dict[str, str]:
    """Create intuitive, non-causal visuals from one front/landscape/reference-arrival set."""
    state_manifest = json.loads(Path(state_manifest_path).read_text(encoding="utf-8"))
    arrival_manifest = json.loads(Path(arrival_manifest_path).read_text(encoding="utf-8"))
    if state_manifest.get("status") != "complete" or state_manifest.get("environment", {}).get("status") != "complete":
        raise ValueError("A completed state extraction with aligned environment fields is required")
    if arrival_manifest.get("status") != "complete":
        raise ValueError("A completed arrival-time extraction is required")
    state = np.load(state_manifest["artifacts"]["state_npz"], allow_pickle=False)
    environment = np.load(state_manifest["environment"]["output"], allow_pickle=False)
    mask, extent = state["burned_mask"], _plot_extent(state["bbox"])
    fuel, altitude = environment["fuel"][0, 0], environment["altitude"][0, 0]
    output_dir = Path(output_root) / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    landscape = output_dir / "forefire_runff_reference_landscape_front.png"
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.4), constrained_layout=True)
    for axis, image, title, label, cmap in (
        (axes[0], fuel, "Fuel index with extracted fire extent", "fuel index", "tab20"),
        (axes[1], altitude, "Altitude with extracted fire extent", "native altitude value", "terrain"),
    ):
        view = axis.imshow(image, origin="lower", extent=extent, cmap=cmap, interpolation="nearest")
        axis.contour(mask, levels=[0.5], colors="white", linewidths=1.2, origin="lower", extent=extent)
        axis.contourf(mask, levels=[0.5, 1.5], colors=["crimson"], alpha=0.2, origin="lower", extent=extent)
        axis.set(title=title, xlabel="Longitude (degrees)", ylabel="Latitude (degrees)")
        figure.colorbar(view, ax=axis, label=label)
    figure.suptitle("Ember: reference front in its sampled landscape (white boundary, red extent)")
    figure.savefig(landscape, dpi=180)
    plt.close(figure)

    classes, total_count = np.unique(fuel, return_counts=True)
    burned_count = np.array([int(((fuel == value) & (mask == 1)).sum()) for value in classes])
    burned_share = burned_count / total_count * 100
    order = np.argsort(total_count)[::-1]
    composition = output_dir / "forefire_runff_reference_fuel_composition.png"
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    positions = np.arange(len(classes))
    axes[0].bar(positions - 0.2, total_count[order], width=0.4, color="#5b8fb9", label="sampled landscape")
    axes[0].bar(positions + 0.2, burned_count[order], width=0.4, color="#dd6b4d", label="inside extracted extent")
    axes[0].set_xticks(positions, [str(int(value)) for value in classes[order]])
    axes[0].set(title="Fuel-index coverage", xlabel="fuel index", ylabel="256×256-grid cells")
    axes[0].legend()
    axes[1].bar(positions, burned_share[order], color="#dd6b4d")
    axes[1].set_xticks(positions, [str(int(value)) for value in classes[order]])
    axes[1].set(title="Share of each sampled fuel index inside extent", xlabel="fuel index", ylabel="percent of that fuel's cells")
    axes[1].set_ylim(0, 100)
    figure.suptitle("Composition only — one front does not establish a causal fuel effect")
    figure.savefig(composition, dpi=180)
    plt.close(figure)

    arrival = np.load(arrival_manifest["artifacts"]["arrival_npz"], allow_pickle=False)
    arrival_time, valid = arrival["arrival_time"], arrival["valid_mask"]
    row_slice, column_slice = _arrival_crop(valid)
    domain = arrival_manifest["domain"]
    rows, columns = arrival_time.shape
    zoom_extent = [domain["SWx"] + column_slice.start / columns * domain["Lx"], domain["SWx"] + column_slice.stop / columns * domain["Lx"],
                   domain["SWy"] + row_slice.start / rows * domain["Ly"], domain["SWy"] + row_slice.stop / rows * domain["Ly"]]
    values = arrival_time[valid]
    arrival_story = output_dir / "forefire_runff_reference_arrival_story.png"
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    image = axes[0].imshow(np.ma.masked_where(~valid[row_slice, column_slice], arrival_time[row_slice, column_slice]), origin="lower", extent=zoom_extent, cmap="inferno", interpolation="nearest")
    axes[0].set(title="Where the front arrived", xlabel="X (model coordinate units)", ylabel="Y (model coordinate units)")
    figure.colorbar(image, ax=axes[0], label="arrival time (model time units; scripts use seconds)")
    counts, bins, patches = axes[1].hist(values, bins=24, color="#7a5195", edgecolor="none")
    axes[1].set(title="When valid arrival cells occurred", xlabel="arrival time (model time units)", ylabel="grid cells")
    axes[1].axvline(float(np.median(values)), color="#dd6b4d", linewidth=2, label=f"median {np.median(values):.1f}")
    axes[1].legend()
    figure.suptitle("Reference arrival-time artifact — not a locally executed simulation")
    figure.savefig(arrival_story, dpi=180)
    plt.close(figure)
    return {"landscape_front": str(landscape), "fuel_composition": str(composition), "arrival_story": str(arrival_story)}


def plot_completed_performance(run_root: str | Path, output_path: str | Path) -> str:
    """Plot actual completed CLI manifests. Raises rather than charting blocked/missing data."""
    records = []
    for path in Path(run_root).rglob("run_manifest.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("status") == "complete" and "wall_seconds" in record:
            records.append((path.parent.name, float(record["wall_seconds"]), record.get("peak_rss_bytes")))
    if not records:
        raise ValueError("No completed run manifests with wall_seconds were found; no performance graph was created.")
    labels, seconds, memory = zip(*records)
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    axes[0].bar(labels, seconds, color="#5b8fb9")
    axes[0].set(title="Measured ForeFire wall time", xlabel="run manifest", ylabel="seconds")
    numeric_memory = [value / (1024 ** 2) if value is not None else np.nan for value in memory]
    axes[1].bar(labels, numeric_memory, color="#61a95e")
    axes[1].set(title="Measured peak resident memory", xlabel="run manifest", ylabel="MiB")
    for axis in axes:
        axis.tick_params(axis="x", rotation=25)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)
    return str(output_path)
