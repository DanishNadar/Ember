/** Writes the deck's reference Fuzzfile to fuzzball/ember.fuzzfile.yaml. Run: npm run export:fuzzfile */
import { writeFileSync } from "node:fs";
import { emberFuzzfileText } from "../lib/emberFuzzfile";
writeFileSync(new URL("../fuzzball/ember.fuzzfile.yaml", import.meta.url), emberFuzzfileText);
console.log("wrote fuzzball/ember.fuzzfile.yaml");
