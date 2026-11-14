"use client";
/**
 * Audience view: fullscreen slide stage with an auto-hiding toolbar, progress bar,
 * chapters overview, notes drawer, autoplay, timer and presenter-window launch.
 */
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronLeft, ChevronRight, LayoutGrid, NotebookText, MonitorPlay, Maximize, Minimize,
  Play, Pause, Compass, Timer, RotateCcw, Accessibility, Keyboard,
} from "lucide-react";
import { slides } from "@/slides/registry";
import { useDeckController, useDeckKeyboard } from "@/hooks/useDeckController";
import { usePresentationTimer } from "@/hooks/usePresentationTimer";
import { useMotionPreference } from "@/hooks/useMotionPreference";
import { formatClock } from "@/lib/format";
import { Stage } from "./Stage";
import { SlideRenderer } from "./SlideRenderer";
import { OverviewGrid } from "./OverviewGrid";
import { SpeakerNotesPanel, speakerNotes } from "./SpeakerNotesPanel";
import { HelpOverlay } from "./HelpOverlay";
import { usePresentationData } from "./DataProvider";
import { FixtureWatermark } from "./FixtureWatermark";

function ToolbarButton({ onClick, label, active = false, children }: { onClick: () => void; label: string; active?: boolean; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      title={label}
      aria-label={label}
      aria-pressed={active}
      className={`flex items-center gap-2 rounded-lg px-3 py-2 text-[13px] font-medium transition ${active ? "bg-ember/15 text-ember" : "text-mute hover:bg-white/5 hover:text-ink"}`}
    >
      {children}
      <span className="hidden min-[2200px]:inline">{label}</span>
    </button>
  );
}

export function Deck() {
  const stepCounts = useMemo(() => slides.map((s) => s.steps), []);
  const deck = useDeckController(stepCounts);
  const data = usePresentationData();
  const timer = usePresentationTimer();
  const { reducedMotion, toggleReducedMotion } = useMotionPreference();
  const [overviewOpen, setOverviewOpen] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [autoplay, setAutoplay] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [chromeVisible, setChromeVisible] = useState(true);
  const hideTimer = useRef<number | undefined>(undefined);

  const slide = slides[deck.slideIndex];

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.().catch(() => {});
    else document.exitFullscreen?.().catch(() => {});
  }, []);

  const openPresenter = useCallback(() => {
    const base = window.location.pathname.replace(/\/?$/, "/");
    window.open(`${base}presenter/${window.location.search}${window.location.hash}`, "emberPresenter", "width=1400,height=860");
  }, []);

  const openExplore = useCallback(() => {
    const base = window.location.pathname.replace(/\/?$/, "/");
    window.open(`${base}explore/${window.location.search}`, "_blank");
  }, []);

  useEffect(() => {
    const onChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  // Start the timer automatically on the first advance.
  useEffect(() => {
    if ((deck.slideIndex > 0 || deck.step > 0) && !timer.running && timer.elapsed === 0) timer.start();
  }, [deck.slideIndex, deck.step, timer]);

  // Autoplay: dwell per build = slide's speaking time / builds.
  useEffect(() => {
    if (!autoplay) return;
    const note = speakerNotes[slide.id];
    const dwell = Math.max(4, (note?.durationSeconds ?? 20) / slide.steps) * 1000;
    const id = window.setTimeout(() => {
      if (deck.slideIndex === slides.length - 1 && deck.step === slide.steps - 1) setAutoplay(false);
      else deck.next();
    }, dwell);
    return () => window.clearTimeout(id);
  }, [autoplay, deck, slide]);

  useDeckKeyboard(deck, {
    o: () => setOverviewOpen((v) => !v),
    g: () => setOverviewOpen((v) => !v),
    n: () => setNotesOpen((v) => !v),
    p: openPresenter,
    f: toggleFullscreen,
    a: () => setAutoplay((v) => !v),
    t: timer.toggle,
    r: timer.reset,
    m: toggleReducedMotion,
    e: openExplore,
    s: deck.completeBuilds,
    "?": () => setHelpOpen((v) => !v),
    escape: () => {
      setOverviewOpen(false);
      setHelpOpen(false);
      setNotesOpen(false);
    },
  });

  // Auto-hide toolbar after inactivity.
  const revealChrome = useCallback(() => {
    setChromeVisible(true);
    window.clearTimeout(hideTimer.current);
    hideTimer.current = window.setTimeout(() => setChromeVisible(false), 2600);
  }, []);
  useEffect(() => {
    revealChrome();
    window.addEventListener("mousemove", revealChrome);
    return () => window.removeEventListener("mousemove", revealChrome);
  }, [revealChrome]);

  const totalSteps = stepCounts.reduce((a, b) => a + b, 0);
  const completedSteps = stepCounts.slice(0, deck.slideIndex).reduce((a, b) => a + b, 0) + deck.step + 1;

  return (
    <div className="fixed inset-0 bg-black" style={{ cursor: chromeVisible ? "default" : "none" }}>
      <div className={`absolute inset-0 transition-[right] duration-300 ${notesOpen ? "right-[420px]" : "right-0"}`}>
        <Stage>
          <AnimatePresence initial={false}>
            <motion.div
              key={slide.id}
              className="absolute inset-0"
              initial={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 1.015, filter: "blur(6px)" }}
              animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
              exit={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.99, filter: "blur(4px)" }}
              transition={{ duration: reducedMotion ? 0.15 : 0.45, ease: [0.2, 0.7, 0.2, 1] }}
            >
              <SlideRenderer slide={slide} sceneNumber={deck.slideIndex + 1} step={deck.step} isActive />
            </motion.div>
          </AnimatePresence>
          {data.isFixture ? <FixtureWatermark /> : null}
        </Stage>

        {/* Progress */}
        <div className="absolute inset-x-0 top-0 h-[4px] bg-white/5">
          <motion.div className="h-full" style={{ background: "linear-gradient(90deg,#B71C1C,#E53935,#FF6B35,#FFD27A)", boxShadow: "0 0 18px 2px rgba(255,107,53,0.7)" }} animate={{ width: `${(completedSteps / totalSteps) * 100}%` }} transition={{ duration: 0.4 }} />
        </div>
      </div>

      {/* Toolbar */}
      <div className="pointer-events-none absolute inset-x-0 bottom-4 z-40 flex justify-center px-4">
      <motion.div
        animate={{ opacity: chromeVisible ? 1 : 0, y: chromeVisible ? 0 : 16 }}
        transition={{ duration: 0.25 }}
        className="glassPanel flex max-w-full items-center gap-0.5 overflow-x-auto rounded-2xl px-2 py-1.5"
        style={{ pointerEvents: chromeVisible ? "auto" : "none" }}
      >
        <ToolbarButton onClick={deck.previous} label="Prev"><ChevronLeft size={18} /></ToolbarButton>
        <div className="fontMono whitespace-nowrap px-2 text-center text-[13px] text-mute">
          <span className="text-ink">{String(deck.slideIndex + 1).padStart(2, "0")}</span> / {slides.length}<span className="hidden min-[1500px]:inline"> · {slide.title}</span>
        </div>
        <ToolbarButton onClick={deck.next} label="Next"><ChevronRight size={18} /></ToolbarButton>
        <div className="mx-1 h-6 w-px bg-white/10" />
        <ToolbarButton onClick={() => setOverviewOpen(true)} label="Chapters"><LayoutGrid size={17} /></ToolbarButton>
        <ToolbarButton onClick={() => setNotesOpen((v) => !v)} label="Notes" active={notesOpen}><NotebookText size={17} /></ToolbarButton>
        <ToolbarButton onClick={openPresenter} label="Presenter"><MonitorPlay size={17} /></ToolbarButton>
        <ToolbarButton onClick={openExplore} label="Explore"><Compass size={17} /></ToolbarButton>
        <ToolbarButton onClick={() => setAutoplay((v) => !v)} label="Autoplay" active={autoplay}>{autoplay ? <Pause size={17} /> : <Play size={17} />}</ToolbarButton>
        <ToolbarButton onClick={toggleReducedMotion} label="Calm motion" active={reducedMotion}><Accessibility size={17} /></ToolbarButton>
        <div className="mx-1 h-6 w-px bg-white/10" />
        <button onClick={timer.toggle} className="fontMono flex items-center gap-2 rounded-lg px-3 py-2 text-[13px] text-mute hover:text-ink" title="Start/pause timer (T)">
          <Timer size={16} className={timer.running ? "text-ember" : ""} /> {formatClock(timer.elapsed)}
        </button>
        <button onClick={timer.reset} className="rounded-lg p-2 text-mute hover:text-ink" title="Reset timer (R)" aria-label="Reset timer"><RotateCcw size={15} /></button>
        <ToolbarButton onClick={() => setHelpOpen(true)} label="Keys"><Keyboard size={17} /></ToolbarButton>
        <ToolbarButton onClick={toggleFullscreen} label="Present" active={isFullscreen}>{isFullscreen ? <Minimize size={17} /> : <Maximize size={17} />}</ToolbarButton>
      </motion.div>
      </div>

      {/* Click zones for quick navigation (outside toolbar) */}
      <AnimatePresence>
        {notesOpen ? (
          <motion.aside
            initial={{ x: 420 }}
            animate={{ x: 0 }}
            exit={{ x: 420 }}
            transition={{ duration: 0.25 }}
            className="absolute bottom-0 right-0 top-0 z-30 w-[420px] overflow-y-auto border-l border-white/10 bg-basalt/95 p-6"
          >
            <div className="fontMono mb-4 text-xs uppercase tracking-[0.2em] text-mute">Speaker notes · {String(deck.slideIndex + 1).padStart(2, "0")}</div>
            <SpeakerNotesPanel slideId={slide.id} />
          </motion.aside>
        ) : null}
        {overviewOpen ? (
          <OverviewGrid
            slides={slides}
            currentIndex={deck.slideIndex}
            onSelect={(index) => {
              deck.goTo(index);
              setOverviewOpen(false);
            }}
            onClose={() => setOverviewOpen(false)}
          />
        ) : null}
        {helpOpen ? <HelpOverlay onClose={() => setHelpOpen(false)} /> : null}
      </AnimatePresence>
    </div>
  );
}
