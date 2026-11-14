"use client";
/**
 * Animated U-Net-style schematic: encoder → bottleneck → decoder with skip connections.
 * Block sizes are schematic (wider = more channels, shorter = lower resolution).
 */
import { motion } from "framer-motion";

const levels = [
  { height: 300, width: 34, label: "H × W" },
  { height: 210, width: 50, label: "H/2" },
  { height: 140, width: 68, label: "H/4" },
  { height: 92, width: 88, label: "H/8" },
];
const bottleneck = { height: 62, width: 112 };

export function UNetDiagram({ width, height, time, reducedMotion }: { width: number; height: number; time: number; reducedMotion: boolean }) {
  const topY = 70;
  const levelDrop = 92;
  const encoderX = [190, 300, 420, 555];
  const bottleneckX = 700;
  const decoderX = [encoderX[3] + 330, encoderX[2] + 590, encoderX[1] + 830, encoderX[0] + 1060].map((x) => x - 60);
  const centerY = (level: number) => topY + level * levelDrop + levels[0].height / 2 - (levels[0].height - levels[Math.min(level, 3)].height) / 2;

  const blocks: Array<{ x: number; y: number; w: number; h: number; color: string; key: string }> = [];
  levels.forEach((lv, l) => {
    const cy = topY + l * levelDrop + lv.height / 2;
    blocks.push({ x: encoderX[l], y: cy - lv.height / 2, w: lv.width, h: lv.height, color: "#48D8FF", key: `e${l}` });
    blocks.push({ x: decoderX[3 - l], y: cy - lv.height / 2, w: lv.width, h: lv.height, color: "#48D8FF", key: `d${l}` });
  });
  const bottleneckY = topY + 4 * levelDrop + bottleneck.height / 2 - 30;
  const pulse = reducedMotion ? 0.5 : (time * 0.35) % 1;
  // Activation pulse travels along the U path: encoder 0..3, bottleneck, decoder 3..0.
  const pathXs = [...encoderX.map((x, l) => x + levels[l].width / 2), bottleneckX + bottleneck.width / 2, ...[3, 2, 1, 0].map((l) => decoderX[3 - l] + levels[l].width / 2)];
  const pathYs = [...levels.map((lv, l) => topY + l * levelDrop + lv.height / 2), bottleneckY + bottleneck.height / 2, ...[3, 2, 1, 0].map((l) => topY + l * levelDrop + levels[l].height / 2)];
  const segment = pulse * (pathXs.length - 1);
  const s0 = Math.floor(segment);
  const s1 = Math.min(pathXs.length - 1, s0 + 1);
  const frac = segment - s0;
  const pulseX = pathXs[s0] + (pathXs[s1] - pathXs[s0]) * frac;
  const pulseY = pathYs[s0] + (pathYs[s1] - pathYs[s0]) * frac;
  void centerY;

  return (
    <svg width={width} height={height} viewBox="0 0 1460 560" role="img" aria-label="U-Net style encoder-decoder schematic">
      <defs>
        <linearGradient id="unetBlock" x1="0" x2="1">
          <stop offset="0" stopColor="#48D8FF" stopOpacity={0.55} />
          <stop offset="1" stopColor="#1C8FB8" stopOpacity={0.25} />
        </linearGradient>
        <radialGradient id="unetPulse">
          <stop offset="0" stopColor="#E9FBFF" />
          <stop offset="0.4" stopColor="#48D8FF" stopOpacity={0.8} />
          <stop offset="1" stopColor="#48D8FF" stopOpacity={0} />
        </radialGradient>
      </defs>

      {/* Input stack */}
      {[0, 1, 2, 3, 4, 5].map((k) => (
        <rect key={k} x={30 + k * 8} y={topY + 40 + k * 8} width={110} height={190} rx={6} fill={k === 5 ? "#FF6B35" : "#1A2230"} fillOpacity={k === 5 ? 0.6 : 0.9} stroke={k === 5 ? "#FF6B35" : "#5B6678"} />
      ))}
      <text x={30} y={topY + 290} className="fontMono" fontSize={15} fill="#94A3B8">input channels</text>

      {/* Skip connections */}
      {levels.map((lv, l) => {
        const y = topY + l * levelDrop + 24;
        return (
          <g key={`skip${l}`}>
            <line x1={encoderX[l] + lv.width + 6} y1={y} x2={decoderX[3 - l] - 8} y2={y} stroke="#48D8FF" strokeOpacity={0.5} strokeWidth={2} className="flowDash" />
            <text x={(encoderX[l] + decoderX[3 - l]) / 2} y={y - 8} textAnchor="middle" className="fontMono" fontSize={13} fill="#5B6678">skip · {lv.label}</text>
          </g>
        );
      })}

      {/* Down / up arrows */}
      {levels.slice(0, 3).map((lv, l) => (
        <g key={`arr${l}`} stroke="#48D8FF" strokeOpacity={0.6} strokeWidth={2} fill="none">
          <path d={`M${encoderX[l] + lv.width / 2},${topY + l * levelDrop + lv.height + 4} L${encoderX[l + 1] + levels[l + 1].width / 2},${topY + (l + 1) * levelDrop + levels[l + 1].height - 6}`} />
          <path d={`M${decoderX[3 - (l + 1)] + levels[l + 1].width / 2},${topY + (l + 1) * levelDrop + levels[l + 1].height - 6} L${decoderX[3 - l] + lv.width / 2},${topY + l * levelDrop + lv.height + 4}`} />
        </g>
      ))}
      <path d={`M${encoderX[3] + levels[3].width / 2},${topY + 3 * levelDrop + levels[3].height + 4} L${bottleneckX + 20},${bottleneckY + 10}`} stroke="#48D8FF" strokeOpacity={0.6} strokeWidth={2} />
      <path d={`M${bottleneckX + bottleneck.width - 20},${bottleneckY + 10} L${decoderX[0] + levels[3].width / 2},${topY + 3 * levelDrop + levels[3].height + 4}`} stroke="#48D8FF" strokeOpacity={0.6} strokeWidth={2} />

      {blocks.map((b, i) => (
        <motion.rect
          key={b.key}
          x={b.x}
          y={b.y}
          width={b.w}
          height={b.h}
          rx={8}
          fill="url(#unetBlock)"
          stroke="#48D8FF"
          strokeOpacity={0.8}
          initial={false}
          animate={{ opacity: 1 }}
          transition={{ delay: reducedMotion ? 0 : i * 0.05 }}
        />
      ))}
      <rect x={bottleneckX} y={bottleneckY} width={bottleneck.width} height={bottleneck.height} rx={10} fill="#48D8FF" fillOpacity={0.35} stroke="#48D8FF" strokeWidth={2} />
      <text x={bottleneckX + bottleneck.width / 2} y={bottleneckY + bottleneck.height + 26} textAnchor="middle" className="fontMono" fontSize={15} fill="#94A3B8">latent representation</text>

      <text x={encoderX[0]} y={topY - 22} className="fontMono" fontSize={17} fill="#48D8FF" letterSpacing="2">ENCODER</text>
      <text x={decoderX[3] + levels[0].width} y={topY - 22} textAnchor="end" className="fontMono" fontSize={17} fill="#48D8FF" letterSpacing="2">DECODER</text>

      {/* Output mask */}
      <rect x={decoderX[3] + 90} y={topY + 55} width={150} height={190} rx={8} fill="#FFB547" fillOpacity={0.12} stroke="#FFB547" />
      <path d={`M${decoderX[3] + levels[0].width + 8},${topY + 150} L${decoderX[3] + 82},${topY + 150}`} stroke="#48D8FF" strokeWidth={2} />
      <ellipse cx={decoderX[3] + 165} cy={topY + 150} rx={46} ry={62} fill="#FF6B35" fillOpacity={0.55} />
      <text x={decoderX[3] + 90} y={topY + 290} className="fontMono" fontSize={15} fill="#94A3B8">predicted mask</text>

      {/* Activation pulse */}
      {!reducedMotion ? <circle cx={pulseX} cy={pulseY} r={34} fill="url(#unetPulse)" /> : null}
    </svg>
  );
}
