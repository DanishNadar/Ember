"use client";
import { motion } from "framer-motion";

const shortcuts: Array<[string, string]> = [
  ["→  /  Space  /  PgDn", "Next build or slide"],
  ["←  /  Shift+Space  /  PgUp", "Previous"],
  ["Shift+→  /  ↓", "Skip builds, next slide"],
  ["Shift+←  /  ↑", "Previous slide"],
  ["Home / End", "First / last slide"],
  ["S", "Reveal all builds on this slide"],
  ["O  or  G", "Chapters overview"],
  ["N", "Speaker notes drawer"],
  ["P", "Open presenter window"],
  ["F", "Fullscreen"],
  ["A", "Toggle autoplay"],
  ["T  /  R", "Start-pause / reset timer"],
  ["M", "Toggle reduced motion"],
  ["E", "Open Explore mode"],
  ["?", "This help"],
];

export function HelpOverlay({ onClose }: { onClose: () => void }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur" onClick={onClose}>
      <div className="glassPanel w-[560px] rounded-2xl p-8" onClick={(e) => e.stopPropagation()}>
        <div className="fontDisplay mb-5 text-2xl font-semibold">Keyboard shortcuts</div>
        <div className="grid grid-cols-[1fr_auto] gap-x-6 gap-y-2 text-[15px]">
          {shortcuts.map(([keys, label]) => (
            <div key={keys} className="contents">
              <div className="fontMono text-ember">{keys}</div>
              <div className="text-mute">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
