# Ember initial project audit

Audit performed 2026-11-14 (America/Chicago) before Ember code was added.

## Directly observed repository state

| Item | Observation |
|---|---|
| Repository | `forefire/`, a Git checkout at `ad57478c35b507f6b94c253052562a9b1347b458` (2026-10-28, `Merge branch 'master' into dev`) |
| Working tree | Clean at audit time (`git -C forefire status --short` produced no entries) |
| Engine version | `v2.6.0`, from `forefire/src/include/Version.h` |
| Upstream | `https://github.com/forefireAPI/forefire.git` |
| Root layout | No Ember application files existed; the workspace contained only `forefire/` |
| Major source areas | `src/` (107 files), `bindings/` (19), `docs/` (44), `tests/` (80), `tools/` (83), plus `app/`, `paper/`, and `third_party/` |
| Test fixtures | `tests/runff/data.nc` (4,123,443 bytes), `fuels.csv`, `.ff` scenarios, `ForeFire.0.nc.ref`, and `real_case.kml.ref`; nested MesoNH NetCDF fixtures also exist |

## Verified engine interfaces and artifacts

- CMake exposes CLI, Python bindings, NetCDF, MPI, tests, and optional tools. The defaults outside wheel builds enable NetCDF, CLI, MPI, tools, and tests.
- The Python-binding documentation demonstrates domain creation, an `Iso` propagation layer, stepping, textual `print[]` output, and KML output through `dumpMode=kml`.
- The checked-in `rungeojson.ff` scenario uses `dumpMode=geojson`, a Rothermel configuration, a NetCDF landscape, scheduled `print` snapshots, a wind trigger, and GeoJSON reload (`startFire[geojson=temp.geojson]`).
- Repository documentation describes `print` formats `ff`, `geojson`, and `kml`; `save[]` arrival-time NetCDF output; and field export/plot support for values including fuel, altitude, slope, windU, windV, speed, and arrival time.

## Execution environment observed

| Category | Observation |
|---|---|
| OS / Python | Windows 11, CPython 3.12.10 ARM64 |
| CPU / GPU | Snapdragon X Elite X1E78100; Qualcomm Adreno X1-85 reported by Windows |
| Available commands | `python`, `cmake`, and `git`; no `forefire`, `fuzzball`, `nvidia-smi`, `ncdump`, MPI launcher, or compiler command was found on `PATH` |
| Python packages present | `numpy`, `pandas`, `matplotlib`, `psutil`, and `shapely` |
| Python packages absent | `pyforefire`, `netCDF4`, `xarray`, `h5py`, `rasterio`, and `torch` |
| GPU claim | No NVIDIA/CUDA device or CUDA tooling was observed. No GPU performance measurement has been made. |

## Capability classification at audit time

| Area | Classification | Evidence / consequence |
|---|---|---|
| ForeFire source, scenarios, and docs | Implemented but unverified locally | Source and fixtures are present, but no local executable or bindings are installed. |
| GeoJSON/KML state export design | Implemented but unverified locally | Documented and represented by checked-in scenario/reference artifacts; local execution is pending a usable build. |
| NetCDF landscape/arrival-time input-output | Partially implemented locally | Engine fixtures are present but neither NetCDF CLI nor Python reader is installed here. |
| Ember extraction/data analysis | Missing | No Ember files existed before this audit. |
| ForeFire runtime baseline | Missing | No executable has run in this environment; no timing may be reported. |
| Neural surrogate | Missing | PyTorch is absent and no training data has been generated. |
| Fuzzball orchestration / multi-node tests | Blocked by infrastructure | No Fuzzball CLI/configuration, scheduler connection, remote nodes, or shared storage was observed. |

## Audit limits and next actions

This audit does not infer physical accuracy, actual simulation output, GPU availability beyond the local host, or remote-hardware access. Ember will add a reproducible, dependency-light extractor for GeoJSON, KML, and NumPy state artifacts; a NetCDF inspector that explicitly reports unavailable readers; provenance and integrity manifests; and data-quality/spatial analysis. A ForeFire run and a valid benchmark require a supported compiler/NetCDF toolchain or an installed compatible ForeFire distribution.

## Commands used

```powershell
git -C forefire status --short
git -C forefire log -1 --format='%H%n%cs%n%s'
python --version
python -c "import importlib.util as u; ..."
Get-CimInstance Win32_Processor, Win32_VideoController
rg --files forefire
```
