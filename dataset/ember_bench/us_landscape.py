"""US landscape for Ember: real terrain (AWS Terrain Tiles) + LANDFIRE FBFM40 fuel, saved as an
.npz that sim.load_landscape_nc() reads like ForeFire's data.nc.

    python -m ember_bench.us_landscape --site santa_monica --out data_real/santa_monica/landscape.npz
    python -m ember_bench.us_landscape --site santa_monica --landfire LF2022_FBFM40.tif --out ...

Without --landfire the fuel map is a PLACEHOLDER (random chaparral/grass mosaic, water where the
terrain is at or below sea level). It is flagged in the file (fuel_source) and in every sample
built from it. Replace it before any result is shown.

Grid: x east, y north, [x, y] order, cell centres ((i+.5)dx, (j+.5)dx) from the SW corner, the
same local Web-Mercator frame as landfire.fetch_dem (scale-corrected at the centre latitude).
"""
import argparse
import math
import os

import numpy as np

from . import landfire

# LANDFIRE non-burnable codes that ForeFire's STDfarsiteFuelsTable does not carry -> NB1 (99).
# 98 (water) and 99 (barren) exist in the table with zero load. Nodata (-9999, 0, 32767) -> 99.
NB_REMAP = {91: 99, 92: 99, 93: 99}
STD_CODES = {0, *range(1, 14), *range(95, 100), *range(101, 110), *range(121, 125), *range(141, 150),
             *range(161, 166), *range(181, 190), *range(201, 205)}


def clean_codes(f):
    f = np.asarray(f).astype(np.int32)
    for a, b in NB_REMAP.items():
        f[f == a] = b
    f[~np.isin(f, list(STD_CODES))] = 99
    return f


def cell_lonlat(lat, lon, size_km, dx, z=12):
    """lon/lat of every cell centre of the fetch_dem grid ([x, y] arrays)."""
    n2 = 2 ** z
    fx = (lon + 180) / 360 * n2
    fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n2
    mpp = 40075016.686 * math.cos(math.radians(lat)) / (n2 * 256)
    n = int(round(size_km * 1000 / dx))
    off = (np.arange(n) + 0.5) * dx / mpp - size_km * 500 / mpp       # tile pixels from centre
    X = fx * 256 + off                                                  # global pixel column per x
    Y = fy * 256 - off                                                  # global pixel row per y
    lons = X / (n2 * 256) * 360 - 180
    lats = np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * Y / (n2 * 256)))))
    LON, LAT = np.meshgrid(lons, lats, indexing="ij")
    return LON, LAT


def landfire_to_grid(tif, lat, lon, size_km, dx, z=12):
    """Nearest-neighbour sample of a LANDFIRE FBFM40 GeoTIFF (any CRS, usually EPSG:5070) on our grid."""
    import rasterio
    from pyproj import Transformer
    LON, LAT = cell_lonlat(lat, lon, size_km, dx, z)
    with rasterio.open(tif) as src:
        tr = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        X, Y = tr.transform(LON.ravel(), LAT.ravel())
        rows, cols = rasterio.transform.rowcol(src.transform, X, Y)
        rows, cols = np.asarray(rows), np.asarray(cols)
        a = src.read(1)
        ok = (rows >= 0) & (rows < a.shape[0]) & (cols >= 0) & (cols < a.shape[1])
        out = np.full(rows.shape, 99, np.int32)
        out[ok] = a[rows[ok], cols[ok]]
        cover = ok.mean()
    if cover < 1.0:
        print(f"WARNING: the GeoTIFF covers only {cover*100:.1f}% of the grid; the rest is set non-burnable")
    return clean_codes(out.reshape(LON.shape))


def placeholder_fuel(alt, seed=0, codes=None):
    """PLACEHOLDER mosaic, not real fuel: smooth random patches (~1 km) of chaparral (SH5, SH7),
    grass/grass-shrub (GR2, GS2) and non-burnable (99); water (98) at or below sea level."""
    codes = codes or {145: 0.40, 147: 0.25, 102: 0.15, 122: 0.10, 99: 0.10}
    rng = np.random.default_rng(seed)
    n = alt.shape[0]
    k = np.fft.fftfreq(n)
    KX, KY = np.meshgrid(k, k, indexing="ij")
    sig = 1000.0 / 30.0 / (2 * math.pi)
    filt = np.exp(-0.5 * (KX ** 2 + KY ** 2) * (2 * math.pi * sig) ** 2)
    z = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * filt))
    q = np.argsort(np.argsort(z.ravel())).reshape(z.shape) / z.size      # uniform ranks
    edges = np.cumsum(list(codes.values())) / sum(codes.values())
    f = np.array(list(codes))[np.searchsorted(edges, q.clip(0, 1 - 1e-9))]
    f[alt <= 0] = 98
    return f.astype(np.int32)


def build(site, out, size_km=48.0, dx=30.0, z=12, landfire_tif=None, lat=None, lon=None):
    if lat is None:
        lat, lon, _ = landfire.SITES[site]
    alt, mpp = landfire.fetch_dem(lat, lon, size_km=size_km, dx=dx, z=z)
    if landfire_tif:
        fuel, src = landfire_to_grid(landfire_tif, lat, lon, size_km, dx, z), f"LANDFIRE FBFM40: {os.path.basename(landfire_tif)}"
    else:
        fuel, src = placeholder_fuel(alt), "PLACEHOLDER (synthetic mosaic, not LANDFIRE)"
    fuel[alt <= 0] = 98                    # sea: the DEM has bathymetry
    alt = np.maximum(alt, 0.0).astype(np.float32)
    L = alt.shape[0] * dx
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    np.savez_compressed(out, fuel=fuel.astype(np.int16), alt=alt, Lx=L, Ly=L, fuel_dx=dx, alt_dx=dx,
                        fuel_source=src, site=site, centre_lat=lat, centre_lon=lon, tile_zoom=z, dem_m_per_px=mpp,
                        frame="local Web-Mercator around centre, x east, y north, SW origin, [x, y]")
    u, c = np.unique(fuel, return_counts=True)
    print(f"{out}: {alt.shape} at {dx} m, {L/1000:.1f} km, fuel = {src}")
    print("  fuel shares:", {int(a): round(b / fuel.size, 3) for a, b in zip(u, c)})
    return out


# ---------------------------------------------------------------- US-wide sites (bounding boxes)
# name: (lat_min, lat_max, lon_min, lon_max, placeholder fuel mix {FBFM40 code: share}, note)
US_SITES = {
    "socal_chaparral": (33.85, 34.35, -119.10, -118.50, {145: .40, 147: .25, 102: .15, 122: .10, 99: .10},
                        "Santa Monica Mtns, CA: chaparral (Woolsey 2018)"),
    "norcal_paradise": (39.55, 40.05, -121.85, -121.25, {165: .30, 183: .25, 102: .15, 145: .15, 99: .15},
                        "Paradise, CA: timber understory + grass (Camp 2018)"),
    "greatbasin_nv":   (40.65, 41.15, -117.15, -116.55, {122: .35, 142: .30, 102: .25, 99: .10},
                        "Great Basin, NV: sagebrush / cheatgrass"),
    "arizona":         (34.05, 34.55, -111.55, -110.95, {165: .30, 183: .25, 122: .20, 145: .15, 99: .10},
                        "Central AZ (Mogollon Rim): pine / chaparral / grass"),
    "texas_panhandle": (35.55, 36.05, -100.95, -100.35, {102: .45, 104: .25, 122: .20, 99: .10},
                        "Texas panhandle: grassland (Smokehouse Creek 2024)"),
    "montana_timber":  (46.55, 47.05, -114.35, -113.75, {165: .35, 183: .30, 185: .15, 102: .10, 99: .10},
                        "Western MT (Missoula area): conifer timber"),
}


def bbox_grid(lat0, lat1, lon0, lon1, dx=30.0, z=12):
    """Web-Mercator pixel coordinates of a dx-metre grid covering the box. Returns
    (X pixel per x, Y pixel per y, nx, ny, metres per pixel at centre)."""
    lat_c = (lat0 + lat1) / 2
    n2 = 2 ** z
    mpp = 40075016.686 * math.cos(math.radians(lat_c)) / (n2 * 256)
    gx = lambda lon: (lon + 180) / 360 * n2 * 256
    gy = lambda lat: (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n2 * 256
    wx, wy = (gx(lon1) - gx(lon0)) * mpp, (gy(lat0) - gy(lat1)) * mpp
    nx, ny = int(wx // dx), int(wy // dx)
    X = gx(lon0) + (np.arange(nx) + 0.5) * dx / mpp
    Y = gy(lat0) - (np.arange(ny) + 0.5) * dx / mpp       # y north = decreasing pixel row
    return X, Y, nx, ny, mpp


def _pix_lonlat(X, Y, z):
    n2 = 2 ** z
    lons = X / (n2 * 256) * 360 - 180
    lats = np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * Y / (n2 * 256)))))
    return np.meshgrid(lons, lats, indexing="ij")


def _tile_retry(z, x, y, tries=5):
    import time
    for k in range(tries):
        try:
            return landfire._tile(z, x, y)
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 ** k)


def fetch_dem_bbox(lat0, lat1, lon0, lon1, dx=30.0, z=12):
    X, Y, nx, ny, mpp = bbox_grid(lat0, lat1, lon0, lon1, dx, z)
    tx0, tx1, ty0, ty1 = int(X.min() // 256), int(X.max() // 256), int(Y.min() // 256), int(Y.max() // 256)
    mos = np.vstack([np.hstack([_tile_retry(z, x, y) for x in range(tx0, tx1 + 1)]) for y in range(ty0, ty1 + 1)])
    ci = np.clip((X - tx0 * 256).astype(int), 0, mos.shape[1] - 1)
    ri = np.clip((Y - ty0 * 256).astype(int), 0, mos.shape[0] - 1)
    return mos[ri][:, ci].T.astype(np.float32), mpp          # [x, y]


def landfire_to_bbox(tif, lat0, lat1, lon0, lon1, dx=30.0, z=12):
    import rasterio
    from pyproj import Transformer
    X, Y, nx, ny, _ = bbox_grid(lat0, lat1, lon0, lon1, dx, z)
    LON, LAT = _pix_lonlat(X, Y, z)
    with rasterio.open(tif) as src:
        tr = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        px, py = tr.transform(LON.ravel(), LAT.ravel())
        rows, cols = (np.asarray(v) for v in rasterio.transform.rowcol(src.transform, px, py))
        a = src.read(1)
        ok = (rows >= 0) & (rows < a.shape[0]) & (cols >= 0) & (cols < a.shape[1])
        out = np.full(rows.shape, 32767, np.int32)
        out[ok] = a[rows[ok], cols[ok]]
    out = out.reshape(LON.shape)
    landfire_to_bbox.last_missing = np.isin(out, [32767, -9999, -32768])   # outside the export / nodata
    return clean_codes(out)


def _placeholder_rect(alt, mix, seed):
    n = max(alt.shape)
    pad = np.zeros((n, n), np.float32)
    f = placeholder_fuel(pad + 1.0, seed=seed, codes=mix)[:alt.shape[0], :alt.shape[1]]
    return f


def build_site(name, out, dx=30.0, z=12, landfire_tif=None, seed=0):
    lat0, lat1, lon0, lon1, mix, note = US_SITES[name]
    alt, mpp = fetch_dem_bbox(lat0, lat1, lon0, lon1, dx, z)
    if landfire_tif:
        fuel, src = landfire_to_bbox(landfire_tif, lat0, lat1, lon0, lon1, dx, z), f"LANDFIRE FBFM40: {os.path.basename(landfire_tif)}"
        miss = landfire_to_bbox.last_missing
        sea = alt <= 0
        print(f"  {name}: LANDFIRE missing/nodata on {miss.mean()*100:.2f}% of the box "
              f"({(miss & ~sea).mean()*100:.2f}% on land, set non-burnable)", flush=True)
    else:
        fuel, src = _placeholder_rect(alt, mix, seed), "PLACEHOLDER (synthetic mosaic, not LANDFIRE)"
    fuel[alt <= 0] = 98
    alt = np.maximum(alt, 0.0).astype(np.float32)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    np.savez_compressed(out, fuel=fuel.astype(np.int16), alt=alt, Lx=alt.shape[0] * dx, Ly=alt.shape[1] * dx,
                        fuel_dx=dx, alt_dx=dx, fuel_source=src, site=name, note=note,
                        bbox=np.array([lat0, lat1, lon0, lon1]), tile_zoom=z, dem_m_per_px=mpp,
                        frame="Web-Mercator grid over the bbox, x east, y north, SW origin, [x, y]")
    u, c = np.unique(fuel, return_counts=True)
    print(f"{name}: {alt.shape} @ {dx} m = {alt.shape[0]*dx/1e3:.1f} x {alt.shape[1]*dx/1e3:.1f} km, "
          f"elev {alt.min():.0f}-{alt.max():.0f} m, fuel {src}", flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="santa_monica")
    ap.add_argument("--lat", type=float); ap.add_argument("--lon", type=float)
    ap.add_argument("--size-km", type=float, default=48.0)
    ap.add_argument("--dx", type=float, default=30.0)
    ap.add_argument("--zoom", type=int, default=12)
    ap.add_argument("--landfire")
    ap.add_argument("--out", help="output .npz (one site) or directory (with --all-us)")
    ap.add_argument("--all-us", action="store_true", help="build every US_SITES box into --out/<site>.npz")
    a = ap.parse_args()
    if a.all_us:
        for k in US_SITES:
            build_site(k, os.path.join(a.out, f"{k}.npz"), a.dx, a.zoom)
    elif a.site in US_SITES and a.landfire:
        build_site(a.site, a.out, a.dx, a.zoom, a.landfire)
    elif a.site in US_SITES:
        build_site(a.site, a.out, a.dx, a.zoom, a.landfire)
    else:
        build(a.site, a.out, a.size_km, a.dx, a.zoom, a.landfire, a.lat, a.lon)
