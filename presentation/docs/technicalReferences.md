# Technical References & Assumptions

## External facts the deck states
| Claim in deck | Where | Source |
|---|---|---|
| The hackathon runs Nov 13–15, 2026 in Chicago, before SC26. Teams use two Lenovo ThinkStation PGX (NVIDIA GB10 Grace Blackwell) systems orchestrated by CIQ Fuzzball. | Slide 1 kicker, slide 9 | CIQ press release, Oct 7, 2026 (GlobeNewswire; republished by HPCwire) |
| ThinkStation PGX is built on the NVIDIA GB10 Grace Blackwell Superchip. | Slide 9 node labels | Lenovo PSREF ThinkStation PGX spec; Lenovo Press LP2321 |
| Fuzzball is CIQ's container-first, job-based workflow orchestration platform for HPC/AI. | Slides 5, 9, 10 | ciq.com/products/fuzzball; CIQ blog "Fuzzball: the future of performance computing" |
| ForeFire is an open-source (GPLv3) wildfire spread simulation engine from CNRS / Università di Corsica. | Slide 6 (only if the team used it) | Filippi et al. (2025), *ForeFire: A Modular, Scriptable C++ Simulation Engine and Library for Wildland-Fire Spread*, JOSS 10(116), 8680, doi:10.21105/joss.08680; github.com/forefireAPI/forefire |
| U-Net encoder–decoder with skip connections. | Slide 8 | Ronneberger, Fischer & Brox (2015), *U-Net: Convolutional Networks for Biomedical Image Segmentation*, MICCAI |

GB10 specs (memory, TOPS, core counts) are **not** shown on slides. They are the vendor's numbers, not project measurements.

## Metric definitions (lib/maskMetrics.ts)
- IoU = TP / (TP + FP + FN)
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F2 = 5·P·R / (4·P + R), which weights recall higher (missing burned area is the costlier error)
- Burned-area error = (predicted area − reference area) / reference area, signed

Undefined ratios (zero denominators) are `null` and render as "—", never as 0.

## Derived comparisons (data/adapters/presentationData.ts)
- **Surrogate acceleration** = simulator s/scenario ÷ surrogate s/scenario. Computed only if both values exist with identical units. Excludes training.
- **Parallel throughput scaling** = two-node scenarios/s ÷ one-node scenarios/s.
- **Workflow acceleration** = sequential seconds ÷ overlapping seconds.
- These three are never multiplied together. Training cost is shown separately.

## The illustrative model (lib/fireModel.ts)
Opening visuals, the landscape, the scenario tree, the replay stand-in and the ensemble demo are driven by a small, deterministic **minimum-travel-time spread model**: Dijkstra arrival times on a 192×108 grid. Its parameters are seeded fractal terrain, fuel and water, plus wind, slope and moisture factors.

It is **not** ForeFire, not the project's simulator and not the neural surrogate. Every visual that uses it carries an *Architectural illustration* or *Proposed* badge. It exists so the deck animates reproducibly offline.

## Libraries
Next.js 15 (static export), React 19, TypeScript 5, Tailwind CSS 3, Framer Motion, lucide-react, @fontsource (Space Grotesk, Inter, JetBrains Mono, bundled locally), and Vitest. Charts are hand-built SVG and Canvas so there are no runtime chart dependencies, and the deck renders offline.

## Assumptions to confirm with the team
1. Simulator identity (ForeFire vs simplified) → `snapshot.simulator.name/kind`.
2. Split unit (scenario vs example) → `dataset.splitUnit`.
3. Whether both nodes ran concurrently → only from Fuzzball logs.
4. Whether an ensemble was executed → slide 13 stays "proposed" otherwise.
