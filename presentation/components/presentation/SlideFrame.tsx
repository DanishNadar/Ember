"use client";
/** Consistent slide chrome: scene kicker, headline, optional lede, then content. */
import { motion } from "framer-motion";
import { createContext, useContext, type ReactNode } from "react";
import { PlatformFooter } from "@/components/visualizations/BrandMarks";

/** Scene number comes from the registry order, so inserting slides never needs renumbering. */
export const SceneNumberContext = createContext<number | null>(null);

export function SlideFrame({ sceneNumber: fallbackNumber, kicker, headline, lede, accent = "#FF6B35", children, aside, reducedMotion = false, showFooter = true }: {
  sceneNumber?: number;
  kicker: string;
  headline: ReactNode;
  lede?: ReactNode;
  accent?: string;
  children?: ReactNode;
  aside?: ReactNode;
  reducedMotion?: boolean;
  showFooter?: boolean;
}) {
  const sceneNumber = useContext(SceneNumberContext) ?? fallbackNumber ?? 0;
  const enter = (delay: number) =>
    reducedMotion
      ? { initial: false as const, animate: { opacity: 1, y: 0 } }
      : { initial: { opacity: 0, y: 18 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.6, delay, ease: [0.2, 0.7, 0.2, 1] as const } };

  return (
    <div className="absolute inset-0 flex flex-col px-[96px] pb-[72px] pt-[72px]">
      <div className="flex items-start justify-between gap-8">
        <div className="max-w-[1400px]">
          <motion.div {...enter(0)} className="fontMono mb-5 flex items-center gap-3 text-[18px] uppercase tracking-[0.22em]" style={{ color: accent }}>
            <span className="inline-block h-[3px] w-12 rounded-full" style={{ background: accent, boxShadow: `0 0 14px 2px ${accent}` }} />
            {String(sceneNumber).padStart(2, "0")} · {kicker}
          </motion.div>
          <motion.h1 {...enter(0.08)} className="headlineGlow fontDisplay text-[70px] font-bold uppercase leading-[1.02] text-ink">
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
      {showFooter ? <PlatformFooter /> : null}
    </div>
  );
}
