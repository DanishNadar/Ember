"use client";
/** Pill-style segmented toggle used for view switches (e.g. Planned / Verified). */
export function SegmentedToggle<T extends string>({ options, value, onChange }: { options: Array<[T, string]>; value: T; onChange: (v: T) => void }) {
  return (
    <div className="flex rounded-xl border border-white/10 bg-basalt p-1" role="tablist">
      {options.map(([key, label]) => (
        <button
          key={key}
          role="tab"
          aria-selected={value === key}
          onClick={() => onChange(key)}
          className={`fontMono whitespace-nowrap rounded-lg px-4 py-2 text-[16px] transition ${value === key ? "bg-[#48D8FF]/15 text-[#48D8FF]" : "text-mute hover:text-ink"}`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
