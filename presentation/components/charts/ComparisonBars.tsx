"use client";
/** Two-or-more horizontal bars with units; optional log scale for order-of-magnitude gaps. */
import { motion } from "framer-motion";

export interface BarItem {
  label: string;
  value: number;
  display: string;
  color: string;
}

export function ComparisonBars({ items, width, logScale = false, active, reducedMotion }: {
  items: BarItem[];
  width: number;
  logScale?: boolean;
  active: boolean;
  reducedMotion: boolean;
}) {
  const values = items.map((i) => i.value).filter((v) => v > 0);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const scale = (v: number) => {
    if (v <= 0) return 0;
    if (!logScale) return v / max;
    const lo = Math.log10(min) - 0.5;
    const hi = Math.log10(max);
    return Math.max(0.03, (Math.log10(v) - lo) / (hi - lo));
  };
  return (
    <div className="flex flex-col gap-4" style={{ width }}>
      {items.map((item, k) => (
        <div key={item.label}>
          <div className="mb-1 flex items-baseline justify-between">
            <span className="text-[17px] text-ink/90">{item.label}</span>
            <span className="fontMono flex items-center gap-2 text-[19px] font-semibold text-ink"><span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: item.color }} />{item.display}</span>
          </div>
          <div className="h-5 overflow-hidden rounded-[4px] bg-white/5" title={`${item.label}: ${item.display}`}>
            <motion.div
              className="h-full rounded-[4px]"
              style={{ background: item.color }}
              initial={false}
              animate={{ width: `${(active || reducedMotion ? scale(item.value) : 0) * 100}%` }}
              transition={{ duration: reducedMotion ? 0 : 1.1, delay: reducedMotion ? 0 : 0.2 + k * 0.15, ease: [0.2, 0.7, 0.2, 1] }}
            />
          </div>
        </div>
      ))}
      {logScale ? <div className="fontMono text-[12px] text-mute">log scale</div> : null}
    </div>
  );
}
