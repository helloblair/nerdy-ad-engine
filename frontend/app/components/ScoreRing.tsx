'use client';
import { useEvalConfig } from '../hooks/useEvalConfig';

export default function ScoreRing({ score, size = 64 }: { score: number; size?: number }) {
  const { threshold } = useEvalConfig();
  const gradient = score >= threshold + 1.0
    ? ['#c850c0', '#9b6cc8']
    : score >= threshold
    ? ['#fbbf24', '#f97316']
    : ['#ec4899', '#c850c0'];
  const id = `grad-${Math.random().toString(36).slice(2, 8)}`;
  const r = (size / 2) - (size > 50 ? 6 : 4);
  const circ = 2 * Math.PI * r;
  const dash = (score / 10) * circ;
  const strokeW = size > 50 ? 4 : 3;
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
      <defs>
        <linearGradient id={id} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={gradient[0]} />
          <stop offset="100%" stopColor={gradient[1]} />
        </linearGradient>
      </defs>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--surface2)" strokeWidth={strokeW} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={`url(#${id})`} strokeWidth={strokeW} strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
      <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="middle" style={{ fill: gradient[0], fontSize: size * 0.22, fontFamily: 'Space Mono', fontWeight: 700, transform: 'rotate(90deg)', transformOrigin: `${size/2}px ${size/2}px` }}>{score.toFixed(1)}</text>
    </svg>
  );
}
