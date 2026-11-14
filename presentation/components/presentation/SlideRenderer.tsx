"use client";
/** Renders one slide definition with backdrop; shared by the deck, presenter and overview. */
import type { SlideDefinition } from "@/slides/slideTypes";
import { SlideBackdrop } from "./SlideBackdrop";
import { usePresentationData } from "./DataProvider";
import { useMotionPreference } from "@/hooks/useMotionPreference";
import { SceneNumberContext } from "./SlideFrame";

export function SlideRenderer({ slide, sceneNumber, step, isActive, isPreview = false }: {
  slide: SlideDefinition;
  sceneNumber: number;
  step: number;
  isActive: boolean;
  isPreview?: boolean;
}) {
  const data = usePresentationData();
  const { reducedMotion } = useMotionPreference();
  const { Component } = slide;
  return (
    <div className="absolute inset-0 overflow-hidden">
      <SlideBackdrop tint={slide.accent} />
      <SceneNumberContext.Provider value={sceneNumber}>
        <Component step={step} isActive={isActive} reducedMotion={reducedMotion || isPreview} data={data} isPreview={isPreview} />
      </SceneNumberContext.Provider>
    </div>
  );
}
