"use client";
/** Chapter overview: every scene as a card, grouped by chapter. Click to jump. */
import { motion } from "framer-motion";
import { X } from "lucide-react";
import type { SlideDefinition } from "@/slides/slideTypes";

export function OverviewGrid({ slides, currentIndex, onSelect, onClose }: {
  slides: SlideDefinition[];
  currentIndex: number;
  onSelect: (index: number) => void;
  onClose: () => void;
}) {
  const chapters = Array.from(new Set(slides.map((s) => s.chapter)));
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-50 overflow-y-auto bg-void/95 backdrop-blur-xl"
      onClick={onClose}
    >
      <div className="mx-auto max-w-[1500px] px-10 py-10" onClick={(e) => e.stopPropagation()}>
        <div className="mb-8 flex items-center justify-between">
          <div>
            <div className="fontMono text-sm uppercase tracking-[0.25em] text-ember">Chapters</div>
            <div className="fontDisplay mt-1 text-3xl font-semibold">Project Ember · scene overview</div>
          </div>
          <button onClick={onClose} className="rounded-full border border-white/10 p-2 text-mute hover:text-ink" aria-label="Close overview">
            <X size={22} />
          </button>
        </div>
        {chapters.map((chapter) => (
          <div key={chapter} className="mb-8">
            <div className="fontMono mb-3 text-xs uppercase tracking-[0.25em] text-mute">{chapter}</div>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
              {slides.map((slide, index) =>
                slide.chapter !== chapter ? null : (
                  <button
                    key={slide.id}
                    onClick={() => onSelect(index)}
                    className={`group relative overflow-hidden rounded-xl border p-4 text-left transition hover:-translate-y-0.5 ${
                      index === currentIndex ? "border-ember/70 bg-ember/10" : "border-white/10 bg-basalt hover:border-white/25"
                    }`}
                  >
                    <div className="absolute inset-x-0 top-0 h-[3px]" style={{ background: slide.accent }} />
                    <div className="fontMono text-xs text-mute">{String(index + 1).padStart(2, "0")}</div>
                    <div className="fontDisplay mt-1 text-lg font-semibold leading-tight text-ink">{slide.title}</div>
                    <div className="mt-2 text-sm leading-snug text-mute">{slide.takeaway}</div>
                  </button>
                ),
              )}
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
