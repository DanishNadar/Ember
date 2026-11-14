"use client";
/** Presenter window: current slide, next preview, notes, timer and pacing, synced to the audience window. */
import { useMemo } from "react";
import { ChevronLeft, ChevronRight, Pause, Play, RotateCcw, SkipForward } from "lucide-react";
import { slides } from "@/slides/registry";
import { useDeckController, useDeckKeyboard } from "@/hooks/useDeckController";
import { usePresentationTimer } from "@/hooks/usePresentationTimer";
import { formatClock } from "@/lib/format";
import { Stage } from "./Stage";
import { SlideRenderer } from "./SlideRenderer";
import { SpeakerNotesPanel, speakerNotes } from "./SpeakerNotesPanel";
import { usePresentationData } from "./DataProvider";

export function PresenterView() {
  const stepCounts = useMemo(() => slides.map((s) => s.steps), []);
  const deck = useDeckController(stepCounts);
  const timer = usePresentationTimer();
  const data = usePresentationData();
  useDeckKeyboard(deck, { t: timer.toggle, r: timer.reset, s: deck.completeBuilds });

  const slide = slides[deck.slideIndex];
  const nextSlide = slides[Math.min(slides.length - 1, deck.slideIndex + 1)];
  const isLast = deck.slideIndex === slides.length - 1;

  const targetTotal = slides.reduce((sum, s) => sum + (speakerNotes[s.id]?.durationSeconds ?? 0), 0);
  const targetSoFar = slides.slice(0, deck.slideIndex).reduce((sum, s) => sum + (speakerNotes[s.id]?.durationSeconds ?? 0), 0);
  const pace = timer.elapsed - targetSoFar;

  return (
    <div className="flex h-screen w-screen flex-col gap-4 bg-void p-5 text-ink">
      <header className="flex items-center justify-between">
        <div className="flex items-baseline gap-4">
          <span className="fontDisplay text-xl font-semibold"><span className="emberText">PROJECT EMBER</span> · Presenter</span>
          {data.isFixture ? <span className="fontMono rounded-full bg-[#FFB547]/15 px-3 py-1 text-xs text-[#FFB547]">FIXTURE DATA LOADED</span> : null}
          <span className="fontMono text-sm text-mute">{data.availableSectionCount}/7 result sections ingested</span>
        </div>
        <div className="flex items-center gap-6">
          <div className="fontMono text-right">
            <div className="text-4xl font-semibold tabular-nums">{formatClock(timer.elapsed)}</div>
            <div className={`text-xs ${pace > 15 ? "text-ember" : pace < -15 ? "text-[#48D8FF]" : "text-[#35D6A0]"}`}>
              {!timer.running && timer.elapsed === 0 ? "timer not started (T)" : pace > 15 ? `${formatClock(pace)} behind` : pace < -15 ? `${formatClock(-pace)} ahead` : "on pace"} · target {formatClock(targetTotal)}
            </div>
          </div>
          <button onClick={timer.toggle} className="rounded-xl border border-white/10 p-3 hover:bg-white/5" aria-label="Start or pause timer">{timer.running ? <Pause size={20} /> : <Play size={20} />}</button>
          <button onClick={timer.reset} className="rounded-xl border border-white/10 p-3 hover:bg-white/5" aria-label="Reset timer"><RotateCcw size={20} /></button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[1.55fr_1fr] gap-5">
        <div className="flex min-h-0 flex-col gap-3">
          <div className="fontMono text-sm text-mute">
            CURRENT · {String(deck.slideIndex + 1).padStart(2, "0")}/{slides.length} · build {deck.step + 1}/{slide.steps}
          </div>
          <div className="min-h-0 flex-1 overflow-hidden rounded-xl border border-ember/40">
            <Stage><SlideRenderer slide={slide} sceneNumber={deck.slideIndex + 1} step={deck.step} isActive /></Stage>
          </div>
          <div className="flex items-center justify-center gap-3">
            <button onClick={deck.previous} className="flex items-center gap-2 rounded-xl border border-white/10 px-6 py-3 hover:bg-white/5"><ChevronLeft /> Prev</button>
            <button onClick={deck.next} className="flex items-center gap-2 rounded-xl bg-ember px-8 py-3 font-semibold text-black hover:brightness-110">Next <ChevronRight /></button>
            <button onClick={deck.nextSlide} className="flex items-center gap-2 rounded-xl border border-white/10 px-5 py-3 text-mute hover:bg-white/5" title="Skip builds (Shift+→)"><SkipForward size={18} /> Skip builds</button>
          </div>
        </div>
        <div className="flex min-h-0 flex-col gap-3">
          <div className="fontMono text-sm text-mute">{isLast ? "END OF DECK" : `NEXT · ${nextSlide.title}`}</div>
          <div className="aspect-video overflow-hidden rounded-xl border border-white/10 opacity-90">
            {isLast ? (
              <div className="flex h-full items-center justify-center text-mute">Questions · Explore mode (E in audience window)</div>
            ) : (
              <Stage><SlideRenderer slide={nextSlide} sceneNumber={deck.slideIndex + 2} step={0} isActive={false} isPreview /></Stage>
            )}
          </div>
          <div className="glassPanel min-h-0 flex-1 overflow-y-auto rounded-xl p-5">
            <SpeakerNotesPanel slideId={slide.id} large />
          </div>
        </div>
      </div>
    </div>
  );
}
