'use client';
import { useEffect, useState } from 'react';
import { InfoTip } from '../components/InfoTip';
import { useEvalConfig, scoreColor, scoreBg, scoreBorder, dimLabel as sharedDimLabel } from '../hooks/useEvalConfig';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
export default function Insights() {
  const evalConfig = useEvalConfig();
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
  const m = matrix?.matrix || {}; const metrics = matrix?.metrics || {}; const total = matrix?.total_ratings || 0; const uniqueAds = matrix?.unique_ads_rated || 0;
  return (
    <div>
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 600, margin: 0 }}><span className="rainbow-text">Insights</span></h1>
          <p style={{ color: 'var(--muted)', marginTop: '4px', fontSize: '0.875rem' }}>Confusion Matrix: AI Evaluator vs Human Judgment</p>
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
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {[
                { label: 'PRECISION', value: `${(metrics.precision * 100).toFixed(1)}%`, sub: 'when AI approves, human agrees', gradient: 'linear-gradient(135deg, #c850c0, #9b6cc8)', color: '#c850c0' },
                { label: 'RECALL', value: `${(metrics.recall * 100).toFixed(1)}%`, sub: 'when human likes, AI caught it', gradient: 'linear-gradient(135deg, #5b9be4, #00d4cf)', color: '#5b9be4' },
                { label: 'ACCURACY', value: `${(metrics.accuracy * 100).toFixed(1)}%`, sub: `from ${total} human ratings`, gradient: 'linear-gradient(135deg, #fbbf24, #f97316)', color: '#f97316' },
                { label: 'AVG COST / AD', value: costData ? `$${costData.avg_cost_per_ad.toFixed(4)}` : '$—', sub: costData ? `${costData.ads_analyzed} ads analyzed` : 'loading...', gradient: 'linear-gradient(135deg, #16a34a, #00d4cf)', color: '#16a34a' },
                { label: 'TOTAL API SPEND', value: costData ? `$${costData.total_spend_usd.toFixed(2)}` : '$—', sub: costData ? `gemini $${costData.cost_by_model.gemini_flash.toFixed(2)} · claude $${costData.cost_by_model.claude_sonnet.toFixed(2)}` : 'loading...', gradient: 'linear-gradient(135deg, #f06c6c, #ec4899)', color: '#f06c6c' },
              ].map(({ label, value, sub, gradient, color }) => (
                <div key={label}>
                  <div style={{ height: '3px', borderRadius: '2px', background: gradient, marginBottom: '12px' }} />
                  <div className="mono" style={{ fontSize: '0.875rem', color: 'var(--muted)', letterSpacing: '0.05em', fontWeight: 600, marginBottom: '6px' }}>{label}</div>
                  <div className="card" style={{ textAlign: 'center' }}>
                    <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color }}>{value}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '4px' }}>{sub}</div>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '0.75rem' }}>
                <h2 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0, color: 'var(--muted)', letterSpacing: '0.05em' }}>CONFUSION MATRIX — {total} RATINGS ACROSS {uniqueAds} ADS</h2>
                <InfoTip text="How to read this: High False Positives = AI too lenient. High False Negatives = AI too strict. Target is high precision — when AI approves, humans should agree." />
              </div>
              <div className="card">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  {[
                    { label: 'True Positive', sublabel: 'Human ✓ AI ✓', value: m.true_positive ?? 0, bgVar: 'var(--green-bg)', borderVar: 'var(--green-border)', colorVar: 'var(--green-text)' },
                    { label: 'False Positive', sublabel: 'Human ✗ AI ✓', value: m.false_positive ?? 0, bgVar: 'var(--red-bg)', borderVar: 'var(--red-border)', colorVar: 'var(--red-text)' },
                    { label: 'False Negative', sublabel: 'Human ✓ AI ✗', value: m.false_negative ?? 0, bgVar: 'var(--amber-bg)', borderVar: 'var(--amber-border)', colorVar: 'var(--amber-text)' },
                    { label: 'True Negative', sublabel: 'Human ✗ AI ✗', value: m.true_negative ?? 0, bgVar: 'var(--green-bg)', borderVar: 'var(--green-border)', colorVar: 'var(--green-text)' },
                  ].map(({ label, sublabel, value, bgVar, borderVar, colorVar }) => (
                    <div key={label} className="card card-plain" style={{ background: bgVar, border: `2px solid ${borderVar}`, borderRadius: '12px', padding: '1.5rem', textAlign: 'center' }}>
                      <div className="mono" style={{ fontSize: '2.5rem', fontWeight: 700, color: colorVar }}>{value}</div>
                      <div style={{ fontWeight: 600, fontSize: '0.875rem', marginTop: '4px', color: 'var(--text)' }}>{label}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '2px' }}>{sublabel}</div>
                      {total > 0 && <div className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '4px' }}>{((value / total) * 100).toFixed(1)}%</div>}
                    </div>
                  ))}
                </div>
              </div>
              {trends?.trends?.length > 0 && (
                <div style={{ marginTop: '2rem' }}>
                  <h2 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.75rem', color: 'var(--muted)', letterSpacing: '0.05em' }}>PERSISTENT WEAKNESS</h2>
                  <div className="card">
                  {(() => {
                    const allDims = evalConfig.db_all_dimensions;
                    const avgs: Record<string, number> = {};
                    allDims.forEach(d => {
                      const vals = trends.trends.map((t: any) => t.dimension_averages?.[d]).filter((v: any) => v != null && v > 0);
                      avgs[d] = vals.length ? vals.reduce((a: number, b: number) => a + b, 0) / vals.length : -1;
                    });
                    const scoredDims = allDims.filter(d => avgs[d] > 0);
                    if (!scoredDims.length) return <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>No dimension data yet</div>;
                    const weakest = scoredDims.reduce((a, b) => avgs[a] < avgs[b] ? a : b);
                    const isVisual = weakest === 'visual_brand_consistency' || weakest === 'scroll_stopping_power';
                    return (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{ background: 'var(--amber-bg)', border: '2px solid var(--amber-border)', borderRadius: '10px', padding: '12px 20px' }}>
                          <span style={{ color: 'var(--amber-text)', fontWeight: 700 }}>{sharedDimLabel(weakest)}</span>
                          {isVisual && <span style={{ fontSize: '0.65rem', color: 'var(--muted)', marginLeft: '6px' }}>(visual)</span>}
                        </div>
                        <div>
                          <div className="mono" style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--amber-text)' }}>{avgs[weakest].toFixed(1)}/10</div>
                          <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>avg across all campaigns</div>
                        </div>
                      </div>
                    );
                  })()}
                  </div>
                </div>
              )}
            </div>
          </div>
          {iterData?.summary?.total_campaigns > 0 && (() => {
            const campaigns = iterData.campaigns || [];
            const allAdsFlat = campaigns.flatMap((c: any) => (c.ads || []).map((a: any) => ({ ...a, campaign: c.campaign_name, weakness: c.expected_weakness })));
            const multiIterAds = allAdsFlat.filter((a: any) => (a.iterations?.length ?? 0) > 1);
            const singlePassAds = allAdsFlat.filter((a: any) => (a.iterations?.length ?? 0) === 1);
            const regressions = multiIterAds.filter((a: any) => {
              const iters = a.iterations || [];
              return iters.some((it: any, idx: number) => idx > 0 && it.score < iters[idx - 1].score);
            });
            const dimLabel = sharedDimLabel;
            const dimColor = (score: number) => scoreColor(score, evalConfig.threshold);
            const dimBg = (score: number) => scoreBg(score, evalConfig.threshold);
            return (
            <div style={{ marginTop: '2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '0.75rem' }}>
                <h2 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0, color: 'var(--muted)', letterSpacing: '0.05em' }}>ITERATION & SELF-HEALING</h2>
                <InfoTip text="The pipeline improves ads through up to 3 fixer cycles. Each iteration targets the weakest dimension. Regression detection adapts strategy when a fix makes things worse." />
              </div>

              {/* Summary stats row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                {[
                  { label: 'ITER 1 AVG', value: iterData.summary.avg_score_iter1?.toFixed(1) ?? '—', gradient: 'linear-gradient(135deg, #f06c6c, #ec4899)', color: '#f06c6c' },
                  { label: 'FINAL AVG', value: iterData.summary.avg_score_iter3?.toFixed(1) ?? '—', gradient: 'linear-gradient(135deg, #16a34a, #00d4cf)', color: '#16a34a' },
                  { label: 'TOTAL LIFT', value: `${iterData.summary.total_lift > 0 ? '+' : ''}${iterData.summary.total_lift?.toFixed(1) ?? '0'} pts`, gradient: 'linear-gradient(135deg, #5b9be4, #c850c0)', color: iterData.summary.total_lift > 0 ? '#16a34a' : 'var(--muted)' },
                  { label: 'FIRST-PASS RATE', value: singlePassAds.length && allAdsFlat.length ? `${Math.round(singlePassAds.length / allAdsFlat.length * 100)}%` : '—', gradient: 'linear-gradient(135deg, #fbbf24, #f97316)', color: '#f97316' },
                ].map(({ label, value, gradient, color }) => (
                  <div key={label}>
                    <div style={{ height: '3px', borderRadius: '2px', background: gradient, marginBottom: '12px' }} />
                    <div className="mono" style={{ fontSize: '0.875rem', color: 'var(--muted)', letterSpacing: '0.05em', fontWeight: 600, marginBottom: '6px' }}>{label}</div>
                    <div className="card" style={{ textAlign: 'center' }}>
                      <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color }}>{value}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Score progression bar chart */}
              {(iterData.summary.avg_score_iter1 > 0 || iterData.summary.avg_score_iter2 > 0 || iterData.summary.avg_score_iter3 > 0) && (
                <div style={{ marginBottom: '1.5rem' }}>
                  <h2 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0, marginBottom: '0.75rem', color: 'var(--muted)', letterSpacing: '0.05em' }}>SCORE PROGRESSION BY CYCLE</h2>
                  <div className="card">
                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '1rem', height: '140px' }}>
                      {[
                        { label: 'Iter 1', score: iterData.summary.avg_score_iter1 },
                        { label: 'Iter 2', score: iterData.summary.avg_score_iter2 },
                        { label: 'Iter 3', score: iterData.summary.avg_score_iter3 },
                      ].filter(d => d.score > 0).map((d, i, arr) => {
                        const pct = (d.score / 10) * 100;
                        const prev = i > 0 ? arr[i - 1].score : null;
                        const isRegression = prev !== null && d.score < prev;
                        const isImproved = prev !== null && d.score > prev;
                        return (
                          <div key={d.label} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                            <div className="mono" style={{ fontSize: '1rem', fontWeight: 700, color: isRegression ? 'var(--red-text)' : isImproved ? 'var(--green-text)' : 'var(--text)' }}>
                              {d.score.toFixed(1)}
                              {isRegression && <span style={{ fontSize: '0.8rem', marginLeft: '2px' }}>&darr;</span>}
                              {isImproved && <span style={{ fontSize: '0.8rem', marginLeft: '2px' }}>&uarr;</span>}
                            </div>
                            <div style={{
                              width: '100%', maxWidth: '80px', borderRadius: '6px 6px 0 0',
                              height: `${pct}%`, minHeight: '8px',
                              background: isRegression
                                ? 'linear-gradient(180deg, var(--red-text), var(--red-border))'
                                : `linear-gradient(180deg, ${i === 0 ? '#f06c6c' : i === 1 ? '#fbbf24' : '#16a34a'}, ${i === 0 ? '#ec4899' : i === 1 ? '#f97316' : '#00d4cf'})`,
                              opacity: 0.85,
                              transition: 'height 0.5s ease',
                              position: 'relative',
                            }}>
                              {d.score >= evalConfig.threshold && (
                                <div style={{ position: 'absolute', top: '-1px', left: 0, right: 0, height: '2px', background: 'var(--green-text)', borderRadius: '1px' }} />
                              )}
                            </div>
                            <div className="mono" style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>{d.label}</div>
                          </div>
                        );
                      })}
                    </div>
                    <div style={{ marginTop: '8px', borderTop: '1px dashed var(--border)', paddingTop: '6px', display: 'flex', justifyContent: 'flex-end' }}>
                      <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>threshold: {evalConfig.threshold}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Regression callouts */}
              {regressions.length > 0 && (
                <div style={{ marginBottom: '1.5rem' }}>
                  <h2 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0, marginBottom: '0.75rem', color: 'var(--red-text)', letterSpacing: '0.05em' }}>REGRESSIONS DETECTED & ADAPTED</h2>
                  <div className="card card-plain" style={{ background: 'var(--red-bg)', border: '1px solid var(--red-border)' }}>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text)' }}>
                      {regressions.map((a: any, i: number) => {
                        const iters = a.iterations || [];
                        const regIdx = iters.findIndex((it: any, idx: number) => idx > 0 && it.score < iters[idx - 1].score);
                        return (
                          <div key={i} style={{ marginBottom: i < regressions.length - 1 ? '8px' : 0 }}>
                            <span style={{ fontWeight: 600 }}>Ad #{a.ad_number}</span> in {a.campaign}:
                            iter {regIdx} ({iters[regIdx - 1]?.score?.toFixed(1)}) &rarr; iter {regIdx + 1} ({iters[regIdx]?.score?.toFixed(1)})
                            <span style={{ color: 'var(--red-text)', fontWeight: 600 }}> &darr;{(iters[regIdx - 1]?.score - iters[regIdx]?.score).toFixed(1)}</span>
                            {iters[regIdx]?.fix_applied && <span style={{ color: 'var(--muted)', fontSize: '0.85rem' }}> &mdash; adapted: {iters[regIdx].fix_applied}</span>}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* Per-campaign ad journey cards */}
              {campaigns.map((campaign: any, ci: number) => {
                const ads = campaign.ads || [];
                if (!ads.length) return null;
                return (
                  <div key={ci} style={{ marginBottom: ci < campaigns.length - 1 ? '1.5rem' : 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.75rem' }}>
                      <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0, color: 'var(--text)' }}>{campaign.campaign_name}</h3>
                      {campaign.expected_weakness && (
                        <span style={{ fontSize: '0.75rem', padding: '3px 10px', borderRadius: '4px', background: 'var(--amber-bg)', color: 'var(--amber-text)', border: '1px solid var(--amber-border)', fontWeight: 600 }}>
                          target: {dimLabel(campaign.expected_weakness)}
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(ads.length, 3)}, 1fr)`, gap: '1rem' }}>
                      {ads.map((ad: any, ai: number) => {
                        const iters = ad.iterations || [];
                        const firstIter = iters[0];
                        const lastIter = iters[iters.length - 1];
                        const lift = (lastIter?.score ?? 0) - (firstIter?.score ?? 0);
                        const dims = firstIter?.dimension_scores ? Object.keys(firstIter.dimension_scores) : [];
                        return (
                          <div key={ai} className="card" style={{ padding: '1.25rem' }}>
                            {/* Ad header */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                              <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--muted)', fontWeight: 600 }}>AD #{ad.ad_number}</span>
                              <span className={`badge ${ad.passed_threshold ? 'badge-approved' : 'badge-flagged'}`}>
                                {ad.passed_threshold ? 'approved' : 'flagged'}
                              </span>
                            </div>

                            {/* Iteration step indicators */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '12px' }}>
                              {iters.map((it: any, idx: number) => {
                                const prev = idx > 0 ? iters[idx - 1] : null;
                                const isReg = prev && it.score < prev.score;
                                const isUp = prev && it.score > prev.score;
                                return (
                                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '4px', flex: 1 }}>
                                    <div style={{
                                      width: '32px', height: '32px', borderRadius: '50%', flexShrink: 0,
                                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                                      fontSize: '0.8rem', fontWeight: 700, fontFamily: "'Space Mono', monospace",
                                      background: isReg ? 'var(--red-bg)' : scoreBg(it.score, evalConfig.threshold),
                                      color: isReg ? 'var(--red-text)' : scoreColor(it.score, evalConfig.threshold),
                                      border: `2px solid ${isReg ? 'var(--red-border)' : scoreBorder(it.score, evalConfig.threshold)}`,
                                    }}>
                                      {it.score.toFixed(1)}
                                    </div>
                                    {idx < iters.length - 1 && (
                                      <div style={{
                                        flex: 1, height: '2px',
                                        background: isUp ? 'var(--green-text)' : isReg ? 'var(--red-text)' : 'var(--border)',
                                      }} />
                                    )}
                                  </div>
                                );
                              })}
                            </div>

                            {/* Lift badge */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                              <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                                {iters.length === 1 ? 'approved on first pass' : `${iters.length} iterations`}
                              </span>
                              {lift !== 0 && (
                                <span className="mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: lift > 0 ? 'var(--green-text)' : 'var(--red-text)' }}>
                                  {lift > 0 ? '+' : ''}{lift.toFixed(1)} lift
                                </span>
                              )}
                            </div>

                            {/* Dimension heatmap — last iteration */}
                            {dims.length > 0 && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                {dims.map(d => {
                                  const firstScore = firstIter?.dimension_scores?.[d] ?? 0;
                                  const lastScore = lastIter?.dimension_scores?.[d] ?? firstScore;
                                  const isWeakest = lastIter?.weakest_dimension === d || firstIter?.weakest_dimension === d;
                                  const dimLift = lastScore - firstScore;
                                  return (
                                    <div key={d} style={{
                                      display: 'flex', alignItems: 'center', gap: '8px', padding: '5px 10px',
                                      borderRadius: '6px', background: isWeakest ? dimBg(lastScore) : 'transparent',
                                      border: isWeakest ? `1px solid ${dimColor(lastScore)}40` : '1px solid transparent',
                                    }}>
                                      <span style={{ fontSize: '0.8rem', color: isWeakest ? dimColor(lastScore) : 'var(--muted)', fontWeight: isWeakest ? 700 : 400, flex: 1, minWidth: 0 }}>
                                        {dimLabel(d)}
                                      </span>
                                      <span className="mono" style={{ fontSize: '0.8rem', fontWeight: 600, color: dimColor(lastScore) }}>
                                        {lastScore.toFixed(1)}
                                      </span>
                                      {iters.length > 1 && dimLift !== 0 && (
                                        <span className="mono" style={{ fontSize: '0.75rem', color: dimLift > 0 ? 'var(--green-text)' : 'var(--red-text)' }}>
                                          {dimLift > 0 ? '+' : ''}{dimLift.toFixed(1)}
                                        </span>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            )}

                            {/* Fix applied info */}
                            {iters.length > 1 && lastIter?.fix_applied && lastIter.fix_applied !== 'none (first pass)' && (
                              <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid var(--border)', fontSize: '0.8rem', color: 'var(--muted)' }}>
                                <span style={{ fontWeight: 600 }}>Fix:</span> {lastIter.fix_applied}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
            );
          })()}
        </>
      )}
    </div>
  );
}
