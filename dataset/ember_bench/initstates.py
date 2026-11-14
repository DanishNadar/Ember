"""Ember initial-state dataset: fire starts on a real landscape, ready for ForeFire and the net.

One sample = one fire start: a window of the landscape (fuel + terrain), an ignition (a point or
an elliptical burning area), wind speed and direction, a wind shift and when it happens, and dead
fuel moisture. ForeFire (labelling) and the surrogate (input tensor) read the SAME sample, so the
net and the physics always see identical conditions.

Everything that is a choice lives in a JSON config (configs/init_corsica.json); this file has no
ranges of its own. Any ForeFire-format landscape NetCDF (variables `fuel`, `altitude`, a `domain`
with Lx/Ly) plus its fuel table works, so a US map can be dropped in by writing a new config.

    python -m ember_bench.initstates build    --config configs/init_corsica.json --out ember_init_v1 [--layers]
    python -m ember_bench.initstates check    --out ember_init_v1            # stats, no ForeFire
    python -m ember_bench.initstates smoke    --out ember_init_v1 --runs 40  # label a few with ForeFire

Output per split (<out>/<split>/):
    samples.csv      one row per sample: every sampled value, window, ignition (human readable)
    scenarios.jsonl  one ForeFire-ready scenario per line (sim.run_scenario(json.loads(line)))
    layers_00000.npz only with --layers: fuel code [k,n,n] uint8, altitude [k,n,n] float16 (m),
                     ignition mask [k,n,n] uint8. Without it, TorchDataset crops data.nc on the fly.
    meta.json        config, grid, channel list, schema version
Input tensor for the net: input_tensor(...) -> (C, n, n) float32, channels in CHANNELS.
"""
import argparse
import csv
import glob
import json
import math
import os
import sys
import time

import numpy as np

from . import sim

SCHEMA_VERSION = 2   # v2: multi-region (region column, Farsite US engine), 21 channels
SHARD = 1000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONT = ["wind_speed", "wind_dir_deg", "wind_shift_deg", "wind_shift_t_frac", "md",
        "ign_win_x", "ign_win_y", "ign_a_m", "ign_aspect", "ign_orient_deg"]

# US Farsite runs also need 10-h, 100-h and live moistures. They are drawn from a separate random
# stream so that adding them never changes the core samples (Corsica rows stay identical to v1).
EXTRA = ["md_10h_offset", "md_100h_offset", "m_live_herb", "m_live_woody"]
ENGINES = {"corsica_native": 0, "farsite": 1}

CHANNELS = [
    ("burnable", "1 if the fuel class can burn, else 0"),
    ("fuel_depth_m", "fuel bed depth (m)"),
    ("dead_load_kg_m2", "dead fuel load (kg/m2): Corsica Sigmad; US 1h+10h+100h"),
    ("live_load_kg_m2", "live fuel load (kg/m2): US herb+woody; 0 for Corsica (its Rothermel ignores live fuel)"),
    ("sav_1_m", "dead 1-h surface-to-volume ratio (1/m)"),
    ("mext", "dead fuel moisture of extinction (ratio)"),
    ("alt_rel_m", "altitude above the window minimum (m)"),
    ("dzdx", "terrain gradient along +x (east), m/m"),
    ("dzdy", "terrain gradient along +y (north), m/m"),
    ("wind_u0", "wind toward +x before the shift (m/s)"),
    ("wind_v0", "wind toward +y before the shift (m/s)"),
    ("wind_u1", "wind toward +x after the shift (m/s)"),
    ("wind_v1", "wind toward +y after the shift (m/s)"),
    ("shift_t_frac", "time of the shift as a fraction of the horizon (constant plane)"),
    ("md", "dead 1-h fuel moisture ratio (constant plane)"),
    ("md_10h", "dead 10-h moisture (US only; 0 for Corsica)"),
    ("md_100h", "dead 100-h moisture (US only; 0 for Corsica)"),
    ("m_live_herb", "live herb moisture (US only; 0 for Corsica)"),
    ("m_live_woody", "live woody moisture (US only; 0 for Corsica)"),
    ("ignition", "1 inside the initial burning area (point = its one cell), else 0"),
    ("engine", "0 = Corsica classic Rothermel, 1 = Farsite (US); constant plane"),
]


# ---------------------------------------------------------------- config + landscape
def load_config(path):
    cfg = json.load(open(path))
    cfg["_dir"] = ROOT
    return cfg


def regions(top):
    """{region: single-region config}. A v1 config (no "regions" key) is one region, "corsica"."""
    if "regions" not in top:
        return {top.get("region", "corsica"): dict(top, region=top.get("region", "corsica"))}
    out = {}
    for name, rc in top["regions"].items():
        c = {k: v for k, v in top.items() if k != "regions"}
        c.update({k: v for k, v in rc.items() if k != "ranges"})
        c["ranges"] = dict(top.get("ranges", {}), **rc.get("ranges", {}))
        c["region"] = name
        c["_multi"] = True
        out[name] = c
    return out


def _p(cfg, rel):
    return rel if os.path.isabs(rel) else os.path.join(cfg.get("_dir", ROOT), rel)


class Landscape:
    def __init__(self, cfg):
        lc = cfg["landscape"]
        self.path = _p(cfg, lc["path"])
        d = sim.load_landscape_nc(self.path)
        self.fuel, self.Lx, self.Ly, self.fdx = d["fuel"], d["Lx"], d["Ly"], d["fuel_dx"]
        self.props = fuel_properties(_p(cfg, lc["fuel_table"]), lc.get("nonburnable", []), lc.get("engine", "corsica_native"))

    def burnable_at(self, x, y):
        i = np.clip((np.asarray(x) / self.fdx).astype(int), 0, self.fuel.shape[0] - 1)
        j = np.clip((np.asarray(y) / self.fdx).astype(int), 0, self.fuel.shape[1] - 1)
        return self.props["burnable"][self.fuel[i, j]] > 0


def fuel_properties(table, nonburnable, engine="corsica_native"):
    """Lookup arrays indexed by fuel code, SI units: burnable, depth, dead load, live load, SAV, mext."""
    keys = ("burnable", "depth", "dead", "live", "sav", "mext")
    if engine == "farsite":   # ForeFire STDfarsiteFuelsTable rows (US customary units)
        out = {k: np.zeros(256, np.float32) for k in keys}
        TAC, FT = 0.224170, 0.3048     # tons/acre -> kg/m2, ft -> m
        for r in json.load(open(table)):
            c = int(r[0]); h1, h10, h100, lh, lw = (float(v) for v in r[2:7])
            out["depth"][c], out["dead"][c], out["live"][c] = float(r[11]) * FT, (h1 + h10 + h100) * TAC, (lh + lw) * TAC
            out["sav"][c], out["mext"][c] = float(r[8]) * 3.28084, float(r[12])
            out["burnable"][c] = float((h1 + h10 + h100 + lh + lw) > 0 and c not in nonburnable)
        return out
    old = _corsica_properties(table, nonburnable)
    return {"burnable": old["burnable"], "depth": old["e"], "dead": old["Sigmad"], "live": np.zeros_like(old["e"]),
            "sav": old["sd"], "mext": old["me"]}


def _corsica_properties(table_csv, nonburnable):
    lines = open(table_csv).read().strip().splitlines()
    h = lines[0].split(";")
    rows = [l.split(";") for l in lines[1:]]
    top = max(int(r[h.index("Index")]) for r in rows) + 1
    out = {k: np.zeros(max(top, 256), np.float32) for k in ("burnable", "e", "Sigmad", "sd", "me")}
    for r in rows:
        c = int(r[h.index("Index")])
        for k in ("e", "Sigmad", "sd", "me"):
            out[k][c] = float(r[h.index(k)])
        out["burnable"][c] = float(out["e"][c] > 0 and c not in nonburnable and float(r[h.index("Md")]) <= 1.0)
    return out


# ---------------------------------------------------------------- sampling
def _lhs(rng, n, lo, hi):
    return lo + (rng.permutation(n) + rng.random(n)) / n * (hi - lo)


def _window_ok(cx, cy, L, land, box, region):
    x0, y0, x1, y1 = cx - L / 2, cy - L / 2, cx + L / 2, cy + L / 2
    if x0 < 0 or y0 < 0 or x1 > land.Lx or y1 > land.Ly:
        return False
    if box is None or region == "anywhere":
        return True
    bx, by = box["x"], box["y"]
    inside = x0 >= bx[0] and x1 <= bx[1] and y0 >= by[0] and y1 <= by[1]
    disjoint = x1 <= bx[0] or x0 >= bx[1] or y1 <= by[0] or y0 >= by[1]
    return inside if region == "inside_holdout" else disjoint


def sample_split(cfg, split, land=None):
    """Latin-hypercube sample of every continuous knob; ignition location uniform over burnable
    ground (rejection sampling), window placed around it so the ignition sits at (ign_win_x,
    ign_win_y) of the window and the window obeys the split's region rule."""
    land = land or Landscape(cfg)
    sp = cfg["splits"][split]
    n_s, seed, region = sp["count"], sp["seed"], sp.get("region", "anywhere")
    g = cfg["grid"]
    L = g["n"] * g["dx_m"]                       # reference window: places the ignition
    L_rule = max(L, cfg.get("max_window_m", L))  # any labeller window up to this size obeys the split rule
    rng = np.random.default_rng(seed)
    cols = {k: _lhs(rng, n_s, *cfg["ranges"][k]) for k in CONT}
    w = cfg.get("ign_shape_weights", {"point": 1.0})
    names = list(w)
    cum = np.cumsum([w[k] for k in names]) / sum(w.values())
    shape = np.array(names)[np.searchsorted(cum, (rng.permutation(n_s) + rng.random(n_s)) / n_s)]
    box = cfg.get("holdout_box_m")
    rx = np.random.default_rng(seed + 7_777_777)          # separate stream for engine-specific extras
    extra = {k: _lhs(rx, n_s, *cfg["ranges"][k]) for k in EXTRA if k in cfg["ranges"]}
    reg_name = cfg.get("region")
    rows, tries = [], 0
    for i in range(n_s):
        fx, fy = cols["ign_win_x"][i], cols["ign_win_y"][i]
        for _ in range(100000):
            tries += 1
            x, y = rng.random() * land.Lx, rng.random() * land.Ly
            cx, cy = x + (0.5 - fx) * L, y + (0.5 - fy) * L
            if land.burnable_at(x, y) and _window_ok(cx, cy, L_rule, land, box, region):
                break
        else:
            raise RuntimeError(f"{split}: no valid ignition found; region/holdout too restrictive")
        r = {"sample_id": (f"{reg_name}-" if cfg.get("_multi") else "") + f"{split}-{i:06d}",
             "region": reg_name or "corsica", "group": cfg.get("group", reg_name or "corsica"), "split": split, "seed": int(seed * 1_000_003 + i),
             "ign_shape": str(shape[i]), "ign_x_m": float(x), "ign_y_m": float(y),
             "crop_cx": float(cx), "crop_cy": float(cy)}
        r.update({k: float(cols[k][i]) for k in CONT})
        if r["ign_shape"] == "point":
            r.update(ign_a_m=0.0, ign_aspect=1.0, ign_orient_deg=0.0)
        r["ign_b_m"] = max(r["ign_a_m"] * r["ign_aspect"], g["dx_m"] / 2) if r["ign_shape"] != "point" else 0.0
        r["wind_shift_t_s"] = r["wind_shift_t_frac"] * g["horizon_s"]   # at the reference horizon
        if extra:   # absolute 10-h / 100-h moistures = 1-h moisture + sampled offsets
            r["md_10h"] = r["md"] + float(extra["md_10h_offset"][i])
            r["md_100h"] = r["md_10h"] + float(extra["md_100h_offset"][i])
            r["m_live_herb"], r["m_live_woody"] = float(extra["m_live_herb"][i]), float(extra["m_live_woody"][i])
        else:
            r.update(md_10h=0.0, md_100h=0.0, m_live_herb=0.0, m_live_woody=0.0)
        r["engine"] = cfg["landscape"].get("engine", "corsica_native")
        r["fuel_source"] = cfg["landscape"].get("fuel_source", "real")
        rows.append(r)
    return rows, tries


# ---------------------------------------------------------------- one sample -> ForeFire / tensor
def _grid(cfg, grid):
    return grid or cfg["grid"]


def ign_in_window(r, cfg, grid=None):
    """Ignition centre in window metres for a window of this grid centred on (crop_cx, crop_cy)."""
    g = _grid(cfg, grid); L = g["n"] * g["dx_m"]
    return r["ign_x_m"] - r["crop_cx"] + L / 2, r["ign_y_m"] - r["crop_cy"] + L / 2, L


def ignition_polygon(r, cfg, grid=None):
    """Ellipse ring in WINDOW metres (None for a point ignition). Node spacing <= dx/2."""
    if r["ign_shape"] == "point":
        return None
    g = _grid(cfg, grid)
    a, b, th = r["ign_a_m"], r["ign_b_m"], math.radians(r["ign_orient_deg"])
    per = math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))   # Ramanujan
    k = max(12, int(math.ceil(per / (g["dx_m"] / 2))))
    t = np.linspace(0, 2 * math.pi, k, endpoint=False)
    ex, ey = a * np.cos(t), b * np.sin(t)
    cx, cy, L = ign_in_window(r, cfg, grid)
    xs = np.clip(cx + ex * math.cos(th) - ey * math.sin(th), 1.0, L - 1.0)
    ys = np.clip(cy + ex * math.sin(th) + ey * math.cos(th), 1.0, L - 1.0)
    return [(float(x), float(y)) for x, y in zip(xs, ys)]


def to_scenario(r, cfg, grid=None):
    """sim.run_scenario() dict for this sample (ForeFire labelling). `grid` = {n, dx_m, horizon_s}
    overrides the reference grid; the window stays centred on (crop_cx, crop_cy)."""
    g = _grid(cfg, grid)
    ix, iy, L = ign_in_window(r, cfg, grid)
    sc = dict(n=g["n"], dx=g["dx_m"], horizon_s=float(g["horizon_s"]), run_id=r["sample_id"], seed=int(r["seed"]),
              landscape_nc=_p(cfg, cfg["landscape"]["path"]), crop_cx=r["crop_cx"], crop_cy=r["crop_cy"],
              terrain="landscape", wind_speed=r["wind_speed"], wind_dir_deg=r["wind_dir_deg"],
              wind_shift_deg=r["wind_shift_deg"], wind_shift_t_s=r["wind_shift_t_frac"] * float(g["horizon_s"]),
              md=r["md"], ign_x=ix / L, ign_y=iy / L,
              # keys of the Ember-Synth schema that a real landscape does not use (dataset.Writer needs them)
              fuel=0, fuel2=0, fuel_patchiness=0.0, slope_deg=0.0, aspect_deg=0.0)
    sc["region"] = r.get("region", "corsica")
    eng = cfg["landscape"].get("engine", "corsica_native")
    if eng == "corsica_native" or cfg["landscape"].get("forefire_settings") == "CORSICA_NATIVE":
        sc.update(json.loads(json.dumps(sim.CORSICA_NATIVE)))
    elif eng == "farsite":
        # Farsite + STDfarsiteFuelsTable; sim applies WAF 0.4 (20-ft -> midflame) and the mph / slope fixes
        sc.update(fuel_set="farsite", model="Farsite", waf=sim.WAF, md_10h=r["md_10h"], md_100h=r["md_100h"],
                  m_live_herb=r["m_live_herb"], m_live_woody=r["m_live_woody"],
                  ff_params={"minSpeed": 0.0})
    poly = ignition_polygon(r, cfg, grid)
    if poly:
        sc["ign_polygon"] = poly
    return sc


def ignition_mask(r, cfg, grid=None):
    g = _grid(cfg, grid); n, dx = g["n"], g["dx_m"]
    m = np.zeros((n, n), np.uint8)
    ix, iy, L = ign_in_window(r, cfg, grid)
    ci, cj = min(n - 1, max(0, int(ix / dx))), min(n - 1, max(0, int(iy / dx)))
    if r["ign_shape"] == "point":
        m[ci, cj] = 1
        return m
    c = (np.arange(n) + 0.5) * dx
    X, Y = np.meshgrid(c, c, indexing="ij")
    th = math.radians(r["ign_orient_deg"])
    dxp, dyp = X - ix, Y - iy
    u = dxp * math.cos(th) + dyp * math.sin(th)
    v = -dxp * math.sin(th) + dyp * math.cos(th)
    m[(u / r["ign_a_m"]) ** 2 + (v / r["ign_b_m"]) ** 2 <= 1.0] = 1
    if not m.any():
        m[ci, cj] = 1
    return m


def layers(r, cfg, grid=None):
    """fuel code [n,n] int, altitude [n,n] m, ignition mask [n,n] for one sample ([x, y] order)."""
    g = _grid(cfg, grid)
    fuel, alt = sim.landscape_crop({"landscape_nc": _p(cfg, cfg["landscape"]["path"]),
                                    "crop_cx": r["crop_cx"], "crop_cy": r["crop_cy"]}, g["n"], g["n"] * g["dx_m"])
    return fuel, alt, ignition_mask(r, cfg, grid)


def input_tensor(r, fuel, alt, ign, props, dx):
    """(C, n, n) float32 in physical units, channel order = CHANNELS. Normalise in the training code."""
    n = fuel.shape[0]
    ch = np.zeros((len(CHANNELS), n, n), np.float32)
    f = np.clip(fuel.astype(np.int64), 0, 255)
    for c, k in enumerate(("burnable", "depth", "dead", "live", "sav", "mext")):
        ch[c] = props[k][f]
    alt = alt.astype(np.float32)
    ch[6] = alt - alt.min()
    ch[7], ch[8] = np.gradient(alt, dx)
    for k, d in ((9, r["wind_dir_deg"]), (11, r["wind_dir_deg"] + r["wind_shift_deg"])):
        th = math.radians(d)
        ch[k], ch[k + 1] = r["wind_speed"] * math.sin(th), r["wind_speed"] * math.cos(th)
    ch[13] = r["wind_shift_t_frac"]
    for c, k in enumerate(("md", "md_10h", "md_100h", "m_live_herb", "m_live_woody")):
        ch[14 + c] = float(r.get(k, 0.0))
    ch[19] = ign
    ch[20] = ENGINES[r.get("engine", "corsica_native")]
    return ch


# ---------------------------------------------------------------- write / load
def build(cfg, out, splits=None, with_layers=False):
    land = Landscape(cfg)
    for split in splits or list(cfg["splits"]):
        t0 = time.time()
        rows, tries = sample_split(cfg, split, land)
        d = os.path.join(out, split)
        os.makedirs(d, exist_ok=True)
        keys = list(rows[0])
        with open(os.path.join(d, "samples.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
        with open(os.path.join(d, "scenarios.jsonl"), "w") as fh:
            for r in rows:
                fh.write(json.dumps(to_scenario(r, cfg)) + "\n")
        if with_layers:
            for s0 in range(0, len(rows), SHARD):
                chunk = rows[s0:s0 + SHARD]
                F, A, I = zip(*(layers(r, cfg) for r in chunk))
                np.savez_compressed(os.path.join(d, f"layers_{s0 // SHARD:05d}.npz"),
                                    sample_id=np.array([r["sample_id"] for r in chunk]),
                                    fuel=np.stack(F).astype(np.uint8), alt_m=np.stack(A).astype(np.float16),
                                    ignition=np.stack(I).astype(np.uint8))
        meta = {"schema_version": SCHEMA_VERSION, "split": split, "count": len(rows),
                "grid": cfg["grid"], "array_index_order": "[sample, x, y]; x = east, y = north; cell (i,j) centre = ((i+.5)dx, (j+.5)dx) in window metres",
                "wind_convention": "wind_dir_deg = direction the wind blows TOWARD, 0 = +y (north), 90 = +x (east). Meteorological 'from' = (dir + 180) % 360",
                "wind_height": "20-ft wind. Corsica: given to ForeFire as is, CORSICA_NATIVE applies windReductionFactor 0.4 inside Rothermel. US/Farsite: sim multiplies by WAF 0.4 and passes mph (Farsite unit bug)",
                "region": cfg.get("region", "corsica"), "engine": cfg["landscape"].get("engine", "corsica_native"),
                "fuel_source": cfg["landscape"].get("fuel_source", "real"),
                "channels": CHANNELS, "continuous_params": CONT, "config": {k: v for k, v in cfg.items() if k != "_dir"},
                "ignition_rejection_tries": tries, "built_s": round(time.time() - t0, 1)}
        json.dump(meta, open(os.path.join(d, "meta.json"), "w"), indent=1)
        print(f"{split}: {len(rows)} samples, {tries} location draws, {time.time() - t0:.1f}s", flush=True)


def build_all(top, out, only=None, splits=None, with_layers=False):
    """Every region into <out>/<region>/<split>/, then <out>/all_samples.csv (region column)."""
    regs = regions(top)
    for name, rc in regs.items():
        if only and name not in only:
            continue
        print(f"== region {name}", flush=True)
        build(rc, os.path.join(out, name), splits, with_layers)
    rows, keys = [], []
    for name in regs:
        for split in regs[name]["splits"]:
            f = os.path.join(out, name, split, "samples.csv")
            if os.path.exists(f):
                for r in csv.DictReader(open(f)):
                    rows.append(r)
                    keys += [k for k in r if k not in keys]
    with open(os.path.join(out, "all_samples.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, restval=""); w.writeheader(); w.writerows(rows)
    print(f"all_samples.csv: {len(rows)} rows", flush=True)


def load_split(out, split):
    """dict: rows (list of dicts), fuel/alt_m/ignition arrays (if written), meta."""
    d = os.path.join(out, split)
    rows = list(csv.DictReader(open(os.path.join(d, "samples.csv"))))
    for r in rows:
        for k, v in r.items():
            if k not in ("sample_id", "split", "ign_shape", "region", "group", "engine", "fuel_source"):
                r[k] = float(v)
    res = {"rows": rows, "meta": json.load(open(os.path.join(d, "meta.json")))}
    parts = [dict(np.load(f)) for f in sorted(glob.glob(os.path.join(d, "layers_*.npz")))]
    if parts:
        for k in parts[0]:
            res[k] = np.concatenate([p[k] for p in parts])
    return res


class TorchDataset:
    """Minimal map-style dataset: ds[i] -> (input (C,n,n) float32, sample row). Wrap targets
    (ForeFire arrival maps, keyed by sample_id) in the training code once labelling has run."""

    def __init__(self, out, split, cfg=None, grid=None):
        self.s = load_split(out, split)
        self.cfg = cfg or dict(self.s["meta"]["config"], _dir=ROOT)
        self.grid = grid or self.cfg["grid"]
        lc = self.cfg["landscape"]
        self.props = fuel_properties(_p(self.cfg, lc["fuel_table"]), lc.get("nonburnable", []), lc.get("engine", "corsica_native"))
        # stored layer shards are only valid for the grid they were built at
        self.stored = "fuel" in self.s and self.grid == self.s["meta"]["grid"]

    def __len__(self):
        return len(self.s["rows"])

    def __getitem__(self, i):
        r = self.s["rows"][i]
        if self.stored:
            f, a, ig = self.s["fuel"][i], self.s["alt_m"][i].astype(np.float32), self.s["ignition"][i]
        else:   # crop from the landscape on the fly (about 20 ms at 320^2); deterministic
            f, a, ig = layers(r, self.cfg, self.grid)
        return input_tensor(r, f, a, ig, self.props, self.grid["dx_m"]), r


# ---------------------------------------------------------------- checks
def _split_dirs(out):
    for root, dirs, files in sorted(os.walk(out)):
        if "meta.json" in files and "samples.csv" in files:
            yield os.path.relpath(root, out)


def check(out):
    for split in _split_dirs(out):
        s = load_split(out, split)
        rows, cfg = s["rows"], dict(s["meta"]["config"], _dir=ROOT)
        print(f"\n== {split}: {len(rows)} samples")
        for k in CONT:
            v = np.array([r[k] for r in rows])
            print(f"  {k:18s} min {v.min():9.3f}  max {v.max():9.3f}  mean {v.mean():9.3f}")
        sh = {}
        for r in rows:
            sh[r["ign_shape"]] = sh.get(r["ign_shape"], 0) + 1
        print("  ignition shapes", sh)
        if "fuel" in s:
            props = fuel_properties(_p(cfg, cfg["landscape"]["fuel_table"]), cfg["landscape"].get("nonburnable", []),
                                    cfg["landscape"].get("engine", "corsica_native"))
            bf = props["burnable"][s["fuel"].astype(int)].mean(axis=(1, 2))
            ign_ok = np.array([(props["burnable"][s["fuel"][i].astype(int)] * s["ignition"][i]).any() for i in range(len(rows))])
            print(f"  burnable fraction of window: p5 {np.percentile(bf,5):.2f} median {np.median(bf):.2f} p95 {np.percentile(bf,95):.2f}")
            print(f"  ignition touches burnable fuel: {ign_ok.mean()*100:.1f}%")
            relief = (s["alt_m"].astype(np.float32).max(axis=(1, 2)) - s["alt_m"].astype(np.float32).min(axis=(1, 2)))
            print(f"  window relief (m): median {np.median(relief):.0f}  max {relief.max():.0f}")
        cx = np.array([r["crop_cx"] for r in rows]); cy = np.array([r["crop_cy"] for r in rows])
        print(f"  window centres x {cx.min()/1e3:.1f}-{cx.max()/1e3:.1f} km, y {cy.min()/1e3:.1f}-{cy.max()/1e3:.1f} km")


def scenarios_for(out, split):
    """ForeFire scenario dicts for a split. Read from scenarios.jsonl when present, otherwise rebuilt
    from samples.csv + the config in meta.json (to_scenario is deterministic), with landscape paths
    resolved against this checkout instead of the absolute paths baked into a jsonl."""
    f = os.path.join(out, split, "scenarios.jsonl")
    if os.path.exists(f):
        return [json.loads(l) for l in open(f).read().splitlines()]
    s = load_split(out, split)
    cfg = dict(s["meta"]["config"]); cfg["_dir"] = ROOT
    return [to_scenario(r, cfg) for r in s["rows"]]


def smoke(out, split, runs, workers=0):
    """Label `runs` samples with ForeFire: proves the scenarios run, reports cost and edge hits."""
    from . import runner
    scs_all = scenarios_for(out, split)
    rng = np.random.default_rng(0)
    pick = rng.choice(len(scs_all), size=min(runs, len(scs_all)), replace=False)
    scs = [scs_all[i] for i in pick]
    res = list(runner.run_many(scs, workers=workers, progress=False))
    ok = [r for r in res if r.get("ok")]
    bad = [r for r in res if not r.get("ok")]
    ts = np.array([r["t_sim"] for r in ok]); area = np.array([r["burned_area_m2"] / 1e6 for r in ok])
    edge = np.array([r["edge_hit"] for r in ok])
    print(f"{split}: {len(ok)} ok, {len(bad)} failed" + (f" (first error: {bad[0].get('error')})" if bad else ""))
    if ok:
        print(f"  solve s: median {np.median(ts):.3f} p90 {np.percentile(ts,90):.3f} max {ts.max():.3f}")
        print(f"  burned km2: median {np.median(area):.2f} p90 {np.percentile(area,90):.2f} max {area.max():.2f}")
        print(f"  edge hits: {edge.mean()*100:.1f}%  zero-spread (<= ignition): "
              f"{np.mean([r['burned_area_m2'] <= 2 * r['scenario']['dx']**2 for r in ok])*100:.1f}%")
        ws = np.array([r["scenario"]["wind_speed"] for r in ok])
        for lo, hi in ((0, 5), (5, 10), (10, 15), (15, 20.01)):
            m = (ws >= lo) & (ws < hi)
            if m.any():
                print(f"  wind {lo:>2}-{hi:<5.0f} n={m.sum():3d} edge {edge[m].mean()*100:5.1f}%  median solve {np.median(ts[m]):.3f}s")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m ember_bench.initstates")
    ap.add_argument("cmd", choices=["build", "check", "smoke"])
    ap.add_argument("--config", default=os.path.join(ROOT, "configs", "init_corsica.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "ember_init_v1"))
    ap.add_argument("--splits", nargs="*")
    ap.add_argument("--regions", nargs="*")
    ap.add_argument("--layers", action="store_true", help="also write fuel/alt/ignition shards (~165 MB per 1000 at 320^2)")
    ap.add_argument("--split", default="train")
    ap.add_argument("--runs", type=int, default=40)
    ap.add_argument("--workers", type=int, default=0)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        top = load_config(a.config)
        if "regions" in top:
            build_all(top, a.out, a.regions, a.splits, a.layers)
        else:
            build(top, a.out, a.splits, a.layers)
    elif a.cmd == "check":
        check(a.out)
    else:
        smoke(a.out, a.split, a.runs, a.workers)


if __name__ == "__main__":
    main()
