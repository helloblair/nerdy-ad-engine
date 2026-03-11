'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import RadarChart from '../../components/RadarChart';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

function ScoreRing({ score, size = 64 }: { score: number; size?: number }) {
  const gradient = score >= 8
    ? ['#c850c0', '#9b6cc8']
    : score >= 7
    ? ['#fbbf24', '#f97316']
    : ['#ec4899', '#c850c0'];
  const id = `grad-${Math.random().toString(36).slice(2, 8)}`;
  const r = (size / 2) - 6; const circ = 2 * Math.PI * r; const dash = (score / 10) * circ;
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
      <defs>
        <linearGradient id={id} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={gradient[0]} />
          <stop offset="100%" stopColor={gradient[1]} />
        </linearGradient>
      </defs>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--surface2)" strokeWidth={4} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={`url(#${id})`} strokeWidth={4} strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
      <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="middle" style={{ fill: gradient[0], fontSize: size * 0.22, fontFamily: 'Space Mono', fontWeight: 700, transform: 'rotate(90deg)', transformOrigin: `${size/2}px ${size/2}px` }}>{score.toFixed(1)}</text>
    </svg>
  );
}

export default function CampaignDetail() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!id) return;
    fetch(`${API}/campaigns/${id}`).then(r => r.json()).then(d => { setData(d); setLoading(false); }).catch(() => setLoading(false));
  }, [id]);
  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><span className="mono rainbow-text" style={{ fontWeight: 600 }}>LOADING...</span></div>;
  if (!data) return <div style={{ color: 'var(--danger)' }}>Campaign not found</div>;
  const { campaign, ads } = data;
  const dims = ['clarity', 'value_proposition', 'cta_score', 'brand_voice', 'emotional_resonance'];
  const dimColors = ['#fbbf24', '#ec4899', '#c850c0', '#9b6cc8', '#5b9be4'];
  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <a href="/campaigns" style={{ color: 'var(--accent)', fontSize: '0.875rem', textDecoration: 'none', fontWeight: 500 }}>← Campaigns</a>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, margin: '8px 0 4px' }}>{campaign.name}</h1>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span className={`badge badge-${campaign.status}`}>{campaign.status}</span>
          <span style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>{campaign.audience}</span>
        </div>
      </div>
      <div style={{ display: 'grid', gap: '1.5rem' }}>
        {ads.map((ad: any) => {
          const ev = ad.evaluation;
          return (
            <div key={ad.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem', gap: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
                    <span className={`badge badge-${ad.status}`}>{ad.status}</span>
                    <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>iter {ad.iteration_number}</span>
                  </div>
                  <h3 style={{ margin: '0 0 8px', fontSize: '1rem', fontWeight: 600 }}>{ad.headline}</h3>
                  <p style={{ margin: '0 0 12px', color: 'var(--muted)', fontSize: '0.875rem', lineHeight: 1.6 }}>{ad.primary_text}</p>
                  <span style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: '8px', padding: '6px 14px', fontSize: '0.8rem', color: 'var(--accent)', fontWeight: 500 }}>{ad.cta_button}</span>
                </div>
                {ev && <ScoreRing score={ev.aggregate_score} size={72} />}
              </div>
              {ev && (
                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                  <div style={{ maxWidth: 260, margin: '0 auto 1rem' }}>
                    <RadarChart scores={{
                      clarity: ev.clarity ?? 0,
                      value_proposition: ev.value_proposition ?? 0,
                      cta_score: ev.cta_score ?? 0,
                      brand_voice: ev.brand_voice ?? 0,
                      emotional_resonance: ev.emotional_resonance ?? 0,
                    }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
                    {dims.map((dim, idx) => {
                      const score = ev[dim];
                      return (
                        <div key={dim} style={{ textAlign: 'center' }}>
                          <div className="mono" style={{ fontSize: '1rem', fontWeight: 700, color: dimColors[idx] }}>{score?.toFixed(1)}</div>
                          <div style={{ fontSize: '0.65rem', color: 'var(--muted)', textTransform: 'capitalize', marginTop: '2px' }}>{dim.replace(/_/g, ' ')}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
