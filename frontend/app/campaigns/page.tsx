'use client';
import { useEffect, useState } from 'react';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetch(`${API}/campaigns`).then(r => r.json()).then(d => { setCampaigns(d.campaigns || []); setLoading(false); }).catch(() => setLoading(false));
  }, []);
  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><span className="mono" style={{ color: 'var(--accent)' }}>LOADING...</span></div>;
  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, margin: 0 }}>Campaigns</h1>
        <p style={{ color: 'var(--muted)', marginTop: '4px', fontSize: '0.875rem' }}>{campaigns.length} campaigns total</p>
      </div>
      <div style={{ display: 'grid', gap: '1rem' }}>
        {campaigns.map(c => (
          <a key={c.id} href={`/campaigns/${c.id}`} style={{ textDecoration: 'none' }}>
            <div className="card" style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600, marginBottom: '4px' }}>{c.name}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>{c.audience}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span className={`badge badge-${c.status}`}>{c.status}</span>
                <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>{c.ad_count ?? 0} ads</span>
                <span style={{ color: 'var(--accent2)' }}>→</span>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
