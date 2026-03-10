"""
fixer_agent.py
--------------
The FixerAgent is the translation layer between the EvaluatorAgent and WriterAgent.

It reads an evaluation result, identifies exactly what's broken, and produces
a targeted repair instruction — telling the WriterAgent precisely what to fix
and what to preserve.

Think of it as a surgeon getting a diagnosis: don't re-examine the whole patient,
go straight to the problem and fix exactly that.

If max_iterations is reached without passing threshold, it sets escalate=True
instead of generating more instructions — this is what triggers the LangGraph
hard cap guard.
"""

import os
from typing import Optional
from anthropic import Anthropic
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# ─── Data Models ─────────────────────────────────────────────────────────────

class EvalSummary(BaseModel):
    """Condensed evaluation result passed into the FixerAgent."""
    clarity: float
    value_proposition: float
    cta_strength: float
    brand_voice: float
    emotional_resonance: float
    aggregate_score: float
    weakest_dimension: str
    improvement_suggestion: str
    iteration: int


class FixerOutput(BaseModel):
    """Targeted repair instruction for the WriterAgent."""
    targeted_instruction: str = Field(
        ...,
        description="Specific, actionable rewrite direction for the weakest dimension"
    )
    dimension_to_fix: str = Field(
        ...,
        description="The single dimension the WriterAgent should focus on"
    )
    preserve_elements: str = Field(
        ...,
        description="What the WriterAgent must NOT change (high-scoring elements)"
    )
    escalate: bool = Field(
        default=False,
        description="True if max iterations reached without passing threshold"
    )
    escalation_reason: Optional[str] = None


# ─── Fixer Agent ─────────────────────────────────────────────────────────────

class FixerAgent:
    """
    Translates EvaluatorAgent verdicts into targeted WriterAgent instructions.

    Uses Claude Sonnet for the same reason as the EvaluatorAgent — the quality
    of the repair instruction directly determines whether the next iteration
    improves. A vague fix = wasted iteration = wasted cost.
    """

    MAX_ITERATIONS = 3

    # Dimension-specific fix strategies derived from reference ad analysis
    DIMENSION_STRATEGIES = {
        "clarity": "Simplify the primary text. Cut it to 2 sentences maximum. Remove any clause that doesn't directly support the main outcome.",
        "value_proposition": "Add a specific number or outcome in the first sentence. Reference the proof point explicitly. Make the benefit concrete and measurable.",
        "cta_strength": "Replace the CTA with something more specific to this campaign. Instead of generic 'Book a Free Session', add what they get: 'Book a Free SAT Strategy Session' or 'Claim Your Free Trial Lesson'.",
        "brand_voice": "Rewrite the primary text with zero adjectives. Use the tension reframe pattern: state two specific numbers the parent already knows and create conflict between them (e.g. '3.8 GPA. 1180 SAT.'). Remove all corporate language.",
        "emotional_resonance": "Rewrite the opening to name the parent's specific fear — not the student's problem, the PARENT'S fear. What keeps them up at night? College rejection? Wasted potential? Name it directly in the first sentence."
    }

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _get_preserved_elements(self, eval: EvalSummary) -> str:
        """Identify high-scoring dimensions to explicitly preserve."""
        scores = {
            "clarity": eval.clarity,
            "value_proposition": eval.value_proposition,
            "cta_strength": eval.cta_strength,
            "brand_voice": eval.brand_voice,
            "emotional_resonance": eval.emotional_resonance,
        }
        # Preserve anything scoring 7.5+
        strong = [dim for dim, score in scores.items() if score >= 7.5]
        if not strong:
            return "No elements scored above 7.5 — full rewrite is acceptable."
        return f"Keep these strong elements unchanged: {', '.join(strong)} (all scored 7.5+)"

    def generate_fix(self, eval: EvalSummary) -> FixerOutput:
        """
        Generate a targeted repair instruction from an evaluation result.
        Returns escalate=True if max iterations reached.
        """
        # Hard cap check — escalate instead of generating more instructions
        if eval.iteration >= self.MAX_ITERATIONS:
            return FixerOutput(
                targeted_instruction="",
                dimension_to_fix=eval.weakest_dimension,
                preserve_elements="",
                escalate=True,
                escalation_reason=(
                    f"Max iterations ({self.MAX_ITERATIONS}) reached. "
                    f"Best score achieved: {eval.aggregate_score:.1f}/10. "
                    f"Persistent weakness: {eval.weakest_dimension}. "
                    f"Ad flagged for human review."
                )
            )

        preserve = self._get_preserved_elements(eval)
        strategy = self.DIMENSION_STRATEGIES.get(
            eval.weakest_dimension,
            eval.improvement_suggestion
        )

        prompt = f"""You are generating a targeted repair instruction for an ad copywriter.

EVALUATION RESULT:
- Weakest dimension: {eval.weakest_dimension} (score: {getattr(eval, eval.weakest_dimension):.1f}/10)
- Evaluator's suggestion: {eval.improvement_suggestion}
- Proven fix strategy for this dimension: {strategy}
- What to preserve: {preserve}
- This is iteration {eval.iteration} of {self.MAX_ITERATIONS}

Write ONE targeted instruction (2-3 sentences max) telling the writer:
1. Exactly what to change in the {eval.weakest_dimension}
2. A specific technique to use (from the strategy above)
3. What NOT to touch

Be surgical. Be specific. No vague directions like "make it more emotional."
Instead: "Replace the opening sentence with a question that names the parent's
specific fear about college admissions deadlines."

Return just the instruction as plain text. No JSON, no headers."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        instruction = response.content[0].text.strip()

        return FixerOutput(
            targeted_instruction=instruction,
            dimension_to_fix=eval.weakest_dimension,
            preserve_elements=preserve,
            escalate=False
        )

    def print_fix(self, fix: FixerOutput):
        """Pretty-print fixer output to terminal."""
        print(f"\n{'='*60}")
        if fix.escalate:
            print(f"⚠️  ESCALATION — Max iterations reached")
            print(f"   Reason: {fix.escalation_reason}")
        else:
            print(f"🔧 FIXER OUTPUT")
            print(f"{'='*60}")
            print(f"  Dimension to fix: {fix.dimension_to_fix}")
            print(f"  Instruction:      {fix.targeted_instruction}")
            print(f"  Preserve:         {fix.preserve_elements}")
        print(f"{'='*60}\n")


# ─── Smoke Test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Smoke test — two scenarios:
    1. Normal fix on iteration 1 (emotional_resonance is weakest)
    2. Escalation on iteration 3 (max iterations reached)
    """
    from progress_tracker import mark_complete

    fixer = FixerAgent()

    print("🧪 SMOKE TEST — FixerAgent")

    # Scenario 1: Normal fix — emotional resonance is weak
    print("\nScenario 1: Normal fix (iteration 1, emotional_resonance weak)...")
    eval_normal = EvalSummary(
        clarity=9.0,
        value_proposition=8.5,
        cta_strength=8.0,
        brand_voice=9.5,
        emotional_resonance=6.2,
        aggregate_score=8.2,
        weakest_dimension="emotional_resonance",
        improvement_suggestion="Replace opening with question naming parent's fear about college admissions",
        iteration=1
    )
    fix_normal = fixer.generate_fix(eval_normal)
    fixer.print_fix(fix_normal)

    assert not fix_normal.escalate, "Should not escalate on iteration 1"
    assert len(fix_normal.targeted_instruction) > 20, "Instruction too short"
    assert fix_normal.dimension_to_fix == "emotional_resonance"
    print("✅ Scenario 1 passed")

    # Scenario 2: Escalation — max iterations reached
    print("\nScenario 2: Escalation (iteration 3, max reached)...")
    eval_maxed = EvalSummary(
        clarity=7.0,
        value_proposition=6.5,
        cta_strength=7.0,
        brand_voice=6.8,
        emotional_resonance=5.5,
        aggregate_score=6.6,
        weakest_dimension="emotional_resonance",
        improvement_suggestion="Needs complete rewrite of emotional hook",
        iteration=3
    )
    fix_maxed = fixer.generate_fix(eval_maxed)
    fixer.print_fix(fix_maxed)

    assert fix_maxed.escalate, "Should escalate on iteration 3"
    assert fix_maxed.escalation_reason is not None
    print("✅ Scenario 2 passed")

    print("\n✅ SMOKE TEST PASSED — FixerAgent working correctly!")
    mark_complete("fixer_agent_built")
