"use client";
/**
 * Supplies PresentationData to every slide. Default source is the bundled verified
 * snapshot (offline-safe). `?fixture=sample` loads the illustrative fixture instead,
 * which always shows a watermark.
 */
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import verifiedSnapshot from "@/data/verified/presentationSnapshot.json";
import { buildPresentationData, type PresentationData } from "@/data/adapters/presentationData";

const PresentationDataContext = createContext<PresentationData | null>(null);

export function PresentationDataProvider({ children }: { children: React.ReactNode }) {
  const [raw, setRaw] = useState<unknown>(verifiedSnapshot);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("fixture") === "sample") {
      import("@/data/fixtures/sampleSnapshot.json").then((module) => setRaw(module.default));
    }
  }, []);

  const data = useMemo(() => buildPresentationData(raw), [raw]);
  return <PresentationDataContext.Provider value={data}>{children}</PresentationDataContext.Provider>;
}

export function usePresentationData(): PresentationData {
  const value = useContext(PresentationDataContext);
  if (!value) throw new Error("usePresentationData must be used inside PresentationDataProvider");
  return value;
}
