# Project Ember — Presentation Script

Target: about 7:00 for the main talk (sum of per-scene targets), then questions in Explore mode.
The presenter window (`P`) shows a pace indicator against these targets.

Keys: `→`/`Space` next build, `Shift+→` skip builds, `S` reveal all builds, `N` notes, `O` chapters, `E` explore.

> These notes mirror `slides/speakerNotes.json`, which the app reads. If you change one, change the other.

---

## 01 · The Spark (~20 s)
**Message:** One spark can lead to many possible futures. Ember explores them faster.
- Let the animation run about 3 s before speaking.
- "We are Project Ember: an adaptive wildfire surrogate."
- "Our goal: go from simulating one future to exploring thousands."

**Do:** Nothing. The ember lands, the fire spreads and cyan alternative fronts flash. The logo appears at about 6 s. Press `→`.
**Evidence:** Illustration from the deck's toy model (badge bottom-left), not simulator output.
**Transition:** "But why does one spark have so many futures? Because conditions change."

## 02 · The Human Problem (~25 s)
**Message:** The same start can produce very different simulated outcomes when conditions change.
- Fire threatens ecosystems, communities, infrastructure and livelihoods.
- Four condition sets cycle on screen: wind direction and speed, fuel moisture. Watch the structures near the front.
- These are illustrations, not forecasts.

**Do:** Let it cycle once, then press `→` for "When conditions change, the questions multiply."
**Transition:** "A physics simulator answers exactly one of these questions at a time."

## 03 · One Simulation Isn't Enough (~25 s)
**Message:** One run answers one set of assumptions. Covering the uncertainty takes many runs.
- Left: one deterministic run with its inputs.
- `→` grows the tree: 3 wind directions × 3 speeds × 3 moisture levels = 27 runs.
- "A simulated trajectory is a model under assumptions, not a record of what will happen."

**Do:** Press `→` twice.
**Transition:** "And every branch costs compute."

## 04 · The Computational Challenge (~20 s)
**Message:** Every question adds an independent simulation job.
- Requests arrive faster than a fixed worker pool can drain them.
- Normalized and conceptual. No timings are claimed here.

**Do:** Let the queue fill for about 5 s, then press `→` to reveal **"What if the physics could be approximated?"**
**Transition:** "That question is Project Ember."

## 05 · Meet Project Ember (~35 s)
**Message:** Physics teaches, AI learns, Fuzzball coordinates, and we explore.
- Simulate, then dataset, then U-Net surrogate, then evaluate, with Fuzzball orchestrating every stage.
- Status chips come from `snapshot.components`. Only claim what they show.

**Do:** Click **Neural surrogate**, then **Fuzzball orchestration**, to show role, I/O, compute and status.
**Transition:** "Let's start where the knowledge comes from: the physics."

## 06 · The Physics Engine (~30 s)
**Message:** The simulator produces the reference the surrogate learns from.
- Name the simulator exactly as the panel states (ForeFire, or the simplified simulator).
- Inputs are burned area, wind, fuel, moisture and slope. Output is burned-area masks over time.

**Do:** Press ▶, drag the scrubber, and toggle *Environment layers* and *Progression lines*.
**Evidence:** An orange badge means a recorded simulator replay. A grey badge means the illustrative stand-in.
**Transition:** "Each of those frames becomes a training lesson."

## 07 · From Simulation to Data (~25 s)
**Message:** Completed simulations become supervised pairs: input channels in, future mask out.
- One snapshot splits into aligned channels. The target is the mask at t + horizon.
- We split by scenario, so test scenarios are never seen in training.

**Do:** `→` explodes the channels, and `→` again shows the split (from `data/manifest.json`).
**Transition:** "Now the model learns from those pairs."

## 08 · The Neural Surrogate (~30 s)
**Message:** A lightweight U-Net maps conditions to the next fire extent.
- The encoder captures context, skip connections keep the front edge sharp, and the decoder outputs a full-resolution mask.
- The model card shows parameters, resolution, training config and device, all from metadata.

**Do:** Toggle **Prediction view** to show a held-out prediction.
**Transition:** "Training and simulation have to run somewhere. Here's the cluster."

## 09 · The Two-Node Experiment (~35 s)
**Message:** Planned design: simulation produces on Node A while Node B trains and evaluates.
- Fuzzball handles dependencies, staging and artifact handoff.
- Switch to **Verified execution**, which is built only from Fuzzball logs. If the logs show one node, say so.

**Do:** Toggle *Planned architecture*, then *Verified execution*.
**Transition:** "Let's look at that execution on a timeline."

## 10 · Fuzzball Orchestration (~30 s)
**Message:** Fuzzball made the multi-stage experiment reproducible and dependency-aware.
- Bars are recorded jobs: start, end, state, node. Arrows are dependencies.
- "Fuzzball orchestrates. It does not optimize the model."

**Do:** Hover a bar for job details, and point out any simulation/training overlap.
**Evidence:** Labeled *Recorded playback · not live*.
**Transition:** "So did the AI actually learn the physics?"

## 11 · The Moment of Truth (~45 s)
**Message:** On held-out simulated scenarios, here is how close the surrogate gets, including where it misses.
- Reference, prediction and error map (orange = over-predicted, cyan = missed).
- Read IoU, precision, recall, F2 and area error for the held-out split.
- Click the example tagged **weakest** on purpose.
- "This is fidelity to simulation, not real-world forecast skill."

**Transition:** "Accuracy is half the story. Did we save compute?"

## 12 · The Performance Reveal (~40 s)
**Message:** Three separate accelerations, and training cost on its own.
- Surrogate acceleration (simulator vs inference per scenario).
- Parallel throughput (one vs two nodes).
- Workflow acceleration (sequential vs overlapping).
- "We never multiply these into one number." If a ratio is below 1×, say why.

**Transition:** "Faster evaluation changes which questions we can afford to ask."

## 13 · What Compute Unlocks (~30 s)
**Message:** More scenarios give an ensemble, and agreement shows where outcomes converge.
- `→` goes from one footprint to many footprints to the agreement heatmap.
- "Agreement is a fraction of members, not a calibrated probability."
- Badged as a proposed extension unless an ensemble was actually ingested.

**Do:** Drag *Ensemble size* and pick members.
**Transition:** "So what did we actually build?"

## 14 · The Next Frontier (~30 s)
**Message:** We didn't replace physics. We made it reusable.
- Read the checkmarks. Only evidenced items are checked.
- Next steps: real environmental data, physics-informed learning, adaptive simulation requests, larger ensembles.
- Quantum-enhanced probability estimation is a research direction. It is not implemented.

**Do:** Press `→` for the ember and logo outro. Leave it up during questions, and press `E` for Explore.
**Close:** "Project Ember: from one simulation to a scalable scientific-AI workflow. Thank you."
