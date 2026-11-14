"use client";
/** Scales the fixed 1920×1080 stage to fit its container while preserving 16:9. */
import { useEffect, useRef, useState } from "react";
import { stageHeight, stageWidth } from "@/lib/theme";

export function useStageScale<T extends HTMLElement>() {
  const containerRef = useRef<T | null>(null);
  const [scale, setScale] = useState(0);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const measure = () => {
      const { width, height } = element.getBoundingClientRect();
      setScale(Math.min(width / stageWidth, height / stageHeight));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return { containerRef, scale };
}
