"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { FuzzballMark, FuzzballLogo, CiqLogo } from "@/components/visualizations/BrandMarks";
import { stackLayers, layerStatus, usageStatusStyle, fuzzballGreen, type StackLayerId } from "@/lib/ecosystem";
import { useSceneClock } from "@/hooks/useSceneClock";
import type { SlideProps } from "./slideTypes";

function StatusPill({ status }: { status: keyof typeof usageStatusStyle }) {
  const style = usageStatusStyle[status];
  return (
    <span className="fontMono inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-[13px]" style={{ color: style.color, background: `${style.color}18`, border: `1px solid ${style.color}45` }}>
      <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: style.color }} />
      {style.label}
    </span>
  );
}

export { StatusPill };

const fuzzballIds: StackLayerId[] = ["interfaces", "orchestrate", "volumes", "substrate"];

export function SlideHackathonStack({ isActive, isPreview, reducedMotion, data }: SlideProps) {
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 10, maxFps: 20 });
  const [selected, setSelected] = useState<StackLayerId>("orchestrate");
  useEffect(() => {
    if (!isActive) setSelected("orchestrate");
  }, [isActive]);

  // Build bottom-up: hardware first, Ember last.
  const order = [...stackLayers].reverse();
  const revealedCount = Math.min(order.length, Math.floor(time / 0.22) + 1);
  const visible = new Set(order.slice(0, revealedCount).map((l) => l.id));
  const layer = stackLayers.find((l) => l.id === selected)!;
  const status = layerStatus(selected, data.snapshot);
  const rowHeight = 62;
  const fuzzballTop = stackLayers.findIndex((l) => l.id === "interfaces");

  return (
    <SlideFrame
      kicker="Built on the hackathon stack"
      headline={<>Every layer, <span style={{ color: fuzzballGreen }}>put to work.</span></>}
      lede="NVIDIA hardware, CIQ's software stack and Fuzzball orchestration, with our surrogate and DDP pipeline on top. Click a layer for details."
      accent={fuzzballGreen}
      aside={<div className="flex items-center gap-8"><FuzzballLogo height={96} /><CiqLogo height={40} /></div>}
      reducedMotion={reducedMotion}
    >
      <div className="flex h-full gap-10">
        <div className="relative w-[1060px]">
          {/* Fuzzball bracket */}
          <div
            className="absolute -left-2 rounded-2xl"
            style={{
              top: fuzzballTop * (rowHeight + 8) - 6,
              height: fuzzballIds.length * (rowHeight + 8) + 4,
              width: 1062,
              border: `2px solid ${fuzzballGreen}66`,
              boxShadow: `0 0 50px -12px ${fuzzballGreen}`,
              opacity: fuzzballIds.every((id) => visible.has(id)) ? 1 : 0,
              transition: "opacity .5s",
            }}
          >
            <div className="absolute inset-y-0 right-0 flex w-[44px] flex-col items-center justify-center gap-2">
              <FuzzballMark size={22} />
              <span className="fontMono text-[12px] uppercase tracking-[0.24em]" style={{ color: fuzzballGreen, writingMode: "vertical-rl" }}>Fuzzball platform</span>
            </div>
          </div>
          <div className="flex w-[1000px] flex-col gap-2">
            {stackLayers.map((l) => {
              const s = layerStatus(l.id, data.snapshot);
              const isSelected = selected === l.id;
              return (
                <motion.button
                  key={l.id}
                  onClick={() => setSelected(l.id)}
                  initial={false}
                  animate={{ opacity: visible.has(l.id) ? 1 : 0, y: visible.has(l.id) ? 0 : 14 }}
                  transition={{ duration: reducedMotion ? 0 : 0.35 }}
                  className="glassPanel relative flex items-center gap-4 rounded-xl px-5 text-left transition hover:brightness-125"
                  style={{ height: rowHeight, ...(isSelected ? { boxShadow: `0 0 0 2px ${l.color}, 0 0 30px -8px ${l.color}` } : {}) }}
                >
                  <span className="absolute inset-y-2 left-0 w-1 rounded-full" style={{ background: l.color }} />
                  <span className="flex w-9 justify-center">
                    {l.logo === "fuzzball" ? <FuzzballMark size={30} /> : <span className="inline-block h-3 w-3 rounded-sm" style={{ background: l.color }} />}
                  </span>
                  <span className="fontMono w-[150px] text-[13px] uppercase tracking-[0.16em] text-mute">{l.vendor}</span>
                  <span className="fontDisplay flex-1 text-[21px] font-semibold text-ink">{l.title}</span>
                  <StatusPill status={s.status} />
                </motion.button>
              );
            })}
          </div>
        </div>

        <motion.div key={selected} initial={reducedMotion ? false : { opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} className="glassPanel flex flex-1 flex-col gap-5 rounded-2xl p-7" style={{ borderTop: `3px solid ${layer.color}` }}>
          <div className="flex items-center gap-3">
            {layer.logo === "fuzzball" ? <FuzzballMark size={40} /> : null}
            <div className="fontDisplay text-[28px] font-semibold leading-tight text-ink">{layer.title}</div>
          </div>
          <div>
            <div className="fontMono mb-1 text-[13px] uppercase tracking-[0.2em] text-[#48D8FF]">What the hackathon provides</div>
            <p className="text-[19px] leading-snug text-ink/90">{layer.environmentFact}</p>
            <div className="fontMono mt-1 text-[13px] text-mute">source: {layer.source}</div>
          </div>
          <div>
            <div className="fontMono mb-1 text-[13px] uppercase tracking-[0.2em]" style={{ color: fuzzballGreen }}>How Ember uses it</div>
            <p className="text-[19px] leading-snug text-ink/90">{layer.emberUse}</p>
          </div>
          <div className="mt-auto flex flex-wrap items-center gap-3">
            <StatusPill status={status.status} />
            {status.detail ? <span className="fontMono text-[13px] text-mute">{status.detail}</span> : null}
          </div>
        </motion.div>
      </div>
    </SlideFrame>
  );
}
