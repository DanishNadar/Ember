/** Ordered scene list. Each slide lives in its own file; notes live in speakerNotes.json. */
import type { SlideDefinition } from "./slideTypes";
import { Slide01Spark } from "./Slide01Spark";
import { Slide02HumanProblem } from "./Slide02HumanProblem";
import { Slide03OneSimulation } from "./Slide03OneSimulation";
import { Slide04ComputeChallenge } from "./Slide04ComputeChallenge";
import { Slide05MeetEmber } from "./Slide05MeetEmber";
import { Slide06PhysicsEngine } from "./Slide06PhysicsEngine";
import { Slide07SimulationToData } from "./Slide07SimulationToData";
import { Slide08NeuralSurrogate } from "./Slide08NeuralSurrogate";
import { Slide09TwoNodes } from "./Slide09TwoNodes";
import { Slide10Fuzzball } from "./Slide10Fuzzball";
import { Slide11MomentOfTruth } from "./Slide11MomentOfTruth";
import { Slide12Performance } from "./Slide12Performance";
import { Slide13ComputeUnlocks } from "./Slide13ComputeUnlocks";
import { Slide14Conclusion } from "./Slide14Conclusion";

export const slides: SlideDefinition[] = [
  { id: "spark", title: "The Spark", takeaway: "One spark, thousands of possible futures.", chapter: "Problem", accent: "#FF6B35", steps: 1, evidence: ["illustration"], Component: Slide01Spark },
  { id: "humanProblem", title: "The Human Problem", takeaway: "Same ignition, different conditions, different outcomes.", chapter: "Problem", accent: "#FF6B35", steps: 2, evidence: ["illustration"], Component: Slide02HumanProblem },
  { id: "oneSimulation", title: "One Simulation Isn't Enough", takeaway: "Each uncertain input multiplies the runs.", chapter: "Problem", accent: "#FF6B35", steps: 3, evidence: ["illustration"], Component: Slide03OneSimulation },
  { id: "computeChallenge", title: "The Computational Challenge", takeaway: "More questions, more compute. Can physics be approximated?", chapter: "Problem", accent: "#E53935", steps: 2, evidence: ["illustration"], Component: Slide04ComputeChallenge },
  { id: "meetEmber", title: "Meet Project Ember", takeaway: "Simulate → dataset → surrogate → evaluate, orchestrated by Fuzzball.", chapter: "Approach", accent: "#FF6B35", steps: 1, evidence: ["illustration"], Component: Slide05MeetEmber },
  { id: "physicsEngine", title: "The Physics Engine", takeaway: "The simulator produces the reference the surrogate learns from.", chapter: "Approach", accent: "#FF6B35", steps: 1, evidence: ["simulatorDerived", "illustration"], Component: Slide06PhysicsEngine },
  { id: "simulationToData", title: "From Simulation to Data", takeaway: "Snapshots become aligned channel tensors and future-mask targets.", chapter: "Approach", accent: "#FFB547", steps: 3, evidence: ["verified", "illustration"], Component: Slide07SimulationToData },
  { id: "neuralSurrogate", title: "The Neural Surrogate", takeaway: "A U-Net learns conditions → future fire extent.", chapter: "Approach", accent: "#48D8FF", steps: 1, evidence: ["verified", "illustration"], Component: Slide08NeuralSurrogate },
  { id: "twoNodes", title: "The Two-Node Experiment", takeaway: "Planned producer–consumer design vs verified placement.", chapter: "System", accent: "#48D8FF", steps: 1, evidence: ["illustration", "verified"], Component: Slide09TwoNodes },
  { id: "fuzzball", title: "Fuzzball Orchestration", takeaway: "Recorded jobs, dependencies and placement on one timeline.", chapter: "System", accent: "#A3B8D9", steps: 1, evidence: ["verified"], Component: Slide10Fuzzball },
  { id: "momentOfTruth", title: "The Moment of Truth", takeaway: "Surrogate fidelity on held-out simulated states, including failures.", chapter: "Evidence", accent: "#48D8FF", steps: 1, evidence: ["verified"], Component: Slide11MomentOfTruth },
  { id: "performance", title: "The Performance Reveal", takeaway: "Three separate accelerations, training cost on its own.", chapter: "Evidence", accent: "#35D6A0", steps: 1, evidence: ["verified"], Component: Slide12Performance },
  { id: "computeUnlocks", title: "What Compute Unlocks", takeaway: "Ensembles show where outcomes agree and where they don't.", chapter: "Outlook", accent: "#FF6B35", steps: 3, evidence: ["proposed"], Component: Slide13ComputeUnlocks },
  { id: "conclusion", title: "The Next Frontier", takeaway: "We didn't replace physics. We made it reusable.", chapter: "Outlook", accent: "#FF6B35", steps: 2, evidence: ["verified", "proposed"], Component: Slide14Conclusion },
];
