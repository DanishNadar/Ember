"use client";
/**
 * Audience view: edge-to-edge slide stage with no on-screen chrome. Everything else
 * (chapters, notes, autoplay, timer, presenter window, fullscreen) lives on the keyboard — press ? for keys.
 */
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useState } from "react";
import { slides } from "@/slides/registry";
import { useDeckController, useDeckKeyboard } from "@/hooks/useDeckController";
import { usePresentationTimer } from "@/hooks/usePresentationTimer";
import { useMotionPreference } from "@/hooks/useMotionPreference";
import { Stage } from "./Stage";
import { SlideRenderer } from "./SlideRenderer";
import { OverviewGrid } from "./OverviewGrid";
import { SpeakerNotesPanel, speakerNotes } from "./SpeakerNotesPanel";
import { HelpOverlay } from "./HelpOverlay";
import { usePresentationData } from "./DataProvider";
import { FixtureWatermark } from "./FixtureWatermark";

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

  return (
    <div className="fixed inset-0 bg-void">
      <div className={`absolute inset-0 transition-[right] duration-300 ${notesOpen ? "right-[420px]" : "right-0"}`}>
        <Stage fill>
          <AnimatePresence initial={false}>
            <motion.div
              key={slide.id}
              className="absolute inset-0"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: reducedMotion ? 0.1 : 0.2, ease: "easeOut" }}
            >
              <SlideRenderer slide={slide} sceneNumber={deck.slideIndex + 1} step={deck.step} isActive />
            </motion.div>
          </AnimatePresence>
          {data.isFixture ? <FixtureWatermark /> : null}
        </Stage>
      </div>

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
