'use client';
import { useEffect, useState } from 'react';
import { InfoTip } from './components/InfoTip';
import { useEvalConfig, dimLabel } from './hooks/useEvalConfig';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

const CAT_COLORS: Record<string, string> = {
  'SAT Prep': '#6366f1',
  'ACT Prep': '#8b5cf6',
  'Math': '#0891b2',
  'Reading': '#059669',
  'Other': '#6b7280',
};

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

const gradients = [
  'linear-gradient(135deg, #fbbf24, #f97316)',
  'linear-gradient(135deg, #c850c0, #9b6cc8)',
  'linear-gradient(135deg, #5b9be4, #00d4cf)',
  'linear-gradient(135deg, #ec4899, #c850c0)',
];

const RAINBOW = 'linear-gradient(90deg, #fbbf24, #f97316, #f06c6c, #ec4899, #c850c0, #9b6cc8, #5b9be4, #00d4cf)';

const STAT_INFO: Record<string, string> = {
  'TOTAL ADS': 'Total number of ads generated across all campaigns. Each campaign can produce up to 10 ads through the pipeline.',
  'AVG SCORE': 'Mean aggregate evaluation score across all ads, out of 10. Computed as the average of 5 text dimensions (clarity, value proposition, CTA, brand voice, emotional resonance), each scored 0–10 by the AI evaluator.',
  'PASS RATE': 'Percentage of ads that meet the quality threshold (set by the evaluator agent). Ads scoring below threshold are flagged for iteration or manual review.',
  'CAMPAIGNS': 'Total number of campaigns created. Each campaign targets a specific persona, category, and goal.',
  'QUALITY BAR': 'The dynamic quality threshold enforced by the ratchet. Starts at 7.0 and only goes up as more high-scoring ads are approved. Based on the 25th percentile of approved scores, with guardrails to prevent sudden spikes.',
};

function ScoreBar({ score }: { score: number }) {
  const pct = score * 10;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
      <div style={{ flex: 1, height: '6px', background: 'var(--surface2)', borderRadius: '3px', overflow: 'hidden', outline: '1px solid var(--border)', outlineOffset: '1px' }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          background: RAINBOW,
          backgroundSize: pct > 0 ? `${10000 / pct}% 100%` : '100% 100%',
          backgroundPosition: 'left',
          borderRadius: '3px',
          transition: 'width 1s ease',
        }} />
      </div>
      <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text)', minWidth: '36px', fontWeight: 600, textAlign: 'right' }}>{score.toFixed(1)}</span>
    </div>
  );
}

export default function Dashboard() {
  const evalConfig = useEvalConfig();
  const [summary, setSummary] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [allAds, setAllAds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([
      fetch(`${API}/analytics/trends`).then(r => r.json()),
      fetch(`${API}/campaigns`).then(r => r.json()),
      fetch(`${API}/ads`).then(r => r.json()),
    ]).then(([trendsData, campaignsData, adsData]) => {
      setSummary(trendsData.summary);
      setTrends(trendsData.trends || []);
      setCampaigns(campaignsData.campaigns || []);
      setAllAds(adsData.ads || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const recentAds = allAds.slice(0, 6);
  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}><span className="mono rainbow-text" style={{ fontSize: '0.875rem', fontWeight: 600 }}>LOADING ENGINE DATA...</span></div>;
  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, margin: 0, letterSpacing: '-0.02em' }}>
          <span className="rainbow-text">Ad Engine</span> Dashboard
        </h1>

      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem', marginBottom: '2rem' }}>
        {[
          { label: 'TOTAL ADS', value: summary?.total_ads ?? 0, gradient: gradients[0] },
          { label: 'AVG SCORE', value: summary?.overall_avg_score?.toFixed(1) ?? '—', gradient: gradients[1] },
          { label: 'PASS RATE', value: `${summary?.pass_rate ?? 0}%`, gradient: gradients[2] },
          { label: 'CAMPAIGNS', value: campaigns.length, gradient: gradients[3] },
        ].map(({ label, value, gradient }) => (
          <div key={label}>
            <div style={{ height: '3px', borderRadius: '2px', background: gradient, marginBottom: '12px' }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <span className="mono" style={{ fontSize: '0.875rem', color: 'var(--muted)', letterSpacing: '0.05em', fontWeight: 600 }}>{label}</span>
              {STAT_INFO[label] && <InfoTip text={STAT_INFO[label]} />}
            </div>
            <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text)' }}>{value}</div>
          </div>
        ))}
      </div>
      {/* Quality Ratchet Indicator */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '2rem',
        padding: '10px 16px', borderRadius: '10px',
        background: evalConfig.ratchet_active ? 'var(--green-bg)' : 'var(--surface2)',
        border: `1px solid ${evalConfig.ratchet_active ? 'var(--green-border)' : 'var(--border)'}`,
      }}>
        <span style={{ fontSize: '1rem' }}>{evalConfig.ratchet_active ? '📈' : '📊'}</span>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className="mono" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--muted)', letterSpacing: '0.05em' }}>QUALITY BAR</span>
            <InfoTip text={STAT_INFO['QUALITY BAR']} />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '2px' }}>
            <span className="mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text)' }}>{evalConfig.threshold.toFixed(1)}</span>
            {evalConfig.ratchet_active && evalConfig.threshold > evalConfig.floor && (
              <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--green-text)', fontWeight: 600 }}>
                ↑ {(evalConfig.threshold - evalConfig.floor).toFixed(1)} from {evalConfig.floor.toFixed(1)} floor
              </span>
            )}
            {!evalConfig.ratchet_active && (
              <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>
                ratchet activates after {10 - evalConfig.ratchet_sample_size} more approved ads
              </span>
            )}
          </div>
        </div>
        <span className="mono" style={{ fontSize: '0.65rem', color: 'var(--muted)', textAlign: 'right' }}>
          {evalConfig.ratchet_sample_size} approved ads
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', alignItems: 'start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '0.75rem' }}>
            <h2 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0, color: 'var(--muted)', letterSpacing: '0.05em' }}>CAMPAIGN PERFORMANCE</h2>
            <InfoTip text="Average evaluation score per campaign, out of 10. Each bar shows the mean of all ad scores within that campaign. Scores are the aggregate of 5 text dimensions evaluated by the AI." />
          </div>
          <div className="card">
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
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '0.75rem' }}>
              <h2 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0, color: 'var(--muted)', letterSpacing: '0.05em' }}>DIMENSION AVERAGES</h2>
              <InfoTip text="Mean score for each of the 5 evaluation dimensions across all campaigns, each out of 10. Clarity: how clear the message is. Value Proposition: strength of the offer. CTA Score: effectiveness of the call-to-action. Brand Voice: alignment with Varsity Tutors tone. Emotional Resonance: how well it connects with the target audience." />
            </div>
            <div className="card">
            {trends.length === 0 ? <p style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>No data yet</p> : (() => {
              const dims = evalConfig.db_text_dimensions;
              const avgs: Record<string, number> = {};
              dims.forEach(d => {
                const vals = trends.map(t => t.dimension_averages?.[d] ?? 0).filter(Boolean);
                avgs[d] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
              });
              return dims.map(dim => (
                <div key={dim} style={{ marginBottom: '1rem' }}>
                  <div style={{ marginBottom: '4px' }}><span style={{ fontSize: '0.8rem', color: 'var(--text)' }}>{dimLabel(dim)}</span></div>
                  <ScoreBar score={avgs[dim]} />
                </div>
              ));
            })()}
            </div>
          </div>
          {recentAds.length > 0 && (
            <div>
              <h2 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.75rem', color: 'var(--muted)', letterSpacing: '0.05em' }}>RECENT ADS</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
                {recentAds.map((ad: any) => {
                  const overallScore = ad.evaluation?.aggregate_score;
                  const imageUrl = ad.image_url ? (ad.image_url.startsWith('http') ? ad.image_url : `${API}${ad.image_url}`) : null;
                  return (
                    <a key={ad.id} href={`/campaigns/${ad.campaign_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                      <div className="card" style={{ padding: '0', display: 'flex', flexDirection: 'column', height: '100%' }}>
                        <div style={{ background: 'var(--surface2)', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', borderRadius: '16px 16px 0 0', aspectRatio: imageUrl ? 'auto' : '16/9' }}>
                          {imageUrl ? (
                            <img src={imageUrl} alt={ad.headline || 'Ad creative'} style={{ width: '100%', height: 'auto', display: 'block' }} onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                          ) : (
                            <span className="mono rainbow-text" style={{ fontSize: '0.6rem', fontWeight: 600, letterSpacing: '0.05em' }}>AD CREATIVE</span>
                          )}
                        </div>
                        <div style={{ padding: '0.75rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
                          <div style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--text)', marginBottom: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ad.headline || 'Untitled Ad'}</div>
                          {ad.campaign_name && <div style={{ fontSize: '0.65rem', color: 'var(--muted)', marginBottom: '6px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ad.campaign_name}</div>}
                          <div style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', gap: '6px', borderTop: '1px solid var(--border)', paddingTop: '6px' }}>
                            {overallScore != null ? (
                              <span className="mono" style={{ fontSize: '0.7rem', fontWeight: 600, background: RAINBOW, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', flexShrink: 0 }}>{overallScore.toFixed(1)}/10</span>
                            ) : (
                              <span className="mono" style={{ fontSize: '0.65rem', color: 'var(--muted)', flexShrink: 0 }}>No score</span>
                            )}
                            <div style={{ display: 'flex', gap: '3px', flexWrap: 'wrap', flex: 1 }}>
                              {getCategories(ad.campaign_product || '').map(cat => (
                                <span key={cat} style={{ fontSize: '0.55rem', padding: '1px 5px', borderRadius: '3px', fontWeight: 600, background: `${CAT_COLORS[cat]}18`, color: CAT_COLORS[cat], border: `1px solid ${CAT_COLORS[cat]}30` }}>{cat}</span>
                              ))}
                            </div>
                            <span style={{ color: 'var(--accent)', fontSize: '0.65rem', fontWeight: 600, flexShrink: 0 }}>View →</span>
                          </div>
                        </div>
                      </div>
                    </a>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
