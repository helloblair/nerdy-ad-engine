# Technical Writeup — Nerdy Ad Engine
*Kirsten Blair — Gauntlet AI Cohort*

## What I Built

An autonomous ad copy generation and evaluation pipeline for Varsity Tutors (Nerdy), targeting Facebook and Instagram paid social. The system takes a campaign brief — audience, product, goal, tone — and generates ad copy through a multi-agent pipeline that writes, evaluates, fixes, and saves ads without human intervention. The core idea: separate the model that generates from the model that judges, then use the judge's structured feedback to iteratively improve quality before anything ships.

## Architecture

Five agents orchestrated by a LangGraph state machine:

- **ResearcherAgent** — Reads a static reference ads library (`reference_ads/varsity_tutors.json`) and extracts creative patterns (hook types, proof points, brand voice rules). Runs once per campaign, not per iteration, because the reference patterns don't change. Deliberately not an LLM call — deterministic extraction is faster, cheaper, and more reliable when the answer is already documented.
- **WriterAgent** (Gemini 2.5 Flash) — Generates ad copy given a brief, persona targeting, and optional fixer feedback. Outputs structured JSON: primary_text, headline, description, cta_button. Supports A/B variant generation with 5 hook strategies (pain_point, social_proof, urgency, aspirational, question).
- **ImageAgent** (Imagen 4 via Gemini API) — Generates photorealistic ad creative images from persona-specific visual style prompts. Runs after the writer, before evaluation. If image generation fails, the pipeline falls back gracefully to text-only evaluation.
- **EvaluatorAgent** (Claude Sonnet 4.6) — LLM-as-judge. Scores each ad across 5 text dimensions + 2 visual dimensions (when image present) with confidence per dimension. Uses Claude's vision capability to evaluate generated images alongside copy. Returns structured JSON with rationales. Calibrated against real Nerdy SAT messaging guidance with explicit brand voice penalties.
- **FixerAgent** (Claude Sonnet 4.6) — Reads evaluation results, identifies the weakest dimension, and produces a targeted repair instruction for the writer. Has dimension-specific fix strategies derived from reference ad analysis.

The graph flow: `researcher → writer → image_agent → evaluator → decision gate`. If the aggregate score is below threshold, the evaluator's output routes to the fixer, which generates a targeted instruction, and the writer regenerates. This loops up to 3 iterations. If the ad still hasn't passed after 3 iterations, it's flagged for human review instead of looping forever.

**Quality Ratchet:** The system implements a dynamic quality threshold that ratchets upward as more ads are approved. Once 10+ ads have been approved, the threshold is set to the 25th percentile of approved scores with gradual headroom (+0.5 per 10 ads, ceiling at 9.0). The ratchet can only go up, never down — ensuring quality never regresses. The floor remains 7.0.

**Persona Targeting:** Campaigns can target one of 15 parent personas (e.g., "The Anxious Achiever Parent", "The Value-Conscious Researcher"), each with detailed psychology profiles, emotional triggers, and proven hook patterns derived from real Nerdy sales call data. The persona context flows through the entire pipeline — writer, image agent, and evaluator all see it.

**Infrastructure:**
- Backend: FastAPI deployed on Fly.io (Dallas region, `dfw`)
- Database: Supabase Postgres (production) + SQLite (local development)
- Frontend: Next.js on Vercel
- Observability: Langfuse integration for tracing pipeline runs

**Why dual DB:** I needed local dev to work without live Supabase credentials. Added a `db.py` abstraction layer so SQLite mirrors the Supabase schema exactly — same method signatures, same return shapes. The pipeline code never touches SQL directly; it calls `get_db()` which returns either backend based on environment.

## Why Two Models?

This was a deliberate separation-of-concerns decision, not a cost optimization.

Gemini 2.5 Flash writes because it's fast, cheap, and produces high creative variance — you want the writer to explore a wide output distribution. Claude Sonnet judges because it's better at structured reasoning, consistent calibration, and decomposing quality into discrete dimensions. When I tested single-model (Claude writes + Claude judges), the evaluator was systematically lenient toward its own outputs. The generator that creates shouldn't be the model that evaluates — same reason you don't grade your own exams.

## The Evaluation Framework

Seven dimensions across two modes, weighted differently based on whether an image is present:

**Text-only evaluation (5 dimensions):**
- **Clarity** (15%) — Is the message immediately understandable?
- **Value Proposition** (20%) — Does it communicate a clear, compelling benefit?
- **CTA Strength** (15%) — Is the call-to-action specific and motivating?
- **Brand Voice** (15%) — Does it match Varsity Tutors' tone?
- **Emotional Resonance** (35%) — Does it connect emotionally with the audience?

**Full evaluation with image (7 dimensions):**
- **Clarity** (10%) — Is the message immediately understandable?
- **Value Proposition** (15%) — Does it communicate a clear, compelling benefit?
- **CTA Strength** (10%) — Is the call-to-action specific and motivating?
- **Brand Voice** (10%) — Does it match Varsity Tutors' tone?
- **Emotional Resonance** (25%) — Does it connect emotionally with the audience?
- **Visual Brand Consistency** (10%) — Does the image match the Varsity Tutors brand aesthetic?
- **Scroll-Stopping Power** (20%) — Would this image stop a parent mid-scroll on Instagram?

Emotional resonance is deliberately the highest-weighted dimension in both modes. A survey of 146 real parents showed it's the #1 predictor of whether a parent clicks — ads that score well on structure but poorly on emotion get rejected by humans 70%+ of the time.

Threshold to pass: 7.0 (weighted aggregate), subject to the quality ratchet which can push it higher as the ad library grows. The evaluator recalculates the aggregate server-side rather than trusting the LLM's math — I caught rounding drift early in calibration.

The evaluator system prompt includes the "Parent Click Test" — before scoring, it asks: "Would a real parent — tired, scrolling Instagram at 10pm, worried about their kid's future — actually stop and tap this?" This anchors scores against human behavior rather than structural correctness. Brand voice penalties automatically score ≤5.0 for corporate language, fake scarcity, or vague claims.

Calibration results: 8.6 on the best reference ad ("Her SAT score jumped 360 points in 8 weeks") vs 2.8 on a deliberately bad corporate ad ("Varsity Tutors offers personalized tutoring services"). Score gap of 5.8 points — the evaluator can distinguish quality.

Each dimension also carries a confidence score (0.0–1.0). If any dimension's confidence drops below 0.6, the ad is flagged `needs_human_review` — the evaluator knows when it's uncertain.

## Key Findings

- **Emotional resonance was the persistent weakness — now addressed.** Originally weighted at 15%, it was flagged as the weakest dimension across most generated ads. After analyzing the confusion matrix data from 146 parent ratings, emotional resonance was reweighted to 35% (text-only) / 25% (with image) — making it the single highest-weighted dimension. The evaluator system prompt now includes strict emotional resonance scoring rules and automatic penalties for emotionally flat copy.
- **AI pass rate is ~100%, human approval is 43.3%.** This is the most important signal in the system. The confusion matrix (90 human ratings collected via survey) shows the AI approves ads that humans wouldn't click on. Precision of 43.3% means the evaluator is too lenient.
- **The confusion matrix is how the system learns.** High false positives = AI too lenient. The fix: raise the threshold, increase emotional resonance weight, or add human-calibrated examples to the evaluation prompt.
- **Self-healing regression detection works.** When the fixer's repair doesn't improve the target dimension between iterations, the pipeline detects the regression and tells the fixer to try a completely different approach. This prevents wasted iterations where the same failing strategy is repeated.

## What I'd Do Differently

- **~~Raise emotional resonance weight from 15% to ~25%~~** — Done. Raised to 35% (text-only) / 25% (with image) based on confusion matrix data. This was the single highest-leverage config change available.
- **Deploy Langfuse from day 1**, not after the pipeline was already running. Cost tracking and trace inspection would have caught the evaluator leniency issue earlier.
- **Build the db abstraction layer before any agents**, not after. I wired agents to Supabase first, then had to retrofit SQLite support when local dev became painful.
- **Add confidence scoring earlier.** Evaluator overconfidence was the core bug — it was giving 0.85+ confidence on scores that humans disagreed with. Adding confidence didn't fix this fully; the next step is calibrating confidence against the human ratings.
- **Collect human ratings from day 1** in parallel with pipeline development, not sequentially.
- **Wire evaluator config as a single source of truth from the start.** I had hardcoded thresholds, weights, and dimension lists scattered across 15+ files. Eventually built a proper sync system where `evaluator_agent.py` is the sole source and everything else derives from it via an API endpoint (`/evaluator/config`), but retrofitting was painful.

## Results

- 50+ ads generated across 9+ campaigns targeting 15 parent personas
- 8.4 average AI score (weighted aggregate)
- 90+ human ratings collected via survey interface
- 43.3% precision on human-AI alignment (confusion matrix)
- 3+ documented iteration improvement cycles with measurable score lifts (avg +1.7 points over 3 iterations)
- Multi-model architecture: Gemini 2.5 Flash (writer) + Imagen 4 (image generation) + Claude Sonnet 4.6 (evaluator + fixer)
- 7-dimension evaluation framework with 5 text + 2 visual dimensions
- A/B variant generation with 5 hook strategies per campaign
- Dynamic quality ratchet that raises the bar as the ad library improves
- Full observability pipeline: Langfuse tracing, cost estimation, analytics dashboard
- Single source of truth architecture: evaluator config propagates to all backend and frontend components via `/evaluator/config` API
