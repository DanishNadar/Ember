"""Training-dataset writer and loader. Schema: see README.md, "Dataset schema".

Layout:
    <out>/meta.json           grid, units, param names, ForeFire version, schema version
    <out>/shard_00000.npz     up to SHARD runs each (np.savez_compressed)
    <out>/index.csv           one row per run: shard, row, params, burned area, timings
"""
import csv
import glob
import json
import math
import os

import numpy as np

from .scenarios import PARAM_NAMES
from . import sim

SCHEMA_VERSION = 2   # v2: altitude_m stored per run (procedural hills)
SHARD = 1000


class Writer:
    def __init__(self, out, n, dx, horizon_s, extra_meta=None):
        os.makedirs(out, exist_ok=True)
        self.out, self.n, self.dx, self.h = out, n, dx, horizon_s
        self.buf, self.shard = [], 0
        self.index = open(os.path.join(out, "index.csv"), "w", newline="")
        self.cw = csv.writer(self.index)
        self.cw.writerow(["shard", "row", "run_id", "terrain", *PARAM_NAMES, "burned_area_m2", "edge_hit",
                          "n_front_nodes", "t_sim_s", "t_worker_s"])
        try:
            import pyforefire
            ffv = getattr(pyforefire, "__version__", "unknown")
        except Exception:
            ffv = "unknown"
        meta = {"schema_version": SCHEMA_VERSION, "n": n, "dx_m": dx, "horizon_s": horizon_s,
                "array_index_order": "[run, x, y]; cell (i,j) centre = ((i+0.5)*dx, (j+0.5)*dx)",
                "arrival_units": "minutes since ignition, float16, +inf = not burned by horizon",
                "param_names": PARAM_NAMES, "forefire_version": ffv,
                "altitude_units": "metres, float16, [run, x, y]",
                "propagation_model": "RothermelAndrews2018", "wind_adjustment_factor": sim.WAF,
                "fuel_codes": {"1..9": "Andrews 2018 SH1..SH9", str(sim.NONBURN): "non-burnable"}}
        meta.update(extra_meta or {})
        json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=2)

    def add(self, r):
        if not r.get("ok"):
            return
        self.buf.append(r)
        if len(self.buf) >= SHARD:
            self.flush()

    def flush(self):
        if not self.buf:
            return
        b = self.buf
        params = np.array([[r["scenario"][k] for k in PARAM_NAMES] for r in b], dtype=np.float32)
        arr = np.stack([r["arrival"] / 60.0 for r in b]).astype(np.float16)
        path = os.path.join(self.out, f"shard_{self.shard:05d}.npz")
        np.savez_compressed(
            path, params=params, param_names=np.array(PARAM_NAMES),
            run_id=np.array([r["scenario"]["run_id"] for r in b], dtype=np.int32),
            arrival_min=arr,
            fuel=np.stack([r["fuel"] for r in b]).astype(np.uint8),
            altitude_m=np.stack([r["alt"] for r in b]).astype(np.float16),
            terrain=np.array([r["scenario"].get("terrain", "plane") for r in b]),
            burned_area_m2=np.array([r["burned_area_m2"] for r in b], dtype=np.float32),
            edge_hit=np.array([r["edge_hit"] for r in b]),
            t_sim_s=np.array([r["t_sim"] for r in b], dtype=np.float32))
        for i, r in enumerate(b):
            sc = r["scenario"]
            self.cw.writerow([self.shard, i, sc["run_id"], sc.get("terrain", "plane"), *[sc[k] for k in PARAM_NAMES],
                              round(r["burned_area_m2"]), int(r["edge_hit"]), r["n_front_nodes"],
                              round(r["t_sim"], 5), round(r["t_worker"], 5)])
        self.index.flush()
        self.shard += 1
        self.buf = []

    def close(self):
        self.flush()
        self.index.close()


def load(path):
    """Concatenate all shards. Returns dict of arrays + meta."""
    meta = json.load(open(os.path.join(path, "meta.json")))
    parts = [dict(np.load(f)) for f in sorted(glob.glob(os.path.join(path, "shard_*.npz")))]
    out = {k: np.concatenate([p[k] for p in parts]) for k in parts[0] if k != "param_names"}
    out["param_names"] = list(parts[0]["param_names"])
    out["meta"] = meta
    return out


def input_channels(params, fuel, n, dx, horizon_s, altitude=None):
    """Default surrogate input for ONE run: (C, n, n) float32.

    0 fuel spread-potential proxy (fuel index / 9, non-burnable = -1)
    1 altitude above tile minimum / 1000 m    2 slope-x (dz/dx)        3 slope-y (dz/dy)
    4 wind u (m/s, 20-ft) / 10   5 wind v / 10
    6 shifted wind u / 10        7 shifted wind v / 10    (applies after horizon/2)
    8 dead fuel moisture / 0.15  9 ignition (Gaussian blob, sigma = 2 cells)
    """
    p = dict(zip(PARAM_NAMES, params))
    L = n * dx
    ch = np.zeros((10, n, n), np.float32)
    f = fuel.astype(np.float32)
    ch[0] = np.where(fuel == sim.NONBURN, -1.0, f / 9.0)
    if altitude is None:  # planar-terrain datasets (schema v1) do not store altitude
        altitude = sim.make_altitude({"slope_deg": p["slope_deg"], "aspect_deg": p["aspect_deg"]}, n, L)
    altitude = np.asarray(altitude, np.float32)
    ch[1] = (altitude - altitude.min()) / 1000.0
    ch[2], ch[3] = np.gradient(altitude, dx)
    for k, d in ((4, p["wind_dir_deg"]), (6, p["wind_dir_deg"] + p["wind_shift_deg"])):
        th = math.radians(d)
        ch[k], ch[k + 1] = p["wind_speed"] * math.sin(th) / 10, p["wind_speed"] * math.cos(th) / 10
    ch[8] = p["md"] / 0.15
    x = (np.arange(n) + 0.5)
    X, Y = np.meshgrid(x, x, indexing="ij")
    ch[9] = np.exp(-((X - p["ign_x"] * n) ** 2 + (Y - p["ign_y"] * n) ** 2) / (2 * 2.0 ** 2))
    return ch
