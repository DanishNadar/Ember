/* eslint-disable @next/next/no-img-element */
/**
 * Official partner marks, taken unmodified from the organizers' "SC26 Hackathon Introduction"
 * deck (public/images/brand). Shown to credit the hackathon platform Ember is built on.
 */
import { fuzzballGreen } from "@/lib/ecosystem";

export function FuzzballMark({ size = 40, className = "" }: { size?: number; className?: string }) {
  return <img src="/images/brand/fuzzballMark.png" alt="Fuzzball" width={size} height={size} className={className} style={{ width: size, height: size }} />;
}

/** Mark stacked over the "Fuzzball" wordmark, as in the organizers' deck. */
export function FuzzballLogo({ height = 120, className = "" }: { height?: number; className?: string }) {
  return <img src="/images/brand/fuzzballLogo.png" alt="Fuzzball by CIQ" className={className} style={{ height, width: "auto" }} />;
}

/** Inline lockup: mark + text, for headers and footers. */
export function FuzzballLockup({ size = 34, label = "Fuzzball", sublabel }: { size?: number; label?: string; sublabel?: string }) {
  return (
    <span className="inline-flex items-center gap-3">
      <FuzzballMark size={size} />
      <span className="leading-none">
        <span className="fontDisplay font-semibold text-ink" style={{ fontSize: size * 0.68 }}>{label}</span>
        {sublabel ? <span className="fontMono mt-1 block uppercase tracking-[0.18em]" style={{ fontSize: Math.max(11, size * 0.32), color: fuzzballGreen }}>{sublabel}</span> : null}
      </span>
    </span>
  );
}

export function CiqLogo({ height = 36, className = "" }: { height?: number; className?: string }) {
  return <img src="/images/brand/ciqLogo.png" alt="CIQ" className={className} style={{ height, width: "auto" }} />;
}

/** NVIDIA · Cambridge Computer · VAST · Lenovo · DRIVE, as shown on the hackathon title slide. */
export function PartnerStrip({ height = 56, className = "" }: { height?: number; className?: string }) {
  return <img src="/images/brand/partnersStrip.png" alt="In partnership with NVIDIA, Cambridge Computer, VAST Data, Lenovo and Drive Capital" className={className} style={{ height, width: "auto" }} />;
}

/** Small persistent footer credit on every content slide. */
export function PlatformFooter() {
  return (
    <div className="pointer-events-none absolute bottom-[22px] right-[96px] flex items-center gap-3 opacity-80">
      <span className="fontMono text-[13px] uppercase tracking-[0.18em] text-mute">Orchestrated with</span>
      <FuzzballMark size={22} />
      <span className="fontDisplay text-[16px] font-semibold text-ink">Fuzzball</span>
      <span className="fontMono text-[13px] text-dim">·</span>
      <span className="fontMono text-[13px] tracking-[0.12em] text-mute">RLC PRO AI 9.8 · NVIDIA GB10 × 2</span>
    </div>
  );
}
