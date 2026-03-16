'use client';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export interface EvalConfig {
  threshold: number;
  floor: number;
  ratchet_active: boolean;
  ratchet_sample_size: number;
  ratchet_headroom: number;
  text_weights: Record<string, number>;
  full_weights: Record<string, number>;
  text_dimensions: string[];
  all_dimensions: string[];
  db_text_dimensions: string[];
  db_all_dimensions: string[];
  max_iterations: number;
}

const DEFAULT_CONFIG: EvalConfig = {
  threshold: 7.0,
  floor: 7.0,
  ratchet_active: false,
  ratchet_sample_size: 0,
  ratchet_headroom: 2.0,
  text_weights: {
    clarity: 0.15,
    value_proposition: 0.20,
    cta_strength: 0.15,
    brand_voice: 0.15,
    emotional_resonance: 0.35,
  },
  full_weights: {
    clarity: 0.10,
    value_proposition: 0.15,
    cta_strength: 0.10,
    brand_voice: 0.10,
    emotional_resonance: 0.25,
    visual_brand_consistency: 0.10,
    scroll_stopping_power: 0.20,
  },
  text_dimensions: ['clarity', 'value_proposition', 'cta_strength', 'brand_voice', 'emotional_resonance'],
  all_dimensions: ['clarity', 'value_proposition', 'cta_strength', 'brand_voice', 'emotional_resonance', 'visual_brand_consistency', 'scroll_stopping_power'],
  db_text_dimensions: ['clarity', 'value_proposition', 'cta_score', 'brand_voice', 'emotional_resonance'],
  db_all_dimensions: ['clarity', 'value_proposition', 'cta_score', 'brand_voice', 'emotional_resonance', 'visual_brand_consistency', 'scroll_stopping_power'],
  max_iterations: 3,
};

let cachedConfig: EvalConfig | null = null;
let fetchPromise: Promise<EvalConfig> | null = null;

function fetchConfig(): Promise<EvalConfig> {
  if (cachedConfig) return Promise.resolve(cachedConfig);
  if (fetchPromise) return fetchPromise;
  fetchPromise = fetch(`${API}/evaluator/config`)
    .then(r => r.ok ? r.json() : DEFAULT_CONFIG)
    .then(cfg => { cachedConfig = cfg; return cfg; })
    .catch(() => DEFAULT_CONFIG);
  return fetchPromise;
}

export function useEvalConfig(): EvalConfig {
  const [config, setConfig] = useState<EvalConfig>(cachedConfig || DEFAULT_CONFIG);
  useEffect(() => { fetchConfig().then(setConfig); }, []);
  return config;
}

/** Score color helpers derived from threshold */
export function scoreColor(score: number, threshold: number): string {
  if (score >= threshold + 1.0) return 'var(--green-text)';
  if (score >= threshold - 0.5) return 'var(--amber-text)';
  return 'var(--red-text)';
}

export function scoreBg(score: number, threshold: number): string {
  if (score >= threshold + 1.0) return 'var(--green-bg)';
  if (score >= threshold - 0.5) return 'var(--amber-bg)';
  return 'var(--red-bg)';
}

export function scoreBorder(score: number, threshold: number): string {
  if (score >= threshold + 1.0) return 'var(--green-border)';
  if (score >= threshold - 0.5) return 'var(--amber-border)';
  return 'var(--red-border)';
}

/** ScoreRing gradient based on threshold */
export function scoreGradient(score: number, threshold: number): string {
  if (score >= threshold + 1.0) return 'conic-gradient(from 220deg, #16a34a, #00d4cf)';
  if (score >= threshold) return 'conic-gradient(from 220deg, #fbbf24, #f97316)';
  return 'conic-gradient(from 220deg, #f06c6c, #ec4899)';
}

/** Dimension label formatter */
export function dimLabel(d: string): string {
  return d.replace(/_/g, ' ').replace(/\b\w/g, (ch: string) => ch.toUpperCase()).replace(/\bCta\b/, 'CTA');
}
