"use client";
/** Renders one slide definition with backdrop; shared by the deck, presenter and overview. */
import type { SlideDefinition } from "@/slides/slideTypes";
import { SlideBackdrop } from "./SlideBackdrop";
import { usePresentationData } from "./DataProvider";
import { useMotionPreference } from "@/hooks/useMotionPreference";

export function SlideRenderer({ slide, step, isActive, isPreview = false }: {
  slide: SlideDefinition;
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
      <Component step={step} isActive={isActive} reducedMotion={reducedMotion || isPreview} data={data} isPreview={isPreview} />
    </div>
  );
}
