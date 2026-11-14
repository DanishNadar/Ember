"""Physics/orientation sanity checks. Each simulation runs in its own process.

    python -m pytest tests -q      (or: python tests/test_sanity.py)
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ember_bench import metrics, runner

BASE = dict(n=64, dx=60.0, horizon_s=1800.0, wind_speed=6.0, wind_dir_deg=90.0, wind_shift_deg=0.0, md=0.06,
            fuel=4, fuel2=1, fuel_patchiness=0.0, slope_deg=0.0, aspect_deg=0.0, ign_x=0.5, ign_y=0.5, seed=0)


def run(**kw):
    scs = [dict(BASE, run_id=i, **{k: v[i] for k, v in kw.items()}) for i in range(len(next(iter(kw.values()))))]
    out = {r["scenario"]["run_id"]: r for r in runner.run_many(scs, workers=4, progress=False)}
    return [out[i] for i in range(len(scs))]


def centroid(at):
    b = np.isfinite(at)
    i, j = np.nonzero(b)
    return i.mean(), j.mean()


def test_wind_direction_orientation():
    # wind blowing to +x (east, 90 deg) must push the burned area to larger x, +y (0 deg) to larger y
    east, north = run(wind_dir_deg=[90.0, 0.0])
    cx, cy = centroid(east["arrival"]); assert cx > 32 + 3 and abs(cy - 32) < 3, (cx, cy)
    cx, cy = centroid(north["arrival"]); assert cy > 32 + 3 and abs(cx - 32) < 3, (cx, cy)


def test_monotone_in_wind_and_moisture():
    a = [r["burned_area_m2"] for r in run(wind_speed=[0.0, 3.0, 6.0])]
    assert a[0] < a[1] < a[2], a
    m = [r["burned_area_m2"] for r in run(md=[0.04, 0.08, 0.12])]
    assert m[0] > m[1] > m[2], m


def test_runs_are_independent():
    # same scenario twice, different neighbours: identical output (no leaked global state)
    r = run(md=[0.06, 0.12, 0.06])
    assert np.array_equal(r[0]["arrival"], r[2]["arrival"])


def test_metrics():
    a = np.full((4, 4), np.inf); a[1:3, 1:3] = 60.0
    assert metrics.iou(np.isfinite(a), np.isfinite(a)) == 1.0
    c = metrics.compare(a + 60.0, a, 10.0, 3600.0)
    assert c["iou_final"] == 1.0 and abs(c["at_mae_min"] - 1.0) < 1e-9


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("ok", k)
