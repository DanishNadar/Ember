/** Project Ember wordmark with flame glyph. */
export function EmberGlyph({ size = 72 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <defs>
        <radialGradient id="emberGlyphFill" cx="50%" cy="62%" r="58%">
          <stop offset="0" stopColor="#FFF1D6" />
          <stop offset="0.3" stopColor="#FFB547" />
          <stop offset="0.65" stopColor="#FF6B35" />
          <stop offset="1" stopColor="#E53935" />
        </radialGradient>
        <filter id="emberGlyphGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="4.5" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <circle cx="32" cy="38" r="24" fill="#FF6B35" opacity="0.18" />
      <path filter="url(#emberGlyphGlow)" d="M32 6c3.2 9.4 14 14.6 14 28.4a14 14 0 0 1-28 0c0-7.6 4.2-11.8 7.4-15 0 5.3 2.2 8.6 5.4 9.6-2.2-8.6 0-16 1.2-23z" fill="url(#emberGlyphFill)" />
      <circle cx="32" cy="40" r="4.5" fill="#48D8FF" opacity="0.9" />
    </svg>
  );
}

export function EmberWordmark({ scale = 1 }: { scale?: number }) {
  return (
    <div className="flex items-center" style={{ gap: 22 * scale }}>
      <EmberGlyph size={88 * scale} />
      <div>
        <div className="fontDisplay font-bold leading-none tracking-[0.06em]" style={{ fontSize: 72 * scale }}>
          <span className="text-ink">PROJECT </span>
          <span className="emberText">EMBER</span>
        </div>
        <div className="fontMono mt-2 uppercase tracking-[0.32em] text-[#48D8FF]" style={{ fontSize: 20 * scale }}>
          Adaptive Wildfire Surrogate
        </div>
      </div>
    </div>
  );
}
