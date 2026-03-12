# Decision Log

A living record of architectural and technical decisions made during this project.
Each entry captures the reasoning behind significant choices — written for future collaborators,
evaluators, and future-me who will have forgotten why we did it this way.

---

## [2026-03-08] — Chose This Project Over The Other Two

**Decision:** Selected the Autonomous Content Generation System (Project 2) over the Live AI Video Tutor (Project 1) and the Live Session Analysis tool (Project 3).

**Why:** Project 1 required a 4-vendor real-time pipeline (STT → LLM → TTS → avatar) with a hard sub-second latency requirement and automatic point deductions for missing any piece. Project 3 required validated computer vision accuracy (85%+ eye contact detection) in 48 hours against variable real-world conditions. Project 2 maps directly to existing skills — LangGraph, FastAPI, Next.js — and has a clear path to hitting every grading criterion without exotic dependencies.

**Tradeoffs:** Project 1 had a flashier demo. Project 2 wins on execution probability under a 48-hour deadline.

**Context:** 48-hour sprint, competition submission, deploy-first workflow required.

---

## [2026-03-08] — Monorepo Structure

**Decision:** Single GitHub repo (`nerdy-ad-engine`) with `frontend/`, `backend/`, `reference_ads/`, and `docs/` as top-level folders.

**Why:** Keeps everything version-controlled together — design decisions, reference data, and code all live in one place. Evaluators can clone one repo and see the full picture. Easier to cross-reference frontend and backend code during a fast build.

**Tradeoffs:** Slightly more complex deployment config (Vercel needs to know to look in `frontend/`, Fly.io in `backend/`). Worth it for the organizational clarity.

---

## [2026-03-08] — Private Repo During Development, Public At Submission

**Decision:** Repo is private during the build, made public at submission time.

**Why:** This project works with Varsity Tutors' real brand data, real ad copy, and real competitive intelligence. A public repo during development risks exposing that data to scrapers, and risks other Gauntlet students seeing the approach before submissions close. The brief says "GitHub preferred" for submission — not "must be public during development."

**Tradeoffs:** Evaluators can't see progress in real time, but that's fine since submission is the deliverable.

---

## [2026-03-08] — Frontend Deployed To Vercel

**Decision:** Next.js frontend deployed to Vercel.

**Why:** Vercel invented Next.js — their infrastructure is purpose-built for it. Zero configuration required, automatic preview deployments on every push, edge network serves assets from servers close to users worldwide, and the free tier is genuinely production-grade. The alternative (AWS S3 + CloudFront) gives similar performance but takes hours to configure correctly.

**Tradeoffs:** Locked into Vercel's ecosystem to some degree. Acceptable given the time constraint and the fact that Next.js apps rarely need to migrate off Vercel.

---

## [2026-03-08] — Backend Deployed To Fly.io

**Decision:** FastAPI backend deployed to Fly.io rather than Vercel or Railway.

**Why:** Vercel is serverless — every request spins up fresh and dies after 60-300 seconds. Our LangGraph agent pipeline is stateful and long-running: a campaign generation job runs for several minutes, the iteration loop needs to persist state between generate → evaluate → fix cycles, and background jobs need to keep running after the HTTP request that triggered them completes. Fly.io gives us a real persistent Linux VM with no execution time ceiling. It also runs Docker containers natively, so local dev and production are identical.

**Tradeoffs:** Slightly more setup than Railway (requires a Dockerfile and fly.toml). Worth it for the persistent process model. Railway was considered but Fly.io has better ARM support for the M-series Mac build environment.

**Context:** App is deployed to Dallas region (`dfw`) — closest fast Fly.io region to Austin, TX where development is happening.

---

## [2026-03-08] — Database: Supabase Over Raw Postgres

**Decision:** Supabase (managed Postgres) rather than a raw Postgres instance on Fly.io or Neon.

**Why:** Supabase gives us Postgres plus several things we'd otherwise have to build ourselves: a REST API that the frontend can query directly for simple reads (reducing backend load), realtime subscriptions so the ad library can update live as ads are generated (a key demo moment), Row Level Security built in at the database layer, and a dashboard UI for inspecting data during development. It's also independent of our backend — if Fly.io has an issue, the data is safe.

**Tradeoffs:** Adds a third platform dependency. Free tier has a 500MB database limit and pauses after 1 week of inactivity. Both acceptable for a sprint project — a production deployment would use a paid tier.

**Context:** Row Level Security (RLS) enabled by default on all new tables. Data API enabled for `supabase-js` client compatibility.

---

## [2026-03-08] — Database Schema: Four Tables

**Decision:** Schema consists of four tables: `campaigns`, `ads`, `evaluations`, `iterations`.

**Why:** Each table maps directly to a grading criterion. `campaigns` captures the brief and tracks pipeline status (System Design, 20%). `ads` stores the actual generated copy (50+ ads requirement). `evaluations` stores all 5 dimension scores with rationale per ad (Quality Measurement, 25%). `iterations` tracks before/after scores per improvement cycle — this is the table that proves the system improves over time (Iteration & Improvement, 20%).

**Tradeoffs:** Could have simplified to 2-3 tables, but the `iterations` table specifically is what enables the quality trend visualizations that hit bonus criteria. Worth the extra join complexity.

**Key schema decisions:**
- UUIDs over integer IDs — safe to generate client-side for parallel agent writes, non-guessable for production security
- `NUMERIC(3,1)` for scores — enforces 1-10 range with one decimal at the database level, rejects malformed LLM output before it corrupts trend data
- `CHECK` constraints on status fields — makes invalid status values literally impossible to store
- `ON DELETE CASCADE` on all foreign keys — clean teardown when a campaign is deleted

---

## [2026-03-08] — Multi-Model Architecture: Gemini Flash + Claude Sonnet

**Decision:** Use Gemini 2.0 Flash for generation (ResearcherAgent, WriterAgent, FixerAgent) and Claude Sonnet 4.6 for evaluation (EvaluatorAgent).

**Why:** The brief explicitly recommends Gemini for copy generation. More importantly, generation and evaluation have fundamentally different requirements. Generation is high-volume and benefits from speed and cost efficiency — Gemini 2.0 Flash is excellent at constrained creative tasks and costs a fraction of frontier models. Evaluation requires careful multi-dimensional reasoning about quality — this is where model capability directly determines whether the product works, so Claude Sonnet's reasoning quality justifies the cost premium. Spending tokens on the judge, not the writer, is the right allocation.

**Tradeoffs:** Two API integrations instead of one. Worth it for the quality difference on evaluation AND it hits the multi-model orchestration bonus criterion (+3 points) with documented rationale.

**Cost estimate:** ~$5-15 total for the full 50+ ad demo run. Performance-per-token (north star metric per the brief) is optimized by this split.

---

## [2026-03-08] — Reference Ads: Meta Ad Library + Synthetic Ground Truth

**Decision:** Use publicly available Meta Ad Library ads as reference data rather than waiting for official Varsity Tutors Slack assets.

**Why:** Nerdy explicitly said "we encourage them to use publicly available data or mock data." The Meta Ad Library has ~96 Varsity Tutors ads including active campaigns — this is their real production creative, which is arguably more valuable than internal reference assets because it shows what they're currently spending money on (implying performance). Synthetic ground truth ads at both quality extremes (deliberately bad ~3/10, deliberately excellent ~9/10) are also created to calibrate the evaluator before it touches real generation.

**Tradeoffs:** None meaningful. This is the right approach regardless of whether Slack assets arrive.

---

## [2026-03-11] — Evaluator Taste Is Derived, Not Invented — And the Confusion Matrix Proves the Gap

**Decision:** Accept that the EvaluatorAgent's quality judgment measures *structural craft* (clarity, brand voice, CTA strength) rather than *human persuasion* (would a real parent click this?). The confusion matrix confirms this gap at ~54% precision, and that's a feature, not a bug — it's the finding.

**Why:** The evaluator's "taste" is fully traceable to provided assets, not invented:

1. **PRD → 5 scoring dimensions.** The brief specified clarity, value proposition, CTA strength, brand voice, and emotional resonance as the quality axes. These became the evaluator's rubric with weights (clarity=0.20, value_proposition=0.25, cta_strength=0.20, brand_voice=0.20, emotional_resonance=0.15) and a 7.0 threshold.

2. **Real Varsity Tutors ads → brand voice rules.** Three highest-performing Varsity Tutors creatives were documented in `reference_ads/varsity_tutors.json` with quality scores (8.5, 9.0, 9.5) and annotated patterns: math-as-urgency, tension reframe between two numbers, specific scores only, zero adjectives, date anchoring, the child is not the problem. These patterns flow into both the WriterAgent (via ResearcherAgent's `format_for_prompt()`) and the EvaluatorAgent's SYSTEM_PROMPT brand voice rules.

3. **Confusion matrix reveals the gap.** When 146 real parents rated the AI-approved ads in a crowdsourced survey, precision was ~54% — meaning roughly half the ads the AI approved, humans found unpersuasive. The AI isn't wrong about craft quality; it's measuring the wrong thing for predicting human response. An ad can be structurally excellent (clear, on-brand, specific CTA) and still fail to move a parent emotionally.

**Tradeoffs:** We could retrain the evaluator on human disagreement data (feed FP and FN cases back as few-shot examples), but that requires enough human ratings to be statistically meaningful — and we now have 146. A v2 iteration would use the confusion matrix quadrants directly: TPs confirm the evaluator's instincts, FPs reveal what "looks good but doesn't persuade," FNs reveal what "looks rough but actually works." This is the canonical RLHF pattern: use human signal to close the loop on automated judgment.

**Context:** This is arguably the most important finding of the project. The system works exactly as designed — the gap between AI craft judgment and human persuasion judgment is measurable, documented, and designable. The confusion matrix isn't showing a failure; it's showing the research question the PRD asked us to answer.

---
