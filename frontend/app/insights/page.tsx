'use client';
import { useEffect, useState } from 'react';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export default function Insights() {
  const [matrix, setMatrix] = useState<any>(null);
  const [trends, setTrends] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([
      fetch(`${API}/analytics/confusion-matrix`).then(r => r.json()),
      fetch(`${API}/analytics/trends`).then(r => r.json()),
    ]).then(([m, t]) => { setMatrix(m); setTrends(t); setLoading(false); }).catch(() => setLoading(false));
  }, []);
  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><span className="mono" style={{ color: 'var(--accent)' }}>LOADING...</span></div>;
  const m = matrix?.matrix || {}; const metrics = matrix?.metrics || {}; const total = matrix?.total_ratings || 0;
  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, margin: 0 }}>Insights</h1>
        <p style={{ color: 'var(--muted)', marginTop: '4px', fontSize: '0.875rem' }}>Confusion matrix — AI evaluator vs human judgment</p>
      </div>
      {total === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>📊</div>
          <h2 style={{ fontWeight: 600, marginBottom: '8px' }}>No ratings yet</h2>
          <p style={{ color: 'var(--muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>Share the survey link with your cohort to collect human ratings.</p>
          <a href="/survey" style={{ background: 'var(--accent)', color: 'var(--bg)', padding: '10px 24px', borderRadius: '8px', textDecoration: 'none', fontWeight: 600, fontSize: '0.875rem' }}>Go to Survey →</a>
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
            {[
              { label: 'PRECISION', value: `${(metrics.precision * 100).toFixed(1)}%`, sub: 'when AI approves, human agrees', color: 'var(--accent)' },
              { label: 'RECALL', value: `${(metrics.recall * 100).toFixed(1)}%`, sub: 'when human likes, AI caught it', color: 'var(--accent2)' },
              { label: 'ACCURACY', value: `${(metrics.accuracy * 100).toFixed(1)}%`, sub: `from ${total} human ratings`, color: 'var(--warn)' },
            ].map(({ label, value, sub, color }) => (
              <div key={label} className="card" style={{ textAlign: 'center' }}>
                <div className="mono" style={{ fontSize: '0.65rem', color: 'var(--muted)', letterSpacing: '0.1em', marginBottom: '8px' }}>{label}</div>
                <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color }}>{value}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '4px' }}>{sub}</div>
              </div>
            ))}
          </div>
          <div className="card" style={{ marginBottom: '2rem' }}>
            <h2 style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: 0, marginBottom: '1.5rem', color: 'var(--muted)', letterSpacing: '0.05em' }}>CONFUSION MATRIX — {total} RATINGS</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', maxWidth: '500px' }}>
              {[
                { label: 'True Positive', sublabel: 'Human ✓ AI ✓', value: m.true_positive ?? 0, color: 'var(--accent)' },
                { label: 'False Positive', sublabel: 'Human ✗ AI ✓', value: m.false_positive ?? 0, color: 'var(--danger)' },
                { label: 'False Negative', sublabel: 'Human ✓ AI ✗', value: m.false_negative ?? 0, color: 'var(--warn)' },
                { label: 'True Negative', sublabel: 'Human ✗ AI ✗', value: m.true_negative ?? 0, color: 'var(--accent)' },
              ].map(({ label, sublabel, value, color }) => (
                <div key={label} style={{ background: 'var(--surface2)', border: `1px solid ${color}30`, borderRadius: '10px', padding: '1.5rem', textAlign: 'center' }}>
                  <div className="mono" style={{ fontSize: '2.5rem', fontWeight: 700, color }}>{value}</div>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem', marginTop: '4px' }}>{label}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '2px' }}>{sublabel}</div>
                  {total > 0 && <div className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '4px' }}>{((value / total) * 100).toFixed(1)}%</div>}
                </div>
              ))}
            </div>
            <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'var(--surface2)', borderRadius: '8px', fontSize: '0.8rem', color: 'var(--muted)', lineHeight: 1.6 }}>
              <strong style={{ color: 'var(--text)' }}>How to read this:</strong> High False Positives = AI too lenient. High False Negatives = AI too strict. Target is high precision — when AI approves, humans should agree.
            </div>
          </div>
          {trends?.trends?.length > 0 && (
            <div className="card">
              <h2 style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: 0, marginBottom: '1rem', color: 'var(--muted)', letterSpacing: '0.05em' }}>PERSISTENT WEAKNESS</h2>
              {(() => {
                const dims = ['clarity', 'value_proposition', 'cta_score', 'brand_voice', 'emotional_resonance'];
                const avgs: Record<string, number> = {};
                dims.forEach(d => {
                  const vals = trends.trends.map((t: any) => t.dimension_averages?.[d] ?? 0).filter(Boolean);
                  avgs[d] = vals.length ? vals.reduce((a: number, b: number) => a + b, 0) / vals.length : 0;
                });
                const weakest = dims.reduce((a, b) => avgs[a] < avgs[b] ? a : b);
                return (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{ background: '#ef444415', border: '1px solid #ef444430', borderRadius: '8px', padding: '12px 20px' }}>
                      <span style={{ color: 'var(--danger)', fontWeight: 700, textTransform: 'capitalize' }}>{weakest.replace(/_/g, ' ')}</span>
                    </div>
                    <div>
                      <div className="mono" style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--danger)' }}>{avgs[weakest].toFixed(1)}/10</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>avg across all campaigns</div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </>
      )}
    </div>
  );
}
