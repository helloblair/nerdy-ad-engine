'use client';
import { useEffect, useState } from 'react';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const gradients = [
  'linear-gradient(135deg, #f97316, #ec4899)',
  'linear-gradient(135deg, #a855f7, #6366f1)',
  'linear-gradient(135deg, #3b82f6, #06b6d4)',
  'linear-gradient(135deg, #ec4899, #a855f7)',
];

function ScoreBar({ score }: { score: number }) {
  const gradient = score >= 8
    ? 'linear-gradient(90deg, #a855f7, #6366f1)'
    : score >= 7
    ? 'linear-gradient(90deg, #f59e0b, #f97316)'
    : 'linear-gradient(90deg, #ef4444, #ec4899)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{ flex: 1, height: '6px', background: 'var(--surface2)', borderRadius: '3px' }}>
        <div style={{ width: `${score * 10}%`, height: '100%', background: gradient, borderRadius: '3px', transition: 'width 1s ease' }} />
      </div>
      <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text)', minWidth: '32px', fontWeight: 600 }}>{score.toFixed(1)}</span>
    </div>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([
      fetch(`${API}/analytics/trends`).then(r => r.json()),
      fetch(`${API}/campaigns`).then(r => r.json()),
    ]).then(([trendsData, campaignsData]) => {
      setSummary(trendsData.summary);
      setTrends(trendsData.trends || []);
      setCampaigns(campaignsData.campaigns || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);
  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><span className="mono rainbow-text" style={{ fontSize: '0.875rem', fontWeight: 600 }}>LOADING ENGINE DATA...</span></div>;
  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, margin: 0, letterSpacing: '-0.02em' }}>
          <span className="rainbow-text">Ad Engine</span> Dashboard
        </h1>
        <p style={{ color: 'var(--muted)', marginTop: '4px', fontSize: '0.875rem' }}>Autonomous content generation — Varsity Tutors / Nerdy</p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        {[
          { label: 'TOTAL ADS', value: summary?.total_ads ?? 0, gradient: gradients[0] },
          { label: 'AVG SCORE', value: summary?.overall_avg_score?.toFixed(1) ?? '—', gradient: gradients[1] },
          { label: 'PASS RATE', value: `${summary?.pass_rate ?? 0}%`, gradient: gradients[2] },
          { label: 'CAMPAIGNS', value: campaigns.length, gradient: gradients[3] },
        ].map(({ label, value, gradient }) => (
          <div key={label} className="card" style={{ position: 'relative', overflow: 'hidden' }}>
            <div className="stat-bar" style={{ background: gradient }} />
            <div className="mono" style={{ fontSize: '0.65rem', color: 'var(--muted)', letterSpacing: '0.1em', marginBottom: '8px' }}>{label}</div>
            <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text)' }}>{value}</div>
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '2rem' }}>
        <div className="card">
          <h2 style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: 0, marginBottom: '1rem', color: 'var(--muted)', letterSpacing: '0.05em' }}>CAMPAIGN PERFORMANCE</h2>
          {trends.length === 0 ? <p style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>No data yet</p> : trends.map((t, i) => {
            const camp = campaigns.find(c => c.id === t.campaign_id);
            return (
              <div key={i} style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text)' }}>{camp?.name ?? t.campaign_id.slice(0,16)}</span>
                  <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{t.ad_count} ads</span>
                </div>
                <ScoreBar score={t.avg_score} />
              </div>
            );
          })}
        </div>
        <div className="card">
          <h2 style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: 0, marginBottom: '1rem', color: 'var(--muted)', letterSpacing: '0.05em' }}>DIMENSION AVERAGES</h2>
          {trends.length === 0 ? <p style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>No data yet</p> : (() => {
            const dims = ['clarity', 'value_proposition', 'cta_score', 'brand_voice', 'emotional_resonance'];
            const avgs: Record<string, number> = {};
            dims.forEach(d => {
              const vals = trends.map(t => t.dimension_averages?.[d] ?? 0).filter(Boolean);
              avgs[d] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
            });
            return dims.map(dim => (
              <div key={dim} style={{ marginBottom: '1rem' }}>
                <div style={{ marginBottom: '4px' }}><span style={{ fontSize: '0.8rem', color: 'var(--text)', textTransform: 'capitalize' }}>{dim.replace(/_/g, ' ')}</span></div>
                <ScoreBar score={avgs[dim]} />
              </div>
            ));
          })()}
        </div>
      </div>
      <div className="card">
        <h2 style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: 0, marginBottom: '1rem', color: 'var(--muted)', letterSpacing: '0.05em' }}>RECENT CAMPAIGNS</h2>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
          <thead><tr style={{ borderBottom: '1px solid var(--border)' }}>
            {['Name','Goal','Status','Ads',''].map(h => <th key={h} style={{ textAlign: 'left', padding: '8px', color: 'var(--muted)', fontSize: '0.7rem', fontFamily: 'Space Mono', letterSpacing: '0.05em' }}>{h}</th>)}
          </tr></thead>
          <tbody>
            {campaigns.slice(0, 8).map(c => (
              <tr key={c.id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '10px 8px', fontWeight: 500 }}>{c.name}</td>
                <td style={{ padding: '10px 8px' }}><span className={`badge badge-${c.goal === 'conversion' ? 'conversion' : 'awareness'}`}>{c.goal}</span></td>
                <td style={{ padding: '10px 8px' }}><span className={`badge badge-${c.status}`}>{c.status}</span></td>
                <td style={{ padding: '10px 8px' }} className="mono">{c.ad_count ?? 0}</td>
                <td style={{ padding: '10px 8px' }}><a href={`/campaigns/${c.id}`} style={{ color: 'var(--accent)', fontSize: '0.75rem', textDecoration: 'none', fontWeight: 600 }}>View →</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
