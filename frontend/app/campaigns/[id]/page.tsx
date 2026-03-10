'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
function ScoreRing({ score, size = 64 }: { score: number; size?: number }) {
  const color = score >= 8 ? 'var(--accent)' : score >= 7 ? 'var(--warn)' : 'var(--danger)';
  const r = (size / 2) - 6; const circ = 2 * Math.PI * r; const dash = (score / 10) * circ;
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--border)" strokeWidth={4} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={4} strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
      <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="middle" style={{ fill: color, fontSize: size * 0.22, fontFamily: 'Space Mono', fontWeight: 700, transform: 'rotate(90deg)', transformOrigin: `${size/2}px ${size/2}px` }}>{score.toFixed(1)}</text>
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
  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><span className="mono" style={{ color: 'var(--accent)' }}>LOADING...</span></div>;
  if (!data) return <div style={{ color: 'var(--danger)' }}>Campaign not found</div>;
  const { campaign, ads } = data;
  const dims = ['clarity', 'value_proposition', 'cta_score', 'brand_voice', 'emotional_resonance'];
  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <a href="/campaigns" style={{ color: 'var(--muted)', fontSize: '0.875rem', textDecoration: 'none' }}>← Campaigns</a>
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
                  <span style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: '6px', padding: '4px 12px', fontSize: '0.8rem', color: 'var(--accent2)' }}>{ad.cta_button}</span>
                </div>
                {ev && <ScoreRing score={ev.aggregate_score} size={72} />}
              </div>
              {ev && (
                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
                    {dims.map(dim => {
                      const score = ev[dim]; const color = score >= 8 ? 'var(--accent)' : score >= 7 ? 'var(--warn)' : 'var(--danger)';
                      return (
                        <div key={dim} style={{ textAlign: 'center' }}>
                          <div className="mono" style={{ fontSize: '1rem', fontWeight: 700, color }}>{score?.toFixed(1)}</div>
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
