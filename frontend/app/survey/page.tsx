'use client';
import { useEffect, useState } from 'react';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
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
        const approved = (detail.ads || []).filter((a: any) => a.status === 'approved');
        allAds.push(...approved.slice(0, 3));
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
  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><span className="mono" style={{ color: 'var(--accent)' }}>LOADING ADS...</span></div>;
  if (done) return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: '1rem', textAlign: 'center' }}>
      <div style={{ fontSize: '3rem' }}>🎉</div>
      <h2 style={{ fontSize: '1.5rem', fontWeight: 600, margin: 0 }}>Thanks for rating!</h2>
      <p style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>You rated {Object.keys(ratings).length} ads. Your responses build our confusion matrix.</p>
      <a href="/insights" style={{ marginTop: '8px', color: 'var(--accent2)', fontSize: '0.875rem' }}>View confusion matrix →</a>
    </div>
  );
  if (ads.length === 0) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><p style={{ color: 'var(--muted)' }}>No ads to rate yet — run the scale script first.</p></div>;
  const ad = ads[current];
  return (
    <div style={{ maxWidth: '600px', margin: '0 auto' }}>
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 600, margin: '0 0 4px' }}>Ad Rating Survey</h1>
        <p style={{ color: 'var(--muted)', fontSize: '0.875rem', margin: 0 }}>Would this ad make you click? Takes ~3 minutes.</p>
      </div>
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Ad {current + 1} of {ads.length}</span>
          <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--accent)' }}>{Math.round((current / ads.length) * 100)}%</span>
        </div>
        <div style={{ height: '4px', background: 'var(--border)', borderRadius: '2px' }}>
          <div style={{ width: `${(current / ads.length) * 100}%`, height: '100%', background: 'var(--accent)', borderRadius: '2px', transition: 'width 0.3s ease' }} />
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
          <span style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: '6px', padding: '6px 16px', fontSize: '0.875rem', color: 'var(--accent2)', display: 'inline-block' }}>{ad.cta_button}</span>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        {[
          { rating: 'good', label: '👍 Yes', color: 'var(--accent)', bg: '#00e5a015', border: '#00e5a040' },
          { rating: 'unsure', label: '🤷 Maybe', color: 'var(--warn)', bg: '#f59e0b15', border: '#f59e0b40' },
          { rating: 'bad', label: '👎 No', color: 'var(--danger)', bg: '#ef444415', border: '#ef444440' },
        ].map(({ rating, label, color, bg, border }) => (
          <button key={rating} onClick={() => handleRate(rating)} disabled={submitting}
            style={{ background: bg, border: `1px solid ${border}`, borderRadius: '10px', padding: '1rem', cursor: submitting ? 'wait' : 'pointer', color, fontSize: '1rem', fontWeight: 600, fontFamily: 'DM Sans, sans-serif', opacity: submitting ? 0.6 : 1 }}>
            {label}
          </button>
        ))}
      </div>
      <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--muted)', marginTop: '1.5rem' }}>Imagine you're a parent with a child aged 8–18. Would you click this ad?</p>
    </div>
  );
}
