#!/usr/bin/env node
/** Regenerates docs/presentationScript.md from slides/speakerNotes.json in registry order. Run: npm run docs:script */
import { readFileSync, writeFileSync } from "node:fs";
const registry = readFileSync(new URL("../slides/registry.ts", import.meta.url), "utf8");
const notes = JSON.parse(readFileSync(new URL("../slides/speakerNotes.json", import.meta.url), "utf8"));
const entries = [...registry.matchAll(/\{ id: "([^"]+)", title: "([^"]+)"/g)].map((m) => ({ id: m[1], title: m[2] }));
const clock = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
const total = entries.reduce((sum, e) => sum + (notes[e.id]?.durationSeconds ?? 0), 0);
let md = `# Project Ember — Presentation Script\n\nGenerated from \`slides/speakerNotes.json\` (run \`npm run docs:script\`). Target ≈ ${clock(total)} for ${entries.length} scenes; questions in Explore mode (\`E\`).\nKeys: \`→\`/\`Space\` next build · \`Shift+→\` skip builds · \`S\` reveal builds · \`N\` notes · \`P\` presenter.\n`;
entries.forEach((e, i) => {
  const n = notes[e.id];
  md += `\n## ${String(i + 1).padStart(2, "0")} · ${e.title} (~${n.durationSeconds} s)\n**Message:** ${n.main}\n${n.talkingPoints.map((p) => `- ${p}`).join("\n")}\n\n**Do:** ${n.interaction}\n**Evidence:** ${n.evidence}\n**Transition:** “${n.transition}”\n`;
});
writeFileSync(new URL("../docs/presentationScript.md", import.meta.url), md);
console.log(`wrote docs/presentationScript.md (${entries.length} scenes, ${clock(total)})`);
