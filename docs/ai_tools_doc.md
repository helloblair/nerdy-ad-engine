# AI Tools and Prompts Used

## Models in Production

| Agent | Model | Why This Model |
|-------|-------|----------------|
| WriterAgent | Gemini 2.5 Flash | Fast, cheap, high creative variance. The writer needs to explore a wide output space, not reason carefully. |
| ImageAgent | Imagen 4 (via Gemini API) | Photorealistic ad creative generation. Same API client as WriterAgent — zero new dependencies. Generates persona-specific visual styles. |
| EvaluatorAgent | Claude Sonnet 4.6 | Structured reasoning, consistent calibration, better at decomposing quality into dimensions. Uses vision capability for image evaluation. The judge must be precise. |
| FixerAgent | Claude Sonnet 4.6 | Repair instruction quality directly determines whether the next iteration improves. A vague fix = wasted iteration = wasted cost. |
| ResearcherAgent | None (deterministic) | Reads static JSON. Using an LLM to re-derive already-documented patterns would be slower, more expensive, and less reliable. |

## Development Tools

- **Claude.ai** — Pair programming throughout the entire build. Architecture decisions (dual-model, LangGraph state machine, weighted scoring), prompt iteration (especially the evaluator system prompt calibration), debugging (JSON parse failures, Supabase timeout diagnosis), and documentation writing.
- **Claude Code (VS Code extension)** — Code generation, refactoring, multi-file edits, and running verification scripts. Used extensively for wiring the LangGraph pipeline, building the FastAPI endpoints, and creating the Next.js frontend.

## Key System Prompts

### WriterAgent SYSTEM_PROMPT

```
You are an expert copywriter for Varsity Tutors Facebook/Instagram ads.
RULES: Lead with specific outcomes and numbers. Address parent pain directly.
Never use corporate language. CTAs must be specific.
IMPORTANT: Respond with raw JSON only. No markdown. No backticks. No explanation.
```

The writer also receives a dynamic prompt built from the campaign brief:

```
Write a Facebook ad for Varsity Tutors.
Audience: {audience}
Product: {product}
Goal: {goal}
Tone: {tone}
Key Benefit: {key_benefit}
Proof Point: {proof_point}

{research_context from ResearcherAgent}

REVISION #{iteration} — Fix this: {fixer_feedback}  (only on iterations 2+)

Return ONLY a raw JSON object, no markdown, no backticks:
{"primary_text":"2-4 sentences","headline":"max 7 words","description":"one line","cta_button":"Book a Free Session","writer_notes":"brief note"}
```

### EvaluatorAgent SYSTEM_PROMPT

The evaluator's system prompt is extensive (~2000 tokens), calibrated against real Nerdy SAT messaging guidance. Key sections:

**Calibration anchor:**
```
CRITICAL CONTEXT: In a survey of 146 real parents, only 43% of ads that this evaluator
previously approved were rated positively by humans. The main failure mode was approving
ads that were structurally sound but emotionally flat. You must be STRICTER than your
instinct — when in doubt, score lower.
```

**The Parent Click Test** (applied to every ad before scoring):
```
Before scoring, ask yourself: "Would a real parent — tired, scrolling Instagram at 10pm,
worried about their kid's future — actually stop and tap this?" If the honest answer is
"probably not", the aggregate CANNOT exceed 6.5 regardless of how well-structured the copy is.
```

**Brand voice rules with automatic penalties** (score ≤5.0 if triggered):
- Corporate language ("unlock potential", "tailored support", "custom strategies")
- Fake scarcity ("spots filling fast", "limited enrollment")
- Vague claims ("personalized", "expert" without mechanism)
- Wrong terminology ("your student" instead of "your child", "SAT prep" instead of "SAT tutoring")

**Emotional resonance rules** (35% weight — highest dimension):
```
Survey data from 146 real parents showed emotional resonance is the #1 predictor of whether
a parent clicks. Ads that score well on structure but poorly on emotion get rejected by
humans 70%+ of the time. Score this dimension HARD.
```

**Visual evaluation rules** (when image present):
- Visual brand consistency: clean, modern, warm, educational aesthetic; no stock photography or clipart
- Scroll-stopping power: emotional response, visual hierarchy, authenticity vs. corporate polish

The evaluator receives a structured evaluation prompt requesting scores for up to 7 dimensions (5 text + 2 visual when image present) — each with score, rationale, and confidence fields. Aggregate score is calculated server-side using weighted averages (not trusting the LLM's math).

### FixerAgent Prompt (no SYSTEM_PROMPT — uses a structured user prompt)

The FixerAgent doesn't use a system prompt. Instead, it sends a structured user-level prompt:

```
You are generating a targeted repair instruction for an ad copywriter.

EVALUATION RESULT:
- Weakest dimension: {weakest_dimension} (score: {score}/10)
- Evaluator's suggestion: {improvement_suggestion}
- Proven fix strategy for this dimension: {strategy}
- What to preserve: {preserve}
- This is iteration {iteration} of {max_iterations}

Write ONE targeted instruction (2-3 sentences max) telling the writer:
1. Exactly what to change in the {weakest_dimension}
2. A specific technique to use (from the strategy above)
3. What NOT to touch

Be surgical. Be specific. No vague directions like "make it more emotional."
Instead: "Replace the opening sentence with a question that names the parent's
specific fear about college admissions deadlines."

Return just the instruction as plain text. No JSON, no headers.
```

The fixer also has hand-written dimension-specific strategies:

- **clarity**: "Simplify the primary text. Cut it to 2 sentences maximum. Remove any clause that doesn't directly support the main outcome."
- **value_proposition**: "Add a specific number or outcome in the first sentence. Reference the proof point explicitly. Make the benefit concrete and measurable."
- **cta_strength**: "Replace the CTA with something more specific to this campaign. Instead of generic 'Book a Free Session', add what they get: 'Book a Free SAT Strategy Session' or 'Claim Your Free Trial Lesson'."
- **brand_voice**: "Rewrite the primary text with zero adjectives. Use the tension reframe pattern: state two specific numbers the parent already knows and create conflict between them (e.g. '3.8 GPA. 1180 SAT.'). Remove all corporate language."
- **emotional_resonance**: "Rewrite the opening to name the parent's specific fear — not the student's problem, the PARENT'S fear. What keeps them up at night? College rejection? Wasted potential? Name it directly in the first sentence."

## Prompt Engineering Decisions

### Why Hook → Problem → Proof → CTA structure in WriterAgent

The writer prompt implicitly encodes the Hook → Problem → Proof → CTA ad copy structure through the fields it requests: `primary_text` (hook + problem + proof), `headline` (hook), `description` (proof), `cta_button` (CTA). The brand voice rules ("lead with outcomes and numbers", "address parent pain directly") push the model toward this structure without rigidly templating it — allowing creative variance within a proven framework.

### Why structured JSON output vs free text in EvaluatorAgent

The evaluator returns a strict JSON schema with per-dimension scores, rationales, and confidence. This was non-negotiable for three reasons: (1) scores need to be numerically comparable across ads, (2) rationales need to be attributable to specific dimensions for the fixer to target, and (3) confidence needs to be a float for the `needs_human_review` threshold check. Free text evaluation was tested early and produced inconsistent scoring and unparseable results.

### How calibration examples were incorporated

The evaluator prompt includes anchoring phrases: "7.0 means this could run tomorrow", "5.0 means needs significant work", "9.0+ means genuinely exceptional." These anchors came from calibration runs against known-good and known-bad ads. The known-good ad (reference: "Her SAT score jumped 360 points in 8 weeks") scored 8.6, and the known-bad ad (generic corporate copy) scored 2.8. The 5.8-point gap confirmed the evaluator could distinguish quality with these anchors in place.

### What didn't work

- **Holistic scoring** (single overall score without dimensions): Too variable. The same ad would score 6.5 on one run and 8.0 on the next. Breaking into weighted dimensions (now 5 text + 2 visual) reduced run-to-run variance from ~1.5 points to ~0.3 points.
- **Non-JSON output**: The evaluator initially returned natural language with scores embedded. Parsing was fragile and broke on every third run. Switching to JSON-only with a strict schema and retry logic solved this.
- **Single model for generation and evaluation**: Tested Claude Sonnet for both writing and judging. The evaluator was systematically lenient toward Claude-generated copy — it recognized and rewarded its own stylistic patterns. Switching the writer to Gemini broke this feedback loop.
- **Unweighted scoring**: Equal weights across all dimensions masked what actually matters. After analyzing 146 parent ratings, emotional resonance emerged as the #1 predictor of human approval and was reweighted to 35% (text-only) / 25% (with image). The current weights are data-informed rather than hand-tuned guesses.
