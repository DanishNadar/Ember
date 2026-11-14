/** Number formatting for metrics. Missing values never render as zero. */
export const missingValue = "—";

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return missingValue;
  return value.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return missingValue;
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatSignedPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return missingValue;
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(digits)}%`;
}

export function formatSeconds(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return missingValue;
  if (value < 1e-3) return `${(value * 1e6).toFixed(0)} µs`;
  if (value < 1) return `${(value * 1000).toFixed(value < 0.01 ? 2 : 1)} ms`;
  if (value < 120) return `${value.toFixed(value < 10 ? 2 : 1)} s`;
  if (value < 7200) return `${(value / 60).toFixed(1)} min`;
  return `${(value / 3600).toFixed(2)} h`;
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return missingValue;
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e4) return `${(value / 1e3).toFixed(1)}K`;
  return value.toLocaleString("en-US");
}

export function formatClock(totalSeconds: number): string {
  const sign = totalSeconds < 0 ? "-" : "";
  const s = Math.abs(Math.floor(totalSeconds));
  const m = Math.floor(s / 60);
  return `${sign}${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}
