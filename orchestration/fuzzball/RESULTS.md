# Verified Ember training on Fuzzball - November 14, 2026

Training status: **Successful for a bounded genuine ForeFire pilot.** Three direct-arrival U-Nets completed 30 epochs each, reloaded their best checkpoints for held-out evaluation, and exported results that were retrieved and SHA-256 verified. This is not training on all 26,000 repository input scenarios.

| Run | Learning rate | Train wall seconds | Best epoch | Validation loss | Validation IoU | Validation arrival MAE (s) | Test loss | Test IoU | Test arrival MAE (s) | Forward mean (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Initial | 0.001 | 239.743 | 27 | 0.04932995 | 0.320707 | 594.865 | 0.02343823 | 0.743433 | 234.776 | 3.969 |
| Parallel A: baseline | 0.001 | 229.699 | 27 | 0.04912878 | 0.329381 | 594.695 | 0.02316111 | 0.758713 | 236.553 | 3.939 |
| Parallel B: lower LR | 0.0003 | 232.631 | 30 | 0.05012433 | 0.269081 | 575.349 | 0.02269065 | 0.636407 | 232.620 | 3.947 |

Parallel A (learning rate 0.001) is selected by the lowest best-checkpoint validation loss, 0.04912878 versus 0.05012433. Test results were excluded from the selection code and record. The lower-learning-rate model has slightly lower conditional arrival MAE, but lower burned-area overlap. Model selection follows the existing combined loss rather than choosing whichever test number looks better.

Arrival MAE is measured only on cells the simulator reached and does not penalize missed fire cells; report it with burned-by-3,600-second IoU. Threshold is 0.5. Inference timings use one resident CUDA sample, five warmups and 30 synchronized forwards; they exclude reading, preprocessing, transfers and output writing. No end-to-end latency, speedup, average GPU utilization, or real-world accuracy is claimed. Training wall time covers the original training CLI, including validation, but excludes image preparation, archive staging and final evaluation.

| Workflow | Status | What actually ran |
|---|---|---|
| `aa6f2ba4-17cf-44cd-82d4-302d366749dc` | Failed before training | ARM64 image preparation completed; NFS ingress mount failed. |
| `be538996-01e2-446f-96a3-c380693f049f` | Finished | Initial one-GPU 30-epoch training, checkpoint reload, test evaluation and result export. |
| `af697105-7739-4a20-823c-de303491edd9` | Finished | Two independent one-GPU 30-epoch jobs, both evaluated and exported. |

Initial training used CIQ-CHI-SPARK29. Parallel baseline used SPARK29; lower LR used CIQ-CHI-SPARK30. Private node IPs are omitted from this shared summary. Each used one NVIDIA GB10, four allocated CPU cores and 16 GiB requested memory. The node inventory reports 20 CPU cores and 127.9 GiB system memory per node. Both GPU kernels and actual PyTorch training/evaluation ran. Runtime: Linux aarch64, Python 3.12.3, PyTorch `2.15.0a0+875d815502.nv26.10`, CUDA 13.4, cuDNN 92700, NVIDIA driver 580.173.02, compute capability 12.1.

The parallel job containers overlapped for **271.456484 seconds** on separate nodes. A saved snapshot shows both processes advancing through epochs and writing independent checkpoints. This is parallel hyperparameter experimentation, not DistributedDataParallel, synchronized multi-node training, or elastic scaling. Job-container overlap includes staging/evaluation and is not an exact measurement of optimizer-step overlap.

| Parallel job | Container start (America/Chicago, CST) | Container end (CST) |
|---|---|---|
| baseline | 2026-11-14 14:29:51.984899 | 2026-11-14 14:34:23.524853 |
| lower-lr | 2026-11-14 14:29:52.068369 | 2026-11-14 14:34:32.042420 |

The retained dataset has 144 full ForeFire 2.6.0 simulations: train 96 (24 each Corsica, SoCal, NorCal, Great Basin); validation 24 (Texas Panhandle); test 24 (Montana). These represent four/one/one independent region families. Whole regions are exclusive to a split, conservatively keeping related terrain, ignitions and weather variations together. Arizona remains unused. The source 26,000-scenario CSV defines inputs only; existing reference KML/NetCDF fixtures were not substituted as training examples.

Every sample has float32 x `[19,320,320]`, float32 arrival seconds `[320,320]`, exact Unicode channel order, stable simulation/family identities, `dataset_kind=forefire`, 3,600-second horizon and 40-m cell size. Unreached cells use -9999 and are right-censored; reached times are in [0,3600]. Native array order is `[channel,x east,y north]`. The domain is 12.8 km square. There were 168 simulator attempts in the retained generation pass, zero simulator failures, one edge-hit exclusion and 23 surplus samples not selected. The retained pass took 21.147 seconds on four WSL CPU workers, not the Fuzzball GPU; that timing is not a GPU speedup benchmark.

The model receives the existing 19 physical channels: burnable, fuel depth, dead/live fuel loads, surface-to-volume ratio, extinction moisture, relative altitude, terrain gradients, pre/post wind u/v, shift time fraction, dead moisture classes, ignition and engine identity. Inputs and targets come from the same scenario row and actual simulation fuel/altitude arrays. Pre/post wind components and shift timing were checked against the simulation configuration; the prescribed 1,800-second wind ramp is recorded. The simulator wrapper's orientation/unit corrections were preserved. No missing weather fields or labels were invented.

Configuration changes are explicit: the default four proposed input channels are replaced with the actual 19-channel contract, ignition channel becomes `ignition`, CUDA is required, and paths point to unique experiment outputs. Grid 320, horizon 3600, base filters 16, depth 3, dropout 0, batch size 4, epochs 30, seed 42, baseline LR 0.001 and existing loss/optimizer settings are retained. Parallel B changes LR to 0.0003. The original training, loader and model source files were not modified. Normalization is fitted on training data only.

Only six region families and 144 simulations are represented. This is a small pilot, not evidence of robust operational generalization. Weather is prescribed scenario input, not a claim about observed weather. ForeFire Farsite's documented downslope behavior remains in these genuine simulator labels. Results measure simulator agreement, not observed wildfire prediction accuracy. Only the final 60-minute burned-mask overlap and conditional arrival MAE provided by the existing evaluator were measured.

Artifacts are retained under `orchestration/fuzzball/runs/arrival-pilot-20261114-02/`. Each output folder contains `best.pt`, `config_used.yaml`, `normalization.json`, `history.csv`, `run_summary.json`, `test_metrics.json`, the dataset manifest, training log and evaluation log. Workflow logs/events and container dependency snapshots are retained alongside the extracted folders.

| Run | Local checkpoint | Local configuration | Metrics and history |
|---|---|---|
| Initial | [best.pt](runs/arrival-pilot-20261114-02/retrieved_initial/pilot/outputs_initial/best.pt) | [config_used.yaml](runs/arrival-pilot-20261114-02/retrieved_initial/pilot/outputs_initial/config_used.yaml) | [summary](runs/arrival-pilot-20261114-02/retrieved_initial/pilot/outputs_initial/run_summary.json), [test metrics](runs/arrival-pilot-20261114-02/retrieved_initial/pilot/outputs_initial/test_metrics.json), [history](runs/arrival-pilot-20261114-02/retrieved_initial/pilot/outputs_initial/history.csv) |
| Parallel A: baseline | [best.pt](runs/arrival-pilot-20261114-02/retrieved_baseline/pilot/outputs_baseline/best.pt) | [config_used.yaml](runs/arrival-pilot-20261114-02/retrieved_baseline/pilot/outputs_baseline/config_used.yaml) | [summary](runs/arrival-pilot-20261114-02/retrieved_baseline/pilot/outputs_baseline/run_summary.json), [test metrics](runs/arrival-pilot-20261114-02/retrieved_baseline/pilot/outputs_baseline/test_metrics.json), [history](runs/arrival-pilot-20261114-02/retrieved_baseline/pilot/outputs_baseline/history.csv) |
| Parallel B: lower LR | [best.pt](runs/arrival-pilot-20261114-02/retrieved_lower_lr/pilot/outputs_lower_lr/best.pt) | [config_used.yaml](runs/arrival-pilot-20261114-02/retrieved_lower_lr/pilot/outputs_lower_lr/config_used.yaml) | [summary](runs/arrival-pilot-20261114-02/retrieved_lower_lr/pilot/outputs_lower_lr/run_summary.json), [test metrics](runs/arrival-pilot-20261114-02/retrieved_lower_lr/pilot/outputs_lower_lr/test_metrics.json), [history](runs/arrival-pilot-20261114-02/retrieved_lower_lr/pilot/outputs_lower_lr/history.csv) |

The selected checkpoint SHA-256 is `1c91d5cd169f40430f698a13464a8686141ff5b90c1c1cff6f75f9b577aee55b`. All three downloaded archives matched their remote object digests, and each downloaded checkpoint matched its runtime-recorded digest. Checkpoints were also reloaded by the original evaluator on the GPU before export.

The verified input package is `fb://user/ember/arrival-pilot-20261114-02/input.tgz` (164,303,759 bytes), SHA-256 `45e3b9acc5903fecb741a4020a57945d30a32650dab0e3ed88c1eec65b245b08`, with 165 member hashes plus the package manifest. Inputs and retained result copies have verified 30-day cache TTLs; local copies persist independently. Retained remote results:

- `fb://user/ember/arrival-pilot-20261114-02/verified/initial-results.tgz`
- `fb://user/ember/arrival-pilot-20261114-02/verified/baseline-results.tgz`
- `fb://user/ember/arrival-pilot-20261114-02/verified/lower-lr-results.tgz`

[Dataset provenance](runs/arrival-pilot-20261114-02/dataset_manifest.json), [input package manifest](runs/arrival-pilot-20261114-02/package_manifest.json), [isolated simulator dependencies](runs/arrival-pilot-20261114-02/dataset_generation_requirements.txt), [initial verification](runs/arrival-pilot-20261114-02/initial_verification.json), [parallel verification](runs/arrival-pilot-20261114-02/parallel_verification.json), [validation-only selection](runs/arrival-pilot-20261114-02/parallel_validation_selection.json), [observed training overlap](runs/arrival-pilot-20261114-02/parallel_training_overlap.json), [retained cache objects](runs/arrival-pilot-20261114-02/retained_artifacts.json).

Connection distinctions: this Codex session still has no registered/exposed Fuzzball MCP tools. WSL Fuzzball CLI and agent v4.3.1 work at `~/.local/bin/fuzzball`; the shell PATH omits that directory. Active context `ember-hackathon` authenticates as Team 15 at `api.fb-hack.civilfritz.net:443`. Cluster `fb-hack` is ready and authenticated API calls succeed. Inventory visibility covered 42 nodes, including 40 NVIDIA GB10 GPUs; that does not imply permission to use every team's resources. Actual compute accessibility is demonstrated on the two Team 15 GPUs by the completed CUDA training/evaluation workflows. No Codex/MCP configuration was changed.

The original staging check was `fuzzball object describe fb://user/ember/arrival-run01-input.tgz --output json`, which returned `object not found: user/ember/arrival-run01-input.tgz`. The local 905-byte archive contained only `model.py`; it lacked the arrival trainer, configuration and data. A complete package was built under a fresh URI and its remote digest verified before submission. The original broken submission was not retried.

The NFS failure is retained verbatim below. The existing `team15-scratch` HOSTPATH/NVMe provisioner succeeded instead; cluster settings were not changed. Repairing the NFS path still requires a cluster administrator to inspect NFS exports and CSI mount permissions.

```text
failed to publish volume 01a1dbb9-9b09-7c3f-aadb-b12a3a459575 for workflow aa6f2ba4-17cf-44cd-82d4-302d366749dc: failed to publish volume 01a1dbb9-9b09-7c3f-aadb-b12a3a459575: rpc error: code = Unknown desc = publishing volume: rpc error: code = Unknown desc = mounting NFS volume: mount -t nfs 10.10.11.15:/hackathon/team-15/ephemeral/aa6f2ba4-17cf-44cd-82d4-302d366749dc/initial-data /csi-publish/f3c5093a-c310-577c-9926-50eb3c719998/ephemeral/aa6f2ba4-17cf-44cd-82d4-302d366749dc/initial-data: exit status 32: mount.nfs: Operation not permitted
```

Additional diagnostics: `fuzzball debug logs workflow storage --since-duration 10m --tail 100` returned `error fetching logs for service workflow: error receiving log: rpc error: code = PermissionDenied desc = cluster admin required`. Administrator intervention was not needed for the scratch workaround. The aggregate `node list --available-resources` lookup also encountered a stale allocation on another team's node (`sql: no rows in result set`; private node address and allocation identifier omitted). Per-node checks on Team 15 succeeded; an administrator can investigate that stale scheduler record separately.

Code added only in this isolated worktree on branch `codex/fuzzball-arrival-20261114`, based on source commit `3d4c8ffdaae8da49c6c567716b4b62f36b7c5911`: [build_pilot.py](build_pilot.py) generates/validates real labels and provenance; [prepare_experiment.py](prepare_experiment.py) audits/package-hashes data and emits bounded workflows; [execute_training.py](execute_training.py) wraps unchanged training/evaluation with CUDA, timing and artifact verification; `.gitignore` isolates generated artifacts; README, this report, and four Fuzzfiles document the executed setup. Historical non-scratch definitions are marked and preserved. The two `*-scratch.fz` files are the executed working definitions. Original datasets, checkpoints, teammates' files and the original main checkout were not overwritten. Nothing was pushed or merged.

Remaining limits: full 26,000-scenario labelling/training was not performed; the team NFS mount remains faulty, but scratch plus object-cache exports completed the requested pilot. No running experiment workflows remain. A first generation attempt was preserved after a Windows/Linux Git-worktree-path failure; explicit source-commit capture fixed it and a fresh output directory was used.

Hackathon summary: "We generated 144 genuine ForeFire simulations, trained the actual direct-arrival U-Net on Fuzzball, ran two independent experiments concurrently on two NVIDIA GB10 nodes, and retrieved verified checkpoints. The validation-selected baseline reached 0.759 held-out simulator IoU and 236.6-second conditional arrival MAE. These are small-pilot simulator-agreement results, not real-world wildfire prediction accuracy."
