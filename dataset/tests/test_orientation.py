"""Terrain orientation: a plane rising toward +x (east), no wind, must burn farther east (upslope)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from ember_bench import runner


def test_upslope_is_east():
    out = {}
    base = dict(n=64, dx=30.0, horizon_s=1500.0, wind_speed=0.0, wind_dir_deg=0.0, wind_shift_deg=0.0, md=0.06,
                fuel=5, fuel2=5, fuel_patchiness=0.0, slope_deg=25.0, aspect_deg=90.0, ign_x=0.5, ign_y=0.5,
                terrain="plane", seed=0)
    scs = [dict(base, run_id="ra18"),
           dict(base, run_id="farsite", fuel_set="farsite", fuel=145, fuel2=145, md_10h=0.07, md_100h=0.08, m_live_herb=0.6, m_live_woody=0.9),
           dict(base, run_id="corsica", fuel_set="corsica", model="Rothermel", waf=1.0,
                ff_params={"propagationSpeedAdjustmentFactor": 0.6, "minSpeed": 0.009, "windReductionFactor": 0.4})]
    for r in runner.run_many(scs, progress=False):
        assert r.get("ok"), r
        b = np.isfinite(r["arrival"]); i, j = np.nonzero(b)
        c = 32
        east, north = i.max() - c, j.max() - c
        out[r["scenario"]["run_id"]] = (east, north)
        assert east > north, (r["scenario"]["run_id"], east, north)
    return out


if __name__ == "__main__":
    print("ok test_upslope_is_east", test_upslope_is_east())
