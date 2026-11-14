# ForeFire performance baseline

## Result

No ForeFire performance result is available from this host. Reporting a duration, throughput, memory peak, or speedup would be fabricated.

## Reproducible attempted execution

| Experiment ID | Command / workload | Outcome | Measurements |
|---|---|---|---|
| `build_probe_20261114` | `cmake -S forefire -B artifacts/build-probe -DFOREFIRE_ENABLE_MPI=OFF -DFOREFIRE_ENABLE_NETCDF=OFF -DFOREFIRE_BUILD_PYTHON=OFF -DFOREFIRE_BUILD_TESTS=OFF -DFOREFIRE_BUILD_TOOLS=OFF -DFOREFIRE_CHECK_LFS=OFF -DFOREFIRE_NATIVE_ARCH=OFF` | Failed in CMake’s Visual Studio ARM64 platform probe before compile | No executable or benchmark produced. |
| `runff_cli_probe_20261114` | `python scripts/run_forefire.py forefire/tests/runff/real_case.ff --run-directory artifacts/runs/runff --executable forefire` | Blocked: `forefire` was not on `PATH` | Machine-readable blocked record: `artifacts/runs/runff/run_manifest.json`. |

The CMake error reports an unset `BaseOutputPath/OutputPath` for the generated ARM64 `VCTargetsPath.vcxproj`. This is a local toolchain configuration failure, not evidence that ForeFire fails on a supported platform.

## Benchmark protocol ready for a supported host

`scripts/run_forefire.py` records the command, start time, process return code, stdout/stderr, wall time, and peak RSS sampled every 0.1 seconds. To benchmark, run each scenario three or more times on a host with a confirmed ForeFire executable and record hardware/software identity alongside the resulting manifests. Vary resolution, duration, snapshot cadence, and only documented propagation models. Separate engine time from the extraction process, and retain raw outputs for every trial.

No CUDA GPU, Fuzzball CLI, MPI launcher, or remote-node placement was observable here; no distributed comparison was attempted.
