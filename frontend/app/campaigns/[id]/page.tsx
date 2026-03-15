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

function AdImage({ imageUrl }: { imageUrl?: string }) {
  const [error, setError] = useState(false);
  if (!imageUrl || error) return null;
  const fullUrl = imageUrl.startsWith('http') ? imageUrl : `${API}${imageUrl}`;
  return (
    <img
      src={fullUrl}
      alt="Generated ad creative"
      onError={() => setError(true)}
      style={{ width: '100%', height: 'auto', display: 'block' }}
    />
  );
}

/* ── Facebook Ad Mockup ──────────────────────────────────────── */
function FacebookAdPreview({ ad }: { ad: any }) {
  const hasImage = !!ad.image_url;
  return (
    <div style={{
      background: 'var(--surface, #fff)',
      borderRadius: '12px',
      border: '1px solid var(--border)',
      overflow: 'hidden',
      width: '100%',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 14px' }}>
        <div style={{
          width: 36, height: 36, borderRadius: '50%',
          background: 'linear-gradient(135deg, #1a73e8, #34a853)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '12px', fontWeight: 700, color: '#fff', flexShrink: 0,
        }}>VT</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>Varsity Tutors</div>
          <div style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>Sponsored · 🌐</div>
        </div>
        <div style={{ color: 'var(--muted)', fontSize: '1rem' }}>···</div>
      </div>

      {/* Primary text */}
      <div style={{ padding: '0 14px 10px', fontSize: '0.8rem', lineHeight: 1.65, color: 'var(--text)' }}>
        {ad.primary_text}
      </div>

      {/* Image — full render */}
      {hasImage && (
        <div style={{ borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
          <AdImage imageUrl={ad.image_url} />
        </div>
      )}

      {/* Below-image bar */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '10px 14px', background: 'var(--surface2)',
      }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '0.6rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.02em' }}>varsitytutors.com</div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{ad.headline}</div>
          {ad.description && (
            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: '1px' }}>{ad.description}</div>
          )}
        </div>
        <button style={{
          flexShrink: 0, marginLeft: '10px',
          background: 'var(--accent, #1a73e8)', color: '#fff',
          border: 'none', borderRadius: '6px',
          padding: '7px 14px', fontSize: '0.75rem', fontWeight: 600, cursor: 'default',
        }}>{ad.cta_button}</button>
      </div>

      {/* Engagement */}
      <div style={{
        display: 'flex', justifyContent: 'space-around',
        padding: '7px 14px', borderTop: '1px solid var(--border)',
        color: 'var(--muted)', fontSize: '0.75rem',
      }}>
        <span>👍 Like</span>
        <span>💬 Comment</span>
        <span>↗ Share</span>
      </div>

      <div style={{ textAlign: 'center', padding: '5px', fontSize: '0.55rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', borderTop: '1px solid var(--border)' }}>
        Facebook Preview
      </div>
    </div>
  );
}

/* ── Instagram Ad Mockup ─────────────────────────────────────── */
function InstagramAdPreview({ ad }: { ad: any }) {
  const hasImage = !!ad.image_url;
  return (
    <div style={{
      background: 'var(--surface, #fff)',
      borderRadius: '12px',
      border: '1px solid var(--border)',
      overflow: 'hidden',
      width: '100%',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px' }}>
        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          background: 'linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '2px', flexShrink: 0,
        }}>
          <div style={{
            width: '100%', height: '100%', borderRadius: '50%',
            background: 'linear-gradient(135deg, #1a73e8, #34a853)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '10px', fontWeight: 700, color: '#fff',
          }}>VT</div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>varsitytutors</div>
          <div style={{ fontSize: '0.6rem', color: 'var(--muted)' }}>Sponsored</div>
        </div>
        <div style={{ color: 'var(--muted)', fontSize: '1rem' }}>···</div>
      </div>

      {/* Image — full render */}
      {hasImage && (
        <div>
          <AdImage imageUrl={ad.image_url} />
        </div>
      )}

      {/* Action icons */}
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px' }}>
        <div style={{ display: 'flex', gap: '14px', fontSize: '1.1rem' }}>
          <span>♡</span>
          <span>💬</span>
          <span>➤</span>
        </div>
        <span style={{ fontSize: '1.1rem' }}>🔖</span>
      </div>

      {/* Caption */}
      <div style={{ padding: '0 14px 8px', fontSize: '0.8rem', lineHeight: 1.6 }}>
        <span style={{ fontWeight: 600, marginRight: '6px' }}>varsitytutors</span>
        <span style={{ color: 'var(--text)' }}>{ad.primary_text}</span>
      </div>

      {/* CTA */}
      <div style={{ padding: '0 14px 10px' }}>
        <button style={{
          width: '100%',
          background: 'var(--accent, #1a73e8)', color: '#fff',
          border: 'none', borderRadius: '8px',
          padding: '9px 16px', fontSize: '0.8rem', fontWeight: 600, cursor: 'default',
        }}>{ad.cta_button}</button>
      </div>

      {/* Headline */}
      <div style={{ padding: '0 14px 12px' }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{ad.headline}</div>
        {ad.description && (
          <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '2px' }}>{ad.description}</div>
        )}
      </div>

      <div style={{ textAlign: 'center', padding: '5px', fontSize: '0.55rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', borderTop: '1px solid var(--border)' }}>
        Instagram Preview
      </div>
    </div>
  );
}

function DimScore({ label, score, color }: { label: string; score: number | null; color: string }) {
  if (score == null) return null;
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: '0.825rem', color: 'var(--muted)' }}>{label}</span>
      <span className="mono" style={{ fontSize: '0.95rem', fontWeight: 700, color }}>{score.toFixed(1)}</span>
    </div>
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

  const textDims: { key: string; label: string; color: string }[] = [
    { key: 'clarity', label: 'Clarity', color: '#fbbf24' },
    { key: 'value_proposition', label: 'Value Proposition', color: '#ec4899' },
    { key: 'cta_score', label: 'CTA Score', color: '#c850c0' },
    { key: 'brand_voice', label: 'Brand Voice', color: '#9b6cc8' },
    { key: 'emotional_resonance', label: 'Emotional Resonance', color: '#5b9be4' },
  ];
  const visualDims: { key: string; label: string; color: string }[] = [
    { key: 'visual_brand_consistency', label: 'Visual Brand Consistency', color: '#34d399' },
    { key: 'scroll_stopping_power', label: 'Scroll Stopping Power', color: '#06b6d4' },
  ];

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

      <div style={{ display: 'grid', gap: '2.5rem' }}>
        {ads.map((ad: any) => {
          const ev = ad.evaluation;
          const hasVisual = ev && (ev.visual_brand_consistency != null || ev.scroll_stopping_power != null);

          return (
            <div key={ad.id}>
              {/* Status badges */}
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '12px' }}>
                <span className={`badge badge-${ad.status}`}>{ad.status}</span>
                <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>iteration {ad.iteration_number}</span>
                {hasVisual && <span style={{ fontSize: '0.65rem', background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: '4px', padding: '2px 8px', color: '#34d399', fontWeight: 500 }}>v2 visual</span>}
              </div>

              {/* Three-column: FB mockup | IG mockup | Evaluation */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: ev ? '1fr 1fr 1fr' : '1fr 1fr',
                gap: '1.25rem',
                alignItems: 'stretch',
              }}>
                {/* ── Facebook ── */}
                <FacebookAdPreview ad={ad} />

                {/* ── Instagram ── */}
                <InstagramAdPreview ad={ad} />

                {/* ── Evaluation Panel ── */}
                {ev && (
                  <div className="card" style={{
                    padding: '1.5rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '20px',
                  }}>
                    {/* Aggregate score */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <ScoreRing score={ev.aggregate_score} size={60} />
                      <div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          {hasVisual ? '7-Dimension Score' : '5-Dimension Score'}
                        </div>
                        <div style={{ fontSize: '0.9rem', color: ev.meets_threshold ? '#34d399' : '#f97316', fontWeight: 600 }}>
                          {ev.meets_threshold ? '✓ Passes threshold' : '✗ Below threshold'}
                        </div>
                      </div>
                    </div>

                    {/* Radar chart */}
                    <div>
                      <RadarChart scores={{
                        clarity: ev.clarity ?? 0,
                        value_proposition: ev.value_proposition ?? 0,
                        cta_score: ev.cta_score ?? 0,
                        brand_voice: ev.brand_voice ?? 0,
                        emotional_resonance: ev.emotional_resonance ?? 0,
                      }} />
                    </div>

                    {/* Text dimensions */}
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px', fontWeight: 600 }}>
                        Text Dimensions
                      </div>
                      {textDims.map(({ key, label, color }) => (
                        <DimScore key={key} label={label} score={ev[key]} color={color} />
                      ))}
                    </div>

                    {/* Visual dimensions */}
                    {hasVisual && (
                      <div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px', fontWeight: 600 }}>
                          Visual Dimensions
                        </div>
                        {visualDims.map(({ key, label, color }) => (
                          <DimScore key={key} label={label} score={ev[key]} color={color} />
                        ))}
                      </div>
                    )}

                    {/* Weakest dimension */}
                    {ev.weakest_dimension && (
                      <div style={{
                        padding: '12px',
                        background: 'var(--surface2)',
                        borderRadius: '8px',
                        border: '1px solid var(--border)',
                      }}>
                        <div style={{ fontSize: '0.7rem', color: '#f97316', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px', fontWeight: 600 }}>
                          ⚠ Weakest: {ev.weakest_dimension.replace(/_/g, ' ')}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--muted)', lineHeight: 1.6 }}>
                          {ev.improvement_suggestion || 'No suggestion available'}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
