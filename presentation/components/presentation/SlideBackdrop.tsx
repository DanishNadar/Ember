/** Atmospheric backdrop shared by all slides: deep gradient, faint grid, vignette. */
export function SlideBackdrop({ tint = "#FF6B35" }: { tint?: string }) {
  return (
    <div className="pointer-events-none absolute inset-0">
      <div className="absolute inset-0 bg-void" />
      <div
        className="absolute inset-0"
        style={{
          background: `radial-gradient(1200px 700px at 85% 110%, ${tint}1f, transparent 60%), radial-gradient(900px 600px at 0% -10%, #48D8FF12, transparent 60%)`,
        }}
      />
      <div className="gridBackdrop absolute inset-0 opacity-60" style={{ maskImage: "radial-gradient(ellipse at center, black 30%, transparent 80%)" }} />
      <div className="absolute inset-0" style={{ boxShadow: "inset 0 0 220px rgba(0,0,0,0.75)" }} />
    </div>
  );
}
