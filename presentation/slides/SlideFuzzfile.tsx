"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { FuzzballLockup } from "@/components/visualizations/BrandMarks";
import { emberFuzzfileLines, fuzzfileCallouts, type FuzzfileTag } from "@/lib/emberFuzzfile";
import { fuzzballGreen } from "@/lib/ecosystem";
import type { SlideProps } from "./slideTypes";

const tagColor: Record<FuzzfileTag, string> = {
  volumes: "#48D8FF",
  fanout: "#FF6B35",
  overlap: "#FFB547",
  gpu: "#35D6A0",
  plain: "#C2AFA4",
};

/** Lightweight YAML colouring: keys, comments, values. */
function YamlLine({ text, dim }: { text: string; dim: boolean }) {
  const commentAt = text.indexOf(" #");
  const code = commentAt >= 0 ? text.slice(0, commentAt) : text;
  const comment = commentAt >= 0 ? text.slice(commentAt) : "";
  const match = code.match(/^(\s*-?\s*)([\w./-]+:)(.*)$/);
  return (
    <div className="whitespace-pre" style={{ opacity: dim ? 0.28 : 1, transition: "opacity .35s" }}>
      {match ? (
        <>
          <span>{match[1]}</span>
          <span className="text-[#7DD3FC]">{match[2]}</span>
          <span className="text-[#F3F6FA]">{match[3]}</span>
        </>
      ) : (
        <span className="text-[#F3F6FA]">{code}</span>
      )}
      {comment ? <span className="text-[#8A7266]">{comment}</span> : null}
    </div>
  );
}

const flowSteps = ["Job submission", "Data movement in", "Execute workflow", "Best-fit resources", "Data movement out"];
const cliCommands = ["fuzzball workflow validate ember.yaml", "fuzzball workflow start ember.yaml -n ember-run", "fuzzball workflow describe <id> -w", "fuzzball workflow log <id> train -f"];

export function SlideFuzzfile({ step, isActive, reducedMotion, data }: SlideProps) {
  const realDefinition = data.snapshot.workflowDefinition ?? null;
  const [override, setOverride] = useState<FuzzfileTag | null>(null);
  useEffect(() => setOverride(null), [step, isActive]);
  const activeTag: FuzzfileTag = override ?? fuzzfileCallouts[Math.min(step, fuzzfileCallouts.length - 1)].tag;

  const half = 28;
  const columns = [emberFuzzfileLines.slice(0, half), emberFuzzfileLines.slice(half)];

  return (
    <SlideFrame
      kicker="Fuzzball workflow · reproducibility as code"
      headline={<>The experiment is <span style={{ color: fuzzballGreen }}>one Fuzzball workflow.</span></>}
      accent={fuzzballGreen}
      aside={<FuzzballLockup size={52} label="Fuzzfile" sublabel="version: v4" />}
      reducedMotion={reducedMotion}
    >
      <div className="flex h-full gap-8">
        <div className="glassPanel relative flex flex-col rounded-2xl p-5" style={{ width: 1180 }}>
          <div className="mb-3 flex items-center justify-between">
            <span className="fontMono text-[15px] text-ink">{realDefinition ? realDefinition.path : "fuzzball/ember.fuzzfile.yaml"}</span>
            {realDefinition ? (
              <EvidenceBadge kind={data.isFixture ? "illustration" : "verified"} isFixture={data.isFixture} detail="team Fuzzfile, verbatim" />
            ) : (
              <EvidenceBadge kind="illustration" detail="reference template (v4 syntax) until your Fuzzfile is ingested" />
            )}
          </div>
          {realDefinition ? (
            <pre className="fontMono min-h-0 flex-1 overflow-hidden whitespace-pre text-[13px] leading-[1.45] text-ink/90">{realDefinition.text}</pre>
          ) : (
            <div className="fontMono grid min-h-0 flex-1 grid-cols-2 gap-6 text-[14.5px] leading-[1.52]">
              {columns.map((lines, c) => (
                <div key={c} className="overflow-hidden">
                  {lines.map((line, k) => {
                    const highlighted = line.tag === activeTag;
                    return (
                      <div key={k} className="flex">
                        <span className="mr-3 inline-block w-[3px] rounded-full" style={{ background: highlighted ? tagColor[line.tag] : "transparent" }} />
                        <YamlLine text={line.text} dim={!highlighted && line.tag !== "plain"} />
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-1 flex-col gap-3">
          {fuzzfileCallouts.map((callout, k) => {
            const active = callout.tag === activeTag;
            return (
              <motion.button
                key={callout.tag}
                onClick={() => setOverride(callout.tag)}
                initial={false}
                animate={{ opacity: active ? 1 : 0.55 }}
                className="rounded-xl border p-4 text-left transition"
                style={{ borderColor: active ? tagColor[callout.tag] : "rgba(220,170,140,0.15)", background: active ? `${tagColor[callout.tag]}12` : "transparent" }}
              >
                <div className="fontDisplay flex items-center gap-2 text-[20px] font-semibold text-ink">
                  <span className="fontMono text-[14px]" style={{ color: tagColor[callout.tag] }}>{k + 1}</span> {callout.title}
                </div>
                <div className="mt-1 text-[16px] leading-snug text-mute">{callout.body}</div>
              </motion.button>
            );
          })}
          <div className="mt-1">
            <div className="fontMono mb-2 text-[12px] uppercase tracking-[0.2em] text-mute">Orchestrate → Substrate</div>
            <div className="flex gap-1">
              {flowSteps.map((s, k) => (
                <div key={s} className="flex-1 rounded-md px-2 py-1.5 text-center text-[12px] leading-tight text-ink/90" style={{ background: `${fuzzballGreen}${k % 2 ? "22" : "33"}` }}>
                  <span className="fontMono block text-[11px]" style={{ color: fuzzballGreen }}>{k + 1}</span>
                  {s}
                </div>
              ))}
            </div>
          </div>
          <div className="fontMono rounded-lg bg-black/40 p-3 text-[13px] leading-relaxed text-[#35D6A0]">
            {cliCommands.map((c) => <div key={c}>$ {c}</div>)}
          </div>
        </div>
      </div>
    </SlideFrame>
  );
}
