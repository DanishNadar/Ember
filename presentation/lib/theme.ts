/**
 * Semantic color system. These mappings are used everywhere:
 * orange/red = physics simulation and fire, cyan = neural / accelerated compute,
 * green = verified improvement, slate = baselines, uncertainty and unavailable data.
 */
export const palette = {
  void: "#0B0606",
  basalt: "#1A0F0C",
  ash: "#2A1712",
  line: "#3A2018",
  ember: "#FF6B35",
  fire: "#E53935",
  flame: "#FFB547",
  cyan: "#48D8FF",
  cyanDeep: "#1C8FB8",
  verified: "#35D6A0",
  ink: "#F3F6FA",
  mute: "#C2AFA4",
  dim: "#8A7266",
  proposed: "#A78BFA",
} as const;

export type AccentName = "ember" | "cyan" | "verified" | "mute";

export const accentColor: Record<AccentName, string> = {
  ember: palette.ember,
  cyan: palette.cyan,
  verified: palette.verified,
  mute: palette.mute,
};

/** Stage geometry: every slide is authored on a fixed 16:9 canvas and scaled to fit. */
export const stageWidth = 1920;
export const stageHeight = 1080;
