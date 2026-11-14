# ForeFire capabilities for Ember

Source inspected: ForeFire `v2.6.0` at commit `ad57478c35b507f6b94c253052562a9b1347b458`. “Accessible” below means accessible from the checked-in fixture or documented engine interface; it does not imply a local ForeFire execution succeeded.

| Variable | Source | Units | Accessible? | Extraction method | Limitations |
|---|---|---:|---|---|---|
| Simulation domain | `data.nc` `domain` attrs | model coordinates; geographic BBox degrees | Yes | `h5py` reads `SWx`, `SWy`, `Lx`, `Ly`, `BBoxWSEN` | Native CRS is not declared by this fixture. |
| Simulation time | `.ff` commands / GeoJSON `valid_at` | seconds or ISO-8601 | Conditionally | Parse scenario commands / state metadata | The analyzed KML reference has no timestamp. |
| Fire-front geometry | `print` docs; KML/GeoJSON output | geometry coordinates | Yes | Ember parses KML or GeoJSON polygons | KML reference lacks CRS metadata. |
| Fire-front movement | Repeated printed states | coordinate units / time | Conditionally | Temporal ordering of timestamped snapshots | One state cannot measure movement. |
| Fire perimeter | Derived from front geometry | source coordinate units | Yes | Closed-ring Euclidean length | Not metres without projected CRS. |
| Burned area | Derived from front geometry/mask | source coordinate units squared | Yes | Shoelace geometry area and raster occupancy | Not square metres without projected CRS; a front may not equal a burned-area polygon in every output mode. |
| Fuel indices | `data.nc:fuel` | categorical index | Yes | HDF5 read, then BBoxWSEN nearest-neighbour alignment | Fuel index meanings require `fuels.csv`; mapping orientation needs a render check. |
| Fuel properties | `fuels.csv` | model-specific | Yes | Semicolon-delimited table | Fields are model parameters; no units were inferred beyond documentation. |
| Wind values | `data.nc:wind` | not declared in fixture | Yes | HDF5 read, retain both leading axes | Time/component axis semantics need engine documentation or a verified run. |
| Elevation / altitude | `data.nc:altitude` | not declared in fixture | Yes | HDF5 read and resampling | Elevation unit not declared in file metadata. |
| Terrain slope | `plot` documentation lists `slope` | unspecified | Not directly verified in fixture | Potentially derive from altitude once grid orientation/units are confirmed | No direct `slope` dataset was found. |
| Propagation model | `params.ff`, `rungeojson.ff` | n/a | Yes | Parse `propagationModel` | Runff fixture configures `Rothermel`; no local run was completed. |
| Numerical resolution | NetCDF layer dimensions/domain extent | model coordinate units per cell | Yes | Read shapes and domain size | `fuel`: 6400×6400; `altitude`: 640×640; `wind`: 160×160, but axis orientation is unverified. |
| Time-step configuration | `.ff` `step[dt=...]` / scheduled commands | seconds | Yes for scripts | Parse ForeFire script | Current reference artifact cannot be tied to an output time. |
| Arrival-time raster | `ForeFire.0.nc.ref` | seconds inferred from fixture script | Yes, reference artifact | HDF5 read of `arrival_time_of_front`; `-9999` is explicitly supplied as its observed sentinel | Checked-in reference output, not locally generated; sentinel should be confirmed for other runs. |
| Reload | `rungeojson.ff` | n/a | Implemented in scenario | `startFire[geojson=temp.geojson]` follows a saved print output | Not locally executed. |
| Runtime diagnostics | Ember runner | seconds, bytes | Framework ready | `psutil` wall/RSS monitor around CLI invocation | Executable absent, so no engine measurement exists. |

## Supported formats

ForeFire documentation lists text/`ff`, GeoJSON, and KML state output selected through `dumpMode`; `save[]` can write a NetCDF arrival-time map. Ember currently performs geometry extraction from GeoJSON and KML, array inspection from NPY/NPZ, and HDF5-backed NetCDF landscape extraction through `h5py`. NetCDF is not assumed to contain geometry, and KML/GeoJSON are not assumed to contain environmental rasters.

## Model/configuration observed

`tests/runff/params.ff` configures `propagationModel=Rothermel`, `spatialIncrement=3`, `perimeterResolution=10`, `propagationSpeedAdjustmentFactor=0.6`, `windReductionFactor=0.4`, and `minSpeed=0.009`. `rungeojson.ff` separately demonstrates Rothermel plus GeoJSON dump/reload. The docs also identify `Iso`, `Rothermel`, `BalbiNov2011`, and `Balbi2015`; Ember does not treat those as equivalently validated in this environment.
