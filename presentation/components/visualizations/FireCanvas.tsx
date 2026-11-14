"use client";
/**
 * Canvas renderer for a FireRun at a given model time. Paints one pixel per grid cell
 * into an offscreen buffer, upscales it smoothly, adds a bloom pass for active fire and
 * optional rising sparks. No DOM nodes per cell.
 */
import { useEffect, useRef } from "react";
import type { FireRun } from "@/lib/fireModel";
import { paintFireFrame, type FireFrameOptions } from "@/lib/fireRender";
import { createSeededRandom } from "@/lib/seededRandom";
import { blurField, filledFootprint, isolineSegments, strokeSegments, terrainContours } from "@/lib/contours";



export interface FrontOverlay {
  run: FireRun;
  time: number;
  color: string;
  alpha?: number;
}

interface Spark {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
}

export interface FireCanvasProps {
  run: FireRun;
  time: number;
  width: number;
  height: number;
  options?: Partial<Omit<FireFrameOptions, "time">>;
  bloom?: boolean;
  sparks?: boolean;
  overlays?: FrontOverlay[];
  windArrows?: boolean;
  className?: string;
  ariaLabel?: string;
  /** Internal pixel density relative to CSS size; lower is cheaper for full-bleed canvases. */
  resolution?: number;
}

const defaultOptions: Omit<FireFrameOptions, "time"> = {
  showFire: true,
  showTerrain: true,
  showContours: true,
  showFuel: true,
  burnDuration: 40,
  isochroneStep: 0,
  terrainReveal: 1,
};

export function FireCanvas({ run, time, width, height, options, bloom = true, sparks = false, overlays, windArrows = false, className, ariaLabel, resolution = 0.75 }: FireCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const bufferRef = useRef<{ base: HTMLCanvasElement; glow: HTMLCanvasElement } | null>(null);
  const sparksRef = useRef<Spark[]>([]);
  const randomRef = useRef(createSeededRandom(9));
  const lastTimeRef = useRef(time);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const { width: gw, height: gh } = run.terrain;
    if (!bufferRef.current || bufferRef.current.base.width !== gw || bufferRef.current.base.height !== gh) {
      const base = document.createElement("canvas");
      const glow = document.createElement("canvas");
      base.width = glow.width = gw;
      base.height = glow.height = gh;
      bufferRef.current = { base, glow };
    }
    const { base, glow } = bufferRef.current;
    const baseCtx = base.getContext("2d")!;
    const glowCtx = glow.getContext("2d")!;
    const merged = { ...defaultOptions, ...options, time };

    const image = baseCtx.createImageData(gw, gh);
    paintFireFrame(image, run, { ...merged, showContours: false });
    baseCtx.putImageData(image, 0, 0);

    const ctx = canvas.getContext("2d")!;
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.globalCompositeOperation = "source-over";
    ctx.filter = "none";
    ctx.drawImage(base, 0, 0, canvas.width, canvas.height);

    const sx = canvas.width / gw;
    const sy = canvas.height / gh;

    // Vector topographic contours (smooth at any scale).
    if (merged.showTerrain && merged.showContours) {
      ctx.strokeStyle = `rgba(148,163,184,${0.16 * (merged.terrainReveal ?? 1)})`;
      ctx.lineWidth = Math.max(0.8, sx * 0.12);
      strokeSegments(ctx, terrainContours(run.terrain, run.terrain.elevation, gw, gh), sx, sy);
    }

    // Bloom: only actively burning cells, blurred additively.
    const burningCells: number[] = [];
    if (merged.showFire) {
      const glowImage = glowCtx.createImageData(gw, gh);
      const g = glowImage.data;
      for (let i = 0; i < run.arrival.length; i++) {
        const age = time - run.arrival[i];
        if (age >= 0 && age < merged.burnDuration) {
          const k = 1 - age / merged.burnDuration;
          const o = i * 4;
          g[o] = 255;
          g[o + 1] = 90 + 80 * k;
          g[o + 2] = 30;
          g[o + 3] = 255 * k;
          burningCells.push(i);
        }
      }
      if (bloom) {
        glowCtx.putImageData(glowImage, 0, 0);
        ctx.globalCompositeOperation = "lighter";
        ctx.filter = `blur(${Math.max(6, sx * 2.2)}px)`;
        ctx.globalAlpha = 0.9;
        ctx.drawImage(glow, 0, 0, canvas.width, canvas.height);
        ctx.filter = `blur(${Math.max(2, sx * 0.6)}px)`;
        ctx.globalAlpha = 0.7;
        ctx.drawImage(glow, 0, 0, canvas.width, canvas.height);
        ctx.filter = "none";
        ctx.globalAlpha = 1;
        ctx.globalCompositeOperation = "source-over";
      }
    }

    // Overlay fronts (e.g. alternative futures) as smooth isolines of arrival time.
    if (overlays) {
      ctx.save();
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      for (const overlay of overlays) {
        const footprint = blurField(filledFootprint(overlay.run.arrival, gw, gh, overlay.time), gw, gh, 1, 0);
        const segments = isolineSegments(footprint, gw, gh, 0.5);
        ctx.globalAlpha = overlay.alpha ?? 0.9;
        ctx.strokeStyle = overlay.color;
        ctx.shadowColor = overlay.color;
        ctx.shadowBlur = 10;
        ctx.lineWidth = Math.max(2, sx * 0.28);
        strokeSegments(ctx, segments, sx, sy);
      }
      ctx.restore();
    }

    // Wind vector glyphs on a coarse lattice.
    if (windArrows) {
      const rad = (run.params.windDirectionDeg * Math.PI) / 180;
      const dx = Math.sin(rad);
      const dy = -Math.cos(rad);
      const len = 10 + run.params.windSpeed * 2.2;
      ctx.strokeStyle = "rgba(72,216,255,0.75)";
      ctx.fillStyle = "rgba(72,216,255,0.75)";
      ctx.lineWidth = 2;
      const stepPx = 90;
      for (let py = stepPx / 2; py < canvas.height; py += stepPx) {
        for (let px = stepPx / 2; px < canvas.width; px += stepPx) {
          const x2 = px + dx * len;
          const y2 = py + dy * len;
          ctx.beginPath();
          ctx.moveTo(px - dx * len * 0.3, py - dy * len * 0.3);
          ctx.lineTo(x2, y2);
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(x2, y2);
          ctx.lineTo(x2 - dx * 8 + dy * 5, y2 - dy * 8 - dx * 5);
          ctx.lineTo(x2 - dx * 8 - dy * 5, y2 - dy * 8 + dx * 5);
          ctx.fill();
        }
      }
    }

    // Sparks: rise from the active front and drift downwind.
    if (sparks) {
      const random = randomRef.current;
      const dt = Math.max(0, Math.min(1.5, (time - lastTimeRef.current) / 8));
      const rad = (run.params.windDirectionDeg * Math.PI) / 180;
      const drift = run.params.windSpeed * 0.06;
      const list = sparksRef.current;
      const spawn = Math.min(14, Math.ceil(burningCells.length / 60));
      for (let s = 0; s < spawn && burningCells.length > 0; s++) {
        const cell = burningCells[Math.floor(random() * burningCells.length)];
        list.push({
          x: (cell % gw) * sx,
          y: Math.floor(cell / gw) * sy,
          vx: Math.sin(rad) * drift + (random() - 0.5) * 0.6,
          vy: -0.6 - random() * 1.4,
          life: 0,
          maxLife: 30 + random() * 50,
          size: 0.8 + random() * 2.2,
        });
      }
      ctx.globalCompositeOperation = "lighter";
      for (let k = list.length - 1; k >= 0; k--) {
        const p = list[k];
        p.life += 1 + dt;
        p.x += p.vx * 2;
        p.y += p.vy * 2;
        if (p.life > p.maxLife) {
          list.splice(k, 1);
          continue;
        }
        const fade = 1 - p.life / p.maxLife;
        ctx.fillStyle = `rgba(255,${140 + 80 * fade},${60 * fade},${fade})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * (0.6 + fade * 0.6), 0, Math.PI * 2);
        ctx.fill();
      }
      if (list.length > 600) list.splice(0, list.length - 600);
      ctx.globalCompositeOperation = "source-over";
    }
    lastTimeRef.current = time;
  }, [run, time, options, bloom, sparks, overlays, windArrows]);

  return (
    <canvas
      ref={canvasRef}
      width={Math.round(width * resolution)}
      height={Math.round(height * resolution)}
      className={className}
      style={{ width, height, display: "block" }}
      role="img"
      aria-label={ariaLabel ?? "Illustrative fire spread visualization"}
    />
  );
}
