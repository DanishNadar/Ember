import type { Metadata, Viewport } from "next";
import "@fontsource/space-grotesk/400.css";
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/600.css";
import "./globals.css";
import { PresentationDataProvider } from "@/components/presentation/DataProvider";
import { MotionPreferenceProvider } from "@/hooks/useMotionPreference";

export const metadata: Metadata = {
  title: "Project Ember — Adaptive Wildfire Surrogate",
  description: "From simulating one future to exploring thousands. CIQ Supercomputing Local AI Hackathon, Chicago 2026.",
  icons: { icon: "/images/emberMark.svg" },
};

export const viewport: Viewport = {
  themeColor: "#0B0606",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <MotionPreferenceProvider>
          <PresentationDataProvider>{children}</PresentationDataProvider>
        </MotionPreferenceProvider>
      </body>
    </html>
  );
}
