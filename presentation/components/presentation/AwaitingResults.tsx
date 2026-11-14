/** Styled empty state shown wherever verified data has not been ingested yet. */
import { Hourglass } from "lucide-react";

export function AwaitingResults({ title = "Awaiting verified results", artifact, note, compact = false, className = "" }: {
  title?: string;
  artifact?: string;
  note?: string;
  compact?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`awaitingBorder relative flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-500/30 text-center ${compact ? "gap-2 p-5" : "gap-4 p-10"} ${className}`}
    >
      <div className="slowPulse flex items-center justify-center rounded-full border border-slate-500/30 bg-slate-500/10" style={{ width: compact ? 44 : 64, height: compact ? 44 : 64 }}>
        <Hourglass size={compact ? 20 : 28} className="text-mute" />
      </div>
      <div className={`fontDisplay font-semibold text-ink ${compact ? "text-[20px]" : "text-[28px]"}`}>{title}</div>
      {artifact ? (
        <div className={`fontMono text-mute ${compact ? "text-[14px]" : "text-[17px]"}`}>
          expects <span className="text-ink/80">{artifact}</span>
        </div>
      ) : null}
      {note ? <div className={`max-w-[560px] text-mute ${compact ? "text-[14px]" : "text-[17px]"}`}>{note}</div> : null}
    </div>
  );
}
