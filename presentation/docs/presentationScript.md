# Project Ember — Presentation Script

Generated from `slides/speakerNotes.json` (run `npm run docs:script`). Target ≈ 7:20 for 17 scenes; questions in Explore mode (`E`).
Keys: `→`/`Space` next build · `Shift+→` skip builds · `S` reveal builds · `N` notes · `P` presenter.

## 01 · The Spark (~15 s)
**Message:** One spark can lead to many possible futures. Project Ember is about exploring them faster.
- Let the animation breathe for about three seconds before speaking.
- We are Project Ember: an adaptive wildfire surrogate.
- Our goal is to go from simulating one future to exploring thousands.
- Built this weekend on two NVIDIA GB10 nodes, orchestrated end to end with CIQ Fuzzball.

**Do:** No clicks needed. The ember lands, the fire spreads, and alternative fronts flash in cyan. The logo appears at about 6 s. Press → once the logo is up.
**Evidence:** Opening visual is an architectural illustration from the deck's own toy spread model, not simulator output (badge bottom-left).
**Transition:** “But why does one spark have so many futures? Because conditions change.”

## 02 · The Human Problem (~20 s)
**Message:** The same starting point can produce very different simulated outcomes when conditions change.
- Wildfire threatens ecosystems, communities, infrastructure and livelihoods.
- Watch the same ignition under four condition sets: wind direction, wind speed, fuel moisture.
- The burned footprint near the structures changes every time. These are illustrations, not forecasts.

**Do:** The scene cycles through condition presets automatically. Press → to reveal the closing statement: 'When conditions change, the questions multiply.'
**Evidence:** Illustrative only; condition panel values drive the toy model and are labeled as such.
**Transition:** “A physics simulator answers exactly one of these questions at a time.”

## 03 · One Simulation Isn't Enough (~20 s)
**Message:** A simulation is one answer to one set of assumptions. Covering the uncertainty takes many runs.
- On the left: one deterministic run with its input assumptions.
- Each uncertain input we vary multiplies the number of runs: 1, then 3, then 9, then 27.
- A simulated trajectory is a model of what could happen under assumptions, not a record of what will happen.

**Do:** Press → twice to grow the scenario tree one level at a time.
**Evidence:** Conceptual diagram. Branch counts show combinatorics, not measured workloads.
**Transition:** “And every branch costs compute.”

## 04 · The Computational Challenge (~15 s)
**Message:** Each question we ask adds another independent simulation job.
- Scenario requests pile up faster than a fixed pool of workers can drain them.
- This is normalized and conceptual: no timings are shown here because none are claimed.
- So the question becomes: what if the physics could be approximated?

**Do:** Let the queue fill for about 5 s, then press → to reveal the question.
**Evidence:** Normalized conceptual animation. Measured runtimes appear only on the Performance slide.
**Transition:** “That question is Project Ember.”

## 05 · Meet Project Ember (~25 s)
**Message:** Ember is a pipeline: physics teaches, AI learns, Fuzzball coordinates, and we explore.
- Simulation generates examples. Examples become a dataset. A U-Net-style surrogate learns from it.
- We evaluate against held-out simulator outputs. Fuzzball runs every stage as one workflow on our two GB10 nodes.
- Each status chip shows what is implemented and what is proposed.

**Do:** The pipeline draws itself. Click 'Neural surrogate' to open its card (role, inputs, outputs, compute, status), then click 'Fuzzball orchestration'.
**Evidence:** Status chips come from snapshot.components. Until confirmed they read 'unconfirmed'.
**Transition:** “Before the science, here's the stack we built it on.”

## 06 · Built on the Hackathon Stack (~30 s)
**Message:** Ember uses the whole hackathon stack: NVIDIA GB10 hardware, CIQ's RLC Pro AI, and Fuzzball as the backbone.
- Bottom up: 2 × Lenovo ThinkStation PGX with NVIDIA GB10, running RLC Pro AI 9.8 with the CUDA stack ready on first boot.
- Fuzzball Substrate runs our containers on both nodes, Orchestrate schedules them, and volumes carry shards and checkpoints between stages.
- We drove it through the Fuzzball CLI, web UI and MCP server.
- Each chip says how we used that layer. Green means used, and logs upgrade it to verified.

**Do:** Layers build bottom-up. Click 'Fuzzball Orchestrate', then 'Fuzzball volumes' to show what's provided vs how Ember uses it.
**Evidence:** Environment facts are cited to the organizers' SC26 Hackathon Introduction deck. Usage status comes from data/verified/ecosystemUsage.json, and only Fuzzball logs upgrade it to 'verified'.
**Transition:** “Now the science, starting with the physics.”

## 07 · The Physics Engine (~25 s)
**Message:** First, we let physics teach. The simulator produces the ground truth the surrogate learns from.
- Name the simulator exactly as configured (ForeFire, or our simplified simulator, as the badge states).
- Inputs: initial burned area, wind, fuel, moisture and slope layers. Output: burned-area masks over time.
- Use the scrubber to show progression.

**Do:** Press play, then drag the time scrubber. Toggle 'Environment layers' and 'Progression lines'.
**Evidence:** With a recorded replay ingested, frames are simulator output (orange badge). Otherwise the viewer shows a labeled illustrative stand-in.
**Transition:** “Each of those frames becomes a training lesson.”

## 08 · From Simulation to Data (~20 s)
**Message:** Every completed simulation becomes supervised training examples: input channels in, future mask out.
- One snapshot splits into aligned channels: burned mask, wind U/V, fuel, moisture, slope.
- The target is the burned-area mask at a fixed horizon later.
- We split by scenario, not by frame, so test scenarios are never seen in training.

**Do:** Press → to explode the snapshot into channels, then again to show the dataset split.
**Evidence:** Split counts come from data/manifest.json. Thumbnails are illustrative unless real samples are ingested.
**Transition:** “Now the model learns from those pairs.”

## 09 · The Neural Surrogate (~25 s)
**Message:** A lightweight U-Net learns the mapping from conditions to the next fire extent.
- The encoder compresses spatial context, and the decoder rebuilds a full-resolution mask.
- Skip connections keep fine edges of the fire front.
- The spec panel reads from model metadata: parameter count, resolution, training config, device.

**Do:** Toggle 'Architecture / Prediction' at the top right. Prediction view shows real held-out predictions when ingested.
**Evidence:** All numbers come from model metadata and the checkpoint. A dash means not yet ingested.
**Transition:** “Training and simulation have to run somewhere. Here's the cluster.”

## 10 · The Two-Node Experiment (~30 s)
**Message:** Two GB10 nodes, one continuous experiment: simulation produces while training consumes, then both nodes fine-tune the surrogate together.
- Planned architecture: Node A generates simulation shards, and Node B trains and evaluates.
- Once the base surrogate is trained, both GB10s join for distributed fine-tuning: one model, data-parallel across Node A and Node B, with gradients synchronized between them.
- Fuzzball Orchestrate coordinates dependencies, and shards move through a Fuzzball volume. Both nodes run RLC Pro AI 9.8 and Fuzzball Substrate.
- Switch to Verified Execution to show what the logs actually recorded, including placement.

**Do:** Start in 'Planned architecture', then click 'Verified execution'. If logs are ingested it shows real job placement. Otherwise it says so.
**Evidence:** Verified view is built only from Fuzzball workflow logs (snapshot.workflow).
**Transition:** “Here's how we told Fuzzball to do that: the workflow itself.”

## 11 · One Fuzzball Workflow (~35 s)
**Message:** The entire experiment is one declarative Fuzzball workflow, which is why it's reproducible and scales across both nodes.
- ① A persistent Fuzzball volume is shared by every job on both nodes.
- ② Simulation fans out as a task-array: one scenario shard per task.
- ③ depends-on with status RUNNING lets the dataset build and training start while simulation is still producing. That's our producer–consumer overlap.
- ④ Training and evaluation request nvidia.com/gpu, so Orchestrate places them on a GB10 GPU.
- We validate, start, watch and pull logs with the Fuzzball CLI.

**Do:** Press → three times to step through the four highlights, or click any callout.
**Evidence:** Until the team's real Fuzzfile is ingested this shows a reference template written to the documented v4 syntax (labeled). Once ingested, the real file is shown verbatim.
**Transition:** “And here is what happened when we ran it.”

## 12 · Fuzzball Orchestration (~25 s)
**Message:** Fuzzball turned the experiment into a recorded, dependency-aware run we can replay and reproduce.
- Each bar is a recorded job, with start, end, state and node.
- Arrows show dependencies. Training starts only when its data exists.
- Fuzzball orchestrates. It does not optimize the model.

**Do:** Hover a bar for job details. Point out overlap between simulation and training if present.
**Evidence:** Timeline is reconstructed from recorded workflow logs. It is labeled 'Recorded playback', never live.
**Transition:** “So did the AI actually learn the physics?”

## 13 · The Moment of Truth (~40 s)
**Message:** On held-out simulated scenarios, here's how closely the surrogate matches the simulator, including where it misses.
- Left: simulator reference. Middle: surrogate prediction. Right: error map (orange = over-predicted, cyan = missed).
- Read the IoU, precision, recall and F2 for the held-out split.
- Show a hard case on purpose. Honesty about failure modes is part of the result.
- This is fidelity to simulation, not real-world forecast skill.

**Do:** Click through the scenario selector, including the weakest example.
**Evidence:** metrics/results.json via snapshot.fidelity. Per-example metrics are recomputed from masks when masks are provided.
**Transition:** “Accuracy is half the story. Did we save compute?”

## 14 · The Performance Reveal (~35 s)
**Message:** We report three separate accelerations, and training cost on its own.
- Surrogate acceleration: simulator runtime vs neural inference per scenario.
- Parallel throughput: one node vs two nodes.
- Workflow acceleration: sequential vs overlapping pipeline.
- We never multiply these into one headline number. Training cost is shown separately, so the comparison is honest.

**Do:** Point at each of the three cards in turn. Any card without measurements shows 'Awaiting'.
**Evidence:** Each card cites snapshot.benchmarks.source. Speedups are computed only when both measurements exist.
**Transition:** “Faster evaluation changes which questions we can afford to ask.”

## 15 · What Compute Unlocks (~25 s)
**Message:** More compute means more scenarios, and an ensemble shows where outcomes agree and where they don't.
- One footprint, then many footprints, then an agreement map.
- Agreement is the fraction of ensemble members that burn a cell. It is not a calibrated probability.
- This is a proposed extension unless an ensemble result is ingested (see badge).

**Do:** Drag 'Ensemble size' from 1 to 24, then toggle 'Agreement heatmap'. Optionally select individual members.
**Evidence:** Marked as proposed future work and illustrative unless snapshot.ensemble exists.
**Transition:** “So what did we actually build?”

## 16 · Built for Every Criterion (~30 s)
**Message:** Ember was built against all four official criteria, and the deck shows evidence for each.
- Technical execution: a complete simulate → learn → evaluate system, recorded as a Fuzzball workflow.
- Ecosystem utility: NVIDIA GB10, CIQ RLC Pro AI and the full Fuzzball platform, each with its usage status.
- Value and impact: faster what-if exploration for wildfire research, with honest limits.
- Innovation: a physics-trained surrogate plus producer–consumer overlap across two nodes.

**Do:** Sweep left to right across the four columns. A green check means an ingested artifact backs it.
**Evidence:** Criteria text is quoted from the organizers' deck (pp. 3, 5). Checks are derived from the snapshot, never typed in.
**Transition:** “So here's where Ember goes next.”

## 17 · The Next Frontier (~25 s)
**Message:** We didn't replace physics. We made it reusable.
- Read the checkmarks: only evidenced contributions are marked complete.
- Point at 'Built with': Fuzzball, CIQ, NVIDIA, Lenovo and VAST, the hackathon stack we built on.
- Next: real environmental data, physics-informed learning, adaptive simulation requests, larger ensembles.
- Quantum-enhanced probability estimation is a future research direction, not part of Ember today.
- Close: Project Ember, from one simulation to a scalable scientific-AI workflow.

**Do:** Press → once to bring back the ember and logo for the close. Leave it on screen for questions, and open Explore mode (E) for deep dives.
**Evidence:** Contribution status derives from snapshot evidence. Future items are badged 'Proposed'.
**Transition:** “Thank you. Questions?”
