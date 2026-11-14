import { describe, expect, it } from "vitest";
import { execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { buildPresentationData } from "@/data/adapters/presentationData";

describe("artifact ingestion", () => {
  it("maps common artifact shapes into a valid snapshot without inventing values", () => {
    const repo = mkdtempSync(path.join(tmpdir(), "emberRepo-"));
    mkdirSync(path.join(repo, "metrics"));
    mkdirSync(path.join(repo, "data"));
    mkdirSync(path.join(repo, "fuzzball"));
    writeFileSync(path.join(repo, "metrics/results.json"), JSON.stringify({
      split: "test", n: 2,
      test: { iou: 0.71, precision: 0.8, recall: 0.86 },
      per_example: [{ scenario_id: "s1", target: [[0, 1], [1, 1]], prediction: [[0, 1], [0, 1]], iou: 0.66 }],
    }));
    writeFileSync(path.join(repo, "data/manifest.json"), JSON.stringify({ num_scenarios: 10, splits: { train: [1, 2, 3, 4, 5, 6, 7, 8], val: [9], test: [10] }, input_channels: ["burned", "wind_u"] }));
    writeFileSync(path.join(repo, "fuzzball/workflow_status.json"), JSON.stringify({ id: "wf-1", jobs: [
      { name: "simulate", status: "Finished", started_at: "2026-11-14T10:00:00Z", finished_at: "2026-11-14T10:05:00Z", host: "pgx-a" },
      { name: "train", status: "Finished", started_at: "2026-11-14T10:05:00Z", finished_at: "2026-11-14T10:20:00Z", host: "pgx-b", depends_on: ["simulate"] },
    ] }));
    writeFileSync(path.join(repo, "metrics/benchmarks.csv"), "metric,value,unit\nsimulator_seconds_per_scenario,3.1,s\nsurrogate_seconds_per_scenario,0.01,s\n");

    const out = path.join(repo, "snapshot.json");
    execFileSync("node", [path.resolve("scripts/ingestArtifacts.mjs"), "--repo", repo, "--out", out], { stdio: "pipe" });
    const raw = JSON.parse(readFileSync(out, "utf8"));
    const data = buildPresentationData(raw);
    expect(data.issues).toEqual([]);
    expect(data.snapshot.fidelity?.aggregate.iou).toBe(0.71);
    expect(data.snapshot.fidelity?.aggregate.f2).toBeNull(); // absent → null, never computed or zero
    expect(data.snapshot.dataset?.splits).toEqual({ train: 8, validation: 1, test: 1 });
    expect(data.snapshot.workflow?.jobs.map((j) => j.node)).toEqual(["pgx-a", "pgx-b"]);
    expect(data.snapshot.workflow?.jobs[1].stage).toBe("training");
    expect(data.surrogateSpeedup?.ratio).toBeCloseTo(310);
    expect(data.parallelScaling).toBeNull();
    expect(data.snapshot.model).toBeNull();
    expect(raw.fidelity.source.sha256).toMatch(/^[0-9a-f]{64}$/);
  });
});
