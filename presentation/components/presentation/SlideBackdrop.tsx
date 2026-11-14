/** Fire-lit volcanic backdrop: warm black, ember horizon glow, heat haze, rising embers. */
import { EmberField } from "@/components/visualizations/EmberField";

export function SlideBackdrop({ tint = "#FF6B35", animate = false }: { tint?: string; animate?: boolean }) {
  return (
    <div className="pointer-events-none absolute inset-0">
      <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, #0B0606 0%, #120807 55%, #1A0906 100%)" }} />
      {/* Horizon fire glow, gently breathing */}
      <div
        className="heatBreath absolute inset-x-[-10%] bottom-[-38%] h-[75%]"
        style={{ background: "radial-gradient(ellipse at 50% 100%, rgba(255,92,32,0.55) 0%, rgba(229,57,53,0.32) 28%, rgba(140,24,10,0.18) 50%, transparent 72%)" }}
      />
      {/* Corner ember light + per-slide accent */}
      <div
        className="absolute inset-0"
        style={{
          background: `radial-gradient(900px 600px at 100% 0%, ${tint}22, transparent 60%), radial-gradient(800px 520px at 0% 10%, rgba(255,140,40,0.10), transparent 60%)`,
        }}
      />
      <div className="gridBackdrop absolute inset-0 opacity-50" style={{ maskImage: "radial-gradient(ellipse at 50% 60%, black 25%, transparent 78%)" }} />
      <EmberField animate={animate} />
      {/* Heat haze line + vignette */}
      <div className="absolute inset-x-0 bottom-0 h-[3px]" style={{ background: "linear-gradient(90deg, transparent, #FF6B35 20%, #FFD27A 50%, #E53935 80%, transparent)", boxShadow: "0 0 30px 6px rgba(255,107,53,0.45)" }} />
      <div className="absolute inset-0" style={{ boxShadow: "inset 0 0 260px rgba(0,0,0,0.78)" }} />
    </div>
  );
}
