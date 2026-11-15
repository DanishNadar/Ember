# Project Ember — Presentation Script

Generated from `slides/speakerNotes.json` (run `npm run docs:script`). Target ≈ 4:40 for 10 scenes; questions in Explore mode (`E`).
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

## 03 · The Computational Challenge (~15 s)
**Message:** Each question we ask adds another independent simulation job.
- Scenario requests pile up faster than a fixed pool of workers can drain them.
- This is normalized and conceptual: no timings are shown here because none are claimed.
- So the question becomes: what if the physics could be approximated?

**Do:** Let the queue fill for about 5 s, then press → to reveal the question.
**Evidence:** Normalized conceptual animation. Measured runtimes appear only on the Performance slide.
**Transition:** “That question is Project Ember.”

## 04 · The Idea (~25 s)
**Message:** Let physics teach, let AI learn: a simulator makes labeled examples, a neural surrogate learns from them.
- ForeFire is a real fire-spread physics simulator. It is accurate, but each run answers one 'what if' and costs CPU time.
- Each run becomes a labeled example: conditions in, where and when the fire arrives out.
- A U-Net learns that mapping on the GPU, so new scenarios can be answered in one forward pass. And we run simulation and training at the same time across two nodes.

**Do:** The three stages and the loop build in on their own.
**Evidence:** Concept diagram.
**Transition:** “So what did we actually feed it?”

## 05 · The Data (~30 s)
**Message:** Real ForeFire simulations on real terrain, with a strict held-out test set.
- We prepared about 26,000 candidate conditions and kept 2,880 completed ForeFire simulations: 2,400 train, 300 validation, 180 test.
- Each sample is a 320 by 320 grid of 40-meter cells, about 13 km square, with 19 input channels: fuel, moisture, slope, wind including a mid-run shift, and the ignition.
- The model predicts two things over 60 minutes: which cells burn and when the fire arrives. The test set is never used to train or pick the model.

**Do:** Let the split bar and fact tiles animate in.
**Evidence:** File counts checked directly, Nov 15.
**Transition:** “We didn't start there.”

## 06 · Scaling Up (~25 s)
**Message:** Our first prototype learned from one region; scaling up the physics data made its timing much sharper.
- The prototype trained on 508 Texas simulations and was scored on 32 validation scenarios: arrival time off by about 10.5 minutes.
- We scaled to 2,880 simulations across multiple regions. Arrival-time error dropped to about 7 minutes, a third lower, on a test set more than five times larger that the model never saw.
- Burn-area overlap held steady at about 0.48 to 0.49 even though the test got much broader. These are different test sets, so this shows the trend, not a controlled A/B.

**Do:** Columns and stat cards animate in.
**Evidence:** Prototype: 32-scenario validation. Scaled: 180-scenario held-out test. Different channels, regions and splits.
**Transition:** “Here's the scaled model in detail.”

## 07 · How Close Did AI Get? (~35 s)
**Message:** On 180 simulations it never saw, the surrogate matches the physics reasonably well and errs on the cautious side.
- Precision 0.78: when it says a cell burns, it is usually right. Recall 0.55: it misses some burned area. Dice 0.65, IoU 0.48.
- Arrival time is off by about 7 minutes on average over a 60-minute horizon.
- It trained in about 11 minutes on a single GPU and the whole model is under 2 MB.
- To be clear: this is agreement with the simulator, not real-world forecast accuracy.

**Do:** None; bars animate in.
**Evidence:** Earlier held-out evaluation on 180 ForeFire test simulations (separate from runs 1–4).
**Transition:** “Getting the system to scale was the hard part.”

## 08 · What Broke and How We Fixed It (~45 s)
**Message:** Most of our time went into making physics and AI run together on real hardware. Four problems stood out.
- We couldn't reach the Fuzzball cluster off-site, so we built and proved each stage in small test runs first and staged the Fuzzball workflow for the on-site GB10 nodes.
- ForeFire and PyTorch lived in incompatible Python environments, so we built a launcher that gives each its own runtime on the same node.
- Our first full two-node run failed: the merge step rejected a duplicate label. That's the validator doing its job. We fixed the shard assignment, kept the strict check, and the next run passed.
- A shared storage mount refused permission, so we moved to node-local scratch with hash-checked handoffs.

**Do:** The four test runs appear left to right, failure included, then the four fixes.
**Evidence:** Runs 1–4 on Nov 15; run 3 failed at the merge step.
**Transition:** “And here's that final run.”

## 09 · Two Nodes, One Model (~45 s)
**Message:** Two nodes simulated and trained at the same time, merged verified labels, then fine-tuned one model across both GPUs.
- Phase one: on each node, ForeFire ran on the CPUs while the surrogate trained on the GPU, overlapping about 7 seconds on each node in this short run.
- Then a barrier: we verified 126 fresh labels and merged them into training. Validation and test stayed untouched.
- Phase two: one model, two GPU ranks, PyTorch DDP over NCCL. Both ranks ended with byte-identical weights. The whole job took 1 minute 40 seconds.
- This was a short proof run; we're not claiming a speedup yet.

**Do:** Press → to build: ① both nodes, ② verify + merge, ③ distributed fine-tuning and the summary stats.
**Evidence:** Two-node test run on Nov 15 (run 4); DDP summary and per-node phase summaries.
**Transition:** “So where does that leave us?”

## 10 · The Next Frontier (~25 s)
**Message:** We didn't replace physics. We made it reusable.
- Read the checkmarks: only evidenced contributions are marked complete.
- Point at 'Built with': Fuzzball, CIQ, NVIDIA, Lenovo and VAST, the hackathon stack we built on.
- Next: real environmental data, physics-informed learning, adaptive simulation requests, larger ensembles.
- Quantum-enhanced probability estimation is a future research direction, not part of Ember today.
- Close: Project Ember, from one simulation to a scalable scientific-AI workflow.

**Do:** Press → once to bring back the ember and logo for the close. Leave it on screen for questions, and open Explore mode (E) for deep dives.
**Evidence:** Contribution status derives from snapshot evidence. Future items are badged 'Proposed'.
**Transition:** “Thank you. Questions?”
