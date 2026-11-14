"use client";
/**
 * Deck navigation state: slide + build step, URL hash sync (#/3), and cross-window sync
 * over BroadcastChannel so the presenter window and audience window stay aligned.
 */
import { useCallback, useEffect, useRef, useState } from "react";

export interface DeckPosition {
  slideIndex: number;
  step: number;
}

interface SyncMessage {
  type: "position";
  position: DeckPosition;
  senderId: string;
}

const channelName = "projectEmberDeck";

function parseHash(slideCount: number): DeckPosition | null {
  if (typeof window === "undefined") return null;
  const match = window.location.hash.match(/^#\/(\d+)(?:\.(\d+))?$/);
  if (!match) return null;
  const slideIndex = Math.min(slideCount - 1, Math.max(0, Number(match[1]) - 1));
  return { slideIndex, step: Number(match[2] ?? 0) };
}

export function useDeckController(stepCounts: number[], { writeHash = true }: { writeHash?: boolean } = {}) {
  const slideCount = stepCounts.length;
  const [position, setPosition] = useState<DeckPosition>({ slideIndex: 0, step: 0 });
  const senderId = useRef(`w${Math.random().toString(36).slice(2)}`);
  const channelRef = useRef<BroadcastChannel | null>(null);
  const suppressBroadcast = useRef(false);

  // Initial position from hash; then listen for peers.
  useEffect(() => {
    const fromHash = parseHash(slideCount);
    if (fromHash) setPosition({ slideIndex: fromHash.slideIndex, step: Math.min(fromHash.step, stepCounts[fromHash.slideIndex] - 1) });
    if (typeof BroadcastChannel === "undefined") return;
    const channel = new BroadcastChannel(channelName);
    channelRef.current = channel;
    channel.onmessage = (event: MessageEvent<SyncMessage>) => {
      const message = event.data;
      if (message?.type === "position" && message.senderId !== senderId.current) {
        suppressBroadcast.current = true;
        setPosition(message.position);
      }
    };
    return () => channel.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slideCount]);

  // Publish changes + keep hash in sync.
  useEffect(() => {
    if (writeHash) {
      const hash = `#/${position.slideIndex + 1}${position.step > 0 ? `.${position.step}` : ""}`;
      if (window.location.hash !== hash) window.history.replaceState(null, "", hash);
    }
    if (suppressBroadcast.current) {
      suppressBroadcast.current = false;
      return;
    }
    channelRef.current?.postMessage({ type: "position", position, senderId: senderId.current } satisfies SyncMessage);
  }, [position, writeHash]);

  const goTo = useCallback((slideIndex: number, step = 0) => {
    const clamped = Math.min(slideCount - 1, Math.max(0, slideIndex));
    setPosition({ slideIndex: clamped, step: Math.min(step, stepCounts[clamped] - 1) });
  }, [slideCount, stepCounts]);

  const next = useCallback(() => {
    setPosition((p) => {
      if (p.step < stepCounts[p.slideIndex] - 1) return { ...p, step: p.step + 1 };
      if (p.slideIndex < slideCount - 1) return { slideIndex: p.slideIndex + 1, step: 0 };
      return p;
    });
  }, [slideCount, stepCounts]);

  const previous = useCallback(() => {
    setPosition((p) => {
      if (p.step > 0) return { ...p, step: p.step - 1 };
      if (p.slideIndex > 0) return { slideIndex: p.slideIndex - 1, step: stepCounts[p.slideIndex - 1] - 1 };
      return p;
    });
  }, [stepCounts]);

  /** Skip remaining builds and jump straight to the next slide. */
  const nextSlide = useCallback(() => setPosition((p) => ({ slideIndex: Math.min(slideCount - 1, p.slideIndex + 1), step: 0 })), [slideCount]);
  const previousSlide = useCallback(() => setPosition((p) => ({ slideIndex: Math.max(0, p.slideIndex - 1), step: 0 })), []);
  /** Reveal all builds on the current slide immediately. */
  const completeBuilds = useCallback(() => setPosition((p) => ({ ...p, step: stepCounts[p.slideIndex] - 1 })), [stepCounts]);

  return { ...position, slideCount, goTo, next, previous, nextSlide, previousSlide, completeBuilds };
}

export type DeckController = ReturnType<typeof useDeckController>;

/** Shared keyboard map for audience and presenter windows. */
export function useDeckKeyboard(deck: DeckController, handlers: Partial<Record<string, () => void>> = {}) {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.isContentEditable)) return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const key = event.key;
      const custom = handlersRef.current[key.toLowerCase()] ?? handlersRef.current[key];
      if (key === "ArrowRight" || key === "PageDown" || (key === " " && !event.shiftKey)) {
        event.preventDefault();
        if (event.shiftKey) deck.nextSlide();
        else deck.next();
      } else if (key === "ArrowLeft" || key === "PageUp" || (key === " " && event.shiftKey)) {
        event.preventDefault();
        if (event.shiftKey) deck.previousSlide();
        else deck.previous();
      } else if (key === "ArrowDown") {
        event.preventDefault();
        deck.nextSlide();
      } else if (key === "ArrowUp") {
        event.preventDefault();
        deck.previousSlide();
      } else if (key === "Home") {
        deck.goTo(0);
      } else if (key === "End") {
        deck.goTo(deck.slideCount - 1);
      } else if (custom) {
        event.preventDefault();
        custom();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [deck]);
}
