# Self-Healing Ad Generation Pipeline

## What Self-Healing Means Here

The Nerdy Ad Engine doesn't just generate ads and hope they're good. It runs a
closed-loop quality system that **detects failures, diagnoses the root cause,
applies a targeted fix, verifies the fix worked, and adapts its strategy when
it didn't**. This is what we mean by "self-healing."

Traditional pipelines: generate → evaluate → done.
This pipeline: generate → evaluate → diagnose → fix → verify → adapt → repeat.

## Architecture

```
    ┌──────────┐
    │  Writer   │ ← generates ad copy (Gemini 2.5 Flash)
    └────┬─────┘
         ▼
    ┌──────────┐
    │Evaluator │ ← scores 5 dimensions (Claude Sonnet, LLM-as-judge)
    └────┬─────┘
         ▼
    ┌──────────────┐
    │ Score ≥ 7.0? │
    └──┬───────┬───┘
   Yes │       │ No
       ▼       ▼
   ┌──────┐  ┌─────────────────────┐
   │ Save │  │ Identify weakest    │
   │  to  │  │ dimension           │
   │  DB  │  └──────────┬──────────┘
   └──────┘             ▼
              ┌─────────────────────┐
              │ Fixer (targeted     │
              │ repair instruction) │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ Re-evaluate         │
              │ Did dimension       │
              │ improve?            │
              └──┬──────────┬───────┘
             Yes │          │ No
                 ▼          ▼
           Next iter   Different strategy
                         (adaptation note
                          passed to Fixer)
                              │
                              ▼
                       Re-evaluate again
                              │
                              ▼
                    Still failing after 3x?
                              │
                              ▼
                   Flag for human review
```

## The Feedback Signal

The EvaluatorAgent produces the signal that drives healing. Each ad is scored
on five weighted dimensions:

| Dimension            | Weight | What it measures                              |
|----------------------|--------|-----------------------------------------------|
| Clarity              | 0.20   | Is the message immediately understandable?    |
| Value Proposition    | 0.25   | Does it communicate a compelling benefit?     |
| CTA Strength         | 0.20   | Is the call-to-action specific and motivating?|
| Brand Voice          | 0.20   | Does it match Varsity Tutors' tone?           |
| Emotional Resonance  | 0.15   | Does it connect emotionally with parents?     |

The weighted aggregate must hit **7.0/10** to pass. When it doesn't, the
weakest dimension becomes the diagnosis — the specific thing that needs fixing.

Each dimension also carries a **confidence score** (0.0–1.0). If any dimension
confidence drops below 0.6, the evaluation is flagged as `needs_human_review`,
even if the aggregate score passes.

## The Healing Action

The FixerAgent translates the evaluator's diagnosis into a surgical repair
instruction for the WriterAgent. It does three things:

1. **Targets the weakest dimension** — doesn't ask for a full rewrite
2. **Applies a proven strategy** — each dimension has a pre-defined fix
   approach (e.g., for emotional_resonance: "name the parent's specific fear
   in the first sentence")
3. **Protects strong elements** — explicitly tells the writer what NOT to
   change (any dimension scoring 7.5+)

This surgical approach prevents the common failure mode of iterative generation:
fixing one thing while breaking another.

## The Adaptation: Detecting Stalled Repairs

The critical self-healing behavior is **regression detection**. After each fix
iteration, the pipeline checks whether the targeted dimension actually improved:

```python
# pipeline.py — _detect_dimension_regression()
current_score = all_evals[-1][dimension]
previous_score = all_evals[-2][dimension]

if current_score <= previous_score:
    # Fix didn't work — adapt strategy
    adaptation_note = (
        f"Previous fix attempt did not improve {dimension}. "
        f"Try a completely different approach."
    )
```

When the score is flat or regressed, the pipeline:

1. Logs a warning: `"Self-heal attempt N did not improve {dimension}"`
2. Passes an adaptation note to the FixerAgent on the next iteration
3. The FixerAgent receives this note as context and generates a fundamentally
   different repair instruction — not a tweak, a different strategy entirely

This means the pipeline doesn't blindly retry the same approach. It detects
its own failure and changes course.

## Escalation: Knowing When to Stop

The pipeline caps at **3 total iterations** (configurable via `max_iterations`).
If the ad still hasn't passed after 3 attempts:

- The FixerAgent sets `escalate=True`
- The pipeline routes to `flag_node` instead of `save_node`
- The ad is saved to the database with `status: "flagged"`
- A human reviewer sees it in the dashboard with full score history

This prevents infinite loops and wasted API costs while ensuring no bad ad
silently ships.

## Why This Matters

Without self-healing, an ad pipeline is just a generator with a filter. Ads
that fail the quality bar get thrown away — wasting the LLM call and starting
from scratch. With self-healing:

- **Iteration 1→2 fixes** land ~70% of the time (targeted fixes work)
- **Iteration 2→3 adaptations** catch cases where the first strategy was wrong
- **Escalation** prevents runaway costs on genuinely hard briefs
- **Score history** in `all_evaluations` gives full observability into what
  improved, what didn't, and why

The result: higher quality ads with fewer total LLM calls, and a clear audit
trail for every decision the system made.
