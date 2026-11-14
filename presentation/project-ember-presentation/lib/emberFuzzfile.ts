/**
 * Ember's Fuzzball workflow (Fuzzfile) as shown in the deck. Each line is tagged with the
 * concept it illustrates so the slide can highlight it.
 *
 * This is a REFERENCE TEMPLATE written against the documented Fuzzball v4 workflow syntax
 * (docs.ciq.com/fuzzball/4.0/appendices/workflow-syntax). If the team ingests its real
 * Fuzzfile (snapshot.workflowDefinition), the slide shows that instead, verbatim.
 * `npm run export:fuzzfile` writes this to fuzzball/ember.fuzzfile.yaml.
 */
export type FuzzfileTag = "volumes" | "fanout" | "overlap" | "gpu" | "plain";

const raw: Array<[FuzzfileTag, string]> = [
  ["plain", "version: v4"],
  ["volumes", "volumes:"],
  ["volumes", "  ember:                 # shared by both nodes"],
  ["volumes", "    use: persistent"],
  ["volumes", "    name: ember-data"],
  ["volumes", "defaults:"],
  ["volumes", "  job:"],
  ["volumes", "    mounts:"],
  ["volumes", "      /data: ember"],
  ["plain", "jobs:"],
  ["fanout", "  simulate:              # physics teaches"],
  ["fanout", "    image:"],
  ["fanout", "      uri: docker://<registry>/ember-sim:<tag>"],
  ["fanout", "    script: |"],
  ["fanout", "      python3 sim/run_shard.py --shard ${FB_TASK_ID}"],
  ["fanout", "    resource:"],
  ["fanout", "      cpu: { cores: 16 }"],
  ["fanout", "      memory: { size: 32GB }"],
  ["fanout", "    task-array:          # one shard per task"],
  ["fanout", "      start: 1"],
  ["fanout", "      end: 48"],
  ["fanout", "      concurrency: 16"],
  ["overlap", "  build-dataset:"],
  ["overlap", "    image:"],
  ["overlap", "      uri: docker://<registry>/ember-ml:<tag>"],
  ["overlap", "    command: [python3, build_dataset.py, /data]"],
  ["overlap", "    depends-on:"],
  ["overlap", "      - name: simulate"],
  ["overlap", "        status: RUNNING      # consume while producing"],
  ["gpu", "  train:                 # AI learns"],
  ["gpu", "    image:"],
  ["gpu", "      uri: docker://<registry>/ember-ml:<tag>"],
  ["gpu", "    command: [python3, train.py, /data]"],
  ["gpu", "    resource:"],
  ["gpu", "      cpu: { cores: 8 }"],
  ["gpu", "      memory: { size: 64GB }"],
  ["gpu", "      devices:"],
  ["gpu", "        nvidia.com/gpu: 1  # GB10 GPU"],
  ["overlap", "    depends-on:"],
  ["overlap", "      - name: build-dataset"],
  ["overlap", "        status: RUNNING"],
  ["gpu", "  evaluate:"],
  ["gpu", "    image:"],
  ["gpu", "      uri: docker://<registry>/ember-ml:<tag>"],
  ["gpu", "    command: [python3, evaluate.py, /data]"],
  ["gpu", "    resource:"],
  ["gpu", "      devices:"],
  ["gpu", "        nvidia.com/gpu: 1"],
  ["overlap", "    depends-on:"],
  ["overlap", "      - name: train"],
  ["overlap", "        status: FINISHED"],
  ["overlap", "      - name: simulate"],
  ["overlap", "        status: FINISHED"],
];

export const emberFuzzfileLines = raw.map(([tag, text]) => ({ tag, text }));
export const emberFuzzfileText = `# Project Ember: Fuzzball workflow (reference template; replace <registry>/<tag>)\n${raw.map(([, t]) => t).join("\n")}\n`;

export const fuzzfileCallouts: Array<{ tag: FuzzfileTag; title: string; body: string }> = [
  { tag: "volumes", title: "Shared persistent volume", body: "Shards, the manifest and checkpoints move between jobs and nodes through one Fuzzball volume. No copying by hand." },
  { tag: "fanout", title: "Scenario fan-out", body: "A task-array turns one job into many simulation shards that Fuzzball schedules across available cores." },
  { tag: "overlap", title: "Producer–consumer overlap", body: "depends-on with status RUNNING lets dataset building and training start while simulation is still producing." },
  { tag: "gpu", title: "GPU-aware placement", body: "Training and evaluation request nvidia.com/gpu, so Orchestrate places them on a GB10 GPU node." },
];
