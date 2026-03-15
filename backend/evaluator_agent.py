"""
evaluator_agent.py
------------------
The EvaluatorAgent is the most critical component of the system.
It acts as an LLM-as-judge, scoring each generated ad across 7 dimensions
using Claude Sonnet — chosen for its reasoning quality and vision capability.

Scoring dimensions (each 1.0 - 10.0):
  1. clarity                    — Is the message immediately understandable?
  2. value_proposition          — Does it communicate a clear, compelling benefit?
  3. cta_strength               — Is the call-to-action specific and motivating?
  4. brand_voice                — Does it match Varsity Tutors' tone and style?
  5. emotional_resonance        — Does it connect emotionally with the target audience?
  6. visual_brand_consistency   — Does the image match the brand aesthetic? (v2)
  7. scroll_stopping_power      — Would this image stop a thumb mid-scroll? (v2)

Aggregate score = weighted average. Threshold to pass = 7.0.

Calibrated against real Nerdy SAT messaging guidance with explicit
brand voice penalties for corporate language, fake scarcity, and vague claims.
"""

import json
import os
import base64
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
    image_base64: Optional[str] = None  # base64-encoded image for visual evaluation


class DimensionScore(BaseModel):
    """Score + rationale for a single evaluation dimension."""
    score: float = Field(..., ge=1.0, le=10.0)
    rationale: str = Field(..., min_length=10)
    confidence: float = Field(..., ge=0.0, le=1.0)


class EvaluationResult(BaseModel):
    """Full evaluation result for a single ad."""
    clarity: DimensionScore
    value_proposition: DimensionScore
    cta_strength: DimensionScore
    brand_voice: DimensionScore
    emotional_resonance: DimensionScore
    visual_brand_consistency: Optional[DimensionScore] = None
    scroll_stopping_power: Optional[DimensionScore] = None
    aggregate_score: float = Field(..., ge=1.0, le=10.0)
    meets_threshold: bool
    weakest_dimension: str
    improvement_suggestion: str
    needs_human_review: bool = False

    @field_validator("aggregate_score")
    @classmethod
    def validate_aggregate(cls, v, info):
        """Aggregate should roughly match the average of dimension scores."""
        return round(v, 1)


# ─── Evaluator Agent ─────────────────────────────────────────────────────────

class EvaluatorAgent:
    """
    LLM-as-judge using Claude Sonnet 4.6.
    Evaluates ad copy across 5 text dimensions + 2 visual dimensions (when image provided).
    Uses Claude's vision capability to score generated ad images.
    Calibrated against real Nerdy SAT messaging guidance.
    """

    THRESHOLD = 7.0

    # Text-only weights (used when no image provided — backward compatible)
    TEXT_WEIGHTS = {
        "clarity": 0.20,
        "value_proposition": 0.25,
        "cta_strength": 0.20,
        "brand_voice": 0.20,
        "emotional_resonance": 0.15,
    }

    # Full weights including visual dimensions (used when image provided)
    FULL_WEIGHTS = {
        "clarity": 0.15,
        "value_proposition": 0.20,
        "cta_strength": 0.15,
        "brand_voice": 0.15,
        "emotional_resonance": 0.10,
        "visual_brand_consistency": 0.10,
        "scroll_stopping_power": 0.15,
    }

    SYSTEM_PROMPT = """You are an expert advertising evaluator specializing in Facebook/Instagram ads for Varsity Tutors (a Nerdy company). You evaluate SAT tutoring ads with ruthless honesty, calibrated against real Nerdy messaging guidance.

SCORING CALIBRATION:
- 7.0 = "this could run tomorrow on Meta" 
- 5.0 = "needs significant work"
- 9.0+ = "genuinely exceptional — real parent would stop scrolling and click"

═══ BRAND VOICE RULES (score brand_voice against these) ═══
MUST USE:
- "your child" (NEVER "your student" — parents think of them as children)
- "SAT tutoring" (NEVER "SAT prep")
- Score claims WITH conditions: "100 points/month at 2 sessions/week + 20 min/day practice"
- Specific mechanism: explain HOW, not just that it works
- Real competitive data: "10x more improvement than self-study, 2.6x more than Princeton Review/Kaplan"
- Natural calendar urgency: test dates, application deadlines, weeks remaining

AUTOMATIC BRAND VOICE PENALTIES (score ≤ 5.0 if present):
- Corporate language: "unlock potential", "maximize score potential", "tailored support", "custom strategies", "growth areas", "concrete score gains", "dream college within reach"
- Fake scarcity: "spots filling fast", "limited enrollment", "secure their spot", "don't miss out"
- Vague claims: "personalized", "expert", "data-driven" without showing the mechanism
- Says "your student" instead of "your child"
- Says "SAT prep" instead of "SAT tutoring"
- Generic CTA like "Learn More" for a conversion campaign

═══ CLARITY RULES ═══
- First line must be a hook that stops the scroll
- Single clear message in under 3 seconds of reading
- No competing messages or multiple CTAs

═══ VALUE PROPOSITION RULES ═══
- Specific, differentiated benefit — not "we have tutors"
- Numbers with conditions beat vague promises
- Competitive comparison adds credibility
- "200 points" claim needs conditions or it's not believable above 1350 starting score

═══ CTA RULES ═══
- Must match the funnel stage: "Book a Free Session" / "Get a Free Diagnostic" for conversion, "See What Score Is Realistic" for awareness
- "Learn More" is almost always wrong for Varsity Tutors ads
- Low-friction first step: free diagnostic, free session, score estimate

═══ EMOTIONAL RESONANCE RULES ═══
- Taps into real parent motivation: fear of missed window, GPA-SAT mismatch frustration, scholarship anxiety, accountability exhaustion, prior bad experience
- Story/question hooks > feature lists
- Pain point → solution → proof → CTA pattern
- Must feel like a parent talking to another parent, not a brand talking at a parent

═══ VISUAL EVALUATION RULES (when image is provided) ═══
VISUAL BRAND CONSISTENCY:
- Does the image feel like a Varsity Tutors ad? Clean, modern, warm, educational
- Color palette should lean toward blues, whites, and warm accents
- NOT generic stock photography (smiling person with thumbs up = score ≤ 4.0)
- NOT clipart or illustrated — should be photorealistic
- No text baked into the image (text is handled by the ad copy layer)
- Should feel aspirational and outcome-focused, not desperate or salesy

SCROLL-STOPPING POWER:
- Would this image make a parent stop scrolling on Instagram?
- Does it evoke an emotional response that complements the ad copy?
- Visual hierarchy — is there a clear focal point?
- Does it stand out from typical feed content?
- Does it feel authentic vs. overly polished/corporate?
- A great ad image tells a micro-story that makes you want to read the copy

You must respond with valid JSON only. No preamble, no markdown, no explanation outside the JSON."""

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    @property
    def WEIGHTS(self):
        """Backward-compatible property that returns text-only weights."""
        return self.TEXT_WEIGHTS

    def _build_eval_prompt(self, ad: AdContent) -> str:
        has_image = ad.image_base64 is not None

        visual_dimensions = ""
        if has_image:
            visual_dimensions = """
  "visual_brand_consistency": {
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences on brand alignment of the image>",
    "confidence": <float 0.0-1.0>
  },
  "scroll_stopping_power": {
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences on visual impact and scroll-stopping potential>",
    "confidence": <float 0.0-1.0>
  },"""

        image_instruction = ""
        if has_image:
            image_instruction = """
An image has been provided with this ad. Evaluate the visual creative alongside the copy.
Score the two visual dimensions (visual_brand_consistency and scroll_stopping_power) based on how well the image works as a Facebook/Instagram ad creative for Varsity Tutors."""

        return f"""Evaluate this Varsity Tutors ad for a {ad.audience} audience.

AD CONTENT:
Primary Text: {ad.primary_text}
Headline: {ad.headline}
Description: {ad.description or "N/A"}
CTA Button: {ad.cta_button}
Campaign Goal: {ad.goal}
Product: {ad.product}
{image_instruction}

Score each dimension from 1.0 to 10.0 with one decimal precision.
For each dimension, also provide a confidence score (0.0-1.0) reflecting how certain you are in the score based on the available evidence. Score 0.9+ when the evidence is clear, 0.5-0.8 when the ad is ambiguous, below 0.5 when you're genuinely unsure.
Identify the single weakest dimension and give one specific, actionable improvement suggestion.

Respond with this exact JSON structure:
{{
  "clarity": {{
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences explaining the score>",
    "confidence": <float 0.0-1.0>
  }},
  "value_proposition": {{
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences explaining the score>",
    "confidence": <float 0.0-1.0>
  }},
  "cta_strength": {{
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences explaining the score>",
    "confidence": <float 0.0-1.0>
  }},
  "brand_voice": {{
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences explaining the score>",
    "confidence": <float 0.0-1.0>
  }},
  "emotional_resonance": {{
    "score": <float 1.0-10.0>,
    "rationale": "<1-2 sentences explaining the score>",
    "confidence": <float 0.0-1.0>
  }},{visual_dimensions}
  "aggregate_score": <weighted average, float 1.0-10.0>,
  "meets_threshold": <true if aggregate >= 7.0, else false>,
  "weakest_dimension": "<name of lowest-scoring dimension>",
  "improvement_suggestion": "<one specific, actionable fix targeting the weakest dimension>"
}}"""

    def _build_messages(self, ad: AdContent) -> list[dict]:
        """Build message payload, including image if provided."""
        prompt_text = self._build_eval_prompt(ad)

        if ad.image_base64:
            return [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": ad.image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt_text,
                        },
                    ],
                }
            ]
        else:
            return [{"role": "user", "content": prompt_text}]

    def evaluate(self, ad: AdContent) -> EvaluationResult:
        """
        Evaluate a single ad. Returns structured EvaluationResult.
        When image_base64 is provided, includes visual dimension scores.
        Raises ValueError if LLM returns malformed JSON after retries.
        """
        has_image = ad.image_base64 is not None
        weights = self.FULL_WEIGHTS if has_image else self.TEXT_WEIGHTS

        for attempt in range(3):
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    system=self.SYSTEM_PROMPT,
                    messages=self._build_messages(ad),
                )

                raw = response.content[0].text.strip()

                # Strip markdown fences if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                raw = raw.strip()

                data = json.loads(raw)

                # Calculate our own aggregate (don't trust LLM math)
                calculated_aggregate = 0.0
                for dim, weight in weights.items():
                    if dim in data:
                        calculated_aggregate += data[dim]["score"] * weight
                calculated_aggregate = round(calculated_aggregate, 1)

                data["aggregate_score"] = calculated_aggregate
                data["meets_threshold"] = calculated_aggregate >= self.THRESHOLD

                dimensions = {
                    "clarity": DimensionScore(**data["clarity"]),
                    "value_proposition": DimensionScore(**data["value_proposition"]),
                    "cta_strength": DimensionScore(**data["cta_strength"]),
                    "brand_voice": DimensionScore(**data["brand_voice"]),
                    "emotional_resonance": DimensionScore(**data["emotional_resonance"]),
                }

                visual_dimensions = {}
                if has_image and "visual_brand_consistency" in data:
                    visual_dimensions["visual_brand_consistency"] = DimensionScore(
                        **data["visual_brand_consistency"]
                    )
                if has_image and "scroll_stopping_power" in data:
                    visual_dimensions["scroll_stopping_power"] = DimensionScore(
                        **data["scroll_stopping_power"]
                    )

                all_dims = {**dimensions, **visual_dimensions}
                needs_human_review = any(
                    dim.confidence < 0.6 for dim in all_dims.values()
                )

                return EvaluationResult(
                    **dimensions,
                    **visual_dimensions,
                    aggregate_score=data["aggregate_score"],
                    meets_threshold=data["meets_threshold"],
                    weakest_dimension=data["weakest_dimension"],
                    improvement_suggestion=data["improvement_suggestion"],
                    needs_human_review=needs_human_review,
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
        print(f"  Clarity:             {result.clarity.score:.1f}/10  (conf: {result.clarity.confidence:.2f})  — {result.clarity.rationale}")
        print(f"  Value Proposition:   {result.value_proposition.score:.1f}/10  (conf: {result.value_proposition.confidence:.2f})  — {result.value_proposition.rationale}")
        print(f"  CTA Strength:        {result.cta_strength.score:.1f}/10  (conf: {result.cta_strength.confidence:.2f})  — {result.cta_strength.rationale}")
        print(f"  Brand Voice:         {result.brand_voice.score:.1f}/10  (conf: {result.brand_voice.confidence:.2f})  — {result.brand_voice.rationale}")
        print(f"  Emotional Resonance: {result.emotional_resonance.score:.1f}/10  (conf: {result.emotional_resonance.confidence:.2f})  — {result.emotional_resonance.rationale}")
        if result.visual_brand_consistency:
            print(f"  Visual Brand:        {result.visual_brand_consistency.score:.1f}/10  (conf: {result.visual_brand_consistency.confidence:.2f})  — {result.visual_brand_consistency.rationale}")
        if result.scroll_stopping_power:
            print(f"  Scroll-Stop Power:   {result.scroll_stopping_power.score:.1f}/10  (conf: {result.scroll_stopping_power.confidence:.2f})  — {result.scroll_stopping_power.rationale}")
        print(f"{'─'*60}")
        print(f"  AGGREGATE:           {result.aggregate_score:.1f}/10")
        print(f"  MEETS THRESHOLD:     {result.meets_threshold} (threshold: {self.THRESHOLD})")
        print(f"  NEEDS HUMAN REVIEW:  {result.needs_human_review}")
        print(f"  WEAKEST DIMENSION:   {result.weakest_dimension}")
        print(f"  SUGGESTION:          {result.improvement_suggestion}")
        has_visual = result.visual_brand_consistency is not None
        print(f"  EVALUATION MODE:     {'7-dimension (text + visual)' if has_visual else '5-dimension (text only)'}")
        print(f"{'='*60}\n")


# ─── Calibration Test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Calibration run — evaluates one known-good and one known-bad ad
    to verify the evaluator is scoring sensibly.
    Expected: good ad ~8.0+, bad ad ~3.0-4.5
    The known-bad ad deliberately uses corporate language and generic CTA
    to test the brand voice penalty rules.
    """
    from progress_tracker import mark_complete

    evaluator = EvaluatorAgent()

    # Known-good ad (uses parent language, specific claims, strong CTA)
    good_ad = AdContent(
        primary_text="3.8 GPA. 1260 SAT. Something's off. Most mid-1200s students are 3-4 targeted fixes away from a 1400+. Our tutors diagnose exactly where points are hiding — and your child sees ~100 points/month at 2 sessions per week.",
        headline="Your Child's SAT Gap Is Fixable",
        description="1-on-1 SAT tutoring with weekly progress reports.",
        cta_button="Get a Free Diagnostic",
        audience="parents of high-achieving juniors with GPA-SAT mismatch",
        product="1-on-1 SAT tutoring",
        goal="conversion"
    )

    # Known-bad ad (corporate language, vague claims, generic CTA — should trigger brand voice penalties)
    bad_ad = AdContent(
        primary_text="Varsity Tutors offers personalized tutoring services for students of all ages. Our experienced tutors are ready to help your student unlock their full potential and achieve concrete score gains.",
        headline="Get Tutoring Today",
        description="Quality tutoring from experienced professionals.",
        cta_button="Learn More",
        audience="parents of K-12 students",
        product="general tutoring",
        goal="awareness"
    )

    print("🧪 CALIBRATION RUN — EvaluatorAgent (text-only, 5 dimensions)")
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
