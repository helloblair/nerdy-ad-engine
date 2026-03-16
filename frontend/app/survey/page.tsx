'use client';
import { useEffect, useState } from 'react';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
export default function Survey() {
  const [ads, setAds] = useState<any[]>([]);
  const [current, setCurrent] = useState(0);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [ratings, setRatings] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetch(`${API}/campaigns`).then(r => r.json()).then(async data => {
      const allAds: any[] = [];
      for (const camp of (data.campaigns || []).slice(0, 5)) {
        const detail = await fetch(`${API}/campaigns/${camp.id}`).then(r => r.json());
        const ratable = (detail.ads || []).filter((a: any) => a.status === 'approved' || a.status === 'flagged');
        allAds.push(...ratable.slice(0, 3));
      }
      setAds(allAds.sort(() => Math.random() - 0.5).slice(0, 10));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);
  const handleRate = async (rating: string) => {
    const ad = ads[current];
    setSubmitting(true);
    setRatings(prev => ({ ...prev, [ad.id]: rating }));
    try { await fetch(`${API}/ads/${ad.id}/rate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ rating }) }); } catch {}
    setSubmitting(false);
    if (current + 1 >= ads.length) setDone(true);
    else setCurrent(prev => prev + 1);
  };
  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><span className="mono rainbow-text" style={{ fontWeight: 600 }}>LOADING ADS...</span></div>;
  if (done) return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: '1rem', textAlign: 'center' }}>
      <div style={{ fontSize: '3rem' }}>🎉</div>
      <h2 className="rainbow-text" style={{ fontSize: '1.5rem', fontWeight: 600, margin: 0 }}>Thanks for rating!</h2>
      <p style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>You rated {Object.keys(ratings).length} ads. Your responses build our confusion matrix.</p>
      <a href="/insights" style={{ marginTop: '8px', color: 'var(--accent)', fontSize: '0.875rem', fontWeight: 600, textDecoration: 'none' }}>View confusion matrix →</a>
    </div>
  );
  if (ads.length === 0) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><p style={{ color: 'var(--muted)' }}>No ads to rate yet — run the scale script first.</p></div>;
  const ad = ads[current];
  const progress = (current / ads.length) * 100;
  return (
    <div>
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 600, margin: '0 0 4px' }}><span className="rainbow-text">Ad Rating</span> Survey</h1>
        <p style={{ color: 'var(--muted)', fontSize: '0.875rem', margin: 0 }}>Would this ad make you click? Takes ~3 minutes.</p>
      </div>
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Ad {current + 1} of {ads.length}</span>
          <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--accent)', fontWeight: 600 }}>{Math.round(progress)}%</span>
        </div>
        <div style={{ height: '6px', background: 'var(--surface2)', borderRadius: '3px', overflow: 'hidden', outline: '1px solid var(--border)', outlineOffset: '1px' }}>
          <div className="progress-rainbow" style={{ width: `${progress}%`, transition: 'width 0.3s ease' }} />
        </div>
      </div>
      <div className="card" style={{ marginBottom: '1.5rem', padding: '2rem' }}>
        <div style={{ marginBottom: '12px' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--muted)', fontFamily: 'Space Mono', letterSpacing: '0.1em' }}>HEADLINE</span>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: '4px 0 0' }}>{ad.headline}</h2>
        </div>
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '12px', marginBottom: '12px' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--muted)', fontFamily: 'Space Mono', letterSpacing: '0.1em' }}>AD COPY</span>
          <p style={{ color: 'var(--text)', fontSize: '0.95rem', lineHeight: 1.7, margin: '4px 0 0' }}>{ad.primary_text}</p>
        </div>
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '12px' }}>
          <span style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: '8px', padding: '6px 16px', fontSize: '0.875rem', color: 'var(--accent)', fontWeight: 500, display: 'inline-block' }}>{ad.cta_button}</span>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
        {[
          { rating: 'good', label: '👍 Yes', bgVar: 'var(--green-bg)', borderVar: 'var(--green-border)', textVar: 'var(--green-text)' },
          { rating: 'unsure', label: '🤷 Maybe', bgVar: 'var(--amber-bg)', borderVar: 'var(--amber-border)', textVar: 'var(--amber-text)' },
          { rating: 'bad', label: '👎 No', bgVar: 'var(--red-bg)', borderVar: 'var(--red-border)', textVar: 'var(--red-text)' },
        ].map(({ rating, label, bgVar, borderVar, textVar }) => (
          <button key={rating} className="rating-btn" onClick={() => handleRate(rating)} disabled={submitting}
            style={{ background: bgVar, border: `2px solid ${borderVar}`, borderRadius: '12px', padding: '1rem', cursor: submitting ? 'wait' : 'pointer', color: textVar, fontSize: '1rem', fontWeight: 600, fontFamily: 'DM Sans, sans-serif', opacity: submitting ? 0.6 : 1 }}>
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
