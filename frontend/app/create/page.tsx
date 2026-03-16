'use client';
import { useEffect, useState, useRef } from 'react';
import RadarChart from '../components/RadarChart';
import ScoreRing from '../components/ScoreRing';
import { ImagePlaceholder } from '../components/ImagePlaceholder';
import { useEvalConfig } from '../hooks/useEvalConfig';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

const PERSONA_COLORS_LIGHT = [
  '#c850c0', '#e06898', '#d97706', '#0891b2', '#7c3aed',
  '#059669', '#dc2626', '#6366f1', '#0d9488', '#b45309',
  '#8b5cf6', '#db2777', '#2563eb', '#ca8a04', '#16a34a', '#6b7280',
];
const PERSONA_COLORS_DARK = [
  '#e879de', '#f7a0c0', '#fbbf24', '#22d3ee', '#a78bfa',
  '#34d399', '#f87171', '#818cf8', '#2dd4bf', '#f59e0b',
  '#c4b5fd', '#f472b6', '#60a5fa', '#fcd34d', '#4ade80', '#9ca3af',
];
const GOAL_COLOR = '#0ea5e9';

/* ── Reusable inline components (same as campaigns/[id]) ─── */

/* ScoreRing imported from ../components/ScoreRing */

function AdImage({ imageUrl }: { imageUrl?: string }) {
  const [error, setError] = useState(false);
  if (!imageUrl || error) return null;
  const fullUrl = imageUrl.startsWith('http') ? imageUrl : `${API}${imageUrl}`;
  return <img src={fullUrl} alt="Generated ad creative" onError={() => setError(true)} style={{ width: '100%', height: 'auto', display: 'block' }} />;
}

function FacebookAdPreview({ ad }: { ad: any }) {
  const hasImage = !!ad.image_url;
  return (
    <div style={{ background: 'var(--surface, #fff)', borderRadius: '12px', border: '1px solid var(--border)', overflow: 'hidden', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 14px' }}>
        <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg, #1a73e8, #34a853)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 700, color: '#fff', flexShrink: 0 }}>VT</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>Varsity Tutors</div>
          <div style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>Sponsored · 🌐</div>
        </div>
        <div style={{ color: 'var(--muted)', fontSize: '1rem' }}>···</div>
      </div>
      <div style={{ padding: '0 14px 10px', fontSize: '0.8rem', lineHeight: 1.65, color: 'var(--text)' }}>{ad.primary_text}</div>
      <div style={{ borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
        {hasImage ? <AdImage imageUrl={ad.image_url} /> : <ImagePlaceholder />}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'var(--surface2)' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '0.6rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.02em' }}>varsitytutors.com</div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{ad.headline}</div>
          {ad.description && <div style={{ fontSize: '0.7rem', color: 'var(--muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: '1px' }}>{ad.description}</div>}
        </div>
        <button style={{ flexShrink: 0, marginLeft: '10px', background: 'var(--accent, #1a73e8)', color: '#fff', border: 'none', borderRadius: '6px', padding: '7px 14px', fontSize: '0.75rem', fontWeight: 600, cursor: 'default' }}>{ad.cta_button}</button>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-around', padding: '7px 14px', borderTop: '1px solid var(--border)', color: 'var(--muted)', fontSize: '0.75rem' }}>
        <span>👍 Like</span><span>💬 Comment</span><span>↗ Share</span>
      </div>
      <div style={{ textAlign: 'center', padding: '5px', fontSize: '0.55rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', borderTop: '1px solid var(--border)' }}>Facebook Preview</div>
    </div>
  );
}

function InstagramAdPreview({ ad }: { ad: any }) {
  const hasImage = !!ad.image_url;
  return (
    <div style={{ background: 'var(--surface, #fff)', borderRadius: '12px', border: '1px solid var(--border)', overflow: 'hidden', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px' }}>
        <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2px', flexShrink: 0 }}>
          <div style={{ width: '100%', height: '100%', borderRadius: '50%', background: 'linear-gradient(135deg, #1a73e8, #34a853)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700, color: '#fff' }}>VT</div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>varsitytutors</div>
          <div style={{ fontSize: '0.6rem', color: 'var(--muted)' }}>Sponsored</div>
        </div>
        <div style={{ color: 'var(--muted)', fontSize: '1rem' }}>···</div>
      </div>
      <div>{hasImage ? <AdImage imageUrl={ad.image_url} /> : <ImagePlaceholder />}</div>
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px' }}>
        <div style={{ display: 'flex', gap: '14px', fontSize: '1.1rem' }}><span>♡</span><span>💬</span><span>➤</span></div>
        <span style={{ fontSize: '1.1rem' }}>🔖</span>
      </div>
      <div style={{ padding: '0 14px 8px', fontSize: '0.8rem', lineHeight: 1.6 }}>
        <span style={{ fontWeight: 600, marginRight: '6px' }}>varsitytutors</span>
        <span style={{ color: 'var(--text)' }}>{ad.primary_text}</span>
      </div>
      <div style={{ padding: '0 14px 10px' }}>
        <button style={{ width: '100%', background: 'var(--accent, #1a73e8)', color: '#fff', border: 'none', borderRadius: '8px', padding: '9px 16px', fontSize: '0.8rem', fontWeight: 600, cursor: 'default' }}>{ad.cta_button}</button>
      </div>
      <div style={{ padding: '0 14px 12px' }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{ad.headline}</div>
        {ad.description && <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '2px' }}>{ad.description}</div>}
      </div>
      <div style={{ textAlign: 'center', padding: '5px', fontSize: '0.55rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', borderTop: '1px solid var(--border)' }}>Instagram Preview</div>
    </div>
  );
}

function DimScore({ label, score, color }: { label: string; score: number | null; color: string }) {
  if (score == null) return null;
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: '0.825rem', color: 'var(--muted)' }}>{label}</span>
      <span className="mono" style={{ fontSize: '0.95rem', fontWeight: 700, color }}>{score.toFixed(1)}</span>
    </div>
  );
}

/* ── Constants ──────────────────────────────────────────────── */

const PERSONAS = [
  'athlete_recruit', 'suburban_optimizer', 'scholarship_family', 'khan_academy_failure',
  'online_skeptic', 'bad_score_urgency', 'immigrant_navigator', 'neurodivergent_advocate',
  'test_anxiety', 'accountability_seeker', 'school_failed_them', 'education_investor',
  'burned_returner', 'parent_relationship', 'sibling_second_child', 'general',
];

const CATEGORIES = [
  { label: 'SAT Prep', product: '1-on-1 SAT tutoring', color: '#6366f1' },
  { label: 'ACT Prep', product: '1-on-1 ACT tutoring', color: '#8b5cf6' },
  { label: 'Math', product: '1-on-1 math tutoring', color: '#0891b2' },
  { label: 'Reading', product: '1-on-1 reading tutoring', color: '#059669' },
  { label: 'General', product: 'Varsity Tutors', color: '#6b7280' },
];

const PERSONA_DEFAULTS: Record<string, { audience: string; tone: string }> = {
  athlete_recruit:       { audience: 'parents of 11th-grade recruited athletes where SAT is a scholarship gatekeeper', tone: 'urgent, competitive, outcome-focused' },
  suburban_optimizer:    { audience: 'upper-middle-class parents with high-GPA child but mid-1200s SAT', tone: 'reframe-focused, empathetic, specific' },
  scholarship_family:    { audience: 'families where SAT score directly impacts scholarship dollars', tone: 'ROI-focused, empathetic, specific' },
  khan_academy_failure:  { audience: 'parents whose child tried free SAT resources with minimal score improvement', tone: 'validating, solution-oriented, direct' },
  online_skeptic:        { audience: 'parents who believe in-person tutoring is better than online', tone: 'reframe-focused, logical, reassuring' },
  bad_score_urgency:     { audience: 'parents whose child just received a disappointing SAT score', tone: 'urgent, empathetic, action-focused' },
  immigrant_navigator:   { audience: 'first-generation immigrant families unfamiliar with the US college admissions system', tone: 'patient, respectful, step-by-step' },
  neurodivergent_advocate: { audience: 'parents of students with ADHD, dyslexia, or processing differences preparing for SAT', tone: 'understanding, confidence-building, right-fit' },
  test_anxiety:          { audience: 'parents of students who know the material but freeze on test day', tone: 'reassuring, confidence-focused, methodical' },
  accountability_seeker: { audience: 'parents exhausted from trying to make their teenager study for the SAT', tone: 'empathetic, structured, authoritative' },
  school_failed_them:    { audience: 'parents frustrated that their school\'s SAT prep program didn\'t work', tone: 'validating, direct, solution-oriented' },
  education_investor:    { audience: 'parents who have already invested in multiple SAT prep resources without results', tone: 'consolidation-focused, methodical, clear' },
  burned_returner:       { audience: 'parents with a bad prior tutoring experience and trust deficit', tone: 'transparent, accountability-first, empathetic' },
  parent_relationship:   { audience: 'parents where SAT prep is causing family tension and conflict', tone: 'warm, de-escalating, relationship-preserving' },
  sibling_second_child:  { audience: 'parents preparing their second child for the SAT after learning from the first', tone: 'knowing, proactive, efficient' },
  general:               { audience: 'parents of high school students preparing for standardized tests', tone: 'warm, urgent, outcome-focused' },
};

const TEXT_DIMS: { key: string; label: string; color: string }[] = [
  { key: 'clarity', label: 'Clarity', color: '#fbbf24' },
  { key: 'value_proposition', label: 'Value Proposition', color: '#ec4899' },
  { key: 'cta_score', label: 'CTA Score', color: '#c850c0' },
  { key: 'brand_voice', label: 'Brand Voice', color: '#9b6cc8' },
  { key: 'emotional_resonance', label: 'Emotional Resonance', color: '#5b9be4' },
];

const VISUAL_DIMS: { key: string; label: string; color: string }[] = [
  { key: 'visual_brand_consistency', label: 'Visual Brand', color: '#34d399' },
  { key: 'scroll_stopping_power', label: 'Scroll Stopping', color: '#06b6d4' },
];

const PIPELINE_STEPS = ['Queued', 'Writing', 'Evaluating', 'Complete'];

function formatPersona(p: string) {
  return p.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()).replace(/\bCta\b/, 'CTA');
}

/* ── Main Page ─────────────────────────────────────────────── */

export default function CreatePage() {
  // Form state
  const [phase, setPhase] = useState<'form' | 'running' | 'done'>('form');
  const [persona, setPersona] = useState('general');
  const [categoryIdx, setCategoryIdx] = useState<number | null>(null);
  const [goal, setGoal] = useState('conversion');
  const [tone, setTone] = useState('warm, urgent, outcome-focused');
  const [keyBenefit, setKeyBenefit] = useState('');
  const [proofPoint, setProofPoint] = useState('');
  const [numAds, setNumAds] = useState(1);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isDark, setIsDark] = useState(false);

  // Pipeline state
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [campaignData, setCampaignData] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const prevAdCount = useRef(0);

  // Theme detection
  useEffect(() => {
    const check = () => setIsDark(document.documentElement.getAttribute('data-theme') === 'dark');
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => obs.disconnect();
  }, []);

  // Auto-fill tone when persona changes
  useEffect(() => {
    setTone(PERSONA_DEFAULTS[persona]?.tone || 'warm, urgent, outcome-focused');
  }, [persona]);

  // Polling
  useEffect(() => {
    if (phase !== 'running' || !campaignId) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/campaigns/${campaignId}`);
        if (!res.ok) return;
        const data = await res.json();
        setCampaignData(data);
        if (data.campaign.status === 'completed' || data.campaign.status === 'failed') {
          setPhase('done');
          clearInterval(interval);
        }
      } catch { /* ignore transient errors */ }
    }, 2000);
    return () => clearInterval(interval);
  }, [phase, campaignId]);

  // Infer pipeline step from data
  function getCurrentStep(): number {
    if (!campaignData) return 0;
    const status = campaignData.campaign?.status;
    const adCount = campaignData.ads?.length || 0;
    if (status === 'completed' || status === 'failed') return 3;
    if (adCount > 0) return 2;
    if (status === 'running') return 1;
    return 0;
  }

  async function handleSubmit() {
    if (categoryIdx === null) return;
    setSubmitting(true);
    setError(null);
    const cat = CATEGORIES[categoryIdx];
    const defaults = PERSONA_DEFAULTS[persona];
    const body: any = {
      name: `${formatPersona(persona)} — ${cat.label}`,
      audience: defaults.audience,
      product: cat.product,
      goal,
      tone,
      num_ads: numAds,
      persona,
    };
    if (keyBenefit) body.key_benefit = keyBenefit;
    if (proofPoint) body.proof_point = proofPoint;

    try {
      const res = await fetch(`${API}/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Request failed');
      }
      const data = await res.json();
      setCampaignId(data.campaign_id);
      setCampaignData(null);
      prevAdCount.current = 0;
      setPhase('running');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  function resetForm() {
    setPhase('form');
    setCampaignId(null);
    setCampaignData(null);
    setPersona('general');
    setCategoryIdx(null);
    setGoal('conversion');
    setTone('warm, urgent, outcome-focused');
    setKeyBenefit('');
    setProofPoint('');
    setNumAds(1);
    setShowAdvanced(false);
    setError(null);
    prevAdCount.current = 0;
  }

  /* ── RENDER: Form Phase ────────────────────────────────── */
  if (phase === 'form') {
    return (
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, marginBottom: '4px' }}>
          <span className="rainbow-text">Create Ad</span>
        </h1>
        <p style={{ color: 'var(--muted)', fontSize: '0.875rem', marginBottom: '2rem' }}>
          Choose a persona and category, then watch the pipeline generate and iterate in real-time.
        </p>

        <div className="card" style={{ padding: '2rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2.5rem' }}>

            {/* Left: Persona picker */}
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '12px', fontWeight: 600 }}>
                Persona
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                {PERSONAS.map((p, i) => {
                  const pc = (isDark ? PERSONA_COLORS_DARK : PERSONA_COLORS_LIGHT)[i % PERSONA_COLORS_LIGHT.length];
                  const active = persona === p;
                  return (
                    <button
                      key={p}
                      className="persona-btn"
                      style={{
                        borderColor: active ? pc : `${pc}40`,
                        background: active ? pc : 'var(--surface2)',
                        color: active ? '#fff' : pc,
                      }}
                      onClick={() => setPersona(p)}
                    >
                      {formatPersona(p)}
                    </button>
                  );
                })}
              </div>
              <div style={{ marginTop: '12px', padding: '10px 14px', background: 'var(--surface2)', borderRadius: '8px', fontSize: '0.75rem', color: 'var(--muted)', lineHeight: 1.6 }}>
                <strong style={{ color: 'var(--text)' }}>Audience:</strong> {PERSONA_DEFAULTS[persona]?.audience}
              </div>
            </div>

            {/* Right: Category + Config */}
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '12px', fontWeight: 600 }}>
                Category
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {CATEGORIES.map((cat, i) => {
                  const active = categoryIdx === i;
                  return (
                    <button
                      key={cat.label}
                      className="cat-pill"
                      style={{
                        borderColor: active ? cat.color : cat.color,
                        background: active ? cat.color : 'var(--surface2)',
                        color: active ? '#fff' : cat.color,
                      }}
                      onClick={() => setCategoryIdx(i)}
                    >
                      {cat.label}
                    </button>
                  );
                })}
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginTop: '24px', marginBottom: '12px', fontWeight: 600 }}>
                Goal
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                {['conversion', 'awareness'].map(g => {
                  const active = goal === g;
                  return (
                    <button
                      key={g}
                      className="cat-pill"
                      style={{
                        borderColor: GOAL_COLOR,
                        background: active ? GOAL_COLOR : 'var(--surface2)',
                        color: active ? '#fff' : GOAL_COLOR,
                      }}
                      onClick={() => setGoal(g)}
                    >
                      {g.charAt(0).toUpperCase() + g.slice(1)}
                    </button>
                  );
                })}
              </div>

              {/* Advanced toggle */}
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                style={{ marginTop: '24px', background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 500, padding: 0 }}
              >
                {showAdvanced ? '▾ Hide advanced' : '▸ Show advanced'}
              </button>

              {showAdvanced && (
                <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: 'var(--muted)', display: 'block', marginBottom: '4px' }}>Tone</label>
                    <input
                      type="text" value={tone} onChange={e => setTone(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--surface2)', color: 'var(--text)', fontSize: '0.8rem', fontFamily: 'inherit' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: 'var(--muted)', display: 'block', marginBottom: '4px' }}>Key Benefit (optional)</label>
                    <input
                      type="text" value={keyBenefit} onChange={e => setKeyBenefit(e.target.value)}
                      placeholder="e.g., personalized learning matched to your child's gaps"
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--surface2)', color: 'var(--text)', fontSize: '0.8rem', fontFamily: 'inherit' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: 'var(--muted)', display: 'block', marginBottom: '4px' }}>Proof Point (optional)</label>
                    <input
                      type="text" value={proofPoint} onChange={e => setProofPoint(e.target.value)}
                      placeholder="e.g., students improve an average of 360 points"
                      style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--surface2)', color: 'var(--text)', fontSize: '0.8rem', fontFamily: 'inherit' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: 'var(--muted)', display: 'block', marginBottom: '4px' }}>Number of Ads (1-5)</label>
                    <input
                      type="number" min={1} max={5} value={numAds} onChange={e => setNumAds(Math.min(5, Math.max(1, parseInt(e.target.value) || 1)))}
                      style={{ width: '80px', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--surface2)', color: 'var(--text)', fontSize: '0.8rem', fontFamily: 'inherit' }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div style={{ marginTop: '1.5rem', padding: '12px 16px', background: 'var(--red-bg, rgba(239,68,68,0.1))', border: '1px solid var(--red-border, rgba(239,68,68,0.3))', borderRadius: '8px', color: 'var(--danger, #ef4444)', fontSize: '0.85rem' }}>
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={categoryIdx === null || submitting}
            style={{
              marginTop: '2rem', width: '100%', padding: '14px 24px',
              borderRadius: '12px', border: 'none', cursor: categoryIdx === null || submitting ? 'not-allowed' : 'pointer',
              background: categoryIdx === null ? 'var(--surface2)' : 'var(--gradient-rainbow)',
              color: categoryIdx === null ? 'var(--muted)' : '#fff',
              fontSize: '1rem', fontWeight: 700, fontFamily: 'inherit',
              opacity: submitting ? 0.7 : 1, transition: 'all 0.2s',
            }}
          >
            {submitting ? 'Starting pipeline...' : 'Generate Ad'}
          </button>
        </div>
      </div>
    );
  }

  /* ── RENDER: Running Phase ─────────────────────────────── */
  const currentStep = getCurrentStep();
  const ads = campaignData?.ads || [];
  const campaign = campaignData?.campaign;

  if (phase === 'running') {
    return (
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, marginBottom: '4px' }}>
          <span className="rainbow-text">Pipeline Running</span>
        </h1>
        <p style={{ color: 'var(--muted)', fontSize: '0.875rem', marginBottom: '2rem' }}>
          Watching the agent pipeline generate, evaluate, and iterate in real-time.
        </p>

        {/* Stepper */}
        <div className="card" style={{ padding: '1.5rem 2rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0' }}>
            {PIPELINE_STEPS.map((step, i) => (
              <div key={step} style={{ display: 'contents' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', minWidth: '60px' }}>
                  <div className={`stepper-dot ${i < currentStep ? 'stepper-dot-done' : i === currentStep ? 'stepper-dot-active' : ''}`} />
                  <span className="mono" style={{ fontSize: '0.65rem', color: i <= currentStep ? 'var(--text)' : 'var(--muted)' }}>{step}</span>
                </div>
                {i < PIPELINE_STEPS.length - 1 && (
                  <div className={`stepper-line ${i < currentStep ? 'stepper-line-done' : ''}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Iteration cards */}
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          {ads.map((ad: any, i: number) => {
            const ev = ad.evaluation;
            return (
              <div key={ad.id} className="card fade-in" style={{ padding: '1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  {ev && <ScoreRing score={ev.aggregate_score} size={50} />}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px' }}>
                      <span className={`badge badge-${ad.status}`}>{ad.status}</span>
                      <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>iteration {ad.iteration_number}</span>
                      {ev && (
                        <span style={{ fontSize: '0.7rem', color: ev.meets_threshold ? 'var(--green-text)' : 'var(--amber-text)', fontWeight: 600 }}>
                          {ev.meets_threshold ? '✓ passes' : '✗ below threshold'}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{ad.headline}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {ad.primary_text?.slice(0, 120)}{ad.primary_text?.length > 120 ? '...' : ''}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Skeleton while running */}
          {currentStep < 3 && (
            <div className="card" style={{ padding: '1.25rem' }}>
              <div className="progress-rainbow" style={{ marginBottom: '16px' }} />
              <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
                <div className="skeleton-block" style={{ width: 50, height: 50, borderRadius: '50%' }} />
                <div style={{ flex: 1 }}>
                  <div className="skeleton-block" style={{ height: 14, width: '40%', marginBottom: 8 }} />
                  <div className="skeleton-block" style={{ height: 12, width: '80%' }} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  /* ── RENDER: Done Phase ────────────────────────────────── */
  const failed = campaign?.status === 'failed';

  return (
    <div>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 600, marginBottom: '4px' }}>
        <span className="rainbow-text">{failed ? 'Pipeline Failed' : 'Ad Created'}</span>
      </h1>
      <p style={{ color: 'var(--muted)', fontSize: '0.875rem', marginBottom: '2rem' }}>
        {failed
          ? 'The pipeline encountered an error. Try again with different parameters.'
          : `Generated ${ads.length} ad${ads.length !== 1 ? 's' : ''} with full evaluation scores.`
        }
      </p>

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '2rem' }}>
        <button
          onClick={resetForm}
          style={{
            padding: '10px 24px', borderRadius: '10px', border: 'none', cursor: 'pointer',
            background: 'var(--gradient-rainbow)', color: '#fff',
            fontSize: '0.9rem', fontWeight: 600, fontFamily: 'inherit',
          }}
        >
          Create Another
        </button>
        {campaignId && (
          <a
            href={`/campaigns/${campaignId}`}
            style={{
              padding: '10px 24px', borderRadius: '10px', border: '1px solid var(--border)',
              background: 'var(--surface2)', color: 'var(--text)', textDecoration: 'none',
              fontSize: '0.9rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center',
            }}
          >
            View Full Campaign
          </a>
        )}
      </div>

      {/* Full ad results */}
      <div style={{ display: 'grid', gap: '2.5rem' }}>
        {ads.map((ad: any) => {
          const ev = ad.evaluation;
          const hasVisual = ev && (ev.visual_brand_consistency != null || ev.scroll_stopping_power != null);
          return (
            <div key={ad.id} className="fade-in">
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '12px' }}>
                <span className={`badge badge-${ad.status}`}>{ad.status}</span>
                <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>iteration {ad.iteration_number}</span>
                {ev?.cost_usd && <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>${ev.cost_usd?.toFixed(4) || ad.cost_usd?.toFixed(4)}</span>}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: ev ? '1fr 1fr 1fr' : '1fr 1fr', gap: '1.5rem', alignItems: 'stretch' }}>
                <FacebookAdPreview ad={ad} />
                <InstagramAdPreview ad={ad} />

                {ev && (
                  <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    {/* Aggregate score */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <ScoreRing score={ev.aggregate_score} size={60} />
                      <div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          {hasVisual ? '7-Dimension Score' : '5-Dimension Score'}
                        </div>
                        <div style={{ fontSize: '0.9rem', color: ev.meets_threshold ? 'var(--green-text)' : 'var(--amber-text)', fontWeight: 600 }}>
                          {ev.meets_threshold ? '✓ Passes threshold' : '✗ Below threshold'}
                        </div>
                      </div>
                    </div>

                    {/* Radar */}
                    <RadarChart scores={{
                      clarity: ev.clarity ?? 0,
                      value_proposition: ev.value_proposition ?? 0,
                      cta_score: ev.cta_score ?? 0,
                      brand_voice: ev.brand_voice ?? 0,
                      emotional_resonance: ev.emotional_resonance ?? 0,
                    }} />

                    {/* Text dimensions */}
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px', fontWeight: 600 }}>
                        Text Dimensions
                      </div>
                      {TEXT_DIMS.map(({ key, label, color }) => (
                        <DimScore key={key} label={label} score={ev[key]} color={color} />
                      ))}
                    </div>

                    {/* Visual dimensions */}
                    {hasVisual && (
                      <div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px', fontWeight: 600 }}>
                          Visual Dimensions
                        </div>
                        {VISUAL_DIMS.map(({ key, label, color }) => (
                          <DimScore key={key} label={label} score={ev[key]} color={color} />
                        ))}
                      </div>
                    )}

                    {/* Weakest dimension */}
                    {ev.weakest_dimension && (
                      <div style={{ padding: '12px', background: 'var(--surface2)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: '0.7rem', color: '#f97316', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px', fontWeight: 600 }}>
                          ⚠ Weakest: {ev.weakest_dimension.replace(/_/g, ' ')}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--muted)', lineHeight: 1.6 }}>
                          {ev.improvement_suggestion || 'No suggestion available'}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
