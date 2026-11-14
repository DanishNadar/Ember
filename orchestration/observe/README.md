# Ember Observatory — live monitoring and concurrent CPU/GPU workflow

This is an **additive** implementation layered on the verified Fuzzball pilot.
It does not overwrite any existing pilot checkpoint, alter the simulator physics,
or merge anything into main.

## What is implemented

- Jupyter notebook: notebooks/Ember_Observatory.ipynb
- Structured JSONL events, printed in Fuzzball stdout as EMBER_EVENT.
- Per-epoch train/validation loss, IoU, Dice, precision, recall, pixel
  accuracy, conditional arrival MAE, elapsed times and hardware snapshots.
- Actual held-out ForeFire-vs-surrogate PNG galleries for six forecast horizons;
  per-scenario overlap/precision/recall. Correct orientation for [x_east,y_north].
- CPU ForeFire shard runner with actual simulator labels and sample hashes.
- Generated Fuzzball v4 scratch workflows for **two 16-core CPU jobs** and
  **up to two separate 1-GPU training jobs**. The scheduler decides placement.
- Optional genuine PyTorch DDP fine-tuning code (requires network rendezvous).
- Dashboard can replay the three old pilots (limited historical columns) and
  poll new Fuzzball logs with a working CLI.

These are *implemented files*, not a claim that new cluster jobs have run.
No Fuzzball tool is available to this ChatGPT session; new GPU and CPU
scheduling is not verified until a team member runs the workflow.

## Install notebook requirements

Within a Jupyter-capable Python environment (Windows or WSL):

~~~bash
python -m pip install jupyter ipykernel matplotlib numpy pandas pyyaml
jupyter notebook notebooks/Ember_Observatory.ipynb
~~~

Select the kernel in VS Code or Jupyter. PyTorch is NOT required on this
notebook machine if using retrieved PNGs and metrics.

Set RUNS_DIR in section 1 to your retrieved pilot folder. For the original
successful pilot, Codex retained files below
orchestration/fuzzball/runs/arrival-pilot-20261114-02. Your local run may be
in a sibling Ember-fuzzball-20261114 checkout rather than this Git worktree.

The notebook's live cell uses the Fuzzball CLI to obtain each job's stdout.
Set WORKFLOWS to the **actual** returned workflow ID and job names, then enable
START_LIVE_WATCH. It makes no API requests on notebook import.

## Rebuild the GPU package with instrumentation

Use the local project checkout with this branch's updated code and the
previously generated, genuine ForeFire PILOT DIRECTORY containing:

- data/train/*.npz, data/val/*.npz, data/test/*.npz
- dataset_manifest.json, baseline.yaml and lower_lr.yaml

The original successful pilot used 144 simulations, NOT all 26,000 source
scenario inputs. If those data are missing, do not substitute dummy examples.
Find the retained pilot dataset or regenerate with build_pilot.py.

~~~bash
python orchestration/fuzzball/prepare_experiment.py \
  --dataset PATH_TO_ACTUAL_PILOT_DATASET --prefix obs-20261114-01

fuzzball object put \
  orchestration/fuzzball/packages/obs-20261114-01-input.tgz \
  fb://user/ember/obs-20261114-01/input.tgz --ttl 30d

fuzzball object describe fb://user/ember/obs-20261114-01/input.tgz --output json
~~~

Check the remote object size/digest. The package builder automatically
includes ml/*.py (including observability and gallery), config, dataset and
the updated execute_training.py.

## Package CPU simulator inputs and create the parallel workflow

The physics package includes repository ForeFire scenario inputs, terrain
and fuel source assets, CPU runner, and telemetry code. Check the archive
size and object digest; never overwrite an existing object prefix.

~~~bash
python orchestration/observe/package_physics.py \
  --output orchestration/observe/physics-20261114-01.tgz

fuzzball object put \
  orchestration/observe/physics-20261114-01.tgz \
  fb://user/ember/obs-20261114-01/physics-input.tgz --ttl 30d

fuzzball object describe fb://user/ember/obs-20261114-01/physics-input.tgz --output json

python orchestration/observe/build_workflow.py \
  --training-uri fb://user/ember/obs-20261114-01/input.tgz \
  --physics-uri fb://user/ember/obs-20261114-01/physics-input.tgz \
  --result-prefix fb://user/ember/obs-20261114-01/results \
  --output orchestration/observe/obs-20261114-01.fz

fuzzball workflow validate orchestration/observe/obs-20261114-01.fz
fuzzball workflow start orchestration/observe/obs-20261114-01.fz --name ember-observatory-01 --output json
~~~

Do not blindly reuse the sample obs-20261114-01 prefix if it already exists;
choose a unique run prefix. Validation checks the YAML syntax, not whether
PyPI, NGC, resources or the input objects will be reachable at runtime.

The generated workflow has four independent jobs (no incorrect dependence
on shared NFS, which failed for the earlier pilot):

| Job | Request | Work |
| --- | --- | --- |
| physics-0 | 16 CPU cores, no GPU | Train-region shard 0 |
| physics-1 | 16 CPU cores, no GPU | Train-region shard 1 |
| train-baseline | 4 CPU cores + 1 NVIDIA GPU | Re-train on staged 144 ForeFire samples |
| train-lower-lr | 4 CPU cores + 1 NVIDIA GPU | Independent 0.0003-LR comparison |

Two CPU shards need separate placements under a 20-core-per-node limit.
16 physics cores plus a 4-core GPU job would occupy a full 20-core CPU
allocation, if the scheduler actually co-locates them and resources permit.
Actual placement and CPU utilization must be verified from logs/telemetry;
the Fuzzfile does not guarantee both GPUs/hosts will be available.
Use build_workflow.py --one-gpu to reduce GPU demand.

Each physics job uses a separate team15-scratch volume. At runtime it installs
forefire==2.6.0, netCDF4 and psutil into the validated ARM64-capable container.
If package download is disabled by cluster policy, build a pinned CPU image
with these dependencies and edit the image in the workflow before submission.
The ForeFire PyPI wheel is CPU-based; a CUDA-capable base *image* does not
mean the physics job requests a GPU.

**Concurrency semantics:** The GPU runs train against the already-staged
baseline dataset while CPU jobs generate *additional*, separately exported
train-region simulations. Newly generated labels are not magically absorbed
into an in-progress training process. To expand training, audit, combine,
and retrain in a later workflow with unchanged, independent val/test splits.

Each result object ends in:
- train-baseline-results.tgz
- train-lower-lr-results.tgz
- physics-0-results.tgz
- physics-1-results.tgz

Retrieve and extract each under its own fresh directory. Then point RUNS_DIR
in the notebook at the parent directory. Fuzzball job output is visible
during execution through:

~~~bash
fuzzball workflow list
fuzzball workflow log ACTUAL_WORKFLOW_ID train-baseline
fuzzball workflow log ACTUAL_WORKFLOW_ID physics-0
~~~

The live notebook uses those same commands.

## Metrics and limitations

- Train and validation loss are tracked per epoch. **Do not calculate a test
  curve every epoch**: keep the test set held out until final evaluation.
- IoU/Dice/precision/recall are based on true burned-by-horizon cells.
  Pixel accuracy may be inflated by unburned background.
- Arrival MAE is conditional on simulator-reached cells only. The PNG error
  panel and per-horizon false positives/negatives expose its blind spots.
- GPU/CPU utilization fields are **point-in-time host snapshots** collected
  at epochs/batches, not calibrated average utilization. The notebook leaves
  missing values blank.
- Timeline uses real event timestamps. Container-pull time and scheduler wait
  are NOT measured by these Python events; correlate with Fuzzball lifecycle
  logs when profiling those phases.
- ForeFire labels measure agreement with a simulator; no operational real-fire
  prediction claim.
- Results from the earlier pilot do not have structured new events or a
  gallery: replay what is present rather than inventing missing values.
- Real 2-node DDP requires a reachable rendezvous; Fuzzball does not switch
  from independent GPU trials to DDP automatically.

## Optional real DDP fine-tuning

ml/train_arrival_ddp.py implements DistributedDataParallel with one
torchrun process per GPU, a nonduplicating held-out validation partition,
global metric reductions and a checkpoint compatible with arrival_model.py.

The environment on **each node** must supply these coordinated values:
MASTER_ADDR, MASTER_PORT, RANK, WORLD_SIZE=2, LOCAL_RANK=0. Both nodes must
be able to connect to the same master rendezvous endpoint and read the
same approved starting checkpoint and training samples, staged locally.
After setting up those values on each participating node, use equivalent
to:

~~~bash
python -m torch.distributed.run \
  --nnodes=2 --nproc_per_node=1 \
  --node_rank=NODE_RANK --master_addr=MASTER_ADDR --master_port=MASTER_PORT \
  ml/train_arrival_ddp.py --config pilot/baseline.yaml \
  --resume pilot/outputs_baseline/best.pt --output UNIQUE_DDP_OUTPUT --epochs 10
~~~

This command is an integration recipe; NODE_RANK / rendezvous must be
provided by a verified multi-node launcher. Do NOT execute it by starting
two unrelated Fuzzball jobs without a communication path. The dashboard
only displays DDP stage transitions when this real DDP code runs and emits
ddp_finetune_started and ddp_finetune_finished.

## Validation

~~~bash
python -m pytest orchestration/observe/test_observatory.py -q
python -m py_compile ml/train_arrival.py ml/train_arrival_ddp.py \
  ml/observability.py ml/export_gallery.py orchestration/observe/*.py
~~~

More confidence requires a genuine end-to-end Fuzzball execution, checks
on actual CPU node placement, completed artifact egress and live notebook
refresh against a running workflow. These were not executed by ChatGPT.
