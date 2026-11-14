"use client";
/** Consistent slide chrome: scene kicker, headline, optional lede, then content. */
import { motion } from "framer-motion";
import type { ReactNode } from "react";

export function SlideFrame({ sceneNumber, kicker, headline, lede, accent = "#FF6B35", children, aside, reducedMotion = false }: {
  sceneNumber: number;
  kicker: string;
  headline: ReactNode;
  lede?: ReactNode;
  accent?: string;
  children?: ReactNode;
  aside?: ReactNode;
  reducedMotion?: boolean;
}) {
  const enter = (delay: number) =>
    reducedMotion
      ? { initial: false as const, animate: { opacity: 1, y: 0 } }
      : { initial: { opacity: 0, y: 18 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.6, delay, ease: [0.2, 0.7, 0.2, 1] as const } };

  return (
    <div className="absolute inset-0 flex flex-col px-[96px] pb-[72px] pt-[72px]">
      <div className="flex items-start justify-between gap-8">
        <div className="max-w-[1400px]">
          <motion.div {...enter(0)} className="fontMono mb-5 flex items-center gap-3 text-[18px] uppercase tracking-[0.22em]" style={{ color: accent }}>
            <span className="inline-block h-[2px] w-10" style={{ background: accent }} />
            {String(sceneNumber).padStart(2, "0")} · {kicker}
          </motion.div>
          <motion.h1 {...enter(0.08)} className="fontDisplay text-[68px] font-bold uppercase leading-[1.02] text-ink">
            {headline}
          </motion.h1>
          {lede ? (
            <motion.p {...enter(0.18)} className="mt-5 max-w-[1100px] text-[26px] leading-snug text-mute">
              {lede}
            </motion.p>
          ) : null}
        </div>
        {aside ? <motion.div {...enter(0.2)}>{aside}</motion.div> : null}
      </div>
      <div className="relative mt-10 min-h-0 flex-1">{children}</div>
    </div>
  );
}
