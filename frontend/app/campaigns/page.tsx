'use client';
import { useEffect, useState, useMemo } from 'react';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

function getCategories(product: string): string[] {
  const p = (product || '').toLowerCase();
  const cats: string[] = [];
  if (p.includes('sat')) cats.push('SAT Prep');
  if (p.includes('act')) cats.push('ACT Prep');
  if (p.includes('math')) cats.push('Math');
  if (p.includes('reading')) cats.push('Reading');
  if (cats.length === 0) cats.push('Other');
  return cats;
}

function getPersona(name: string): string | null {
  if (!name.includes(' \u2014 ')) return null;
  const persona = name.split(' \u2014 ')[0].trim();
  const skip = ['Weak CTA', 'Weak Value Proposition', 'Weak Emotional Resonance', 'Pipeline v2 Smoke Test', 'Pipeline Smoke Test', 'Regen Test', 'Test Campaign'];
  if (skip.includes(persona)) return null;
  return persona;
}

const CAT_COLORS: Record<string, string> = {
  'SAT Prep': '#6366f1',
  'ACT Prep': '#8b5cf6',
  'Math': '#0891b2',
  'Reading': '#059669',
  'Other': '#6b7280',
};

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/campaigns`).then(r => r.json()).then(d => { setCampaigns(d.campaigns || []); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const allCategories = useMemo(() => {
    const set = new Set<string>();
    campaigns.forEach(c => getCategories(c.product).forEach(cat => set.add(cat)));
    return ['SAT Prep', 'ACT Prep', 'Math', 'Reading', 'Other'].filter(c => set.has(c));
  }, [campaigns]);

  const filtered = useMemo(() => {
    if (!activeFilter) return campaigns;
    return campaigns.filter(c => getCategories(c.product).includes(activeFilter));
  }, [campaigns, activeFilter]);

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><span className="mono rainbow-text" style={{ fontWeight: 600 }}>LOADING...</span></div>;

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, margin: 0 }}><span className="rainbow-text">Campaigns</span></h1>
        <p style={{ color: 'var(--muted)', marginTop: '4px', fontSize: '0.875rem' }}>
          {activeFilter ? `${filtered.length} of ${campaigns.length}` : campaigns.length} campaigns{activeFilter ? ` in ${activeFilter}` : ' total'}
        </p>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <button
          onClick={() => setActiveFilter(null)}
          style={{
            padding: '6px 14px', borderRadius: '6px', border: '1px solid var(--border)',
            background: !activeFilter ? 'var(--text)' : 'var(--surface)',
            color: !activeFilter ? 'var(--bg)' : 'var(--muted)',
            cursor: 'pointer', fontSize: '0.8rem', fontWeight: 500,
          }}
        >All</button>
        {allCategories.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveFilter(activeFilter === cat ? null : cat)}
            style={{
              padding: '6px 14px', borderRadius: '6px', border: `1px solid ${CAT_COLORS[cat] || 'var(--border)'}`,
              background: activeFilter === cat ? CAT_COLORS[cat] : 'var(--surface)',
              color: activeFilter === cat ? '#fff' : CAT_COLORS[cat],
              cursor: 'pointer', fontSize: '0.8rem', fontWeight: 500,
            }}
          >{cat}</button>
        ))}
      </div>

      <div style={{ display: 'grid', gap: '1rem' }}>
        {filtered.map(c => {
          const cats = getCategories(c.product);
          const persona = getPersona(c.name);
          return (
            <a key={c.id} href={`/campaigns/${c.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div className="card" style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, marginBottom: '4px', color: 'var(--text)' }}>{c.name}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginBottom: '6px' }}>{c.audience}</div>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {cats.map(cat => (
                      <span key={cat} style={{
                        fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', fontWeight: 600,
                        background: `${CAT_COLORS[cat]}18`, color: CAT_COLORS[cat], border: `1px solid ${CAT_COLORS[cat]}40`,
                      }}>{cat}</span>
                    ))}
                    {persona && (
                      <span style={{
                        fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', fontWeight: 500,
                        background: 'var(--surface)', color: 'var(--muted)', border: '1px solid var(--border)',
                      }}>{persona}</span>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexShrink: 0 }}>
                  <span className={`badge badge-${c.status}`}>{c.status}</span>
                  <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>{c.ad_count ?? 0} ads</span>
                  <span style={{ color: 'var(--accent)', fontWeight: 600 }}>&rarr;</span>
                </div>
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}
