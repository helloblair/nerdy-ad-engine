'use client';
import { useEffect, useState, useMemo } from 'react';
import ScoreRing from '../components/ScoreRing';
import { useEvalConfig, scoreColor, scoreBg, dimLabel } from '../hooks/useEvalConfig';
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

const PERSONA_COLORS_LIGHT = [
  '#c850c0', '#e06898', '#d97706', '#0891b2', '#7c3aed',
  '#059669', '#dc2626', '#6366f1', '#0d9488', '#b45309',
  '#8b5cf6', '#db2777', '#2563eb', '#ca8a04', '#16a34a',
];

const PERSONA_COLORS_DARK = [
  '#e879de', '#f7a0c0', '#fbbf24', '#22d3ee', '#a78bfa',
  '#34d399', '#f87171', '#818cf8', '#2dd4bf', '#f59e0b',
  '#c4b5fd', '#f472b6', '#60a5fa', '#fcd34d', '#4ade80',
];

function personaColor(persona: string, allPersonas: string[], isDark: boolean): string {
  const idx = allPersonas.indexOf(persona);
  const palette = isDark ? PERSONA_COLORS_DARK : PERSONA_COLORS_LIGHT;
  return palette[idx % palette.length];
}

/* ── Mini Score Ring ─────────────────────────────────────────── */
/* ScoreRing imported from ../components/ScoreRing */

/* ── Dimension Mini Bar ──────────────────────────────────────── */
function DimBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.65rem' }}>
      <span style={{ color: 'var(--muted)', width: '28px', textAlign: 'right', flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, height: '4px', borderRadius: '2px', background: 'var(--surface2)', overflow: 'hidden' }}>
        <div style={{ width: `${(score / 10) * 100}%`, height: '100%', borderRadius: '2px', background: color, transition: 'width 0.3s' }} />
      </div>
      <span className="mono" style={{ fontSize: '0.6rem', color, fontWeight: 600, width: '22px' }}>{score.toFixed(1)}</span>
    </div>
  );
}

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [ads, setAds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'campaigns' | 'ads'>('ads');
  const [catFilter, setCatFilter] = useState<string | null>(null);
  const [personaFilter, setPersonaFilter] = useState<string | null>(null);
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/campaigns`).then(r => r.json()),
      fetch(`${API}/ads`).then(r => r.json()),
    ]).then(([campData, adsData]) => {
      setCampaigns(campData.campaigns || []);
      setAds(adsData.ads || []);
      setLoading(false);
    }).catch(() => setLoading(false));

    const check = () => setIsDark(document.documentElement.getAttribute('data-theme') === 'dark');
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => obs.disconnect();
  }, []);

  // Categories from campaigns (for campaign view) and ads (for ad view)
  const allCategories = useMemo(() => {
    const set = new Set<string>();
    if (view === 'campaigns') {
      campaigns.forEach(c => getCategories(c.product).forEach(cat => set.add(cat)));
    } else {
      ads.forEach(a => getCategories(a.campaign_product || '').forEach(cat => set.add(cat)));
    }
    return ['SAT Prep', 'ACT Prep', 'Math', 'Reading', 'Other'].filter(c => set.has(c));
  }, [campaigns, ads, view]);

  const allPersonas = useMemo(() => {
    const set = new Set<string>();
    const names = view === 'campaigns'
      ? campaigns.map(c => c.name)
      : ads.map(a => a.campaign_name || '');
    names.forEach(n => {
      const p = getPersona(n);
      if (p) set.add(p);
    });
    return Array.from(set).sort();
  }, [campaigns, ads, view]);

  const filteredCampaigns = useMemo(() => {
    return campaigns.filter(c => {
      if (catFilter && !getCategories(c.product).includes(catFilter)) return false;
      if (personaFilter && getPersona(c.name) !== personaFilter) return false;
      return true;
    });
  }, [campaigns, catFilter, personaFilter]);

  const filteredAds = useMemo(() => {
    return ads.filter(a => {
      if (catFilter && !getCategories(a.campaign_product || '').includes(catFilter)) return false;
      if (personaFilter && getPersona(a.campaign_name || '') !== personaFilter) return false;
      return true;
    });
  }, [ads, catFilter, personaFilter]);

  const activeFilterLabel = [catFilter, personaFilter].filter(Boolean).join(' + ') || null;
  const displayCount = view === 'campaigns' ? filteredCampaigns.length : filteredAds.length;
  const totalCount = view === 'campaigns' ? campaigns.length : ads.length;

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><span className="mono rainbow-text" style={{ fontWeight: 600 }}>LOADING...</span></div>;

  return (
    <div>
      {/* Header with view toggle */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 600, margin: 0 }}><span className="rainbow-text">Campaigns</span></h1>
          <p style={{ color: 'var(--muted)', marginTop: '4px', fontSize: '0.875rem' }}>
            {activeFilterLabel ? `${displayCount} of ${totalCount}` : `${totalCount}`}
            {view === 'ads' ? ' ads' : ' campaigns'}
            {activeFilterLabel ? ` matching ${activeFilterLabel}` : ' total'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border)' }}>
          {(['campaigns', 'ads'] as const).map(v => (
            <button
              key={v}
              onClick={() => setView(v)}
              style={{
                padding: '6px 14px', border: 'none', cursor: 'pointer',
                fontSize: '0.75rem', fontWeight: 600, textTransform: 'capitalize',
                background: view === v ? 'var(--text)' : 'var(--surface)',
                color: view === v ? 'var(--bg)' : 'var(--muted)',
              }}
            >{v === 'ads' ? `All Ads (${ads.length})` : 'Campaigns'}</button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '0.75rem 1rem', marginBottom: '1.5rem', alignItems: 'start' }}>
        <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)', fontWeight: 600, letterSpacing: '0.05em', lineHeight: '28px', whiteSpace: 'nowrap' }}>TYPE</span>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setCatFilter(null)}
            style={{
              padding: '5px 12px', borderRadius: '6px', border: '1px solid var(--border)',
              background: !catFilter ? 'var(--text)' : 'var(--surface)',
              color: !catFilter ? 'var(--bg)' : 'var(--muted)',
              cursor: 'pointer', fontSize: '0.75rem', fontWeight: 500,
            }}
          >All</button>
          {allCategories.map(cat => (
            <button
              key={cat}
              onClick={() => setCatFilter(catFilter === cat ? null : cat)}
              style={{
                padding: '5px 12px', borderRadius: '6px', border: `1px solid ${CAT_COLORS[cat] || 'var(--border)'}`,
                background: catFilter === cat ? CAT_COLORS[cat] : 'var(--surface)',
                color: catFilter === cat ? '#fff' : CAT_COLORS[cat],
                cursor: 'pointer', fontSize: '0.75rem', fontWeight: 500,
              }}
            >{cat}</button>
          ))}
        </div>

        <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)', fontWeight: 600, letterSpacing: '0.05em', lineHeight: '28px', whiteSpace: 'nowrap' }}>PERSONA</span>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setPersonaFilter(null)}
            style={{
              padding: '5px 12px', borderRadius: '6px', border: '1px solid var(--border)',
              background: !personaFilter ? 'var(--text)' : 'var(--surface)',
              color: !personaFilter ? 'var(--bg)' : 'var(--muted)',
              cursor: 'pointer', fontSize: '0.75rem', fontWeight: 500,
            }}
          >All</button>
          {allPersonas.map(p => {
            const pc = personaColor(p, allPersonas, isDark);
            const active = personaFilter === p;
            return (
              <button
                key={p}
                onClick={() => setPersonaFilter(active ? null : p)}
                style={{
                  padding: '5px 12px', borderRadius: '6px', border: `1px solid ${active ? pc : pc + '40'}`,
                  background: active ? pc : 'var(--surface)',
                  color: active ? '#fff' : pc,
                  cursor: 'pointer', fontSize: '0.75rem', fontWeight: 500,
                }}
              >{p}</button>
            );
          })}
        </div>
      </div>

      {/* ─── Campaign Card View ─── */}
      {view === 'campaigns' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.25rem' }}>
          {filteredCampaigns.map(c => {
            const cats = getCategories(c.product);
            const persona = getPersona(c.name);
            const imgSrc = c.thumbnail ? `${API}${c.thumbnail}` : null;
            return (
              <a key={c.id} href={`/campaigns/${c.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="card" style={{ cursor: 'pointer', padding: 0, display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ position: 'relative', width: '100%', aspectRatio: '16 / 10', background: 'var(--surface2)', overflow: 'hidden', borderRadius: '16px 16px 0 0' }}>
                    {imgSrc ? (
                      <img src={imgSrc} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                    ) : (
                      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: '0.8rem', fontWeight: 500 }}>No image</div>
                    )}
                    {c.status !== 'completed' && (
                      <div style={{ position: 'absolute', top: '10px', right: '10px' }}>
                        <span className={`badge badge-${c.status}`}>{c.status}</span>
                      </div>
                    )}
                  </div>
                  <div style={{ padding: '1rem 1.25rem', flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text)', lineHeight: 1.3 }}>{c.name}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted)', lineHeight: 1.4 }}>{c.audience}</div>
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: 'auto' }}>
                      {cats.map(cat => (
                        <span key={cat} style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', fontWeight: 600, background: `${CAT_COLORS[cat]}18`, color: CAT_COLORS[cat], border: `1px solid ${CAT_COLORS[cat]}40` }}>{cat}</span>
                      ))}
                      {persona && (() => {
                        const pc = personaColor(persona, allPersonas, isDark);
                        return <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', fontWeight: 600, background: `${pc}18`, color: pc, border: `1px solid ${pc}40` }}>{persona}</span>;
                      })()}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px', paddingTop: '8px', borderTop: '1px solid var(--border)' }}>
                      <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{c.ad_count ?? 0} ad{(c.ad_count ?? 0) !== 1 ? 's' : ''}</span>
                      <span style={{ color: 'var(--accent)', fontWeight: 600, fontSize: '0.8rem' }}>&rarr;</span>
                    </div>
                  </div>
                </div>
              </a>
            );
          })}
        </div>
      )}

      {/* ─── All Ads Grid View ─── */}
      {view === 'ads' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
          {filteredAds.map((ad: any) => {
            const ev = ad.evaluation;
            const cats = getCategories(ad.campaign_product || '');
            const persona = getPersona(ad.campaign_name || '');
            const imgSrc = ad.image_url ? `${API}${ad.image_url}` : null;
            const hasVisual = ev && (ev.visual_brand_consistency != null || ev.scroll_stopping_power != null);

            const DIM_ABBREV = [
              { key: 'clarity', label: 'CLR', color: '#fbbf24' },
              { key: 'value_proposition', label: 'VAL', color: '#ec4899' },
              { key: 'cta_score', label: 'CTA', color: '#c850c0' },
              { key: 'brand_voice', label: 'BRV', color: '#9b6cc8' },
              { key: 'emotional_resonance', label: 'EMO', color: '#5b9be4' },
            ];
            const VIS_ABBREV = [
              { key: 'visual_brand_consistency', label: 'VIS', color: '#34d399' },
              { key: 'scroll_stopping_power', label: 'STP', color: '#06b6d4' },
            ];

            return (
              <a key={ad.id} href={`/campaigns/${ad.campaign_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="card" style={{ cursor: 'pointer', padding: 0, display: 'flex', flexDirection: 'column', height: '100%' }}>
                  {/* Image */}
                  <div style={{ position: 'relative', width: '100%', aspectRatio: '1 / 1', background: 'var(--surface2)', overflow: 'hidden', borderRadius: '16px 16px 0 0' }}>
                    {imgSrc ? (
                      <img src={imgSrc} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                    ) : (
                      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: '0.75rem' }}>Generating...</div>
                    )}
                    {/* Status badge overlay */}
                    <div style={{ position: 'absolute', top: '8px', right: '8px' }}>
                      <span className={`badge badge-${ad.status}`}>{ad.status}</span>
                    </div>
                    {/* Score overlay */}
                    {ev && (
                      <div style={{ position: 'absolute', bottom: '8px', right: '8px', background: 'rgba(0,0,0,0.7)', borderRadius: '10px', padding: '2px' }}>
                        <ScoreRing score={ev.aggregate_score} size={48} />
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div style={{ padding: '0.75rem 1rem', flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {/* Headline */}
                    <div style={{ fontWeight: 700, fontSize: '0.9rem', lineHeight: 1.3, color: 'var(--text)' }}>{ad.headline}</div>

                    {/* Campaign name */}
                    <div style={{ fontSize: '0.7rem', color: 'var(--muted)', lineHeight: 1.3 }}>{ad.campaign_name}</div>

                    {/* Category + persona tags */}
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                      {cats.map(cat => (
                        <span key={cat} style={{ fontSize: '0.6rem', padding: '1px 6px', borderRadius: '3px', fontWeight: 600, background: `${CAT_COLORS[cat]}18`, color: CAT_COLORS[cat], border: `1px solid ${CAT_COLORS[cat]}30` }}>{cat}</span>
                      ))}
                      {persona && (() => {
                        const pc = personaColor(persona, allPersonas, isDark);
                        return <span style={{ fontSize: '0.6rem', padding: '1px 6px', borderRadius: '3px', fontWeight: 600, background: `${pc}18`, color: pc, border: `1px solid ${pc}30` }}>{persona}</span>;
                      })()}
                    </div>

                    {/* 7-Dimension score bars */}
                    {ev && (
                      <div style={{ marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                        {DIM_ABBREV.map(d => (
                          ev[d.key] != null ? <DimBar key={d.key} label={d.label} score={ev[d.key]} color={d.color} /> : null
                        ))}
                        {hasVisual && VIS_ABBREV.map(d => (
                          ev[d.key] != null ? <DimBar key={d.key} label={d.label} score={ev[d.key]} color={d.color} /> : null
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
