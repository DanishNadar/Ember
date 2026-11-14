# Project Ember — Interactive Presentation

Cinematic, data-driven slide deck for **Project Ember: Adaptive Wildfire Surrogate**
(CIQ Supercomputing Local AI Hackathon, Chicago, Nov 13–15 2026).

```bash
npm install
npm run dev        # http://localhost:3000   (P = presenter, E = explore, ? = keys)
npm test           # adapter, metrics, ingestion and model tests
npm run build      # static export → ./out (fully offline)
EMBER_REPO=/path/to/ember npm run ingest   # pull verified results into the deck
```

- **Never fabricates results.** Every result view reads `data/verified/presentationSnapshot.json`. Empty sections show *Awaiting verified results*.
- Every visual is badged: Verified · Simulator-derived · Illustration · Proposed · Unavailable.
- `/?fixture=sample` previews layouts with synthetic data, behind a persistent watermark.

Docs: [`docs/presentationScript.md`](docs/presentationScript.md) · [`docs/demoInstructions.md`](docs/demoInstructions.md) · [`docs/judgingCoverage.md`](docs/judgingCoverage.md) · [`docs/technicalReferences.md`](docs/technicalReferences.md)

## Layout
```
app/                    routes: / (deck), /presenter, /explore
components/presentation deck engine, stage, toolbar, presenter, explore, badges
components/visualizations fire canvas, spark cinematic, architecture, U-Net, nodes
components/scientific   replay viewer, comparison triptych, ensemble, channels
components/charts       Gantt, bars, latency histogram, utilization, metric stat
slides/                 one file per scene + registry + speakerNotes.json
data/schemas            snapshot types + validation
data/adapters           results adapter + artifact path config
data/verified           bundled snapshot (offline source of truth)
data/fixtures           synthetic fixture (watermarked)
lib/                    toy fire model, renderers, contours, metrics, formatting
scripts/                ingestArtifacts.mjs, buildFixture.ts
tests/                  vitest suites
```
