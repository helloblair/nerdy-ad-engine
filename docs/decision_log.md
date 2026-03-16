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

## [2026-03-08] — Dual-Model Architecture: Gemini Writes, Claude Judges

**Decision:** Use Gemini 2.5 Flash for ad copy generation and Claude Sonnet for evaluation and fixing — deliberately separating the model that creates from the model that judges.

**Why:** This wasn't about cost — it was about bias. I tested single-model first (Claude writes + Claude judges) and the evaluator was systematically lenient toward its own outputs. It recognized and rewarded its own stylistic patterns, like grading your own exam. The scores looked great on paper (averages around 8.2) but didn't hold up when I started collecting human ratings. Switching the writer to Gemini broke that feedback loop — scores dropped to a more honest ~7.8 average, and the ads that *did* pass were noticeably better. The cross-model tension forces genuinely higher quality.

Gemini Flash also brings the right properties for a writer: fast, cheap, and high creative variance. You *want* the writer exploring a wide output space, not carefully reasoning its way to one "correct" ad. Claude's strength is the opposite: structured reasoning, consistent calibration, decomposing quality into discrete dimensions. Let each model do what it's best at.

**Tradeoffs:** Two API integrations instead of one. Two sets of API keys, two billing dashboards, two failure modes. Gemini's JSON output is slightly less reliable than Claude's (hence the 3-retry parse loop in WriterAgent). And there's a philosophical cost: I can't fully formalize *why* cross-model evaluation catches more issues — I just know empirically that the score gap between good and bad ads widened from ~3 points to ~5.8 points when I split the models. Someone could argue that's coincidence. The calibration data says otherwise, but it's not a formal proof.

**Context:** The PRD recommends Gemini for generation. The evaluation model choice was left intentionally open — "Ambiguous Elements (You Decide): These are intentionally open. Your decisions reveal your thinking." Gemini's free tier also supports 50+ ad generation without burning through budget, which directly helps the performance-per-token metric. The dual-model approach earns +3 bonus for multi-model orchestration.

---

## [2026-03-08] — LangGraph for Pipeline Orchestration

**Decision:** Use LangGraph's StateGraph to orchestrate the 4-agent pipeline instead of simple LangChain chains, CrewAI, or custom Python.

**Why:** The pipeline has cycles. That's the whole thing. When an ad scores below 7.0, we need to route back through the fixer and writer, then re-evaluate — this isn't a linear chain, it's a graph with conditional edges and loops. I looked at four options:

- **LangChain chains:** No native cycle support. Would need manual loop logic bolted on top.
- **CrewAI:** Agent-centric and the role-based model maps well to 4 agents, but weaker conditional routing and less state control.
- **Custom Python:** Full control, zero dependencies. But I'd be reimplementing state management, routing, and retry logic — the pipeline *is* a state graph, so why not use a state graph framework?
- **LangGraph:** First-class conditional routing and cycles. StateGraph fits the evaluate-fix loop directly with conditional edges. Built for exactly this pattern.

The graph flow: `researcher → writer → evaluator → decision gate`. If the aggregate score is below 7.0, route to fixer, which generates a targeted instruction, then back to writer. This loops up to 3 iterations. LangGraph models this natively.

**Tradeoffs:** LangGraph is a heavier dependency than I'd like, and the learning curve is real — the docs aren't always clear on edge cases with conditional routing. A custom Python implementation would've been lighter. But I'd have spent days reimplementing what LangGraph already does: state tracking across iterations, conditional routing at the decision gate, and clean inspection of intermediate states for debugging.

**Context:** The PRD requires a feedback loop: "generate → evaluate → identify weakest dimension → targeted regeneration → re-evaluate." That "re-evaluate" at the end means the flow cycles back. Any framework that doesn't natively support cycles would require workarounds.

---

## [2026-03-09] — Dimension Weights: value_proposition at 25%, emotional_resonance at 15%

> **UPDATE [2026-03-15]:** This entry documents the *original* weight decision. The weights have since been significantly rebalanced — see the [2026-03-15] entries below for current values. Emotional resonance is now 35% (text-only) / 25% (with image), the highest-weighted dimension.

**Decision:** Weight the five evaluation dimensions unevenly: clarity (20%), value_proposition (25%), cta_strength (20%), brand_voice (20%), emotional_resonance (15%).

**Why:** Not all dimensions matter equally for ad performance. Value proposition is the most predictive dimension for whether a human would actually engage with an ad — if you don't communicate a clear benefit in the first line, nothing else matters. I weighted it highest at 25%. Emotional resonance got the lowest weight at 15% because early calibration runs suggested it was the hardest dimension to score consistently, and I wanted to avoid amplifying noisy scores.

**Tradeoffs:** Here's the honest part: **I got the emotional_resonance weight wrong.** The human ratings data (90+ ratings via the survey) showed that humans weight emotional connection *much* more heavily than 15% implies. The pattern of human "bad" ratings correlated strongly with low emotional resonance scores. **This has since been fixed** — emotional resonance is now the highest-weighted dimension at 35% (text-only) / 25% (with image).

**Context:** Equal weights were tested first and rejected (see "What Didn't Work: Unweighted Scoring" below). This entry is preserved because the decision-making process matters: starting with educated guesses, discovering they were wrong via the confusion matrix, and correcting with data is exactly how calibration should work.

---

## [2026-03-11] — SQLite + Supabase Dual-Mode Database

**Decision:** Support two database backends — SQLite for local development, Supabase (Postgres) for production — switchable via a `DB_BACKEND` environment variable, with an abstraction layer (`DatabaseInterface` ABC with 14 methods) keeping business logic database-agnostic.

**Why:** The PRD has two requirements that pull in opposite directions. "Must run locally (API keys acceptable)" and "one-command setup" demand zero-friction local dev. But there's also a live deployed version that needs persistent, multi-user storage. SQLite gives you the first for free — it's built into Python's stdlib, creates the DB file automatically, needs no credentials. Supabase gives you the second — managed Postgres with a REST API, realtime subscriptions, and row-level security. An evaluator can clone the repo, run `make install && make dev`, and have a working system in under 2 minutes with no external database setup. That's the bar. SQLite clears it.

**Tradeoffs:** Schema drift is the big one. SQLite and Supabase schemas must be manually kept in sync — there's a `migrations.py` but it's not a real migration framework. DDL changes (new columns, new tables) require manual updates in two places. I hit this during the scale run when I added a cost tracking column and forgot to update the SQLite schema. Also, SQLite is single-writer, so it wouldn't survive concurrent API requests in production.

And I should've built the abstraction layer *first* — I wired agents directly to Supabase initially, then had to retrofit SQLite support when local dev became painful. Classic "should've done it right the first time" lesson.

**Context:** Deployed version uses Supabase (Postgres). Local dev defaults to SQLite. Both share the same API surface via `get_db()`.

---

## [2026-03-09] — Server-Side Weighted Average (Don't Trust LLM Math)

**Decision:** Calculate the aggregate evaluation score in Python using a weighted average, not by asking the LLM to compute it.

**Why:** LLMs are unreliable at arithmetic. I caught rounding drift early in calibration — the evaluator would report dimension scores that didn't add up to the aggregate it claimed. Sometimes off by 0.3 points, sometimes by a full point. When your quality threshold is 7.0 and the difference between "approved" and "needs fixing" is a few tenths, you can't tolerate that. So the evaluator returns per-dimension scores and the pipeline computes the aggregate deterministically in Python. Simple multiplication and addition. No hallucinated math.

**Tradeoffs:** Minor: the evaluator's JSON response includes an `aggregate_score` field that we effectively ignore. It's there because the prompt originally asked for it and removing it might destabilize the output format. A cleaner design would strip it from the schema entirely. But it doesn't cause harm — it's just dead data.

**Context:** This is the kind of bug that's invisible until it isn't. If you're shipping ads based on a quality threshold, the thing computing the score had better be deterministic. This decision took 10 minutes to implement and probably saved hours of debugging mysterious threshold behavior. The server-side recalculation catches the ~15% of cases where the LLM's self-reported aggregate doesn't match its own dimension scores.

---

## [2026-03-09] — ResearcherAgent Runs Once Per Campaign, Not Per Ad

**Decision:** The ResearcherAgent extracts reference ad patterns once at the start of a campaign and passes that context to all subsequent ad generations, rather than re-running for each ad.

**Why:** The reference ads are a static JSON file (`reference_ads/varsity_tutors.json`). The patterns — hook types, proof points, brand voice rules — don't change between the first ad in a campaign and the fifth. Re-running the researcher for each ad would mean re-reading the same file and re-extracting the same patterns — pure waste. The ResearcherAgent is also deliberately *not* an LLM call. It's deterministic extraction from structured data. Using an LLM to re-derive patterns that are already documented in JSON would be slower, more expensive, and less reliable. Use LLMs where judgment is needed (writing, evaluating, fixing), use deterministic code where the answer is already known.

**Tradeoffs:** If the reference ads were dynamic (say, pulled from a live competitor intelligence API), this decision would be wrong — you'd want to re-fetch per ad to catch updates. But they're not dynamic; they're a curated JSON file. The only real cost is that adding new reference ads requires restarting the campaign to pick up the changes.

**Context:** The pipeline state carries `research_context` from the researcher node through all subsequent iterations. It's set once and read many times. Keeps the LangGraph state clean and the API costs down.

---

## [2026-03-09] — What Didn't Work: Holistic Scoring

**Decision:** Abandoned single-score holistic evaluation in favor of 5-dimension weighted scoring.

**Why:** I started with the simplest possible evaluation: "Rate this ad 1-10." The scores were wildly inconsistent. The same ad would score 6.5 on one run and 8.0 on the next — run-to-run variance of ~1.5 points. That's useless for a quality gate. Breaking evaluation into five independent dimensions (clarity, value_proposition, cta_strength, brand_voice, emotional_resonance) reduced variance to ~0.3 points. My theory: forcing the evaluator to reason about each aspect separately constrains its output and reduces the impact of whatever mood the model is in on any given call.

**Tradeoffs:** More complex output schema. More tokens per evaluation (5 rationales instead of 1). Harder to explain to non-technical stakeholders. But the stability gain was non-negotiable — you can't build a fix loop on top of a score that changes randomly between runs.

**Context:** This was the first major pivot in the evaluation design. It happened early and shaped everything that followed — the fixer targets the weakest *dimension*, the weights reflect *dimension* importance, the regression detection tracks *dimension-level* changes. Everything downstream depends on this being stable.

---

## [2026-03-09] — What Didn't Work: Non-JSON Evaluator Output

**Decision:** Switched from natural language evaluation output to strict JSON-only responses after parsing failures broke the pipeline every third run.

**Why:** The evaluator initially returned natural language with scores embedded in prose: "The clarity of this ad is strong, I'd rate it an 8/10..." Parsing this was fragile. The model would format scores differently, use different delimiters, or bury the score in a parenthetical. It broke on roughly every third run. Switching to JSON-only with a strict schema and explicit "respond with valid JSON only, no preamble, no markdown" instructions solved it. Adding retry logic for the rare JSON parse failure made it robust.

**Tradeoffs:** The JSON constraint limits the evaluator's expressiveness. Natural language rationales were sometimes more nuanced and useful for debugging. But reliability beats nuance when you're running a pipeline at scale. The structured `rationale` fields in the JSON schema capture 90% of the useful signal anyway.

**Context:** This is a common pain point with LLM-as-judge systems. The model *wants* to be conversational. You have to be very explicit about output format, and even then, you need retry logic as a safety net.

---

## [2026-03-09] — What Didn't Work: Single-Model Generation + Evaluation

**Decision:** Rejected using Claude Sonnet for both writing and judging ads after testing revealed systematic leniency.

**Why:** When Claude writes an ad and Claude evaluates it, the evaluator is lenient toward its own stylistic patterns. It's not deliberately biased — it just shares blind spots with the generator. The scores looked good (averages around 8.2) but the ads themselves were... fine. Competent but not compelling. When I switched the writer to Gemini and kept Claude as the judge, two things happened: scores dropped (average ~7.8, more honest) and the ads that *did* pass were noticeably better. The cross-model tension forces genuinely higher quality. Calibration confirmed it: cross-model evaluation produces a wider score gap between known-good and known-bad ads (5.8 points vs ~3 points), meaning the evaluator is more discriminating.

**Tradeoffs:** One model, one API key, one billing relationship — that's objectively simpler. And I can't fully formalize *why* same-model bias occurs. It's an empirical observation, not a theoretical proof. But the data is consistent, and the PRD's discussion of the "taste problem" basically warns about this exact failure mode.

**Context:** This discovery is what led to the dual-model architecture being a core design principle, not just a cost optimization. The separation of concerns argument only became clear after seeing the single-model results.

---

## [2026-03-09] — What Didn't Work: Unweighted Scoring

**Decision:** Moved from equal dimension weights (20% each) to unequal weights after finding that equal weights masked the importance of value proposition.

**Why:** With all five dimensions weighted at 20%, value proposition — the single most important thing in an ad (does the reader understand *why* they should care?) — had the same influence as emotional resonance (the hardest dimension to score reliably). The aggregate score didn't reflect what actually makes an ad effective. Weighting value_proposition at 25% improved correlation with early human ratings. The ads that humans liked almost always had strong value propositions; the ones they didn't like often scored fine on clarity and brand voice but said nothing compelling.

**Tradeoffs:** Any weighting scheme is an opinion encoded as math. These specific weights are based on my analysis of reference ads and a small set of human ratings, not on statistically rigorous A/B testing with real conversion data. Someone with different domain expertise might weight them differently. The weights should really be *learned* from human ratings data, not hand-set. That calibration work hasn't been done yet.

**Context:** The natural next step is to use the 90 human ratings from the survey to empirically calibrate the weights. Right now they're informed judgment. They should be data-driven.

---

## [2026-03-10] — Self-Healing Regression Detection

**Decision:** Implemented `_detect_dimension_regression()` in `pipeline.py` to catch cases where a fix attempt makes things worse, then pass adaptation notes to the FixerAgent telling it to try a completely different approach.

**Why:** The fix loop has a subtle failure mode that I only caught after watching several iteration cycles: fixing one dimension can hurt another. If the fixer says "make the CTA more urgent," the writer might rewrite the CTA in a way that breaks brand voice — too pushy, too salesy. Without regression detection, the pipeline would happily proceed with the "improved" ad, not noticing it traded one weakness for another. The detector compares each dimension's score before and after a fix. If the targeted dimension didn't improve (or got worse), it passes an adaptation note: "Previous fix attempt did not improve {dimension}. Try a completely different approach." The fixer sees this and generates a fundamentally different repair strategy, not a tweak of the same failing one.

**Tradeoffs:** Only detects regressions within a single pipeline run, not across campaigns. If the pipeline consistently fails on emotional_resonance for SAT-prep ads, it discovers that fresh every time — there's no cross-campaign learning. The adaptation note is also a blunt instrument: "try a completely different approach" without specifying what "different" means. The fixer has to figure that out from its dimension-specific strategy library.

**Context:** I considered three approaches: per-dimension regression detection (chosen), global quality threshold ratcheting (simple concept but coarse-grained — raises the threshold but doesn't catch dimension-level issues), and statistical process control (industry standard for quality monitoring but overkill for 50 ads — requires large sample sizes). Per-dimension detection hits the sweet spot of useful without overengineered. Iteration 1→2 fixes land ~70% of the time; iteration 2→3 adaptations catch the cases where the first strategy was wrong.

---

## [2026-03-10] — Confidence-Based Human Review Flagging

**Decision:** Flag ads for human review when any evaluation dimension has confidence below 0.6, even if the aggregate score passes the 7.0 threshold.

**Why:** The evaluator should know when it's uncertain. A score of 7.5 with 0.9 confidence is very different from a score of 7.5 with 0.4 confidence — the second one is basically guessing. The `needs_human_review` flag catches these cases and routes them to a human reviewer in the dashboard instead of auto-approving. It's an acknowledgment that LLM-as-judge has limits and the system shouldn't pretend otherwise.

**Tradeoffs:** The 0.6 threshold is a judgment call — I don't have empirical data proving it's the right cutoff. It's based on calibration runs where I manually checked evaluations at various confidence levels. And honestly, the confidence scores themselves aren't well-calibrated yet. The evaluator reports 0.85+ confidence on scores that humans disagree with. So we're flagging the cases where the evaluator *knows* it's uncertain, but missing the cases where it's *confidently wrong*. That's the harder problem, and it's not solved.

**Context:** Confidence calibration against the human ratings dataset is the obvious next step. You'd use the 90 human ratings as ground truth and measure whether the evaluator's confidence actually predicts human agreement. If it doesn't (and early signs suggest it doesn't), the confidence scores need recalibration — probably by adding worked examples to the evaluation prompt showing what 0.9 vs 0.5 confidence should look like.

---

## [2026-03-09] — Three-Iteration Cap on Fix Loop

**Decision:** Hard cap the fix loop at 3 iterations. If an ad hasn't passed after 3 attempts, flag it for human review instead of looping forever.

**Why:** Diminishing returns. The data shows iteration 1→2 fixes land about 70% of the time — targeted repairs on the weakest dimension usually work. Iteration 2→3 catches cases where the first strategy was wrong (thanks to regression detection). But going beyond 3 iterations hits a wall: if three different repair strategies haven't worked, the problem is likely in the brief, not the copy. Continuing to loop burns API credits without meaningful improvement. Flagging for human review is the honest thing to do — the system is saying "I've tried my best, someone smarter needs to look at this."

**Tradeoffs:** Some ads might converge with 4 or 5 iterations. The cap is fixed, not adaptive — it doesn't consider how close the score is to 7.0 or how much each iteration improved things. An ad scoring 6.9 after 3 iterations gets the same treatment as one scoring 4.0. A smarter system would allocate iteration budget dynamically based on trajectory.

**Context:** The cap is configurable via `max_iterations`. Three felt right empirically but I don't have rigorous data proving it's optimal. It's a reasonable default, not a proven optimum.

---

## [2026-03-08] — Monorepo Structure

**Decision:** Single GitHub repo with `frontend/`, `backend/`, `reference_ads/`, and `docs/` as top-level folders.

**Why:** Keeps everything version-controlled together — design decisions, reference data, and code all live in one place. Evaluators can clone one repo and see the full picture. Easier to cross-reference frontend and backend code during a fast build.

**Tradeoffs:** Slightly more complex deployment config (Vercel needs to look in `frontend/`, Fly.io in `backend/`). Worth it for organizational clarity.

---

## [2026-03-08] — Frontend on Vercel, Backend on Fly.io

**Decision:** Next.js frontend on Vercel, FastAPI backend on Fly.io (Dallas region).

**Why:** The PRD only requires "Demo video or live walkthrough." I chose to build a full web application as the live walkthrough because a polished deployed app speaks louder than a CLI demo — and the "-10 for no working demo" deduction is eliminated by a live URL. Vercel is purpose-built for Next.js (zero config, edge network, automatic HTTPS). Fly.io was chosen over Vercel serverless for the backend because our LangGraph pipeline is stateful and long-running — a campaign generation job runs for several minutes, and background jobs need to keep running after the HTTP request completes. Fly.io gives us a real persistent VM, not a serverless function with a 60-second timeout.

**Tradeoffs:** Two platforms to manage. Single Fly.io region (dfw) means no geo-distribution — all API requests route to Dallas regardless of user location. Fine for a demo; production would need multi-region or edge caching.

**Context:** FastAPI was chosen over Flask (no native async — blocks during LLM API calls) and Django (heavyweight ORM fights the dual-database pattern). Async support was the decisive factor since every agent call hits an external API and waits.

---

## [2026-03-10] — ~~Skipping~~ Meta Ad Library Live Scraping

> **UPDATE [2026-03-15]:** This decision was reversed. Competitive intelligence scraping is now implemented — see the [2026-03-15] entry below.

**Original Decision:** Use static reference ads (curated JSON) instead of building a live Meta Ad Library scraping pipeline, deliberately forgoing the +10 bonus points.

**Original Why:** The +10 bonus for competitive intelligence was the largest single bonus available — 40% of all bonus points. But the infrastructure required (headless browser via Playwright/Selenium for Meta's dynamically-rendered Ad Library, anti-detection measures, rate limiting, data parsing) would've taken 1-2 days and produced a fragile system. Meta's UI changes frequently, so any scraper would've been a maintenance liability.

**Context:** Chose the approach with the best effort-to-value ratio at the time — then reversed it once the core pipeline was stable.

---

## [2026-03-15] — Competitive Intelligence: Meta Ad Library Scraping for 8 Competitors

**Decision:** Built a Playwright-based scraper (`competitor_scraper.py`) that collects publicly available ad data from Meta Ad Library for 8 competitors: Khan Academy, Chegg, Course Hero, Wyzant, Princeton Review, Kaplan, Sylvan Learning, and Kumon. Integrated the scraped data into the ResearcherAgent → WriterAgent generation pipeline.

**Why:** The PRD is explicit: *"Great artists steal. Study our biggest competitor's ads. What patterns do you see? What hooks work? What CTAs convert?"* The Competitive Intelligence section specifies what to extract: recurring copy patterns, CTAs that appear most often, emotional angles, and how competitors handle specificity. This is the "great artists steal" approach — not copying, but studying what shapes work and fitting VT's brand into proven patterns. The +10 bonus (largest single bonus) justified revisiting the earlier skip decision once the core pipeline was stable.

**How it works:**
1. **Scraper** (`competitor_scraper.py`): Playwright renders Meta Ad Library pages for each competitor's Facebook Page ID. Extracts primary text, headline, CTA, platform, start date, and active status. Computes `days_active` from start dates. Only collects active ads — inactive ads dropped at scrape time. Results sorted by longevity. Output: `reference_ads/competitors/{competitor}.json`.
2. **Quality filter** (ResearcherAgent): Only ads that are (a) currently active AND (b) running 30+ days feed into the pipeline. Longevity is the best public proxy for ad performance — if a competitor keeps paying to run it, it's working.
3. **Integration**: `ResearcherAgent.extract_context()` loads competitor data, filters for quality, adds `CompetitorInsight` objects to `ResearchContext`. `format_for_prompt()` injects a "COMPETITOR INTELLIGENCE" section into the WriterAgent prompt showing each competitor's long-running ads, CTAs, and counts.
4. **API endpoints**: `GET /competitors/ads` and `GET /competitors/summary` expose scraped data to the frontend.

**Critical design decision — generation only, not evaluation:** The PRD's intent for competitor data is clear: feed the writer, not the judge. The evaluator scores against VT's own brand voice, not against competitors. Competitor data shapes what gets *generated*; VT's brand standards shape what gets *approved*.

**Tradeoffs:** Playwright is a heavy dependency (~150MB for Chromium). Meta's Ad Library DOM structure is unstable — CSS class selectors will need updating when Meta redesigns. The scraper includes fallback selectors and saves debug screenshots on failure, but it's inherently fragile. The 30-day longevity filter is a judgment call — some effective seasonal ads run shorter. Existing ads in the database don't retroactively benefit; only future generations pick up competitor context.

**Context:** This reverses the [2026-03-10] decision. The scraper runs standalone (`python competitor_scraper.py`), not as part of the main pipeline — it refreshes competitor JSON files, which the ResearcherAgent picks up automatically on the next campaign run.

---

## [2026-03-12] — What I'd Do Differently (Honest Retrospective)

**Decision:** Documenting what I'd change if starting over. The PRD says "your decision log matters as much as your output," and a log that only records wins isn't a log — it's marketing.

**Why:** Because being honest about gaps is more valuable than pretending they don't exist. Here's the list:

1. **~~Raise emotional_resonance weight from 15% to ~25%.~~** Done — raised to 35% (text-only) / 25% (with image), making it the highest-weighted dimension. The confusion matrix data was unambiguous and this was the single highest-leverage config change.

2. **Deploy Langfuse from day 1.** I added observability after the pipeline was already running. If I'd had cost tracking and trace inspection from the start, I would've caught the evaluator leniency issue weeks earlier instead of discovering it through the human survey.

3. **Build the database abstraction layer before any agents.** I wired agents directly to Supabase first, then had to retrofit SQLite support when local dev became a pain. Should've started with the interface and implemented against it.

4. **Add confidence scoring earlier.** Evaluator overconfidence was the core bug — giving 0.85+ confidence on scores that humans disagreed with. Adding the confidence field was easy; calibrating it against real data is the hard part that's still not done.

5. **Collect human ratings in parallel with development, not after.** I built the survey interface after the pipeline was working, then collected ratings sequentially. If I'd had the survey running from day 1, I'd have a larger dataset and could've used it to tune weights and calibration *during* development.

**Tradeoffs:** None of these are fatal. The system works. But each represents a place where different sequencing would've led to a better-calibrated system sooner.

**Context:** The 43.3% precision finding from the confusion matrix is the system's most important self-assessment. It means when the AI evaluator approves an ad, humans only agree 43% of the time. The AI is too lenient. Every "what I'd do differently" item above would help close that gap. A well-reasoned decision log with honest limitations is worth more than a polished demo with no explanation of how you got there — that's a direct quote from the PRD, and I believe it.

---

## [2026-03-12] — A/B Variant Generation: Same Brief, Different Creative Approaches

**Decision:** Added an A/B variant generator (`ab_variant_generator.py`) that takes a single CampaignBrief and produces 2-5 distinct ad variants, each using a different creative approach (hook strategy). Five approaches are defined: pain_point_hook, social_proof_hook, urgency_hook, aspirational_hook, and question_hook.

**Why these specific approaches:** These five hooks map to well-established direct response copywriting frameworks. Pain point hooks exploit loss aversion (Kahneman's prospect theory — people respond more strongly to avoiding loss than gaining benefit). Social proof hooks leverage conformity bias (Cialdini's "social proof" principle — if other students improved, mine can too). Urgency hooks create time pressure via scarcity (Cialdini again). Aspirational hooks tap into identity-based motivation (the parent imagines their child succeeding). Question hooks use the Zeigarnik effect — an open question creates cognitive tension the reader needs to resolve. Together, these five approaches cover the major persuasion vectors for educational marketing to parents.

**A/B is NOT iteration:** This is a critical architectural distinction. The existing pipeline's fix loop (write → evaluate → fix → re-write) improves a *single* ad by targeting its weakest dimension. A/B variant generation creates *multiple different ads from scratch*, each taking a fundamentally different creative strategy. Iteration asks "how do we make this ad better?" A/B asks "which creative angle works best for this audience?" They're complementary — each A/B variant still runs through the full iteration pipeline, so you get the best version of each approach.

**How it works:** The generator injects the creative approach description into the brief's tone field before passing it to WriterAgent. This steers Gemini toward a specific hook strategy without modifying the core prompt template. Each variant runs through the full pipeline independently (write → evaluate → fix/save/flag), so every variant gets quality-scored and iterated on. Results are tagged with `variant_approach` in the database for grouping and comparison.

**Tradeoffs:** More variants = more API cost per campaign. Three variants means 3x the Gemini + Claude API calls (minimum 6 calls, up to 18 if all three variants need the full 3-iteration fix cycle). The approach injection via tone modification is a pragmatic hack — it works because Gemini is sensitive to tone instructions, but a cleaner design would use a dedicated `creative_direction` field in the prompt template. Also, the current implementation runs variants sequentially, not in parallel — parallelizing would cut wall-clock time significantly but adds complexity around rate limiting and error handling.

**Context:** PRD v2 scope explicitly calls for "A/B variant generation — same brief, different creative approaches." This implementation satisfies that requirement with a clean separation from the existing iteration loop. The `POST /campaigns/{id}/ab-test` endpoint accepts optional approach names for controlled testing, or defaults to random selection for exploratory generation.

## [2026-03-14] — Integrated Nerdy SAT Messaging Guidance + Persona Targeting

**Decision:** Overhauled WriterAgent and EvaluatorAgent prompts with real Nerdy messaging data (do's/don'ts, competitive positioning, persona psychology, proven hooks) and added persona targeting to CampaignBrief.

**Why:** We received detailed SAT messaging guidance from Nerdy including specific language rules ("your child" not "your student", "SAT tutoring" not "SAT prep"), competitive positioning data (10x vs self-study, 2.6x vs group classes, pricing comparisons), 15 detailed parent personas with psychology/hook examples, and explicit anti-patterns (no corporate language, no fake scarcity, no vague claims). This is exactly the kind of domain knowledge that separates generic ad generation from ads that could actually run. Baking it into both the writer AND evaluator means the system can now generate persona-targeted ads AND score them against real brand standards.

**Tradeoffs:** The system prompts are significantly longer now, which means more input tokens per call. But the quality-per-token should improve dramatically — fewer iteration cycles needed because the writer has better guidance upfront, and the evaluator catches brand violations that were previously invisible.

**Context:** This data came from the Nerdy team via the Gauntlet Slack channel. The personas map directly to real sales call patterns and customer segments. Adding persona targeting to CampaignBrief also gives us a natural way to generate diverse ad libraries (9 personas × multiple campaigns = richer 50+ ad corpus with genuine variety).

## [2026-03-15] — V2 Image Generation with Imagen 4 + 7-Dimension Visual Evaluation

**Decision:** Added a 5th agent (ImageAgent) using Imagen 4 via Gemini API to generate ad creative images, and extended the evaluation framework from 5 to 7 dimensions by adding visual_brand_consistency and scroll_stopping_power — scored by Claude Sonnet's vision capability.

**Why:** The confusion matrix data showed 43.3% precision — humans disagreed with the AI evaluator more than half the time. During the human rating survey, a consistent piece of feedback emerged: people respond more to visual ads than plain copy. The PRD lists image generation and visual evaluation as v2 scope features, but the decision to implement them wasn't about scope ambition — it was driven by the data saying our text-only ads weren't connecting with humans the way the scores suggested. Adding images and evaluating them visually closes a gap the text-only pipeline couldn't address.

**Architecture choice — new ImageAgent vs. bolting onto WriterAgent:** The ImageAgent is a standalone 5th agent in the LangGraph pipeline, not a method on WriterAgent. This preserves the single-responsibility principle (writer writes copy, image agent generates visuals) and keeps the pipeline flow clean: write → generate_image → evaluate → fix/save/flag. It also means the image generation step can fail gracefully without crashing the pipeline — if Imagen returns nothing, the ad still gets text-only 5-dimension evaluation.

**Why Imagen 4 over Flux or Gemini native image gen:** We already have the Gemini API client and key from WriterAgent. Imagen 4 produces photorealistic output suited for ad creatives and is accessible through the same `google-genai` library — zero new dependencies. Flux would mean a new API provider, new billing, and new failure mode for marginal quality difference at this stage.

**Why 7 dimensions instead of sub-scores:** Adding visual_brand_consistency and scroll_stopping_power as first-class dimensions (rather than sub-scores under brand_voice and emotional_resonance) means they participate fully in the weighted average, threshold enforcement, fixer targeting, and iteration tracking. The evaluator uses Claude's vision API to literally look at the generated image alongside the copy. When no image is present, the system falls back to 5-dimension text-only scoring — fully backward compatible.

**Weight rebalancing:** Text-only weights (rebalanced based on 146-parent survey): clarity 15%, value_proposition 20%, cta_strength 15%, brand_voice 15%, emotional_resonance 35%. Full 7-dimension weights: clarity 10%, value_proposition 15%, cta_strength 10%, brand_voice 10%, emotional_resonance 25%, visual_brand_consistency 10%, scroll_stopping_power 20%. Emotional resonance remains the highest-weighted dimension in both modes — the survey data showing it's the #1 predictor of parent clicks drove this decision. Scroll-stopping power got 20% because it's the visual equivalent of the hook — if the image doesn't stop the scroll, the copy never gets read.

**Tradeoffs:** Image generation adds ~$0.04 per ad (Imagen 4) and ~2-3 seconds of latency per pipeline run. The visual evaluation adds token cost from sending base64 images to Claude's vision API. Persona-specific visual style prompts (15 personas × unique visual directions) add complexity to the ImageAgent, and Imagen occasionally bakes text into images (like "VARSITY TUTORS" watermarks) despite the prompt saying not to — that's an Imagen limitation, not a code issue.

**Context:** The frontend now renders ads as Facebook and Instagram mockups side-by-side with the radar chart evaluation panel, making the v2 visual pipeline immediately visible in the demo. This is one of the strongest differentiators from other submissions — most will have text-only pipelines.

---

## [2026-03-15] — Quality Ratchet: Dynamic Threshold That Only Goes Up

**Decision:** Implemented a quality ratchet (`quality_ratchet.py`) that dynamically raises the evaluation threshold based on the quality of already-approved ads, with the EvaluatorAgent's `active_threshold` property and `set_dynamic_threshold()` method.

**Why:** A static 7.0 threshold means the 50th approved ad has the same quality bar as the 1st. As the ad library grows and the system demonstrates it can produce better output, the bar should rise. The ratchet computes the 25th percentile of all approved ad scores and uses that as the new threshold — with gradual headroom (+0.5 per 10 ads, ceiling at 9.0). Requires 10+ approved ads to activate. The ratchet can only go up, never down — quality never regresses.

**Tradeoffs:** The ratchet is stateless (recomputed from DB on each pipeline run) and deterministic. It doesn't incorporate human ratings or conversion data, only AI evaluator scores. A production system should calibrate against human agreement, not just AI scores. The 25th percentile choice is conservative — it means 75% of existing ads would still pass if re-evaluated. A more aggressive ratchet (50th percentile) would raise quality faster but risk rejecting too many ads in early campaigns.

**Context:** The `/evaluator/config` endpoint exposes the ratchet state (active, sample size, headroom) so the frontend can display the current effective threshold. The `get_approved_scores()` database method was added to both SQLite and Supabase implementations to support the ratchet query.

---

## [2026-03-15] — Evaluator Config as Single Source of Truth

**Decision:** Made `evaluator_agent.py` the single source of truth for all evaluation logic — threshold, weights, dimensions — and wired everything else to derive from it. Added `/evaluator/config` API endpoint that exposes the full config to the frontend.

**Why:** Hardcoded thresholds, weights, and dimension lists were scattered across 15+ files (backend main, fixer, tests, demo scripts, 5+ frontend pages). When weights changed, half the codebase was stale. This is exactly the kind of config drift that causes subtle bugs — a frontend showing "7.0 threshold" while the backend uses 7.5, or a test asserting against old weights.

**How it works:** `EvaluatorAgent` defines `THRESHOLD`, `TEXT_WEIGHTS`, `FULL_WEIGHTS` as class-level constants. `main.py` imports these and derives `DB_TEXT_DIMS` and `DB_ALL_DIMS` (mapping evaluator dimension names to DB column names via `EVAL_TO_DB_DIM`). The `/evaluator/config` endpoint returns everything the frontend needs. The `useEvalConfig` hook in the frontend caches this with a singleton pattern and exposes it to all pages. Shared helpers (`scoreColor`, `scoreBg`, `scoreBorder`, `dimLabel`) derive from the config.

**Tradeoffs:** The frontend falls back to a hardcoded `DEFAULT_CONFIG` if the API is unreachable — this is a snapshot that could go stale if the backend changes. But it's better than the previous state where every file had its own copy. The `cta_strength` → `cta_score` column mapping (`EVAL_TO_DB_DIM`) is an annoying historical artifact that could be cleaned up with a DB migration.

**Context:** This was a major cohesion pass touching every file that referenced evaluator logic. The `ScoreRing` component was also extracted into a shared component to eliminate three local implementations.
