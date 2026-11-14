"use client";
/**
 * Ambient rising embers behind every slide. One small canvas, its own rAF loop (no React
 * re-renders), seeded so it looks the same every run. Static frame when not animating.
 */
import { useEffect, useRef } from "react";
import { createSeededRandom } from "@/lib/seededRandom";

interface Ember {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  life: number;
  maxLife: number;
  hue: number;
  phase: number;
}

const width = 960;
const height = 540;

function spawn(random: () => number, initial: boolean): Ember {
  const maxLife = 220 + random() * 380;
  return {
    x: random() * width,
    y: initial ? random() * height : height + 10 + random() * 40,
    vx: (random() - 0.5) * 0.25,
    vy: -(0.25 + random() * 0.9),
    size: 0.6 + Math.pow(random(), 3) * 3.2,
    life: initial ? random() * maxLife : 0,
    maxLife,
    hue: 12 + random() * 30,
    phase: random() * Math.PI * 2,
  };
}

export function EmberField({ animate, density = 1, intensity = 1 }: { animate: boolean; density?: number; intensity?: number }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    const random = createSeededRandom(4242);
    // Pre-rendered glow sprites (one per hue band) — far cheaper than a gradient per ember.
    const sprites = [14, 24, 34, 44].map((hue) => {
      const sprite = document.createElement("canvas");
      sprite.width = sprite.height = 64;
      const sctx = sprite.getContext("2d")!;
      const g = sctx.createRadialGradient(32, 32, 0, 32, 32, 32);
      g.addColorStop(0, `hsla(${hue + 20}, 100%, 78%, 1)`);
      g.addColorStop(0.22, `hsla(${hue}, 100%, 56%, 0.6)`);
      g.addColorStop(1, `hsla(${hue - 8}, 100%, 40%, 0)`);
      sctx.fillStyle = g;
      sctx.fillRect(0, 0, 64, 64);
      return { hue, sprite };
    });
    const embers: Ember[] = Array.from({ length: Math.round(110 * density) }, () => spawn(random, true));
    let frame = 0;
    let tick = 0;

    const draw = () => {
      tick++;
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = "lighter";
      for (let k = 0; k < embers.length; k++) {
        const e = embers[k];
        e.life += 1;
        e.x += e.vx + Math.sin((tick + e.phase * 60) / 50) * 0.18;
        e.y += e.vy;
        if (e.life > e.maxLife || e.y < -10) embers[k] = spawn(random, false);
        const t = e.life / e.maxLife;
        const fade = Math.sin(Math.PI * Math.min(1, t)) * (0.65 + 0.35 * Math.sin(tick / 6 + e.phase));
        const alpha = Math.max(0, fade) * 0.85 * intensity;
        const r = e.size * (1 + (1 - t) * 0.6);
        if (alpha <= 0.01) continue;
        const sprite = sprites[Math.min(3, Math.max(0, Math.floor((e.hue - 12) / 7.5)))].sprite;
        const d = r * 10;
        ctx.globalAlpha = alpha;
        ctx.drawImage(sprite, e.x - d / 2, e.y - d / 2, d, d);
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
      if (animate) frame = requestAnimationFrame(draw);
    };

    if (animate) frame = requestAnimationFrame(draw);
    else draw();
    return () => cancelAnimationFrame(frame);
  }, [animate, density, intensity]);

  return <canvas ref={canvasRef} width={width} height={height} className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden />;
}
