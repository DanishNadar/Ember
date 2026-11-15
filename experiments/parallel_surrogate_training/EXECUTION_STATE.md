# Project Ember execution state

Last observed: 2026-11-14, Fuzzball context `fb-hack`, team
`team15@fb-hack.local`.

## CPU labels

- Completed workflow `185f19b3-bcf4-4875-af3f-64f36af3875f`
  (`ember-forefire-corsica-00-01-v1`) produced:
  - `[0, 2500)`: 2,342 accepted and 158 edge-hit-rejected samples;
    `sha256:45b42830949508af6d7581bf908f23a60a9cac36b33e36e069ffec6423ea75c9`.
  - `[2500, 5000)`: 2,336 accepted and 164 edge-hit-rejected samples;
    `sha256:e03239c1986858e9ddc0abaf1cff15fddf86a35bf40ae83ea75b08aeaf84686a`.
  Both jobs completed without reported simulator failures.
- Completed workflow `7544f8af-d2bc-4c5e-8bd5-5debec65b091`
  (`ember-forefire-corsica-02-03-v1`) produced:
  - `[5000, 7500)`: 2,343 accepted and 157 edge-hit-rejected samples;
    `sha256:c99e40b9e6fb...`.
  - `[7500, 10000)`: 2,337 accepted and 163 edge-hit-rejected samples;
    `sha256:d546279ec3e9...`.
  Both jobs completed without reported simulator failures. The four frozen
  Corsica ranges therefore contain 9,358 accepted and 642 edge-hit-rejected
  records from 10,000 source scenarios.

## Published, verified inputs

- SoCal/train shard:
  `fb://user/ember/research/forefire_research_v1/shards/socal_train.tar.gz`
  - Object digest:
    `sha256:d55fbae1ce1d759550440be7392c1f59ca99de995634adad375610839a6aafc6`
  - 2,000 source scenarios; generator validation completed before publication.
- Initial-state source bundle:
  `fb://user/ember/publications/ember_init_v2.1_source.tar.gz`
  - SHA-256: `0b94adea5f450a7cb4b9b6b3198a66b0f6fab6424107b689a5c13b5e2474e5cd`
- Current production generator bundle:
  `fb://user/ember/publications/parallel_surrogate_training-forefire_research_v4.tar.gz`
  - SHA-256: `9c5f44a5b24aa4c719a0a350591a40835cc8090783fe68c6aaf98be64c5d9fce`

## Next actions

1. Independently validate the published Corsica shard manifests, provenance
   reports, and sample checksums before release assembly.
2. Generate NorCal/train, Great Basin/train, Texas/validation, and
   Montana/test with the same pinned source/code bundle and contract.
4. Assemble only the completed shards under one release, run
   `assemble_research_release.py`, publish the resulting immutable manifest,
   and run the independent read-only verifier.
5. Only then freeze A/B configs and submit equal-budget one-GPU Candidate A and
   Candidate B jobs.  Select solely on validation; evaluate the selected
   candidate once on the held-out test split.

## Gates

No scientific GPU training or test evaluation may begin until the full
fixed-family dataset passes manifest, provenance, checksum, and split-leakage
validation.  Agreement metrics are simulator agreement only, never claims of
real-world wildfire accuracy.

## Read-only HPC assessment

- The active labelling jobs request 8 CPUs and 16 GiB each. Inside one job,
  `nproc` reports 8, `/work` has about 1.9 TiB available, and no CUDA device is
  exposed. ForeFire label generation is CPU-only; adding a GPU would not
  accelerate it.
- The observed current job has a Python parent near one fully utilized core
  while fresh ForeFire worker processes cycle; a point-in-time process sample
  is not a throughput benchmark. Measured completed-shard throughput is about
  3.5 source scenarios/s per job.
- Fuzzball reports many healthy cluster nodes, but current free CPU/GPU counts,
  queue statistics, and group compute policy are administrator-only. Keep the
  approved two concurrent CPU label jobs; do not infer permission to expand it.
- Safe acceleration already in use: independent shard jobs run together;
  immutable source/code artifacts use Fuzzball cache; output NPZs are already
  compressed, so subsequent shards use uncompressed tar containers to avoid
  redundant gzip CPU time.
