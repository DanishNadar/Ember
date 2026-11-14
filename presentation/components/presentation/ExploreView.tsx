"use client";
/**
 * Exploration mode for technical Q&A, separate from the slide narrative.
 * Tabs: simulation viewer, model comparison, performance explorer, architecture
 * explorer, and data diagnostics.
 */
import { useEffect, useState } from "react";
import { ArrowLeft, Flame, BrainCircuit, Gauge, Network, ClipboardCheck } from "lucide-react";
import { usePresentationData } from "./DataProvider";
import { EvidenceBadge } from "./EvidenceBadge";
import { AwaitingResults } from "./AwaitingResults";
import { FixtureWatermark } from "./FixtureWatermark";
import { SimulatorReplay } from "@/components/scientific/SimulatorReplay";
import { IllustrativeSandbox } from "@/components/scientific/IllustrativeSandbox";
import { ComparisonTriptych, DifferenceLegend, useDecodedExample } from "@/components/scientific/ComparisonTriptych";
import { ArchitectureDetail } from "@/components/visualizations/ArchitectureDiagram";
import { ComparisonBars } from "@/components/charts/ComparisonBars";
import { LatencyHistogram } from "@/components/charts/LatencyHistogram";
import { UtilizationChart } from "@/components/charts/UtilizationChart";
import { GanttChart } from "@/components/charts/GanttChart";
import { architectureComponents } from "@/lib/architecture";
import { formatNumber, formatSeconds, formatSignedPercent } from "@/lib/format";
import { sectionNames } from "@/data/schemas/validateSnapshot";
import { expectedArtifacts } from "@/data/schemas/presentationSchema";

type TabId = "simulation" | "comparison" | "performance" | "architecture" | "diagnostics";

const tabs: Array<{ id: TabId; label: string; Icon: typeof Flame }> = [
  { id: "simulation", label: "Simulation viewer", Icon: Flame },
  { id: "comparison", label: "Model comparison", Icon: BrainCircuit },
  { id: "performance", label: "Performance explorer", Icon: Gauge },
  { id: "architecture", label: "Architecture explorer", Icon: Network },
  { id: "diagnostics", label: "Data & evidence", Icon: ClipboardCheck },
];

function Section({ title, children, aside }: { title: string; children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <section className="glassPanel rounded-2xl p-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="fontDisplay text-2xl font-semibold text-ink">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

function ComparisonTab() {
  const data = usePresentationData();
  const fidelity = data.snapshot.fidelity;
  const [index, setIndex] = useState(0);
  const [overlay, setOverlay] = useState(false);
  const [opacity, setOpacity] = useState(0.6);
  const example = fidelity?.examples[index] ?? null;
  const decoded = useDecodedExample(example);
  if (!fidelity) return <AwaitingResults artifact="metrics/results.json" note="Comparison requires held-out reference and prediction masks or images." />;
  const m = decoded?.agreement ?? example?.metrics ?? null;
  return (
    <div className="space-y-6">
      <Section title="Reference vs prediction" aside={<EvidenceBadge kind={data.evidenceFor("fidelity")} isFixture={data.isFixture} detail={fidelity.source.path} />}>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <select value={index} onChange={(e) => setIndex(Number(e.target.value))} className="fontMono rounded-lg border border-white/15 bg-basalt px-3 py-2 text-sm text-ink" aria-label="Test scenario">
            {fidelity.examples.map((ex, k) => <option key={ex.id} value={k}>{ex.id} · {ex.label}</option>)}
          </select>
          <label className="fontMono flex items-center gap-2 text-sm text-mute">
            <input type="checkbox" checked={overlay} onChange={(e) => setOverlay(e.target.checked)} /> overlay reference on prediction
          </label>
          <label className="fontMono flex items-center gap-2 text-sm text-mute">
            opacity <input type="range" min={0} max={1} step={0.05} value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} className="emberRange cyanRange w-40" disabled={!overlay} />
          </label>
        </div>
        {example ? <ComparisonTriptych example={example} panelSize={360} overlayMode={overlay} overlayOpacity={opacity} /> : null}
        <div className="mt-4"><DifferenceLegend /></div>
        {m ? (
          <div className="fontMono mt-4 flex flex-wrap gap-8 text-sm">
            <span className="text-mute">IoU <span className="text-ink">{formatNumber(m.iou, 3)}</span></span>
            <span className="text-mute">precision <span className="text-ink">{formatNumber(m.precision, 3)}</span></span>
            <span className="text-mute">recall <span className="text-ink">{formatNumber(m.recall, 3)}</span></span>
            <span className="text-mute">F2 <span className="text-ink">{formatNumber(m.f2, 3)}</span></span>
            <span className="text-mute">area error <span className="text-ink">{formatSignedPercent(m.burnedAreaError)}</span></span>
            {decoded ? <span className="text-mute">TP {decoded.agreement.truePositive} · FP {decoded.agreement.falsePositive} · FN {decoded.agreement.falseNegative}</span> : null}
          </div>
        ) : null}
      </Section>
      <Section title="All held-out examples">
        <table className="fontMono w-full text-left text-sm">
          <thead className="text-mute"><tr><th className="py-2">id</th><th>label</th><th>IoU</th><th>precision</th><th>recall</th><th>F2</th><th>area error</th></tr></thead>
          <tbody>
            {fidelity.examples.map((ex) => (
              <tr key={ex.id} className="border-t border-white/5 text-ink/90">
                <td className="py-2">{ex.id}</td><td>{ex.label}</td><td>{formatNumber(ex.metrics?.iou, 3)}</td><td>{formatNumber(ex.metrics?.precision, 3)}</td><td>{formatNumber(ex.metrics?.recall, 3)}</td><td>{formatNumber(ex.metrics?.f2, 3)}</td><td>{formatSignedPercent(ex.metrics?.burnedAreaError)}</td>
              </tr>
            ))}
            <tr className="border-t border-white/20 text-[#48D8FF]">
              <td className="py-2">aggregate</td><td>{fidelity.split} · n={fidelity.sampleCount ?? "—"}</td><td>{formatNumber(fidelity.aggregate.iou, 3)}</td><td>{formatNumber(fidelity.aggregate.precision, 3)}</td><td>{formatNumber(fidelity.aggregate.recall, 3)}</td><td>{formatNumber(fidelity.aggregate.f2, 3)}</td><td>{formatSignedPercent(fidelity.aggregate.burnedAreaError)}</td>
            </tr>
          </tbody>
        </table>
      </Section>
    </div>
  );
}

function PerformanceTab() {
  const data = usePresentationData();
  const bench = data.snapshot.benchmarks;
  const workflow = data.snapshot.workflow;
  return (
    <div className="space-y-6">
      {!bench ? <AwaitingResults artifact="benchmark CSV/JSON → snapshot.benchmarks" note="Only measured values are shown here." /> : (
        <>
          <Section title="Runtime comparisons" aside={<EvidenceBadge kind={data.evidenceFor("benchmarks")} isFixture={data.isFixture} detail={bench.source.path} />}>
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
              {[
                { title: "Surrogate acceleration", ratio: data.surrogateSpeedup, items: bench.surrogateAcceleration ? [
                  { label: "Simulator / scenario", value: bench.surrogateAcceleration.simulatorSecondsPerScenario.value, display: formatSeconds(bench.surrogateAcceleration.simulatorSecondsPerScenario.value), color: "#FF6B35" },
                  { label: "Surrogate / scenario", value: bench.surrogateAcceleration.surrogateSecondsPerScenario.value, display: formatSeconds(bench.surrogateAcceleration.surrogateSecondsPerScenario.value), color: "#48D8FF" },
                ] : null, log: true },
                { title: "Parallel throughput", ratio: data.parallelScaling, items: bench.parallelThroughput ? [
                  { label: "One node", value: bench.parallelThroughput.oneNodeScenariosPerSecond.value, display: `${formatNumber(bench.parallelThroughput.oneNodeScenariosPerSecond.value)} /s`, color: "#94A3B8" },
                  { label: "Two nodes", value: bench.parallelThroughput.twoNodeScenariosPerSecond.value, display: `${formatNumber(bench.parallelThroughput.twoNodeScenariosPerSecond.value)} /s`, color: "#48D8FF" },
                ] : null, log: false },
                { title: "Workflow acceleration", ratio: data.workflowSpeedup, items: bench.workflowAcceleration ? [
                  { label: "Sequential", value: bench.workflowAcceleration.sequentialSeconds.value, display: formatSeconds(bench.workflowAcceleration.sequentialSeconds.value), color: "#94A3B8" },
                  { label: "Overlapping", value: bench.workflowAcceleration.overlappingSeconds.value, display: formatSeconds(bench.workflowAcceleration.overlappingSeconds.value), color: "#FFB547" },
                ] : null, log: false },
              ].map((card) => (
                <div key={card.title}>
                  <div className="fontDisplay mb-3 text-lg text-ink">{card.title}</div>
                  {card.items ? (
                    <>
                      <ComparisonBars items={card.items} width={360} logScale={card.log} active reducedMotion={false} />
                      <div className="fontMono mt-3 text-sm text-mute">{card.ratio ? `ratio ${formatNumber(card.ratio.ratio, 2)}× · ${card.ratio.description}` : "ratio not computable"}</div>
                    </>
                  ) : <AwaitingResults compact artifact={card.title} />}
                </div>
              ))}
            </div>
          </Section>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Section title="Latency distribution">
              {bench.latencySamplesMs?.length ? <LatencyHistogram samples={bench.latencySamplesMs} width={560} height={160} /> : <AwaitingResults compact artifact="latencySamplesMs" />}
            </Section>
            <Section title="Workflow duration breakdown">
              {bench.workflowBreakdown?.length ? (
                <div className="space-y-3">
                  {bench.workflowBreakdown.map((b) => {
                    const total = bench.workflowBreakdown!.reduce((s, x) => s + x.seconds, 0);
                    return (
                      <div key={b.stage}>
                        <div className="fontMono flex justify-between text-sm"><span className="text-ink">{b.stage}</span><span className="text-mute">{formatSeconds(b.seconds)} · {((b.seconds / total) * 100).toFixed(0)}%</span></div>
                        <div className="mt-1 h-3 rounded-[4px] bg-white/5"><div className="h-full rounded-[4px] bg-[#94A3B8]" style={{ width: `${(b.seconds / total) * 100}%` }} /></div>
                      </div>
                    );
                  })}
                  <div className="fontMono text-xs text-mute">stage durations as recorded; overlapping stages can sum to more than wall-clock time</div>
                </div>
              ) : <AwaitingResults compact artifact="workflowBreakdown" />}
            </Section>
          </div>
          <Section title="Hardware utilization">
            {bench.utilization?.length ? <UtilizationChart samples={bench.utilization} width={1100} /> : <AwaitingResults compact artifact="utilization samples" note="No GPU/CPU utilization claims are made without recorded samples." />}
          </Section>
        </>
      )}
      <Section title="Recorded workflow timeline" aside={workflow ? <EvidenceBadge kind={data.evidenceFor("workflow")} isFixture={data.isFixture} detail="recorded playback" /> : undefined}>
        {workflow ? <GanttChart jobs={workflow.jobs} width={1200} height={Math.max(220, workflow.jobs.length * 48 + 50)} playhead={1} /> : <AwaitingResults compact artifact="Fuzzball workflow logs" />}
      </Section>
    </div>
  );
}

function ArchitectureTab() {
  const data = usePresentationData();
  return (
    <div className="space-y-4">
      {architectureComponents.map((c) => (
        <section key={c.id} className="glassPanel rounded-2xl p-6" style={{ borderLeft: `3px solid ${c.color}` }}>
          <ArchitectureDetail component={c} data={data} />
        </section>
      ))}
      <Section title="Data contract between stages">
        <ol className="fontMono space-y-2 text-sm text-ink/90">
          <li>1. scenario config → simulator → burned-area masks per time step (+ environmental layers)</li>
          <li>2. masks + layers → dataset builder → (C × H × W, 1 × H × W) pairs, split by scenario → data/manifest.json</li>
          <li>3. pairs → U-Net training → models/best.pt (+ model metadata JSON)</li>
          <li>4. checkpoint + held-out pairs → evaluation → metrics/results.json, outputs/comparison.png</li>
          <li>5. Fuzzball workflow → job states, timestamps, placement → workflow status JSON</li>
          <li>6. scripts/ingestArtifacts.mjs → data/verified/presentationSnapshot.json → this deck</li>
        </ol>
        {data.snapshot.model ? <div className="fontMono mt-3 text-sm text-mute">model definition: {data.snapshot.model.definitionFile ?? "—"} · checkpoint: {data.snapshot.model.checkpoint ?? "—"}</div> : null}
      </Section>
    </div>
  );
}

function DiagnosticsTab() {
  const data = usePresentationData();
  return (
    <div className="space-y-6">
      <Section title="Evidence status by section">
        <table className="fontMono w-full text-left text-sm">
          <thead className="text-mute"><tr><th className="py-2">section</th><th>classification</th><th>source artifact</th><th>expected from</th></tr></thead>
          <tbody>
            {sectionNames.map((name) => {
              const section = data.snapshot[name] as { source?: { path: string } } | null;
              return (
                <tr key={name} className="border-t border-white/5">
                  <td className="py-2 text-ink">{name}</td>
                  <td><EvidenceBadge kind={data.evidenceFor(name)} isFixture={data.isFixture} /></td>
                  <td className="text-ink/80">{section?.source?.path ?? "—"}</td>
                  <td className="text-mute">{expectedArtifacts[name]}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="fontMono mt-3 text-sm text-mute">snapshot generated: {data.snapshot.generatedAt ?? "never (no artifacts ingested yet)"}</div>
      </Section>
      <Section title={`Validation issues (${data.issues.length})`}>
        {data.issues.length === 0 ? <div className="fontMono text-sm text-[#35D6A0]">No schema issues. Missing sections are simply awaiting data.</div> : (
          <ul className="fontMono space-y-1 text-sm text-ember">{data.issues.map((issue, k) => <li key={k}>[{issue.section}] {issue.message}</li>)}</ul>
        )}
      </Section>
    </div>
  );
}

export function ExploreView() {
  const data = usePresentationData();
  const [tab, setTab] = useState<TabId>("simulation");
  useEffect(() => {
    document.documentElement.classList.add("allowScroll");
    return () => document.documentElement.classList.remove("allowScroll");
  }, []);

  return (
    <div className="min-h-screen bg-void text-ink">
      {data.isFixture ? <div className="relative h-16"><FixtureWatermark /></div> : null}
      <header className="sticky top-0 z-20 border-b border-white/10 bg-void/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-4 px-6 py-4">
          <a href="../" className="flex items-center gap-2 text-mute hover:text-ink"><ArrowLeft size={18} /> Deck</a>
          <div className="fontDisplay text-xl font-semibold"><span className="emberText">EMBER</span> · Explore</div>
          <nav className="ml-auto flex flex-wrap gap-1" role="tablist">
            {tabs.map(({ id, label, Icon }) => (
              <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${tab === id ? "bg-ember/15 text-ember" : "text-mute hover:text-ink"}`}>
                <Icon size={16} /> {label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-[1400px] space-y-6 px-6 py-8">
        {tab === "simulation" ? (
          <>
            <Section title="Recorded simulator replay">
              <SimulatorReplay simulator={data.snapshot.simulator} isFixture={data.isFixture} width={1000} height={560} active reducedMotion={false} />
            </Section>
            <Section title="Illustrative what-if sandbox" aside={<span className="fontMono text-xs text-mute">hypothetical controls · illustrative output</span>}>
              <IllustrativeSandbox />
            </Section>
          </>
        ) : null}
        {tab === "comparison" ? <ComparisonTab /> : null}
        {tab === "performance" ? <PerformanceTab /> : null}
        {tab === "architecture" ? <ArchitectureTab /> : null}
        {tab === "diagnostics" ? <DiagnosticsTab /> : null}
      </main>
    </div>
  );
}
