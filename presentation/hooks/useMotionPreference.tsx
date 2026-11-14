"use client";
/** Reduced-motion preference: follows the OS setting, with a presenter override (key M). */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

interface MotionPreference {
  reducedMotion: boolean;
  toggleReducedMotion: () => void;
}

const MotionPreferenceContext = createContext<MotionPreference>({ reducedMotion: false, toggleReducedMotion: () => {} });

export function MotionPreferenceProvider({ children }: { children: React.ReactNode }) {
  const [systemReduced, setSystemReduced] = useState(false);
  const [override, setOverride] = useState<boolean | null>(null);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setSystemReduced(query.matches);
    const onChange = () => setSystemReduced(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const reducedMotion = override ?? systemReduced;

  useEffect(() => {
    document.documentElement.classList.toggle("reducedMotion", reducedMotion);
  }, [reducedMotion]);

  const toggleReducedMotion = useCallback(() => setOverride((prev) => !(prev ?? systemReduced)), [systemReduced]);
  const value = useMemo(() => ({ reducedMotion, toggleReducedMotion }), [reducedMotion, toggleReducedMotion]);
  return <MotionPreferenceContext.Provider value={value}>{children}</MotionPreferenceContext.Provider>;
}

export function useMotionPreference() {
  return useContext(MotionPreferenceContext);
}
