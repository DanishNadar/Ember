"use client";
/** Animated, clickable Ember pipeline. Detail card shows role, I/O, compute and status. */
import { AnimatePresence, motion } from "framer-motion";
import { Flame, Database, BrainCircuit, Gauge, Network, Sparkles, type LucideIcon } from "lucide-react";
import { architectureComponents, statusStyles, type ArchitectureComponent } from "@/lib/architecture";
import type { PresentationData } from "@/data/adapters/presentationData";

const icons: Record<ArchitectureComponent["id"], LucideIcon> = {
  simulation: Flame,
  dataset: Database,
  surrogate: BrainCircuit,
  evaluation: Gauge,
  orchestration: Network,
  exploration: Sparkles,
};

const pipeline = architectureComponents.filter((c) => c.id !== "orchestration");
const orchestration = architectureComponents.find((c) => c.id === "orchestration")!;

export function StatusChip({ status }: { status: keyof typeof statusStyles }) {
  const style = statusStyles[status];
  return (
    <span className="fontMono inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[13px]" style={{ color: style.color, background: `${style.color}18`, border: `1px solid ${style.color}40` }}>
      <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: style.color }} />
      {style.label}
    </span>
  );
}

export function ArchitectureDetail({ component, data }: { component: ArchitectureComponent; data: PresentationData }) {
  const status = data.componentStatus(component.id);
  const Icon = icons[component.id];
  return (
    <div className="grid grid-cols-[1.1fr_1fr_1fr_1fr] gap-8">
      <div>
        <div className="flex items-center gap-3">
          <Icon size={28} style={{ color: component.color }} />
          <div className="fontDisplay text-[30px] font-semibold text-ink">{component.title}</div>
        </div>
        <p className="mt-3 text-[19px] leading-snug text-mute">{component.role}</p>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <StatusChip status={status.status} />
          {status.sourceFiles.length > 0 ? <span className="fontMono text-[14px] text-mute">{status.sourceFiles.join(", ")}</span> : null}
        </div>
      </div>
      <div>
        <div className="fontMono mb-2 text-[13px] uppercase tracking-[0.2em] text-mute">Inputs</div>
        <ul className="space-y-1 text-[18px] text-ink/90">{component.inputs.map((x) => <li key={x}>· {x}</li>)}</ul>
      </div>
      <div>
        <div className="fontMono mb-2 text-[13px] uppercase tracking-[0.2em] text-mute">Outputs</div>
        <ul className="space-y-1 text-[18px] text-ink/90">{component.outputs.map((x) => <li key={x}>· {x}</li>)}</ul>
      </div>
      <div>
        <div className="fontMono mb-2 text-[13px] uppercase tracking-[0.2em] text-mute">Compute profile</div>
        <p className="text-[18px] text-ink/90">{component.compute}</p>
        <div className="fontMono mb-1 mt-4 text-[13px] uppercase tracking-[0.2em] text-mute">Data contract</div>
        <p className="fontMono text-[15px] text-[#48D8FF]">{component.dataContract}</p>
      </div>
    </div>
  );
}

export function ArchitectureDiagram({ selectedId, onSelect, revealed, data, reducedMotion }: {
  selectedId: ArchitectureComponent["id"] | null;
  onSelect: (id: ArchitectureComponent["id"]) => void;
  revealed: number; // number of components visible (0..6)
  data: PresentationData;
  reducedMotion: boolean;
}) {
  const cardWidth = 280;
  const gap = 82;
  const rowY = 0;
  const width = pipeline.length * cardWidth + (pipeline.length - 1) * gap;
  const selected = architectureComponents.find((c) => c.id === selectedId) ?? null;

  return (
    <div className="flex h-full flex-col">
      <div className="relative mx-auto" style={{ width, height: 340 }}>
        <svg className="absolute inset-0" width={width} height={340}>
          {pipeline.slice(0, -1).map((c, k) => {
            const x1 = k * (cardWidth + gap) + cardWidth;
            const x2 = x1 + gap;
            const visible = revealed > k + 1;
            return (
              <g key={c.id} opacity={visible ? 1 : 0} style={{ transition: "opacity .5s" }}>
                <line x1={x1 + 6} y1={rowY + 90} x2={x2 - 10} y2={rowY + 90} stroke={k >= 1 ? "#48D8FF" : "#FF6B35"} strokeOpacity={0.25} strokeWidth={3} />
                <line x1={x1 + 6} y1={rowY + 90} x2={x2 - 10} y2={rowY + 90} stroke={k >= 1 ? "#48D8FF" : "#FF6B35"} strokeWidth={3} className="flowDash" />
                <path d={`M${x2 - 14},${rowY + 82} L${x2 - 4},${rowY + 90} L${x2 - 14},${rowY + 98}`} fill="none" stroke={k >= 1 ? "#48D8FF" : "#FF6B35"} strokeWidth={3} />
              </g>
            );
          })}
          {/* Orchestration taps into every stage */}
          {pipeline.map((c, k) => (
            <line
              key={`tap-${c.id}`}
              x1={k * (cardWidth + gap) + cardWidth / 2}
              y1={190}
              x2={k * (cardWidth + gap) + cardWidth / 2}
              y2={262}
              stroke="#A3B8D9"
              strokeOpacity={revealed >= 6 ? 0.6 : 0}
              strokeWidth={2}
              strokeDasharray="4 6"
              style={{ transition: "stroke-opacity .5s" }}
            />
          ))}
        </svg>
        {pipeline.map((c, k) => {
          const Icon = icons[c.id];
          const status = data.componentStatus(c.id);
          const isSelected = selectedId === c.id;
          return (
            <motion.button
              key={c.id}
              onClick={() => onSelect(c.id)}
              initial={false}
              animate={{ opacity: revealed > k ? 1 : 0, y: revealed > k ? 0 : 20 }}
              transition={{ duration: reducedMotion ? 0 : 0.5 }}
              className={`glassPanel absolute flex flex-col items-start rounded-2xl p-5 text-left transition ${isSelected ? "ring-2" : "hover:-translate-y-1"}`}
              style={{ left: k * (cardWidth + gap), top: rowY, width: cardWidth, height: 180, ...(isSelected ? { boxShadow: `0 0 0 2px ${c.color}, 0 0 40px -6px ${c.color}` } : {}) }}
            >
              <div className="flex w-full items-center justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl" style={{ background: `${c.color}1c`, color: c.color }}><Icon size={26} /></div>
                <span className="fontMono text-[15px] text-mute">0{c.order}</span>
              </div>
              <div className="fontDisplay mt-3 text-[23px] font-semibold leading-tight text-ink">{c.title}</div>
              <div className="mt-auto"><StatusChip status={status.status} /></div>
            </motion.button>
          );
        })}
        <motion.button
          onClick={() => onSelect("orchestration")}
          initial={false}
          animate={{ opacity: revealed >= 6 ? 1 : 0, y: revealed >= 6 ? 0 : 20 }}
          transition={{ duration: reducedMotion ? 0 : 0.5 }}
          className="glassPanel absolute flex items-center justify-between rounded-2xl px-6 text-left"
          style={{ left: 0, top: 262, width, height: 74, ...(selectedId === "orchestration" ? { boxShadow: `0 0 0 2px ${orchestration.color}, 0 0 40px -6px ${orchestration.color}` } : {}) }}
        >
          <div className="flex items-center gap-4">
            <Network size={26} className="text-[#A3B8D9]" />
            <span className="fontDisplay text-[23px] font-semibold text-ink">CIQ Fuzzball orchestration</span>
            <span className="text-[18px] text-mute">dependencies · resources · staging · artifacts</span>
          </div>
          <StatusChip status={data.componentStatus("orchestration").status} />
        </motion.button>
      </div>

      <div className="mt-6 min-h-0 flex-1">
        <AnimatePresence mode="wait">
          {selected ? (
            <motion.div key={selected.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: reducedMotion ? 0 : 0.3 }} className="glassPanel rounded-2xl p-7">
              <ArchitectureDetail component={selected} data={data} />
            </motion.div>
          ) : (
            <motion.div key="hint" initial={{ opacity: 0 }} animate={{ opacity: revealed >= 6 ? 1 : 0 }} className="fontMono pt-6 text-center text-[18px] text-mute">
              Click any component to inspect its role, inputs, outputs, compute and status.
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
