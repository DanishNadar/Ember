/** Small, unobtrusive label that classifies what a visual shows. */
import { CircleCheck, Flame, Shapes, Telescope, Hourglass, FlaskConical } from "lucide-react";
import type { EvidenceKind } from "@/data/schemas/presentationSchema";

const evidenceStyles: Record<EvidenceKind | "fixture", { label: string; color: string; Icon: typeof CircleCheck }> = {
  verified: { label: "Verified measurement", color: "#35D6A0", Icon: CircleCheck },
  simulatorDerived: { label: "Simulator-derived result", color: "#FF6B35", Icon: Flame },
  illustration: { label: "Architectural illustration", color: "#C2AFA4", Icon: Shapes },
  proposed: { label: "Proposed future work", color: "#A78BFA", Icon: Telescope },
  unavailable: { label: "Unavailable", color: "#8A7266", Icon: Hourglass },
  fixture: { label: "Illustrative fixture — not results", color: "#FFB547", Icon: FlaskConical },
};

export function EvidenceBadge({ kind, detail, isFixture = false, className = "" }: {
  kind: EvidenceKind;
  detail?: string;
  isFixture?: boolean;
  className?: string;
}) {
  const style = evidenceStyles[isFixture && kind !== "unavailable" && kind !== "proposed" ? "fixture" : kind];
  const { Icon } = style;
  return (
    <span
      className={`inline-flex items-center gap-2 whitespace-nowrap rounded-full px-3 py-1 text-[15px] font-medium fontMono ${className}`}
      style={{ color: style.color, background: `${style.color}14`, border: `1px solid ${style.color}38` }}
      title={detail ?? style.label}
    >
      <Icon size={15} strokeWidth={2.2} />
      {style.label}
      {detail ? <span className="text-mute font-normal">· {detail}</span> : null}
    </span>
  );
}
