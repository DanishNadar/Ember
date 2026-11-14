import type { ComponentType } from "react";
import type { PresentationData } from "@/data/adapters/presentationData";
import type { EvidenceKind } from "@/data/schemas/presentationSchema";

export interface SlideProps {
  /** Current build step within the slide (0-based). */
  step: number;
  /** True when this slide is the one being presented (drives animation clocks). */
  isActive: boolean;
  reducedMotion: boolean;
  data: PresentationData;
  /** Previews (overview / presenter "next") render statically and skip heavy loops. */
  isPreview?: boolean;
}

export interface SlideDefinition {
  id: string;
  title: string;
  takeaway: string;
  chapter: "Problem" | "Approach" | "System" | "Evidence" | "Outlook";
  accent: string;
  /** Number of build steps (1 = no builds). */
  steps: number;
  evidence: EvidenceKind[];
  Component: ComponentType<SlideProps>;
}
