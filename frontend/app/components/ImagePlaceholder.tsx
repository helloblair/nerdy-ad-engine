'use client';

const RAINBOW = 'linear-gradient(90deg, #fbbf24, #f97316, #f06c6c, #ec4899, #c850c0, #9b6cc8, #5b9be4, #00d4cf)';

/**
 * Placeholder shown when an ad has no generated image (e.g. Imagen quota exhausted).
 * compact: thumbnail mode (dashboard cards)
 * full: ad preview mode (Facebook/Instagram mockups)
 */
export function ImagePlaceholder({ compact }: { compact?: boolean }) {
  if (compact) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: '6px', padding: '1rem', width: '100%', height: '100%',
      }}>
        <span className="mono" style={{
          fontSize: '0.6rem', fontWeight: 600, letterSpacing: '0.05em',
          background: RAINBOW, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        }}>IMAGE PENDING</span>
        <span style={{ fontSize: '0.5rem', color: 'var(--muted)', textAlign: 'center', lineHeight: 1.4 }}>
          Can be generated after the fact
        </span>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: '8px', padding: '2rem 1.5rem', background: 'var(--surface2)',
      aspectRatio: '1.91/1',
    }}>
      <div style={{
        width: '36px', height: '36px', borderRadius: '10px',
        background: RAINBOW, opacity: 0.15,
      }} />
      <span className="mono" style={{
        fontSize: '0.7rem', fontWeight: 600, letterSpacing: '0.05em',
        background: RAINBOW, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
      }}>IMAGE PENDING</span>
      <span style={{
        fontSize: '0.65rem', color: 'var(--muted)', textAlign: 'center', lineHeight: 1.5, maxWidth: '220px',
      }}>
        Image generation unavailable — creative can be generated after the fact via backfill
      </span>
    </div>
  );
}
