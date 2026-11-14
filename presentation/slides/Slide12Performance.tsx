"use client";
import type { ReactNode } from "react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { AwaitingResults } from "@/components/presentation/AwaitingResults";
import { ComparisonBars } from "@/components/charts/ComparisonBars";
import { LatencyHistogram } from "@/components/charts/LatencyHistogram";
import type { DerivedComparison } from "@/data/adapters/presentationData";
import { formatNumber, formatSeconds } from "@/lib/format";
import type { SlideProps } from "./slideTypes";

function RatioReadout({ comparison, unitWord }: { comparison: DerivedComparison | null; unitWord: string }) {
  if (!comparison) return <div className="fontMono text-[16px] text-dim">ratio not computable · needs both measurements</div>;
  const improved = comparison.ratio > 1;
  return (
    <div className="flex items-baseline gap-3">
      <span className="fontMono text-[52px] font-semibold leading-none" style={{ color: improved ? "#35D6A0" : "#FF6B35" }}>
        {formatNumber(comparison.ratio, comparison.ratio >= 100 ? 0 : 2)}×
      </span>
      <span className="text-[17px] text-mute">{improved ? unitWord : `not an improvement (${unitWord} < 1)`}</span>
    </div>
  );
}

function BenchCard({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="glassPanel flex flex-col rounded-2xl p-6">
      <div className="fontDisplay text-[26px] font-semibold text-ink">{title}</div>
      <div className="mb-4 text-[16px] text-mute">{subtitle}</div>
      <div className="flex min-h-0 flex-1 flex-col justify-between gap-4">{children}</div>
    </div>
  );
}

export function Slide12Performance({ isActive, reducedMotion, data }: SlideProps) {
  const bench = data.snapshot.benchmarks;
  const sa = bench?.surrogateAcceleration ?? null;
  const pt = bench?.parallelThroughput ?? null;
  const wa = bench?.workflowAcceleration ?? null;
  const evidence = data.evidenceFor("benchmarks");

  return (
    <SlideFrame
      sceneNumber={12}
      kicker="The performance reveal"
      headline={<>Did we actually <span className="emberText">save compute?</span></>}
      aside={bench ? <EvidenceBadge kind={evidence} isFixture={data.isFixture} detail={bench.source.path} /> : <EvidenceBadge kind="unavailable" detail="no benchmark artifact ingested" />}
      reducedMotion={reducedMotion}
    >
      <div className="grid h-full grid-cols-3 grid-rows-[1fr_auto] gap-6">
        <BenchCard title="Surrogate acceleration" subtitle="Simulator runtime vs neural inference, per scenario">
          {sa ? (
            <>
              <ComparisonBars
                width={480}
                logScale
                active={isActive}
                reducedMotion={reducedMotion}
                items={[
                  { label: "Simulator", value: sa.simulatorSecondsPerScenario.value, display: formatSeconds(sa.simulatorSecondsPerScenario.value), color: "#FF6B35" },
                  { label: "Neural surrogate", value: sa.surrogateSecondsPerScenario.value, display: formatSeconds(sa.surrogateSecondsPerScenario.value), color: "#48D8FF" },
                ]}
              />
              <RatioReadout comparison={data.surrogateSpeedup} unitWord="faster per scenario" />
              <div className="fontMono text-[13px] text-mute">batch {sa.batchSize ?? "—"} · {sa.hardware ?? "hardware —"} · data loading {sa.includesDataLoading === null ? "unspecified" : sa.includesDataLoading ? "included" : "excluded"} · excludes training</div>
            </>
          ) : (
            <AwaitingResults compact className="flex-1" artifact="benchmarks → surrogateAcceleration" />
          )}
        </BenchCard>

        <BenchCard title="Parallel throughput" subtitle="One node vs two nodes, scenarios per second">
          {pt ? (
            <>
              <ComparisonBars
                width={480}
                active={isActive}
                reducedMotion={reducedMotion}
                items={[
                  { label: "One node", value: pt.oneNodeScenariosPerSecond.value, display: `${formatNumber(pt.oneNodeScenariosPerSecond.value)} /s`, color: "#C2AFA4" },
                  { label: "Two nodes", value: pt.twoNodeScenariosPerSecond.value, display: `${formatNumber(pt.twoNodeScenariosPerSecond.value)} /s`, color: "#48D8FF" },
                ]}
              />
              <RatioReadout comparison={data.parallelScaling} unitWord="throughput scaling" />
            </>
          ) : (
            <AwaitingResults compact className="flex-1" artifact="benchmarks → parallelThroughput" note="Shown only if one-node and two-node runs were both measured." />
          )}
        </BenchCard>

        <BenchCard title="Workflow acceleration" subtitle="Sequential vs overlapping producer–consumer pipeline">
          {wa ? (
            <>
              <ComparisonBars
                width={480}
                active={isActive}
                reducedMotion={reducedMotion}
                items={[
                  { label: "Sequential", value: wa.sequentialSeconds.value, display: formatSeconds(wa.sequentialSeconds.value), color: "#C2AFA4" },
                  { label: "Overlapping", value: wa.overlappingSeconds.value, display: formatSeconds(wa.overlappingSeconds.value), color: "#FFB547" },
                ]}
              />
              <RatioReadout comparison={data.workflowSpeedup} unitWord="shorter end-to-end" />
            </>
          ) : (
            <AwaitingResults compact className="flex-1" artifact="benchmarks → workflowAcceleration" note="Shown only if both workflow modes were measured." />
          )}
        </BenchCard>

        <div className="glassPanel col-span-3 flex items-center gap-10 rounded-2xl px-6 py-4">
          <div className="w-[300px]">
            <div className="fontMono text-[13px] uppercase tracking-[0.2em] text-mute">Training cost · separate</div>
            <div className="fontMono text-[30px] font-semibold text-ink">{bench?.trainingCost ? formatSeconds(bench.trainingCost.wallClockSeconds.value) : "—"}</div>
            <div className="fontMono text-[13px] text-mute">{bench?.trainingCost?.device ?? "awaiting measurement"}</div>
          </div>
          <div>
            <div className="fontMono mb-1 text-[13px] uppercase tracking-[0.2em] text-mute">Inference latency distribution</div>
            {bench?.latencySamplesMs?.length ? <LatencyHistogram samples={bench.latencySamplesMs} width={560} height={92} /> : <div className="fontMono text-[15px] text-dim">no latency samples recorded</div>}
          </div>
          <div className="ml-auto max-w-[520px] text-[16px] leading-snug text-mute">
            Three separate comparisons, <span className="text-ink">never multiplied</span> into one headline number. Training cost is reported on its own.
          </div>
        </div>
      </div>
    </SlideFrame>
  );
}
