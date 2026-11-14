/** Stylized compute unit (schematic of a desktop AI system), tinted by role. */
export function ComputeNode({ label, role, color, activity, width = 470, height = 300 }: {
  label: string;
  role: string;
  color: string;
  activity: number; // 0..1 glow intensity
  width?: number;
  height?: number;
}) {
  const bars = 18;
  return (
    <div className="relative" style={{ width, height }}>
      <div
        className="absolute inset-0 rounded-[28px]"
        style={{
          background: "linear-gradient(160deg, #1d2534 0%, #121824 45%, #0b1018 100%)",
          border: `1px solid ${color}55`,
          boxShadow: `0 0 ${40 + activity * 60}px -10px ${color}${activity > 0.5 ? "aa" : "55"}, inset 0 1px 0 rgba(255,255,255,0.08)`,
        }}
      />
      {/* Front grille */}
      <div className="absolute left-7 right-7 top-7 flex h-[96px] gap-[6px]">
        {Array.from({ length: bars }, (_, k) => {
          const phase = (k / bars + activity * 0.7) % 1;
          return <div key={k} className="flex-1 rounded-sm" style={{ background: color, opacity: 0.15 + 0.6 * activity * (0.5 + 0.5 * Math.sin(phase * Math.PI * 2)) }} />;
        })}
      </div>
      <div className="absolute left-7 right-7 top-[140px]">
        <div className="fontMono text-[14px] uppercase tracking-[0.2em]" style={{ color }}>{role}</div>
        <div className="fontDisplay mt-1 text-[32px] font-semibold text-ink">{label}</div>
        <div className="fontMono mt-1 text-[15px] text-mute">Lenovo ThinkStation PGX · NVIDIA GB10</div>
      </div>
      <div className="absolute bottom-6 left-7 right-7 flex items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/5">
          <div className="h-full rounded-full" style={{ width: `${Math.round(activity * 100)}%`, background: color, transition: "width .3s" }} />
        </div>
        <span className="fontMono text-[13px] text-mute">schematic activity</span>
      </div>
    </div>
  );
}
