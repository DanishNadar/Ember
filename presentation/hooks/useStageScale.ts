"use client";
/**
 * Scales the 1920×1080 authoring canvas to its container.
 * `fill` extends the canvas along the spare axis so it covers the container edge to edge
 * (no letterbox bars); otherwise the canvas stays exactly 16:9.
 */
import { useEffect, useRef, useState } from "react";
import { stageHeight, stageWidth } from "@/lib/theme";

export function useStageScale<T extends HTMLElement>(fill = false) {
  const containerRef = useRef<T | null>(null);
  const [size, setSize] = useState({ scale: 0, width: stageWidth, height: stageHeight });

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const measure = () => {
      const { width, height } = element.getBoundingClientRect();
      const scale = Math.min(width / stageWidth, height / stageHeight);
      setSize(
        fill && scale > 0
          ? { scale, width: width / scale, height: height / scale }
          : { scale, width: stageWidth, height: stageHeight },
      );
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [fill]);

  return { containerRef, ...size };
}
