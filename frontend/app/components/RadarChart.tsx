'use client';
interface RadarScores {
  clarity: number;
  value_proposition: number;
  cta_score: number;
  brand_voice: number;
  emotional_resonance: number;
}
const DIMENSIONS: { key: keyof RadarScores; labels: string[] }[] = [
  { key: 'clarity', labels: ['Clarity'] },
  { key: 'value_proposition', labels: ['Value', 'Proposition'] },
  { key: 'cta_score', labels: ['CTA', 'Score'] },
  { key: 'brand_voice', labels: ['Brand', 'Voice'] },
  { key: 'emotional_resonance', labels: ['Emotional', 'Resonance'] },
];
const DIM_COLORS = ['#fbbf24', '#ec4899', '#c850c0', '#9b6cc8', '#5b9be4'];
const GRID_LEVELS = [2, 4, 6, 8, 10];
const MAX = 10;
const ANGLE_OFFSET = -Math.PI / 2;
function polarToXY(cx: number, cy: number, radius: number, index: number, total: number) {
  const angle = ANGLE_OFFSET + (2 * Math.PI * index) / total;
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  };
}
function pentagonPoints(cx: number, cy: number, radius: number, count: number): string {
  return Array.from({ length: count }, (_, i) => {
    const { x, y } = polarToXY(cx, cy, radius, i, count);
    return `${x},${y}`;
  }).join(' ');
}
export default function RadarChart({ scores }: { scores: RadarScores }) {
  const gradId = `radar-fill-${Math.random().toString(36).slice(2, 8)}`;
  const viewSize = 380;
  const cx = viewSize / 2;
  const cy = viewSize / 2;
  const maxR = 110;
  const count = DIMENSIONS.length;
  const scoreValues = DIMENSIONS.map((d) => scores[d.key] ?? 0);
  const dataPoints = scoreValues.map((val, i) => {
    const r = (val / MAX) * maxR;
    return polarToXY(cx, cy, r, i, count);
  });
  const dataPolygon = dataPoints.map((p) => `${p.x},${p.y}`).join(' ');
  const labelOffset = 52;
  return (
    <svg
      viewBox={`0 0 ${viewSize} ${viewSize}`}
      style={{ width: '100%', maxWidth: 380, aspectRatio: '1', display: 'block', margin: '0 auto' }}
    >
      <defs>
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#c850c0" stopOpacity={0.3} />
          <stop offset="100%" stopColor="#5b9be4" stopOpacity={0.3} />
        </linearGradient>
      </defs>
      {/* Grid pentagons */}
      {GRID_LEVELS.map((level) => {
        const r = (level / MAX) * maxR;
        return (
          <polygon
            key={level}
            points={pentagonPoints(cx, cy, r, count)}
            fill="none"
            stroke="var(--border, #e5e7eb)"
            strokeWidth={0.5}
            opacity={0.5}
          />
        );
      })}
      {/* Axis lines */}
      {DIMENSIONS.map((_, i) => {
        const { x, y } = polarToXY(cx, cy, maxR, i, count);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--border, #e5e7eb)" strokeWidth={0.5} opacity={0.35} />;
      })}
      {/* Score polygon fill + stroke */}
      <polygon points={dataPolygon} fill={`url(#${gradId})`} stroke="#c850c0" strokeWidth={1.8} strokeLinejoin="round" />
      {/* Vertex dots */}
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={4.5} fill={DIM_COLORS[i]} />
      ))}
      {/* Labels — score on top, multi-line dimension name below */}
      {DIMENSIONS.map((dim, i) => {
        const { x, y } = polarToXY(cx, cy, maxR + labelOffset, i, count);
        const val = scoreValues[i];
        const lineCount = dim.labels.length;
        // Shift the whole label group up slightly to center it visually
        const baseY = y - ((lineCount - 1) * 6);
        return (
          <text
            key={dim.key}
            x={x}
            y={baseY}
            textAnchor="middle"
            dominantBaseline="middle"
            style={{ fontFamily: 'DM Sans, sans-serif' }}
          >
            <tspan x={x} dy="-0.5em" style={{ fontWeight: 700, fill: DIM_COLORS[i], fontSize: 14, fontFamily: 'Space Mono, monospace' }}>
              {val.toFixed(1)}
            </tspan>
            {dim.labels.map((line, li) => (
              <tspan key={li} x={x} dy={li === 0 ? '1.5em' : '1.2em'} style={{ fontSize: 11, fill: 'var(--muted, #888)', fontWeight: 400 }}>
                {line}
              </tspan>
            ))}
          </text>
        );
      })}
    </svg>
  );
}
