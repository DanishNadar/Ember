/** Ordered scene list. Each slide lives in its own file; notes live in speakerNotes.json. */
import type { SlideDefinition } from "./slideTypes";
import { Slide01Spark } from "./Slide01Spark";
import { Slide02HumanProblem } from "./Slide02HumanProblem";
import { Slide04ComputeChallenge } from "./Slide04ComputeChallenge";
import { Slide14Conclusion } from "./Slide14Conclusion";
import { SlideIdea } from "./SlideIdea";
import { SlideData } from "./SlideData";
import { SlideSurrogateResults } from "./SlideSurrogateResults";
import { SlideScaleUp } from "./SlideScaleUp";

export const slides: SlideDefinition[] = [
  { id: "spark", title: "The Spark", takeaway: "One spark, thousands of possible futures.", chapter: "Problem", accent: "#FF6B35", steps: 1, evidence: ["illustration"], Component: Slide01Spark },
  { id: "humanProblem", title: "The Human Problem", takeaway: "Same ignition, different conditions, different outcomes.", chapter: "Problem", accent: "#FF6B35", steps: 2, evidence: ["illustration"], Component: Slide02HumanProblem },
  { id: "computeChallenge", title: "The Computational Challenge", takeaway: "More questions, more compute. Can physics be approximated?", chapter: "Problem", accent: "#E53935", steps: 2, evidence: ["illustration"], Component: Slide04ComputeChallenge },
  { id: "idea", title: "The Idea", takeaway: "Physics teaches, AI learns, both run at once on two nodes.", chapter: "Approach", accent: "#48D8FF", steps: 1, evidence: ["illustration"], Component: SlideIdea },
  { id: "data", title: "The Data", takeaway: "~3k real ForeFire simulations, 19 channels, strict held-out test.", chapter: "Approach", accent: "#FFB547", steps: 1, evidence: ["verified"], Component: SlideData },
  { id: "scaleUp", title: "Scaling Up", takeaway: "Prototype → scaled → two-GPU fine-tune: arrival error 10.5 → 6.6 min, IoU 0.49 → 0.52.", chapter: "Evidence", accent: "#48D8FF", steps: 1, evidence: ["verified"], Component: SlideScaleUp },
  { id: "surrogateResults", title: "How Close Did AI Get?", takeaway: "Held-out IoU 0.48, Dice 0.65, precision 0.78, ~7 min arrival error.", chapter: "Evidence", accent: "#48D8FF", steps: 1, evidence: ["verified"], Component: SlideSurrogateResults },
  { id: "conclusion", title: "The Next Frontier", takeaway: "We didn't replace physics. We made it reusable.", chapter: "Outlook", accent: "#FF6B35", steps: 2, evidence: ["verified", "proposed"], Component: Slide14Conclusion },
];
