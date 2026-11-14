/** Persistent banner whenever the illustrative fixture (not real results) is loaded. */
import { FlaskConical } from "lucide-react";

export function FixtureWatermark() {
  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-30 flex justify-center">
      <div className="fontMono mt-3 flex items-center gap-2 rounded-full border border-[#FFB547]/60 bg-[#FFB547]/15 px-5 py-2 text-[17px] font-semibold uppercase tracking-[0.18em] text-[#FFB547]">
        <FlaskConical size={18} /> Illustrative fixture — not experiment results
      </div>
    </div>
  );
}
