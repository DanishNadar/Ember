"""Real US landscape inputs.

Elevation: AWS Terrain Tiles (terrarium PNG, public, no key; USGS 3DEP-derived in CONUS).
Fuels: LANDFIRE FBFM40 (Scott & Burgan 40) GeoTIFF, downloaded by hand from landfire.gov
(the LANDFIRE servers are not reachable from the build VM). `fbfm40_to_index` maps codes to
the rows of sim.fuel_table().
"""
import io
import math
import urllib.request

import numpy as np

TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

SITES = {  # name: (lat, lon, note)
    "aullene": (41.77, 9.08, "Aullene, Corse-du-Sud: area of ForeFire's bundled real_case.ff"),
    "santa_monica": (34.17, -118.78, "Santa Monica Mtns, CA: chaparral (SH5/SH7), Woolsey 2018"),
    "paradise": (39.78, -121.55, "Paradise, CA: timber-understory + grass, Camp 2018"),
    "boulder": (40.02, -105.35, "Front Range, CO: grass/shrub/timber, Marshall 2021 nearby"),
}


def _tile(z, x, y):
    from PIL import Image
    with urllib.request.urlopen(TILE_URL.format(z=z, x=x, y=y), timeout=30) as r:
        a = np.asarray(Image.open(io.BytesIO(r.read())).convert("RGB")).astype(np.float64)
    return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768


def fetch_dem(lat, lon, size_km=20.0, dx=30.0, z=13):
    """Elevation (m) on a dx-metre grid centred on (lat, lon), indexed [x, y] (x east, y north)."""
    n2 = 2 ** z
    fx, fy = (lon + 180) / 360 * n2, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n2
    mpp = 40075016.686 * math.cos(math.radians(lat)) / (n2 * 256)      # metres per tile pixel
    half = size_km * 500 / mpp / 256                                    # half-width in tiles
    x0, x1, y0, y1 = int(fx - half), int(fx + half), int(fy - half), int(fy + half)
    mos = np.vstack([np.hstack([_tile(z, x, y) for x in range(x0, x1 + 1)]) for y in range(y0, y1 + 1)])
    # sample the mosaic (rows = south-going) on the target grid
    n = int(round(size_km * 1000 / dx))
    off = (np.arange(n) + 0.5) * dx / mpp - size_km * 500 / mpp
    px = (fx - x0) * 256 + off                      # column per x
    py = (fy - y0) * 256 - off                      # row per y (north = up = smaller row)
    ci, ri = np.clip(px.astype(int), 0, mos.shape[1] - 1), np.clip(py.astype(int), 0, mos.shape[0] - 1)
    return mos[ri][:, ci].T.astype(np.float32), mpp   # [x, y]


# LANDFIRE FBFM40 code -> sim.fuel_table() index. SH maps exactly; GR/GS/TU/TL map to the
# approximate 1-h-only rows (ForeFire's RothermelAndrews2018 has no live/10-h/100-h columns).
def fbfm40_to_index(code):
    code = int(code)
    if 141 <= code <= 149:
        return code - 140                    # SH1..SH9
    if 101 <= code <= 102 or 121 <= code <= 122:
        return 11                            # GR1-2, GS1-2 -> GR2 row
    if 103 <= code <= 109 or 123 <= code <= 124:
        return 12                            # GR3-9, GS3-4 -> GR4 row
    if 161 <= code <= 165:
        return 21                            # TU -> TU1 row
    if 181 <= code <= 189 or 201 <= code <= 204:
        return 31                            # TL, SB -> TL3 row
    return 99                                # NB (91-99), water, urban, unknown


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "santa_monica"
    lat, lon, note = SITES[name]
    dem, mpp = fetch_dem(lat, lon)
    out = f"dem_{name}_30m.npy"
    np.save(out, dem)
    gx, gy = np.gradient(dem, 30.0)
    sl = np.degrees(np.arctan(np.hypot(gx, gy)))
    print(f"{note}\n{out} {dem.shape} elev {dem.min():.0f}-{dem.max():.0f} m, source {mpp:.1f} m/px, "
          f"slope median {np.median(sl):.1f} p90 {np.percentile(sl, 90):.1f} deg")
