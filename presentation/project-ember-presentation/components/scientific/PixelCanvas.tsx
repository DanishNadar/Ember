"use client";
/** Generic grid-to-canvas painter. `paint` fills an ImageData of gridWidth × gridHeight. */
import { useEffect, useRef } from "react";

export function PixelCanvas({ gridWidth, gridHeight, displayWidth, displayHeight, paint, paintKey, smooth = false, className, ariaLabel }: {
  gridWidth: number;
  gridHeight: number;
  displayWidth: number;
  displayHeight: number;
  paint: (image: ImageData) => void;
  /** Change this to trigger a repaint. */
  paintKey: unknown;
  smooth?: boolean;
  className?: string;
  ariaLabel?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const paintRef = useRef(paint);
  paintRef.current = paint;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || gridWidth === 0 || gridHeight === 0) return;
    const ctx = canvas.getContext("2d")!;
    const image = ctx.createImageData(gridWidth, gridHeight);
    paintRef.current(image);
    ctx.putImageData(image, 0, 0);
  }, [gridWidth, gridHeight, paintKey]);

  return (
    <canvas
      ref={canvasRef}
      width={gridWidth}
      height={gridHeight}
      className={className}
      role="img"
      aria-label={ariaLabel}
      style={{ width: displayWidth, height: displayHeight, imageRendering: smooth ? "auto" : "pixelated", display: "block" }}
    />
  );
}
