"""Project Ember benchmark CLI.

    python -m ember_bench scaling    # single-run cost vs grid size x horizon      -> results/scaling.csv
    python -m ember_bench ensemble   # N random scenarios on all cores + dataset   -> results/ensemble_*.json, data/
    python -m ember_bench floor      # ForeFire's own noise floor (the accuracy bar) -> results/floor.csv
    python -m ember_bench riskmap    # burn-probability map convergence vs members  -> results/riskmap_*.json
    python -m ember_bench breakeven  # break-even queries from measured numbers      -> results/breakeven.md
"""
import argparse
import csv
import json
import os
import platform
import statistics as st
import sys
import time

import numpy as np

from . import metrics, runner, scenarios
from .dataset import Writer


def _host():
    return {"host": platform.node(), "machine": platform.machine(), "cores": runner.n_cores(),
            "python": platform.python_version(), "time": time.strftime("%Y-%m-%dT%H:%M:%S")}


def _save(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    json.dump(obj, open(path, "w"), indent=2, default=float)
    print(f"wrote {path}")


# ---------------------------------------------------------------- scaling
def cmd_scaling(a):
    rows = []
    for n in a.sizes:
        dx = a.domain_km * 1000 / n if a.domain_km else a.dx
        for h in a.horizons:
            # same scenarios (same seed) at every resolution, so rows are comparable
            # Timing set: centred ignition and moderate wind so fires stay inside the domain at
            # every horizon (otherwise long horizons only keep the slow fires: survivorship bias).
            scs = scenarios.sample(a.reps, n, dx, h, seed=a.seed, fixed={"ign_x": 0.5, "ign_y": 0.5},
                                   ranges={"wind_speed": (0.0, a.wind_max)})
            # workers=1 by default so t_sim is single-run latency without core contention
            res = list(runner.run_many(scs, workers=a.workers or 1, keep_arrays=False, progress=False))
            allok = [r for r in res if r["ok"]]
            # All runs count. edge_hit_frac should be ~0 for this set; if not, the domain is too
            # small for the horizon and the row is flagged.
            ok = allok
            ts = [r["t_sim"] for r in ok]
            row = {"n": n, "dx_m": dx, "domain_km": n * dx / 1000, "horizon_h": h / 3600, "runs": len(ok),
                   "t_sim_median_s": st.median(ts), "t_sim_p90_s": float(np.percentile(ts, 90)),
                   "t_sim_max_s": max(ts), "t_setup_median_s": st.median(r["t_setup"] for r in ok),
                   "t_extract_median_s": st.median(r["t_extract"] for r in ok),
                   "t_process_median_s": st.median(r["t_worker"] for r in ok),
                   "front_nodes_median": st.median(r["n_front_nodes"] for r in ok),
                   "burned_km2_median": st.median(r["burned_area_m2"] for r in ok) / 1e6,
                   "edge_hit_frac": sum(r["edge_hit"] for r in allok) / max(1, len(allok))}
            rows.append(row)
            print(" ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}" for k, v in row.items()),
                  flush=True)
    os.makedirs(a.out, exist_ok=True)
    p = os.path.join(a.out, "scaling.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    _save(os.path.join(a.out, "scaling_host.json"), _host())
    print(f"wrote {p}")


# ---------------------------------------------------------------- ensemble (+ dataset)
def cmd_ensemble(a):
    dem = {"dem_path": a.dem, "dem_dx": a.dem_dx} if a.dem else None
    if "dem" in a.terrain and not dem:
        sys.exit("--terrain dem / mix+dem needs --dem FILE")
    scs = scenarios.split(a.split, a.runs, a.n, a.dx, a.horizon, seed=a.seed, terrain=a.terrain, dem=dem)
    w = Writer(a.data, a.n, a.dx, a.horizon, extra_meta={"split": a.split, "terrain": a.terrain,
                                                         "holdout": scenarios.HOLDOUT}) if a.data else None
    ts, tw, edge, fails = [], [], 0, 0
    for r in runner.run_many(scs, workers=a.workers, keep_arrays=bool(w)):
        if not r["ok"]:
            fails += 1
            continue
        ts.append(r["t_sim"]); tw.append(r["t_worker"]); edge += r["edge_hit"]
        if w:
            w.add(r)
    if w:
        w.close()
    wall, k = runner.run_many.last_wall, runner.run_many.last_workers
    out = {"n": a.n, "dx_m": a.dx, "horizon_s": a.horizon, "runs": a.runs, "split": a.split, "terrain": a.terrain, "failed": fails, "workers": k,
           "wall_s": wall, "runs_per_s": len(ts) / wall, "core_s_per_run": wall * k / max(1, len(ts)),
           "t_sim_mean_s": float(np.mean(ts)), "t_sim_median_s": float(np.median(ts)),
           "t_sim_p99_s": float(np.percentile(ts, 99)), "t_worker_mean_s": float(np.mean(tw)),
           "parallel_efficiency": float(np.sum(tw) / (wall * k)), "edge_hit_frac": edge / max(1, len(ts)),
           "dataset": a.data, **_host()}
    tag = "" if a.split == "all" else f"_{a.split}_s{a.seed}"
    _save(os.path.join(a.out, f"ensemble_n{a.n}_h{int(a.horizon)}_r{a.runs}{tag}.json"), out)


# ---------------------------------------------------------------- noise floor
def cmd_floor(a):
    """How different are two ForeFire runs that 'should' agree? A surrogate that is
    closer to ForeFire than this is as good as ForeFire for any practical purpose."""
    base = scenarios.sample(a.cases, a.n, a.dx, a.horizon, seed=a.seed, fixed={"wind_shift_deg": 0.0})
    variants = {
        "numerics: 2x finer front": lambda s: dict(s, perimeter_res=a.dx / 2),
        "input: moisture +0.01": lambda s: dict(s, md=s["md"] + 0.01),
        "input: wind +0.5 m/s": lambda s: dict(s, wind_speed=s["wind_speed"] + 0.5),
        "input: wind dir +5 deg": lambda s: dict(s, wind_dir_deg=s["wind_dir_deg"] + 5),
        "input: ignition +1 cell": lambda s: dict(s, ign_x=s["ign_x"] + 1.0 / s["n"]),
    }
    jobs = list(base)
    for f in variants.values():
        jobs += [f(s) for s in base]
    res = list(runner.run_many(jobs, workers=a.workers, keep_arrays=True))
    by = {}
    for r in res:
        if r["ok"]:
            by.setdefault(r["scenario"]["run_id"], []).append(r)
    rows = []
    for vname, f in variants.items():
        ms = []
        for s in base:
            rs = by.get(s["run_id"], [])
            ref = next((r for r in rs if r["scenario"] == s), None)
            tgt = f(s)
            var = next((r for r in rs if r["scenario"] == tgt), None)
            if ref is None or var is None or not np.isfinite(ref["arrival"]).any():
                continue
            ms.append(metrics.compare(var["arrival"], ref["arrival"], a.dx, a.horizon))
        row = {"variant": vname, "cases": len(ms)}
        for k in ms[0]:
            v = np.array([m[k] for m in ms], float)
            row[f"{k}_median"] = float(np.nanmedian(v))
            row[f"{k}_p10"] = float(np.nanpercentile(v, 10))
        rows.append(row)
        print(row, flush=True)
    os.makedirs(a.out, exist_ok=True)
    p = os.path.join(a.out, f"floor_n{a.n}_h{int(a.horizon)}.csv")
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {p}")


# ---------------------------------------------------------------- risk map
def cmd_riskmap(a):
    """Weather-uncertainty ensemble around one fire. How many members until the
    burn-probability map stops changing? That N x single-run cost is what a
    surrogate has to beat for this use case."""
    base = scenarios.sample(1, a.n, a.dx, a.horizon, seed=a.seed,
                            fixed={"wind_speed": 6.0, "md": 0.06, "fuel": 4, "fuel_patchiness": 0.4,
                                   "wind_shift_deg": 0.0})[0]
    members = scenarios.ensemble_weather(base, a.runs, seed=a.seed)
    arr = np.full((a.runs, a.n, a.n), np.inf, np.float32)
    for r in runner.run_many(members, workers=a.workers, keep_arrays=True):
        if r["ok"]:
            arr[r["scenario"]["run_id"]] = r["arrival"]
    wall, k = runner.run_many.last_wall, runner.run_many.last_workers
    ref = metrics.burn_probability(arr)
    conv = {}
    for m in [10, 25, 50, 100, 250, 500, 1000, 2500, 5000]:
        if m >= a.runs:
            break
        conv[m] = metrics.prob_map_error(metrics.burn_probability(arr[:m]), ref)
    out = {"n": a.n, "horizon_s": a.horizon, "members": a.runs, "wall_s": wall, "workers": k,
           "core_s_per_member": wall * k / a.runs, "base_scenario": base,
           "convergence_vs_full": conv, **_host()}
    os.makedirs(a.out, exist_ok=True)
    np.save(os.path.join(a.out, f"burnprob_n{a.n}_h{int(a.horizon)}_r{a.runs}.npy"), ref)
    _save(os.path.join(a.out, f"riskmap_n{a.n}_h{int(a.horizon)}_r{a.runs}.json"), out)


# ---------------------------------------------------------------- break-even
def breakeven(t_ff_core_s, n_train, t_train_gpu_s, t_nn_s, cores, gpu_count=1):
    """Queries Q* after which surrogate total cost < ForeFire total cost, in wall-clock
    on the given hardware. ForeFire uses `cores` CPU cores in parallel; the surrogate uses
    the GPU. Data generation for training runs on the same CPU cores.

        cost_ff(Q)   = Q * t_ff / cores
        cost_nn(Q)   = n_train * t_ff / cores + t_train + Q * t_nn
        Q*           = (n_train * t_ff / cores + t_train) / (t_ff / cores - t_nn)
    Returns inf if the surrogate is not faster per query than ForeFire on all cores.
    """
    ff_per_q = t_ff_core_s / cores
    fixed = n_train * ff_per_q + t_train_gpu_s / gpu_count
    gain = ff_per_q - t_nn_s
    return float("inf") if gain <= 0 else fixed / gain, ff_per_q, fixed


def cmd_breakeven(a):
    import glob
    ens = [json.load(open(p)) for p in glob.glob(os.path.join(a.out, "ensemble_*.json"))]
    nn = {}
    pnn = os.path.join(a.out, "surrogate_cost.json")
    if os.path.exists(pnn):
        nn = {int(k): v for k, v in json.load(open(pnn)).items()}
    lines = ["# Break-even: surrogate vs just running ForeFire", "",
             f"Target node: {a.target_cores} CPU cores for ForeFire, 1 GPU for the surrogate. "
             f"ForeFire per-core cost is scaled from the measuring host by `--core-speed` = {a.core_speed} "
             "(1.0 = same per-core speed).", "",
             "Q* = queries after which (data generation + training + Q x inference) < Q x ForeFire.", "",
             "| grid | horizon | ForeFire core-s/run | ForeFire wall/run on node | NN infer s/query | train runs | train GPU-h | Q* (break-even queries) | ForeFire time for Q* runs |",
             "|---|---|---|---|---|---|---|---|---|"]
    for e in sorted(ens, key=lambda e: (e["n"], e["horizon_s"], e["runs"])):
        if e["runs"] < 10000 and any(o["n"] == e["n"] and o["horizon_s"] == e["horizon_s"] and o["runs"] >= 10000
                                      for o in ens):
            continue  # prefer the 10k-run measurement
        t_ff = e["core_s_per_run"] / a.core_speed
        # assumed inference cost scales with pixel count from the 128x128 figure
        t_nn = nn.get(e["n"], {}).get("infer_s_per_query", a.nn_infer_s * (e["n"] / 128) ** 2)
        src = "measured" if e["n"] in nn else "assumed"
        for n_train in a.train_runs:
            for gh in a.train_gpu_hours:
                q, ffq, fixed = breakeven(t_ff, n_train, gh * 3600, t_nn, a.target_cores)
                qs = "never" if q == float("inf") else f"{q:,.0f}"
                tq = "-" if q == float("inf") else f"{q * ffq / 60:,.1f} min"
                lines.append(f"| {e['n']}² | {e['horizon_s'] / 3600:g} h | {t_ff:.3f} | {ffq * 1000:.1f} ms | "
                             f"{t_nn * 1000:.2f} ms ({src}) | {n_train:,} | {gh:g} | {qs} | {tq} |")
    p = os.path.join(a.out, "breakeven.md")
    open(p, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"wrote {p}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ember_bench")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, n=128, horizon=10800):
        p.add_argument("--n", type=int, default=n, help="grid cells per side")
        p.add_argument("--dx", type=float, default=30.0, help="cell size, m")
        p.add_argument("--horizon", type=float, default=horizon, help="simulated seconds")
        p.add_argument("--workers", type=int, default=0, help="0 = all cores")
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--out", default="results")

    p = sub.add_parser("scaling"); common(p)
    p.add_argument("--sizes", type=int, nargs="+", default=[64, 128, 256, 512, 1024])
    p.add_argument("--horizons", type=float, nargs="+", default=[3600, 10800, 21600])
    p.add_argument("--reps", type=int, default=8)
    p.add_argument("--wind-max", type=float, default=6.0, help="20-ft wind upper bound for the timing set")
    p.add_argument("--domain-km", type=float, default=None,
                   help="fix the physical domain and vary resolution (dx = domain/n) instead of fixed dx")
    p = sub.add_parser("ensemble"); common(p)
    p.add_argument("--runs", type=int, default=1000)
    p.add_argument("--data", default=None, help="write dataset shards here")
    p.add_argument("--split", default="all", choices=["all", "train", "ood"],
                   help="train = in-distribution space (holdout removed); ood = only the held-out region")
    p.add_argument("--terrain", default="mix", choices=["mix", "mix+dem", "flat", "plane", "hills", "dem"],
                   help="mix = flat/plane/hills cycled per run; *dem needs --dem")
    p.add_argument("--dem", default=None, help="real elevation: .npy [x,y] metres, or NetCDF with 'altitude'")
    p.add_argument("--dem-dx", type=float, default=30.0, help="DEM cell size, m (SRTM/3DEP 1 arc-sec ~ 30 m)")
    p = sub.add_parser("floor"); common(p)
    p.add_argument("--cases", type=int, default=40)
    p = sub.add_parser("riskmap"); common(p, n=256)
    p.add_argument("--runs", type=int, default=1000)
    p = sub.add_parser("breakeven"); common(p)
    p.add_argument("--target-cores", type=int, default=20, help="GB10: 10 X925 + 10 A725")
    p.add_argument("--core-speed", type=float, default=1.0)
    p.add_argument("--nn-infer-s", type=float, default=0.001,
                   help="assumed GPU inference s/query at 128x128 (scaled by pixel count) if not measured")
    p.add_argument("--train-runs", type=int, nargs="+", default=[2000, 10000])
    p.add_argument("--train-gpu-hours", type=float, nargs="+", default=[0.5, 2.0])
    a = ap.parse_args(argv)
    {"scaling": cmd_scaling, "ensemble": cmd_ensemble, "floor": cmd_floor,
     "riskmap": cmd_riskmap, "breakeven": cmd_breakeven}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
