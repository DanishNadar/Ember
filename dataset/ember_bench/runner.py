"""Parallel execution: one fresh forked process per ForeFire run, all cores busy.

ForeFire keeps simulation state in process-global statics (upstream issue #175),
so we never run two simulations in one process. The parent imports pyforefire
once (so children do not pay the import) but never creates a ForeFire object.
"""
import multiprocessing as mp
import os
import sys
import time

from . import sim


def n_cores():
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:
        return os.cpu_count() or 1


def _quiet():
    # ForeFire prints from C++ ("creating bmap ...") straight to fd 1.
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)


def _work(args):
    sc, keep_arrays = args
    t = time.perf_counter()
    try:
        r = sim.run_scenario(sc)
        r["ok"] = True
    except Exception as e:  # a crashed run is a result too
        r = {"ok": False, "error": repr(e)}
    r["t_worker"] = time.perf_counter() - t
    r["pid"] = os.getpid()
    if not keep_arrays:
        for k in ("arrival", "fuel", "alt"):
            r.pop(k, None)
    r["scenario"] = sc
    return r


def run_many(scenarios, workers=0, keep_arrays=True, progress=True):
    """Yield results (unordered) and return wall time via the last item's '_wall'."""
    import pyforefire  # noqa: F401  (pay the import once, before forking)
    for path in {s["dem_path"] for s in scenarios if s.get("dem_path")}:
        sim.load_dem(path)  # load once; forked workers inherit it
    for path in {s["landscape_nc"] for s in scenarios if s.get("landscape_nc")}:
        sim.load_landscape_nc(path)
    workers = workers or n_cores()
    ctx = mp.get_context("fork")
    t0 = time.perf_counter()
    done = 0
    with ctx.Pool(workers, initializer=_quiet, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(_work, [(s, keep_arrays) for s in scenarios], chunksize=1):
            done += 1
            if progress and (done % max(1, len(scenarios) // 20) == 0 or done == len(scenarios)):
                el = time.perf_counter() - t0
                print(f"  {done}/{len(scenarios)}  {el:.1f}s  ({done / el:.1f} runs/s)", file=sys.stderr, flush=True)
            yield r
    run_many.last_wall = time.perf_counter() - t0
    run_many.last_workers = workers
