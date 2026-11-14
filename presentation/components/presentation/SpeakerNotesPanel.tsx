"use client";
/** Speaker notes for one slide: message, points, interaction cue, evidence, transition. */
import notes from "@/slides/speakerNotes.json";

export type SpeakerNote = {
  durationSeconds: number;
  main: string;
  talkingPoints: string[];
  interaction: string;
  evidence: string;
  transition: string;
};

export const speakerNotes = notes as Record<string, SpeakerNote>;

export function SpeakerNotesPanel({ slideId, large = false }: { slideId: string; large?: boolean }) {
  const note = speakerNotes[slideId];
  if (!note) return <div className="text-mute">No notes for this slide.</div>;
  const body = large ? "text-[19px]" : "text-[15px]";
  return (
    <div className={`space-y-4 leading-relaxed ${body}`}>
      <div>
        <div className="fontMono mb-1 text-[11px] uppercase tracking-[0.2em] text-ember">Main message · ~{note.durationSeconds}s</div>
        <div className={`fontDisplay font-semibold text-ink ${large ? "text-[24px]" : "text-[18px]"}`}>{note.main}</div>
      </div>
      <div>
        <div className="fontMono mb-1 text-[11px] uppercase tracking-[0.2em] text-mute">Talking points</div>
        <ul className="list-disc space-y-1 pl-5 text-ink/90">
          {note.talkingPoints.map((point) => <li key={point}>{point}</li>)}
        </ul>
      </div>
      <div>
        <div className="fontMono mb-1 text-[11px] uppercase tracking-[0.2em] text-[#48D8FF]">Do this</div>
        <div className="text-ink/90">{note.interaction}</div>
      </div>
      <div>
        <div className="fontMono mb-1 text-[11px] uppercase tracking-[0.2em] text-[#35D6A0]">Evidence</div>
        <div className="text-mute">{note.evidence}</div>
      </div>
      <div>
        <div className="fontMono mb-1 text-[11px] uppercase tracking-[0.2em] text-mute">Transition</div>
        <div className="italic text-ink/80">“{note.transition}”</div>
      </div>
    </div>
  );
}
