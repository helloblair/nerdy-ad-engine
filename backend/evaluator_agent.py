"""
evaluator_agent.py
------------------
The EvaluatorAgent is the most critical component of the system.
It acts as an LLM-as-judge, scoring each generated ad across 5 dimensions
using Claude Sonnet — chosen for its reasoning quality over cheaper alternatives.

Scoring dimensions (each 1.0 - 10.0):
  1. clarity              — Is the message immediately understandable?
  2. value_proposition    — Does it communicate a clear, compelling benefit?
  3. cta_strength         — Is the call-to-action specific and motivating?
  4. brand_voice          — Does it match Varsity Tutors' tone and style?
  5. emotional_resonance  — Does it connect emotionally with the target audience?

Aggregate score = weighted average. Threshold to pass = 7.0.
"""

import json
import os
from typing import Optional
from anthropic import Anthropic
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv()

# ─── Data Models ─────────────────────────────────────────────────────────────

class AdContent(BaseModel):
    """The ad copy to be evaluated."""
    primary_text: str
    headline: str
    description: Optional[str] = None
    cta_button: str
    audience: str
    product: str
    goal: str  # "awareness" or "conversion"


class DimensionScore(BaseModel):
    """Score + rationale for a single evaluation dimension."""
    score: float = Field(..., ge=1.0, le=10.0)
    rationale: str = Field(..., min_length=10)


class EvaluationResult(BaseModel):
    """Full evaluation result for a single ad."""
    clarity: DimensionScore
    value_proposition: DimensionScore
    cta_strength: DimensionScore
    brand_voice: DimensionScore
    emotional_resonance: DimensionScore
    aggregate_score: float = Field(..., ge=1.0, le=10.0)
    meets_threshold: bool
    weakest_dimension: str
    improvement_suggestion: str

    @field_validator("aggregate_score")
    @classmethod
    def validate_aggregate(cls, v, info):
        """Aggregate should roughly match the average of dimension scores."""
        return round(v, 1)


# ─── Evaluator Agent ─────────────────────────────────────────────────────────

class EvaluatorAgent:
    """
    LLM-as-judge using Claude Sonnet 4.6.
    Evaluates ad copy across 5 dimensions and returns structured scores.
    """

    THRESHOLD = 7.0

    # Dimension weights for aggregate score
    WEIGHTS = {
        "clarity": 0.20,
        "value_proposition": 0.25,
        "cta_strength": 0.20,
        "brand_voice": 0.20,
        "emotional_resonance": 0.15,
    }

    SYSTEM_PROMPT = """You are an expert advertising evaluator specializing in educational 
marketing for Varsity Tutors (Nerdy). You have deep knowledge of:
- What makes effective Facebook and Instagram ads for parents of K-12 students
- Varsity Tutors' brand voice: outcome-focused, specific, warm but urgent, never corporate
- The emotional landscape of parents worried about their child's academic performance

You evaluate ads with ruthless honesty. A score of 7.0 means "this could run tomorrow."
A score of 5.0 means "needs significant work." A score of 9.0+ means "genuinely exceptional."

VARSITY TUTORS BRAND VOICE RULES:
- Lead with outcomes and specific numbers, not features ("jumped 360 points" not "personalized tutoring")
- Address parent pain directly — fear of their child falling behind, test anxiety, wasted potential
- Never mention company history, awards, or corporate language
- CTAs must be specific and action-oriented ("Book a Free Session" not "Learn More")
- Emotional reframes work well: "Your child isn't struggling with math — they're struggling with confidence"

You must respond with valid JSON only. No preamble, no markdown, no explanation outside the JSON."""

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _build_eval_prompt(self, ad: AdContent) -> str:
        return f"""Evaluate this Varsity Tutors ad for a {ad.audience} audience.

AD CONTENT:
Primary Text: {ad.primary_text}
Headline: {ad.headline}
Description: {ad.description or "N/A"}
CTA Button: {ad.cta_button}
Campaign Goal: {ad.goal}
Product: {ad.product}

Score each dimension from 1.0 to 10.0 with one decimal precision.
Identify the single weakest dimension and give one specific, actionable improvement suggestion.

Respond with this exact JSON structure:
{{
  "clarity": {{
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences explaining the score>"
  }},
  "value_proposition": {{
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences explaining the score>"
  }},
  "cta_strength": {{
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences explaining the score>"
  }},
  "brand_voice": {{
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences explaining the score>"
  }},
  "emotional_resonance": {{
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences explaining the score>"
  }},
  "aggregate_score": <weighted average, float 1.0-10.0>,
  "meets_threshold": <true if aggregate >= 7.0, else false>,
  "weakest_dimension": "<name of lowest-scoring dimension>",
  "improvement_suggestion": "<one specific, actionable fix targeting the weakest dimension>"
}}"""

    def evaluate(self, ad: AdContent) -> EvaluationResult:
        """
        Evaluate a single ad. Returns structured EvaluationResult.
        Raises ValueError if LLM returns malformed JSON after retries.
        """
        for attempt in range(3):
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1000,
                    system=self.SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": self._build_eval_prompt(ad)}
                    ]
                )

                raw = response.content[0].text.strip()

                # Strip markdown fences if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                raw = raw.strip()

                data = json.loads(raw)

                # Calculate our own aggregate as a sanity check
                calculated_aggregate = sum(
                    data[dim]["score"] * weight
                    for dim, weight in self.WEIGHTS.items()
                )
                calculated_aggregate = round(calculated_aggregate, 1)

                # Use our calculated aggregate (don't trust LLM math)
                data["aggregate_score"] = calculated_aggregate
                data["meets_threshold"] = calculated_aggregate >= self.THRESHOLD

                return EvaluationResult(
                    clarity=DimensionScore(**data["clarity"]),
                    value_proposition=DimensionScore(**data["value_proposition"]),
                    cta_strength=DimensionScore(**data["cta_strength"]),
                    brand_voice=DimensionScore(**data["brand_voice"]),
                    emotional_resonance=DimensionScore(**data["emotional_resonance"]),
                    aggregate_score=data["aggregate_score"],
                    meets_threshold=data["meets_threshold"],
                    weakest_dimension=data["weakest_dimension"],
                    improvement_suggestion=data["improvement_suggestion"],
                )

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                if attempt == 2:
                    raise ValueError(
                        f"EvaluatorAgent failed after 3 attempts: {e}\nRaw response: {raw}"
                    )
                print(f"⚠️  Evaluation attempt {attempt + 1} failed, retrying... ({e})")

    def print_result(self, ad: AdContent, result: EvaluationResult):
        """Pretty-print evaluation results to terminal."""
        threshold_icon = "✅" if result.meets_threshold else "❌"
        print(f"\n{'='*60}")
        print(f"EVALUATION RESULT {threshold_icon}")
        print(f"{'='*60}")
        print(f"Headline: {ad.headline}")
        print(f"{'─'*60}")
        print(f"  Clarity:             {result.clarity.score:.1f}/10  — {result.clarity.rationale}")
        print(f"  Value Proposition:   {result.value_proposition.score:.1f}/10  — {result.value_proposition.rationale}")
        print(f"  CTA Strength:        {result.cta_strength.score:.1f}/10  — {result.cta_strength.rationale}")
        print(f"  Brand Voice:         {result.brand_voice.score:.1f}/10  — {result.brand_voice.rationale}")
        print(f"  Emotional Resonance: {result.emotional_resonance.score:.1f}/10  — {result.emotional_resonance.rationale}")
        print(f"{'─'*60}")
        print(f"  AGGREGATE:           {result.aggregate_score:.1f}/10")
        print(f"  MEETS THRESHOLD:     {result.meets_threshold} (threshold: {self.THRESHOLD})")
        print(f"  WEAKEST DIMENSION:   {result.weakest_dimension}")
        print(f"  SUGGESTION:          {result.improvement_suggestion}")
        print(f"{'='*60}\n")


# ─── Calibration Test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Calibration run — evaluates one known-good and one known-bad ad
    to verify the evaluator is scoring sensibly before we wire it into LangGraph.
    Expected: good ad ~8.0+, bad ad ~3.0-4.5
    """
    from progress_tracker import mark_complete

    evaluator = EvaluatorAgent()

    # Known-good ad (based on real Varsity Tutors Meta Ad Library creative)
    good_ad = AdContent(
        primary_text="Her SAT score jumped 360 points in 8 weeks. Not because she studied harder — because she finally had a tutor who explained it the way her brain works.",
        headline="360-Point SAT Improvement",
        description="1-on-1 tutoring matched to your child's learning style.",
        cta_button="Book a Free Session",
        audience="parents of high school students preparing for SAT",
        product="1-on-1 SAT tutoring",
        goal="conversion"
    )

    # Known-bad ad (deliberately weak — generic, no specifics, weak CTA)
    bad_ad = AdContent(
        primary_text="Varsity Tutors offers personalized tutoring services for students of all ages. Our experienced tutors are ready to help your child succeed in school.",
        headline="Get Tutoring Today",
        description="Quality tutoring from experienced professionals.",
        cta_button="Learn More",
        audience="parents of K-12 students",
        product="general tutoring",
        goal="awareness"
    )

    print("🧪 CALIBRATION RUN — EvaluatorAgent")
    print("Testing known-good ad (expect ~8.0+)...")
    good_result = evaluator.evaluate(good_ad)
    evaluator.print_result(good_ad, good_result)

    print("Testing known-bad ad (expect ~3.0-4.5)...")
    bad_result = evaluator.evaluate(bad_ad)
    evaluator.print_result(bad_ad, bad_result)

    # Sanity check
    assert good_result.aggregate_score > bad_result.aggregate_score, \
        "❌ CALIBRATION FAILED: Good ad scored lower than bad ad!"

    score_gap = good_result.aggregate_score - bad_result.aggregate_score
    print(f"✅ CALIBRATION PASSED — Score gap: {score_gap:.1f} points")
    print(f"   Good ad: {good_result.aggregate_score:.1f} | Bad ad: {bad_result.aggregate_score:.1f}")

    if good_result.aggregate_score >= 7.5 and bad_result.aggregate_score <= 5.0:
        print("✅ Score ranges look correct — evaluator is calibrated!")
        mark_complete("evaluator_agent_built")
        mark_complete("evaluator_calibrated")
    else:
        print("⚠️  Scores outside expected ranges — review system prompt before proceeding")
