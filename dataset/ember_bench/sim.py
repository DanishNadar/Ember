"""One ForeFire run from a scenario dict -> arrays + timings.

ForeFire keeps process-global state, so call run_scenario() exactly once per
process (the sweep driver uses a fresh worker per task).
"""
import math, time
import numpy as np

# Andrews (2018) SH shrub fuel models 1..9, standard Rothermel inputs.
# Columns: Index;fl1h_tac;fd_ft;Dme_pc;SAVcar_ftinv;H_BTUlb;fuelDens_lbft3;totMineral_r;effectMineral_r;mdOnDry1h_r
SH = {1:(0.25,1.0,15,1674),2:(1.35,1.0,15,1672),3:(0.45,2.4,40,1371),4:(0.85,3.0,30,1682),
      5:(3.6,6.0,15,1252),6:(2.9,2.0,30,1144),7:(3.5,6.0,15,1233),8:(2.05,3.0,40,1386),9:(4.5,4.4,40,1378)}
# Extra US fuel models (Scott & Burgan 2005), 1-h dead load only, same columns as SH. APPROXIMATE
# values from the standard table, not re-checked; grass models ignore live-herb curing transfer.
US_EXTRA = {11: ("GR2", 0.10, 1.0, 15, 2000), 12: ("GR4", 0.25, 2.0, 15, 2000),
            21: ("TU1", 0.20, 0.6, 20, 2000), 31: ("TL3", 0.50, 0.3, 20, 2000)}
NONBURN = 99   # firebreak / rock index, zero fuel load
WAF = 0.4      # wind adjustment factor, 20-ft wind -> midflame wind

def fuel_table(md):
    rows = ["Index;fl1h_tac;fd_ft;Dme_pc;SAVcar_ftinv;H_BTUlb;fuelDens_lbft3;totMineral_r;effectMineral_r;mdOnDry1h_r"]
    for k,(l,d,me,sav) in SH.items():
        rows.append(f"{k};{l};{d};{me};{sav};8000;32;0.0555;0.010;{md}")
    for k,(_,l,d,me,sav) in US_EXTRA.items():
        rows.append(f"{k};{l};{d};{me};{sav};8000;32;0.0555;0.010;{md}")
    rows.append(f"{NONBURN};0.0;0.01;15;1500;8000;32;0.0555;0.010;{md}")
    return "\n".join(rows)

# Physical (Balbi-family / classic Rothermel) models read this column set instead.
# Row = Mediterranean shrub (index 82 of ForeFire's tests/runff/fuels.csv); every SH index
# maps to it, NONBURN gets zero depth. Moisture Md is a ratio; me = extinction moisture.
BALBI_MODELS = {"Rothermel", "BalbiNov2011", "Balbi2015", "Balbi2020", "BalbiUnsteady"}


def fuel_table_balbi(md, me=0.30):
    hdr = "Index;Rhod;Rhol;Md;Ml;sd;sl;e;Sigmad;Sigmal;stoch;RhoA;Ta;Tau0;Deltah;DeltaH;Cp;Cpa;Ti;X0;r00;Blai;me"
    row = lambda k, e: (f"{k};614.0;613.0;{md};1.0;4287.0;5738.0;{e};1.378;0.174;8.3;1.0;300;70000;"
                        f"18727000.0;18727000.0;1800;1000;600;0.3;2.5e-05;4.0;{me}")
    return "\n".join([hdr] + [row(k, 0.4) for k in SH] + [row(NONBURN, 0.0)])


# ---- Corsica (ForeFire's real case, Aullene): its own 111-class Mediterranean fuel table ----
# Different model family from the US set: ForeFire "Rothermel" with SI columns (e = fuel depth m,
# Sigmad = dead load kg/m2, Md = dead moisture ratio, me = 0.30 for every class).
import os as _os
CORSICA_CSV = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "corsica_fuels.csv")


def corsica_table(md):
    lines = open(CORSICA_CSV).read().strip().splitlines()
    hdr = lines[0].split(";"); im = hdr.index("Md")
    out = [lines[0]]
    for ln in lines[1:]:
        c = ln.split(";")
        if md is not None and float(c[im]) <= 1.0:   # keep the table's "never burns" rows (Md > 1)
            c[im] = repr(float(md))
        out.append(";".join(c))
    return "\n".join(out)


# Settings of ForeFire's own Aullene case (tests/runff/params.ff). Wind is given to ForeFire as is
# (sc["waf"] = 1.0), exactly like real_case.ff's trigger[wind;vel=(10.09,0.68,0)].
CORSICA_NATIVE = {"ff_params": {"propagationSpeedAdjustmentFactor": 0.6, "minSpeed": 0.009,
                                "windReductionFactor": 0.4, "relax": 0.5},
                  "waf": 1.0, "fuel_set": "corsica", "model": "Rothermel"}
NONBURN_CORSICA = [0, 62, 105, 106, 121, 162]   # zero fuel depth in the table (162 = sea)
# CORINE Land Cover classes of the Corsica table (Aullene landscape is CLC-coded), with an
# approximate Corsica land-cover share used for the synthetic mosaic (CLC 2018, rounded).
CLC = {231: ("pasture", 0.04), 243: ("agriculture + natural", 0.04), 311: ("broad-leaved forest", 0.16),
       312: ("coniferous forest", 0.08), 313: ("mixed forest", 0.05), 321: ("natural grassland", 0.05),
       322: ("moors and heathland", 0.07), 323: ("sclerophyllous maquis", 0.30),
       324: ("transitional woodland-shrub", 0.11), 333: ("sparse vegetation", 0.03),
       332: ("bare rock (non-burnable)", 0.04), 112: ("urban (non-burnable)", 0.03)}


def corsica_classes():
    """Burnable class indices (fuel depth e > 0) of the Corsica table."""
    lines = open(CORSICA_CSV).read().strip().splitlines()
    hdr = lines[0].split(";"); ie, ii = hdr.index("e"), hdr.index("Index")
    return [int(l.split(";")[ii]) for l in lines[1:] if float(l.split(";")[ie]) > 0]


_LAND = {}


def load_landscape_nc(path):
    """ForeFire landscape NetCDF (tests/runff/data.nc, the Aullene case). Returns a dict with
    fuel [x, y] int16 and altitude [x, y] float32 plus their own cell sizes (in data.nc the fuel is
    6400^2 at 10 m and altitude 640^2 at 100 m over 64 x 64 km). NetCDF rows are y from the south
    (checked: sea in the west, high mountains in the north-east). Cached; preloaded before forking."""
    if path not in _LAND and path.endswith(".npz"):     # us_landscape.py output, same keys
        z = np.load(path)
        _LAND[path] = dict(fuel=z["fuel"].astype(np.int16), alt=z["alt"].astype(np.float32), Lx=float(z["Lx"]),
                           Ly=float(z["Ly"]), fuel_dx=float(z["fuel_dx"]), alt_dx=float(z["alt_dx"]),
                           bbox=str(z["fuel_source"]))
    if path not in _LAND:
        import netCDF4
        ds = netCDF4.Dataset(path)
        dom = ds["domain"]
        Lx, Ly = float(dom.Lx), float(dom.Ly)
        fuel = np.asarray(ds["fuel"][:]).reshape(ds["fuel"].shape[-2:]).T.astype(np.int16)
        alt = np.asarray(ds["altitude"][:]).reshape(ds["altitude"].shape[-2:]).T.astype(np.float32)
        _LAND[path] = dict(fuel=fuel, alt=alt, Lx=Lx, Ly=Ly, fuel_dx=Lx / fuel.shape[0],
                           alt_dx=Lx / alt.shape[0], bbox=getattr(dom, "BBoxWSEN", ""))
    return _LAND[path]


def landscape_crop(sc, n, L):
    """n x n window of size L (m) from the landscape, centred at (crop_cx, crop_cy) metres in the
    landscape's own frame. Fuel: nearest sample; altitude: bilinear."""
    d = load_landscape_nc(sc["landscape_nc"])
    cx, cy = sc.get("crop_cx", d["Lx"] / 2), sc.get("crop_cy", d["Ly"] / 2)
    x0, y0 = cx - L / 2, cy - L / 2
    if x0 < 0 or y0 < 0 or x0 + L > d["Lx"] or y0 + L > d["Ly"]:
        raise ValueError("crop outside landscape")
    c = (np.arange(n) + 0.5) * L / n
    X, Y = x0 + c, y0 + c
    fi = np.clip((X / d["fuel_dx"]).astype(int), 0, d["fuel"].shape[0] - 1)
    fj = np.clip((Y / d["fuel_dx"]).astype(int), 0, d["fuel"].shape[1] - 1)
    fuel = d["fuel"][np.ix_(fi, fj)].astype(np.int32)
    A = d["alt"]; ax = np.clip(X / d["alt_dx"] - 0.5, 0, A.shape[0] - 1.001); ay = np.clip(Y / d["alt_dx"] - 0.5, 0, A.shape[1] - 1.001)
    i, j = ax.astype(int), ay.astype(int); u, v = ax - i, ay - j
    alt = ((1 - u)[:, None] * (1 - v)[None] * A[np.ix_(i, j)] + u[:, None] * (1 - v)[None] * A[np.ix_(i + 1, j)]
           + (1 - u)[:, None] * v[None] * A[np.ix_(i, j + 1)] + u[:, None] * v[None] * A[np.ix_(i + 1, j + 1)])
    return fuel, np.maximum(alt, 0.0)


def make_fuel_map(sc, n, rng):
    if sc.get("fuel_set") == "corsica" and not sc.get("landscape_nc"):
        # synthetic Mediterranean mosaic from Corsica classes until the real map is available
        k = max(2, n // 12)
        if sc.get("corsica_class"):                       # homogeneous single class
            pick = np.full((k, k), int(sc["corsica_class"]))
        elif sc.get("corsica_mix", "clc") == "clc":       # land-cover-weighted CLC mosaic
            codes = np.array(list(CLC)); w = np.array([v[1] for v in CLC.values()])
            pick = rng.choice(codes, size=(k, k), p=w / w.sum())
        else:
            pick = rng.choice(corsica_classes(), size=(k, k))
        idx = (np.arange(n) * k // n)
        f = pick[np.ix_(idx, idx)].astype(np.int32)
        het = sc.get("fuel_patchiness", 0.0)
        coarse = rng.random((k, k))[np.ix_(idx, idx)]
        f[coarse > 1 - het * 0.15] = 0          # class 0 has zero depth: non-burnable
        return f
    return _make_fuel_map_us(sc, n, rng)


def _make_fuel_map_us(sc, n, rng):
    """Main fuel everywhere; optional random patches of a second fuel and non-burnable."""
    f = np.full((n, n), sc["fuel"], dtype=np.int32)
    het = sc.get("fuel_patchiness", 0.0)
    if het > 0:
        # smooth random field -> patches
        k = max(2, n // 16)
        coarse = rng.random((k, k))
        idx = (np.arange(n) * k // n)
        field = coarse[np.ix_(idx, idx)]
        f[field < het * 0.5] = sc.get("fuel2", 1)
        f[field > 1 - het * 0.15] = NONBURN
    return f

_DEM = {}


def load_dem(path):
    """Real elevation for terrain="dem". Accepts .npy (2-D metres, [x, y], cell size given by
    `dem_dx`) or a ForeFire/NetCDF landscape with an `altitude` variable (needs netCDF4).
    Cached per process; runner.run_many() preloads it before forking so workers share it."""
    if path not in _DEM:
        if path.endswith(".npy"):
            _DEM[path] = np.load(path).astype(np.float32)
        else:
            import netCDF4
            v = np.asarray(netCDF4.Dataset(path)["altitude"][:], dtype=np.float32)
            _DEM[path] = v.reshape(v.shape[-2:]).T if v.ndim > 2 else v.T   # NetCDF is (y, x)
    return _DEM[path]


def dem_crop(sc, n, L):
    """Random window of the DEM covering L x L metres, resampled to n x n (nearest)."""
    dem = load_dem(sc["dem_path"])
    ddx = float(sc.get("dem_dx", 30.0))
    w = int(round(L / ddx))
    if w > min(dem.shape):
        raise ValueError(f"DEM {dem.shape} at {ddx} m is smaller than the {L:.0f} m domain")
    rng = np.random.default_rng(sc.get("terrain_seed", sc.get("seed", 0)) + 104729)
    i0, j0 = rng.integers(0, dem.shape[0] - w + 1), rng.integers(0, dem.shape[1] - w + 1)
    idx = (np.arange(n) * w // n)
    z = dem[i0 + idx][:, j0 + idx].astype(np.float64)
    return z - z.min()


def make_altitude(sc, n, L):
    """Terrain in metres, indexed [x, y].

    terrain="flat": zero.  terrain="dem": random crop of a real DEM (dem_path, dem_dx); slope_deg
    and aspect_deg are then ignored.
    terrain="plane": planar slope of `slope_deg` rising toward `aspect_deg` (0=+y north, 90=+x east).
    terrain="hills": smooth random hills (Gaussian-filtered noise, feature size ~L/6, seeded by
    `terrain_seed` or `seed`), scaled so the 90th-percentile slope equals `slope_deg`, plus a
    gentle regional tilt toward `aspect_deg` (1/4 of `slope_deg`).
    """
    s = math.tan(math.radians(sc["slope_deg"]))
    a = math.radians(sc["aspect_deg"])
    x = (np.arange(n) + 0.5) * L / n
    X, Y = np.meshgrid(x, x, indexing="ij")    # ForeFire layers are (x, y)
    plane = X * math.sin(a) + Y * math.cos(a)
    kind = sc.get("terrain", "plane")
    if kind == "flat":
        return np.zeros((n, n))
    if kind == "dem":
        return dem_crop(sc, n, L)
    if kind != "hills":
        return s * plane
    rng = np.random.default_rng(sc.get("terrain_seed", sc.get("seed", 0)) + 7919)
    k = np.fft.fftfreq(n)
    KX, KY = np.meshgrid(k, k, indexing="ij")
    sigma = n / 6.0 / (2 * math.pi)             # feature size ~ L/6
    filt = np.exp(-0.5 * (KX ** 2 + KY ** 2) * (2 * math.pi * sigma) ** 2)
    z = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * filt))
    gx, gy = np.gradient(z, L / n)
    g90 = np.percentile(np.hypot(gx, gy), 90)
    z = z * (s / g90 if g90 > 0 else 0.0)
    z -= z.min()
    return z + 0.25 * s * plane

def start_front(ff, pts, depth):
    """Start a fire from a closed polygon [(x, y), ...] in domain metres. ForeFire grows a front
    outward only when its nodes run clockwise (checked: counter-clockwise fronts burn inward),
    so the ring is reoriented here."""
    pts = [(float(x), float(y)) for x, y in pts]
    area2 = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area2 > 0:                       # counter-clockwise -> reverse
        pts = pts[::-1]
    ff.execute("FireFront[id=2;domain=0;t=0]")
    for i, (x, y) in enumerate(pts):
        ff.execute(f"\tFireNode[domain=0;id={4 + 2 * i};fdepth={depth};kappa=0;loc=({x},{y},0);"
                   f"vel=(0,0,0);t=0;state=init;frontId=2]")


def run_scenario(sc, out_n=None, capture_front=False):
    """sc keys: n (cells/side), dx (m), horizon_s, wind_speed (20-ft wind, m/s), wind_dir_deg (direction
    the wind blows TO, 0=north/+y, 90=east/+x), wind_shift_deg (direction change at horizon/2),
    md (dead 1h moisture ratio), fuel (1..9), fuel_patchiness, fuel2, slope_deg, aspect_deg,
    ign_x, ign_y (fractions of domain), seed.
    Arrays are indexed [x, y] (ForeFire layer order): arrival[i, j] is cell centre ((i+.5)dx, (j+.5)dx)."""
    t0 = time.perf_counter()
    import pyforefire as pyff
    t_import = time.perf_counter()
    n, dx = sc["n"], sc["dx"]; L = n * dx
    rng = np.random.default_rng(sc.get("seed", 0))
    ff = pyff.ForeFire()
    corsica = sc.get("fuel_set") == "corsica"
    farsite = sc.get("fuel_set") == "farsite"
    model = sc.get("model", "Rothermel" if corsica else ("Farsite" if farsite else "RothermelAndrews2018"))
    if corsica:
        ff["fuelsTable"] = corsica_table(sc["md"])
    elif farsite:
        # ForeFire's built-in Scott & Burgan 40 + Anderson 13 table (index = FBFM40 code); matches
        # BehavePlus on flat ground (forefire-us-fuels/RESULTS.md). Every moisture class set explicitly.
        ff["fuelsTable"] = "STDfarsiteFuelsTable"
        for k, key in (("ones", "md"), ("tens", "md_10h"), ("hundreds", "md_100h"),
                       ("liveh", "m_live_herb"), ("livew", "m_live_woody")):
            ff["moistures." + k] = float(sc[key])
    else:
        ff["fuelsTable"] = fuel_table_balbi(sc["md"]) if model in BALBI_MODELS else fuel_table(sc["md"])
    ff["propagationModel"] = model
    pr = sc.get("perimeter_res", max(5.0, dx))   # front node spacing tied to grid
    for k, v in {"spatialIncrement": pr / 5.0, "perimeterResolution": pr,
                 "minimalPropagativeFrontDepth": dx, "initialFrontDepth": dx / 2,
                 "relax": 0.5, "smoothing": 1.0, "minSpeed": 0.0, "bmapLayer": 1,
                 "windReductionFactor": 0.4, "propagationSpeedAdjustmentFactor": 1.0,
                 "SWx": 0.0, "SWy": 0.0, "Lx": L, "Ly": L,
                 "atmoNX": sc.get("atmo_n", max(1, n // 8)), "atmoNY": sc.get("atmo_n", max(1, n // 8))}.items():
        ff[k] = v
    if farsite:
        ff["windReductionFactor"] = 1.0       # midflame wind is applied below via waf
    for k, v in sc.get("ff_params", {}).items():   # raw ForeFire parameter overrides (e.g. CORSICA_NATIVE)
        ff[k] = v
    ff.execute(f"FireDomain[sw=(0.,0.,0.);ne=({L},{L},0);t=0]")
    ff.addLayer("propagation", model, "propagationModel")
    if sc.get("landscape_nc"):
        fuel, alt = landscape_crop(sc, n, L)
        if sc.get("corsica_class"):                      # keep real terrain, override fuel
            fuel = np.where(np.isin(fuel, NONBURN_CORSICA), fuel, int(sc["corsica_class"]))
        if sc.get("terrain") == "flat":
            alt = np.zeros_like(alt)
    else:
        fuel = make_fuel_map(sc, n, rng)
        alt = make_altitude(sc, n, L)
    ff.addIndexLayer("table", "fuel", 0., 0., 0., L, L, 0., fuel[None, None])
    # pyforefire reads the ALTITUDE layer with axis 0 = y (the fuel layer is [x, y]); checked with a
    # plane rising east (Rothermel and Farsite). Passing [x, y] mirrors the terrain across the diagonal,
    # which every run before 2026-11-14 18:50 UTC did. Hence the transpose.
    alt_ff = np.asarray(alt, dtype=np.float64).T.copy()
    if farsite and sc.get("farsite_slope_fix", True):
        alt_ff = alt_ff / 2.0                 # FarsitePropagationModel.cpp:289 doubles tan(slope)
    ff.addScalarLayer("data", "altitude", 0., 0., 0., L, L, 0., alt_ff[None, None])
    if model in BALBI_MODELS:  # some Balbi variants read air temperature and live moisture layers
        ff.addScalarLayer("data", "temperature", 0., 0., 0., L, L, 0., np.full((1, 1, 4, 4), 300.0))
        ff.addScalarLayer("data", "moisture", 0., 0., 0., L, L, 0., np.full((1, 1, 4, 4), 1.0))
    # The wind layer must be at full grid resolution: ForeFire does not extrapolate wind past
    # the outermost cell centre, so a coarse (e.g. 4x4) layer leaves a no-wind band of half a
    # layer cell at every edge and fires stall ~L/8 short of the boundary.
    w = np.zeros((2, 2, n, n)); w[0, 0] = 1; w[1, 1] = 1
    ff.addScalarLayer("windScalDir", "windU", 0., 0., 0., L, L, 0., w[0:1])
    ff.addScalarLayer("windScalDir", "windV", 0., 0., 0., L, L, 0., w[1:2])
    # RothermelAndrews2018 in ForeFire does NOT apply windReductionFactor, so we convert the
    # 20-ft (6.1 m) wind to midflame wind ourselves with a fixed adjustment factor.
    waf = sc.get("waf", WAF)
    # Farsite bug (FarsitePropagationModel.cpp:288): it treats the wind number as mph, so pass mph.
    unit = 1.0 / 0.44704 if (farsite and sc.get("farsite_wind_fix", True)) else 1.0
    def wind_uv(dir_deg):
        th = math.radians(dir_deg)
        sp = waf * sc["wind_speed"] * unit
        return sp * math.sin(th), sp * math.cos(th)
    u, v = wind_uv(sc["wind_dir_deg"])
    ff.execute(f"trigger[wind;loc=(0.,0.,0.);vel=({u},{v},0.);t=0]")
    if sc.get("ign_polygon"):
        start_front(ff, sc["ign_polygon"], depth=dx / 2)   # initial burning area (domain metres)
    else:
        ff.execute(f"startFire[loc=({sc['ign_x']*L},{sc['ign_y']*L},0.);t=0.]")
    t_setup = time.perf_counter()
    shift = sc.get("wind_shift_deg", 0.0)
    if shift:
        # default: frontal passage at horizon/2 (Ember-Synth v1); initial-state sets give wind_shift_t_s
        half = float(sc.get("wind_shift_t_s", sc["horizon_s"] / 2))
        if half > 0:
            ff.execute(f"goTo[t={half}]")
        u2, v2 = wind_uv(sc["wind_dir_deg"] + shift)
        ff.execute(f"trigger[wind;loc=(0.,0.,0.);vel=({u2},{v2},0.);t={max(half, 0.0)}]")
    ff.execute(f"goTo[t={sc['horizon_s']}]")
    t_sim = time.perf_counter()
    # ff["arrival_time"] comes back as [y, x] (row = y); transpose to the [x, y] order of our layers.
    at = np.asarray(ff["arrival_time"], dtype=np.float64).T
    front_txt = ff.execute("print[]") if capture_front else None
    nodes = ff.execute("print[]").count("FireNode")
    t_ext = time.perf_counter()
    # resample bmap -> n x n analysis grid (cell = min arrival time of its sub-cells)
    bx, by = at.shape
    if bx % n == 0 and by % n == 0 and bx >= n:
        at = at.reshape(n, bx // n, n, by // n).min(axis=(1, 3))
    else:
        ix = (np.arange(n) * bx // n); iy = (np.arange(n) * by // n)
        at = at[np.ix_(ix, iy)]
    at = np.where(np.isfinite(at) & (at < 1e30), at, np.inf)
    at = np.where(at < 0, 0.0, at)            # cells inside the initial ignition footprint
    at[at > sc["horizon_s"]] = np.inf
    burned = np.isfinite(at)
    fuel = np.asarray(fuel)
    m = max(2, n // 64)   # the bmap does not always mark the outermost cells, so test a margin
    edge_hit = bool(burned[:m].any() or burned[-m:].any() or burned[:, :m].any() or burned[:, -m:].any())
    res = dict(arrival=at.astype(np.float32), fuel=fuel.astype(np.int16), alt=np.asarray(alt).astype(np.float32),
               burned_area_m2=float(burned.sum() * dx * dx), n_front_nodes=nodes, edge_hit=edge_hit,
               t_import=t_import - t0, t_setup=t_setup - t_import, t_sim=t_sim - t_setup,
               t_extract=t_ext - t_sim, t_total=t_ext - t0, bmap_shape=(bx, by))
    if capture_front: res["front"] = front_txt
    return res
