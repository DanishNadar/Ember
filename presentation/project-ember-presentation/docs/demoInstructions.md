# Demo Instructions

## Start
```bash
npm install
npm run dev            # http://localhost:3000
# or the production/offline build:
npm run build          # static export to ./out
npx serve out          # any static server works; no network needed
```
Requires Node 18.18+ (tested on Node 22). The deck needs no GPU, Fuzzball cluster or internet. Fonts and metrics are bundled.

## Navigate
| Key | Action |
|---|---|
| `→` `Space` `PgDn` | next build / slide |
| `←` `Shift+Space` `PgUp` | previous |
| `Shift+→` / `↓` | skip remaining builds |
| `S` | reveal all builds on the current slide |
| `Home` / `End` | first / last |
| `O` or `G` | chapter overview |
| `N` | notes drawer |
| `F` | fullscreen |
| `A` | autoplay (dwell ≈ speaking time / builds) |
| `T` / `R` | start-pause / reset timer (auto-starts on first advance) |
| `M` | reduced motion (also follows the OS setting) |
| `E` | Explore mode in a new tab |
| `?` | shortcut help |

URLs deep-link: `/#/11` opens scene 11, and `/#/13.2` opens scene 13 at build 3.

## Presenter mode
Press `P` (or the toolbar's Presenter button). A second window opens with the current slide, a next-slide preview, notes, a timer and a pace indicator against the ~7:00 target. The two windows stay in sync through BroadcastChannel, so either one can drive. Put the audience window on the projector and press `F`.

## Update metrics (no slide edits needed)
1. Point the ingester at the experiment repo:
   ```bash
   EMBER_REPO=/path/to/ember npm run ingest
   # or: node scripts/ingestArtifacts.mjs --repo /path/to/ember --dry-run
   ```
2. If your paths differ, edit `data/adapters/artifactConfig.json` (each key lists candidate paths).
3. The script writes `data/verified/presentationSnapshot.json` with a SHA-256 for every source. It keeps the previous snapshot as `.previous.json`. It never modifies the experiment repo, and it copies images into `public/experiment-assets/`.
4. Rebuild (`npm run build`). Check Explore → *Data & evidence* for validation issues.

Accepted shapes (flexible key names are documented in the script):
- `metrics/results.json`: aggregate metrics (`iou`, `precision`, `recall`, `f2`, `burned_area_error`) plus optional `examples[]` with reference/prediction masks (0/1 nested arrays or "0101" row strings) or image paths.
- `data/manifest.json`: scenario counts, splits (counts or ID lists) and input channel names.
- Model metadata JSON: type, parameter count, shapes, device and training config. A `.pt` file alone is **not** parsed. Parameter counts are never guessed.
- Fuzzball workflow status JSON: jobs with name, status, start/end, host/node, depends_on and resources.
- Benchmarks: JSON, or CSV with `metric,value,unit` rows (e.g. `simulator_seconds_per_scenario`).
- `presentation/components.json`: `[{ "id": "surrogate", "status": "implemented", "sourceFiles": ["model/unet.py"] }]`.

- **Your Fuzzfile** (`fuzzball/ember.yaml`, etc.): shown verbatim on scene 11 in place of the reference template. `npm run export:fuzzfile` writes the template to `fuzzball/ember.fuzzfile.yaml` as a starting point.
- **Ecosystem usage** (`presentation/ecosystemUsage.json`, or edit `data/verified/ecosystemUsage.json` directly): set each stack layer to `teamStated`, `planned`, `environment` or `unconfirmed`. **Confirm VAST Data and volumes before presenting.** Orchestrate, Substrate and hardware upgrade to "verified" automatically when Fuzzball logs are ingested.

A missing file leaves its section **awaiting**. Nothing is filled with zeros.

## Preview layouts before results exist
`/?fixture=sample` loads a synthetic fixture so you can rehearse scenes 9–14. Every slide then shows an **"Illustrative fixture — not experiment results"** banner. **Never present with `?fixture`.**

## Offline backup
- `out/` is fully self-contained. Copy it to a USB stick and open it with any static server, or run `npx serve out`.
- Recorded Fuzzball logs are shown as *Recorded playback · not live*. The deck has no live-monitoring mode, so it cannot fabricate status.
- Keep the PNGs from `outputs/` in `public/experiment-assets/` as a last-resort visual.

## Demonstrate the interactive elements
- **Scene 6:** click stack layers (Fuzzball Orchestrate, volumes) to show what the hackathon provides vs how Ember uses it.
- **Scene 11:** step through the Fuzzfile highlights with → or click the callouts.
- **Scene 5:** click a pipeline card for role, I/O, compute and status.
- **Scene 7:** play, scrub, and toggle layers and progression lines.
- **Scene 9:** switch between Architecture and Prediction view.
- **Scene 10:** switch between Planned and Verified execution.
- **Scene 12:** hover a Gantt bar.
- **Scene 13:** pick scenarios, including the one tagged *weakest*.
- **Scene 15:** ensemble size slider, member picker and heatmap.
- **Explore (`E`):** simulation viewer plus an illustrative what-if sandbox, model comparison with overlay opacity, a performance explorer (latency, utilization, breakdown, Gantt), an architecture explorer with the data contract, and data diagnostics.

## Deploy (only when authorized)
```bash
npm run build
npx vercel deploy               # Vercel detects Next.js and builds it; or import the repo in the Vercel dashboard
```
`next.config.mjs` uses `output: "export"`, so any static host works.
