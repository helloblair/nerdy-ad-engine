'use client';
import { useEffect, useState } from 'react';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
export default function Insights() {
  const [matrix, setMatrix] = useState<any>(null);
  const [trends, setTrends] = useState<any>(null);
  const [costData, setCostData] = useState<any>(null);
  const [iterData, setIterData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([
      fetch(`${API}/analytics/confusion-matrix`).then(r => r.json()),
      fetch(`${API}/analytics/trends`).then(r => r.json()),
      fetch(`${API}/analytics/cost`).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(`${API}/analytics/iterations`).then(r => r.ok ? r.json() : null).catch(() => null),
    ]).then(([m, t, c, it]) => { setMatrix(m); setTrends(t); setCostData(c); setIterData(it); setLoading(false); }).catch(() => setLoading(false));
  }, []);
  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><span className="mono rainbow-text" style={{ fontWeight: 600 }}>LOADING...</span></div>;
  const m = matrix?.matrix || {}; const metrics = matrix?.metrics || {}; const total = matrix?.total_ratings || 0;
  return (
    <div>
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 600, margin: 0 }}><span className="rainbow-text">Insights</span></h1>
          <p style={{ color: 'var(--muted)', marginTop: '4px', fontSize: '0.875rem' }}>Confusion matrix — AI evaluator vs human judgment</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="nav-btn"
            onClick={async () => {
              try {
                const res = await fetch(`${API}/analytics/report`);
                const data = await res.json();
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = 'report.json'; a.click();
                URL.revokeObjectURL(url);
              } catch (e) { console.error('Export failed', e); }
            }}
          >Export JSON</button>
          <button
            className="nav-btn"
            onClick={() => { window.open(`${API}/analytics/export/csv`, '_blank'); }}
          >Export CSV</button>
        </div>
      </div>
      {total === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>📊</div>
          <h2 style={{ fontWeight: 600, marginBottom: '8px' }}>No ratings yet</h2>
          <p style={{ color: 'var(--muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>Share the survey link with your cohort to collect human ratings.</p>
          <a href="/survey" className="nav-btn rainbow-text" style={{ padding: '10px 24px', textDecoration: 'none', fontWeight: 700, fontSize: '0.875rem' }}>Go to Survey →</a>
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
            {[
              { label: 'PRECISION', value: `${(metrics.precision * 100).toFixed(1)}%`, sub: 'when AI approves, human agrees', gradient: 'linear-gradient(135deg, #c850c0, #9b6cc8)', color: '#c850c0' },
              { label: 'RECALL', value: `${(metrics.recall * 100).toFixed(1)}%`, sub: 'when human likes, AI caught it', gradient: 'linear-gradient(135deg, #5b9be4, #00d4cf)', color: '#5b9be4' },
              { label: 'ACCURACY', value: `${(metrics.accuracy * 100).toFixed(1)}%`, sub: `from ${total} human ratings`, gradient: 'linear-gradient(135deg, #fbbf24, #f97316)', color: '#f97316' },
              { label: 'AVG COST / AD', value: costData ? `$${costData.avg_cost_per_ad.toFixed(4)}` : '$—', sub: costData ? `${costData.ads_analyzed} ads analyzed` : 'loading...', gradient: 'linear-gradient(135deg, #16a34a, #00d4cf)', color: '#16a34a' },
              { label: 'TOTAL API SPEND', value: costData ? `$${costData.total_spend_usd.toFixed(2)}` : '$—', sub: costData ? `gemini $${costData.cost_by_model.gemini_flash.toFixed(2)} · claude $${costData.cost_by_model.claude_sonnet.toFixed(2)}` : 'loading...', gradient: 'linear-gradient(135deg, #f06c6c, #ec4899)', color: '#f06c6c' },
            ].map(({ label, value, sub, gradient, color }) => (
              <div key={label} className="card" style={{ textAlign: 'center', position: 'relative' }}>
                <div className="stat-bar" style={{ background: gradient }} />
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
                { label: 'True Positive', sublabel: 'Human ✓ AI ✓', value: m.true_positive ?? 0, bgVar: 'var(--green-bg)', borderVar: 'var(--green-border)', colorVar: 'var(--green-text)' },
                { label: 'False Positive', sublabel: 'Human ✗ AI ✓', value: m.false_positive ?? 0, bgVar: 'var(--red-bg)', borderVar: 'var(--red-border)', colorVar: 'var(--red-text)' },
                { label: 'False Negative', sublabel: 'Human ✓ AI ✗', value: m.false_negative ?? 0, bgVar: 'var(--amber-bg)', borderVar: 'var(--amber-border)', colorVar: 'var(--amber-text)' },
                { label: 'True Negative', sublabel: 'Human ✗ AI ✗', value: m.true_negative ?? 0, bgVar: 'var(--green-bg)', borderVar: 'var(--green-border)', colorVar: 'var(--green-text)' },
              ].map(({ label, sublabel, value, bgVar, borderVar, colorVar }) => (
                <div key={label} className="card" style={{ background: bgVar, border: `2px solid ${borderVar}`, borderRadius: '12px', padding: '1.5rem', textAlign: 'center' }}>
                  <div className="mono" style={{ fontSize: '2.5rem', fontWeight: 700, color: colorVar }}>{value}</div>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem', marginTop: '4px', color: 'var(--text)' }}>{label}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '2px' }}>{sublabel}</div>
                  {total > 0 && <div className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '4px' }}>{((value / total) * 100).toFixed(1)}%</div>}
                </div>
              ))}
            </div>
            <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
              <span
                title="How to read this: High False Positives = AI too lenient. High False Negatives = AI too strict. Target is high precision — when AI approves, humans should agree."
                style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '24px', height: '24px', borderRadius: '50%', background: 'var(--surface2)', border: '1px solid var(--border)', cursor: 'help', fontSize: '0.75rem', fontWeight: 700, color: 'var(--muted)', fontStyle: 'italic', fontFamily: 'Georgia, serif', transition: 'border-color 0.2s, color 0.2s' }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--muted)'; }}
              >i</span>
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
                    <div style={{ background: 'var(--amber-bg)', border: '2px solid var(--amber-border)', borderRadius: '10px', padding: '12px 20px' }}>
                      <span style={{ color: 'var(--amber-text)', fontWeight: 700, textTransform: 'capitalize' }}>{weakest.replace(/_/g, ' ')}</span>
                    </div>
                    <div>
                      <div className="mono" style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--amber-text)' }}>{avgs[weakest].toFixed(1)}/10</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>avg across all campaigns</div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
          {iterData?.summary?.total_campaigns > 0 && (
            <div className="card" style={{ marginTop: '2rem' }}>
              <h2 style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: 0, marginBottom: '1.5rem', color: 'var(--muted)', letterSpacing: '0.05em' }}>ITERATION IMPROVEMENT</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
                {[
                  { label: 'ITER 1 AVG', value: iterData.summary.avg_score_iter1?.toFixed(1) ?? '—', gradient: 'linear-gradient(135deg, #f06c6c, #ec4899)', color: '#f06c6c' },
                  { label: 'ITER 3 AVG', value: iterData.summary.avg_score_iter3?.toFixed(1) ?? '—', gradient: 'linear-gradient(135deg, #16a34a, #00d4cf)', color: '#16a34a' },
                  { label: 'TOTAL LIFT', value: `+${iterData.summary.total_lift?.toFixed(1) ?? '0'} pts`, gradient: 'linear-gradient(135deg, #5b9be4, #c850c0)', color: '#16a34a' },
                ].map(({ label, value, gradient, color }) => (
                  <div key={label} className="card" style={{ textAlign: 'center', position: 'relative' }}>
                    <div className="stat-bar" style={{ background: gradient }} />
                    <div className="mono" style={{ fontSize: '0.65rem', color: 'var(--muted)', letterSpacing: '0.1em', marginBottom: '8px' }}>{label}</div>
                    <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color }}>{value}</div>
                  </div>
                ))}
              </div>
              {iterData.campaigns?.length > 0 && (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--border)' }}>
                      {['Campaign', 'Start', 'End', 'Lift', 'Key Weakness'].map(h => (
                        <th key={h} className="mono" style={{ padding: '8px 12px', textAlign: 'left', fontSize: '0.7rem', color: 'var(--muted)', letterSpacing: '0.05em' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {iterData.campaigns.map((c: any, i: number) => {
                      const allAds = c.ads || [];
                      const starts = allAds.map((a: any) => a.iterations?.[0]?.score ?? 0);
                      const ends = allAds.map((a: any) => a.iterations?.[a.iterations.length - 1]?.score ?? 0);
                      const avgStart = starts.length ? (starts.reduce((a: number, b: number) => a + b, 0) / starts.length) : 0;
                      const avgEnd = ends.length ? (ends.reduce((a: number, b: number) => a + b, 0) / ends.length) : 0;
                      const lift = avgEnd - avgStart;
                      return (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td style={{ padding: '10px 12px', fontWeight: 500 }}>{c.campaign_name}</td>
                          <td className="mono" style={{ padding: '10px 12px' }}>{avgStart.toFixed(1)}</td>
                          <td className="mono" style={{ padding: '10px 12px', fontWeight: 600, color: avgEnd >= 7.0 ? '#16a34a' : 'var(--text)' }}>{avgEnd.toFixed(1)}</td>
                          <td className="mono" style={{ padding: '10px 12px', color: lift > 0 ? '#16a34a' : 'var(--text)', fontWeight: 600 }}>{lift > 0 ? '+' : ''}{lift.toFixed(1)}</td>
                          <td style={{ padding: '10px 12px', textTransform: 'capitalize', color: 'var(--muted)' }}>{(c.expected_weakness || '').replace(/_/g, ' ')}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
