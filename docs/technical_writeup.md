# Technical Writeup — Nerdy Ad Engine
*Kirsten Blair — Gauntlet AI Cohort*

## What I Built

An autonomous ad copy generation and evaluation pipeline for Varsity Tutors (Nerdy), targeting Facebook and Instagram paid social. The system takes a campaign brief — audience, product, goal, tone — and generates ad copy through a multi-agent pipeline that writes, evaluates, fixes, and saves ads without human intervention. The core idea: separate the model that generates from the model that judges, then use the judge's structured feedback to iteratively improve quality before anything ships.

## Architecture

Four agents orchestrated by a LangGraph state machine:

- **ResearcherAgent** — Reads a static reference ads library (`reference_ads/varsity_tutors.json`) and extracts creative patterns (hook types, proof points, brand voice rules). Runs once per campaign, not per iteration, because the reference patterns don't change. Deliberately not an LLM call — deterministic extraction is faster, cheaper, and more reliable when the answer is already documented.
- **WriterAgent** (Gemini 2.5 Flash) — Generates ad copy given a brief and optional fixer feedback. Outputs structured JSON: primary_text, headline, description, cta_button.
- **EvaluatorAgent** (Claude Sonnet 4.6) — LLM-as-judge. Scores each ad across 5 dimensions with confidence per dimension. Returns structured JSON with rationales.
- **FixerAgent** (Claude Sonnet 4.6) — Reads evaluation results, identifies the weakest dimension, and produces a targeted repair instruction for the writer. Has dimension-specific fix strategies derived from reference ad analysis.

The graph flow: `researcher → writer → evaluator → decision gate`. If the aggregate score is below 7.0, the evaluator's output routes to the fixer, which generates a targeted instruction, and the writer regenerates. This loops up to 3 iterations. If the ad still hasn't passed after 3 iterations, it's flagged for human review instead of looping forever.

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

Five dimensions, weighted:
- **Clarity** (20%) — Is the message immediately understandable?
- **Value Proposition** (25%) — Does it communicate a clear, compelling benefit?
- **CTA Strength** (20%) — Is the call-to-action specific and motivating?
- **Brand Voice** (20%) — Does it match Varsity Tutors' tone?
- **Emotional Resonance** (15%) — Does it connect emotionally with the audience?

Threshold to pass: 7.0 (weighted aggregate). The evaluator recalculates the aggregate server-side rather than trusting the LLM's math — I caught rounding drift early in calibration.

Calibration results: 8.6 on the best reference ad ("Her SAT score jumped 360 points in 8 weeks") vs 2.8 on a deliberately bad corporate ad ("Varsity Tutors offers personalized tutoring services"). Score gap of 5.8 points — the evaluator can distinguish quality.

Each dimension also carries a confidence score (0.0–1.0). If any dimension's confidence drops below 0.6, the ad is flagged `needs_human_review` — the evaluator knows when it's uncertain.

## Key Findings

- **Emotional resonance is the persistent weakness.** Flagged as weakest dimension across the majority of generated ads. Average score ~7.2 while other dimensions average 7.8–8.5. The weight (15%) is too low given how much humans care about it.
- **AI pass rate is ~100%, human approval is 43.3%.** This is the most important signal in the system. The confusion matrix (90 human ratings collected via survey) shows the AI approves ads that humans wouldn't click on. Precision of 43.3% means the evaluator is too lenient.
- **The confusion matrix is how the system learns.** High false positives = AI too lenient. The fix: raise the threshold, increase emotional resonance weight, or add human-calibrated examples to the evaluation prompt.
- **Self-healing regression detection works.** When the fixer's repair doesn't improve the target dimension between iterations, the pipeline detects the regression and tells the fixer to try a completely different approach. This prevents wasted iterations where the same failing strategy is repeated.

## What I'd Do Differently

- **Raise emotional resonance weight from 15% to 25%** based on confusion matrix data showing humans weight emotional connection more heavily than the evaluator does.
- **Deploy Langfuse from day 1**, not after the pipeline was already running. Cost tracking and trace inspection would have caught the evaluator leniency issue earlier.
- **Build the db abstraction layer before any agents**, not after. I wired agents to Supabase first, then had to retrofit SQLite support when local dev became painful.
- **Add confidence scoring earlier.** Evaluator overconfidence was the core bug — it was giving 0.85+ confidence on scores that humans disagreed with. Adding confidence didn't fix this fully; the next step is calibrating confidence against the human ratings.
- **Collect human ratings from day 1** in parallel with pipeline development, not sequentially.

## Results

- 50+ ads generated across 9 campaigns
- 8.4 average AI score (weighted aggregate)
- 90 human ratings collected via survey interface
- 43.3% precision on human-AI alignment (confusion matrix)
- 3+ documented iteration improvement cycles with measurable score lifts
- Dual-model architecture: Gemini 2.5 Flash (writer) + Claude Sonnet 4.6 (evaluator + fixer)
- Full observability pipeline: Langfuse tracing, cost estimation, analytics dashboard
