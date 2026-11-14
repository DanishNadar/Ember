"""Scenario parameter space and samplers.

Every scenario is a flat dict that sim.run_scenario() understands. The sampled
parameters (PARAMS) are what a surrogate gets as input, together with the
fuel map and terrain that sim.py builds from them.
"""
import numpy as np

# name: (low, high, kind)   kind: "float" | "int" | "angle"
PARAMS = {
    "wind_speed":      (0.0, 10.0, "float"),   # 20-ft wind, m/s (midflame = 0.4x)
    "wind_dir_deg":    (0.0, 360.0, "angle"),  # direction the wind blows TO, 0 = +y (north)
    "wind_shift_deg":  (-60.0, 60.0, "float"), # wind direction change at horizon/2
    "md":              (0.03, 0.15, "float"),  # dead 1-h fuel moisture, ratio
    "fuel":            (1, 9, "int"),          # Andrews 2018 shrub model SH1..SH9
    "fuel2":           (1, 9, "int"),          # secondary fuel used in patches
    "fuel_patchiness": (0.0, 0.6, "float"),    # 0 = homogeneous fuel
    "slope_deg":       (0.0, 30.0, "float"),
    "aspect_deg":      (0.0, 360.0, "angle"),  # direction terrain rises toward
    "ign_x":           (0.3, 0.7, "float"),    # ignition, fraction of domain
    "ign_y":           (0.3, 0.7, "float"),
}
PARAM_NAMES = list(PARAMS)


# terrain modes: one kind, or a mix cycled run by run (dem only when a DEM file is given)
TERRAIN_KINDS = ["flat", "plane", "hills", "dem"]
TERRAINS = {"mix": ["flat", "plane", "hills"], "mix+dem": ["flat", "plane", "hills", "dem"]}


def sample(n_runs, n, dx, horizon_s, seed=0, fixed=None, ranges=None, terrain="hills", dem=None):
    """Uniform (Latin hypercube) sample of the scenario space. `ranges` overrides PARAMS bounds."""
    rng = np.random.default_rng(seed)
    fixed = fixed or {}
    space = {k: ((ranges or {}).get(k, v[:2]) + (v[2],)) for k, v in PARAMS.items()}
    cols = {}
    for name, (lo, hi, kind) in space.items():
        # Latin hypercube: one point in each of n_runs strata, shuffled
        u = (rng.permutation(n_runs) + rng.random(n_runs)) / n_runs
        if kind == "int":
            cols[name] = np.floor(lo + u * (hi - lo + 1)).astype(int).clip(lo, hi)
        else:
            cols[name] = lo + u * (hi - lo)
    out = []
    for i in range(n_runs):
        sc = {k: (int(v[i]) if space[k][2] == "int" else float(v[i])) for k, v in cols.items()}
        kinds = TERRAINS[terrain] if terrain in TERRAINS else [terrain]
        sc.update(n=n, dx=dx, horizon_s=float(horizon_s), seed=int(seed * 1_000_003 + i), run_id=i,
                  terrain=kinds[i % len(kinds)])
        if sc["terrain"] == "flat":
            sc["slope_deg"] = 0.0
        sc.update(dem or {})
        sc.update(fixed)
        out.append(sc)
    return out


# Out-of-distribution test region, never seen in training: the strongest winds and the
# heaviest shrub model. Keeps a random-split test set from flattering the surrogate.
HOLDOUT = {"wind_speed_above": 8.0, "fuel": 9}


def split(kind, n_runs, n, dx, horizon_s, seed=0, terrain="hills", dem=None):
    """'all' = whole space; 'train' (also use for val/test with other seeds) = holdout removed;
    'ood' = half high-wind runs, half SH9 runs."""
    if kind == "all":
        return sample(n_runs, n, dx, horizon_s, seed, terrain=terrain, dem=dem)
    if kind == "train":
        rng = {"wind_speed": (0.0, HOLDOUT["wind_speed_above"]), "fuel": (1, 8), "fuel2": (1, 8)}
        return sample(n_runs, n, dx, horizon_s, seed, ranges=rng, terrain=terrain, dem=dem)
    h = n_runs // 2
    a = sample(h, n, dx, horizon_s, seed, ranges={"wind_speed": (HOLDOUT["wind_speed_above"], 10.0)},
               terrain=terrain, dem=dem)
    b = sample(n_runs - h, n, dx, horizon_s, seed + 7, fixed={"fuel": HOLDOUT["fuel"]}, terrain=terrain, dem=dem)
    for i, sc in enumerate(b):
        sc["run_id"] = h + i
    return a + b


def ensemble_weather(base, n_runs, seed=0, wind_sd=1.5, dir_sd=20.0, md_sd=0.015):
    """Forecast-uncertainty ensemble: one landscape + ignition, perturbed weather.

    This is the operational use case (burn-probability map), as opposed to
    sample(), which covers the whole space for surrogate training.
    """
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n_runs):
        sc = dict(base)
        sc["wind_speed"] = float(max(0.0, base["wind_speed"] + rng.normal(0, wind_sd)))
        sc["wind_dir_deg"] = float((base["wind_dir_deg"] + rng.normal(0, dir_sd)) % 360)
        sc["md"] = float(np.clip(base["md"] + rng.normal(0, md_sd), 0.02, 0.4))
        sc["run_id"] = i
        out.append(sc)
    return out
