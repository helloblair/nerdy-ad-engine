'use client';
import { useState, useRef, useCallback } from 'react';

export function InfoTip({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  const [above, setAbove] = useState(true);
  const ref = useRef<HTMLSpanElement>(null);
  const handleEnter = useCallback(() => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect();
      setAbove(rect.top > 200);
    }
    setShow(true);
  }, []);
  const pos = above
    ? { bottom: 'calc(100% + 8px)', top: undefined as string | undefined }
    : { top: 'calc(100% + 8px)', bottom: undefined as string | undefined };
  return (
    <span
      ref={ref}
      style={{ position: 'relative', display: 'inline-flex', flexShrink: 0 }}
      onMouseEnter={handleEnter}
      onMouseLeave={() => setShow(false)}
    >
      <span
        style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          width: '16px', height: '16px', borderRadius: '50%',
          background: show ? 'var(--surface)' : 'var(--surface2)',
          border: show ? 'none' : '1px solid var(--border)',
          cursor: 'help', fontSize: '0.6rem', fontWeight: 700,
          color: show ? 'var(--accent)' : 'var(--muted)',
          fontStyle: 'italic', fontFamily: 'Georgia, serif',
          transition: 'all 0.25s',
          boxShadow: show
            ? '0 0 0 1px rgba(200,80,192,0.3), 0 0 12px rgba(200,80,192,0.1), 0 0 24px rgba(91,155,228,0.08)'
            : 'none',
        }}
      >i</span>
      {show && (
        <span style={{
          position: 'absolute', ...pos, left: '50%', transform: 'translateX(-50%)',
          width: '260px', padding: '10px 14px',
          background: 'var(--surface)', border: '1px solid transparent',
          borderRadius: '10px', fontSize: '0.75rem', lineHeight: 1.6,
          color: 'var(--text)', fontStyle: 'normal', fontFamily: 'DM Sans, sans-serif', fontWeight: 400,
          boxShadow: '0 0 0 1px rgba(200,80,192,0.3), 0 0 12px rgba(200,80,192,0.1), 0 0 24px rgba(91,155,228,0.08), 0 4px 16px rgba(0,0,0,0.1)',
          zIndex: 50, pointerEvents: 'none',
          backgroundClip: 'padding-box',
        }}>
          <span style={{
            position: 'absolute', inset: '-1px', borderRadius: '11px',
            background: 'var(--gradient-rainbow)', zIndex: -2, opacity: 0.6,
          }} />
          <span style={{
            position: 'absolute', inset: '0', borderRadius: '10px',
            background: 'var(--surface)', zIndex: -1,
          }} />
          {text}
        </span>
      )}
    </span>
  );
}
