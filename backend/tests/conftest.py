"""
Shared pytest fixtures for nerdy-ad-engine test suite.

All external API calls (Gemini, Anthropic, Supabase) are mocked at the module
level so tests run without tokens or network access.
"""

import sys
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend/ is on sys.path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from writer_agent import CampaignBrief, WriterInput, GeneratedAd
from evaluator_agent import AdContent, DimensionScore, EvaluationResult


# ── Fixtures: Briefs ────────────────────────────────────────────────────────

@pytest.fixture
def sample_brief():
    return CampaignBrief(
        audience="parents of high school juniors preparing for SAT",
        product="1-on-1 SAT tutoring",
        goal="conversion",
        tone="urgent, empathetic, outcome-focused",
        key_benefit="personalized learning matched to your child's gaps",
        proof_point="students improve an average of 360 points in 8 weeks",
    )


@pytest.fixture
def sample_writer_input(sample_brief):
    return WriterInput(brief=sample_brief, iteration=1)


# ── Fixtures: Ads ───────────────────────────────────────────────────────────

@pytest.fixture
def good_ad():
    """An ad that should score above 7.0."""
    return GeneratedAd(
        primary_text=(
            "Her SAT score jumped 360 points in 8 weeks. Not because she studied "
            "harder — because she finally had a tutor who explained it the way her "
            "brain works."
        ),
        headline="360-Point SAT Improvement",
        description="1-on-1 tutoring matched to your child's learning style.",
        cta_button="Book a Free Session",
        writer_notes="Proof-point lead, emotional reframe close.",
    )


@pytest.fixture
def bad_ad():
    """An ad that should score below 7.0."""
    return GeneratedAd(
        primary_text=(
            "Varsity Tutors offers personalized tutoring services for students of "
            "all ages. Our experienced tutors are ready to help your child succeed "
            "in school."
        ),
        headline="Get Tutoring Today",
        description="Quality tutoring from experienced professionals.",
        cta_button="Learn More",
        writer_notes="Generic — deliberately weak for testing.",
    )


@pytest.fixture
def good_ad_content():
    return AdContent(
        primary_text=(
            "Her SAT score jumped 360 points in 8 weeks. Not because she studied "
            "harder — because she finally had a tutor who explained it the way her "
            "brain works."
        ),
        headline="360-Point SAT Improvement",
        description="1-on-1 tutoring matched to your child's learning style.",
        cta_button="Book a Free Session",
        audience="parents of high school juniors preparing for SAT",
        product="1-on-1 SAT tutoring",
        goal="conversion",
    )


@pytest.fixture
def bad_ad_content():
    return AdContent(
        primary_text=(
            "Varsity Tutors offers personalized tutoring services for students of "
            "all ages. Our experienced tutors are ready to help your child succeed."
        ),
        headline="Get Tutoring Today",
        description="Quality tutoring from experienced professionals.",
        cta_button="Learn More",
        audience="parents of K-12 students",
        product="general tutoring",
        goal="awareness",
    )


# ── Fixtures: Evaluation results ────────────────────────────────────────────

def _make_eval(scores: dict, meets: bool, weakest: str) -> dict:
    """Build a raw evaluation dict matching EvaluationResult.model_dump() shape."""
    from evaluator_agent import EvaluatorAgent
    weights = EvaluatorAgent.WEIGHTS
    agg = round(sum(scores[d] * weights[d] for d in weights), 1)
    return {
        "clarity": {"score": scores["clarity"], "rationale": "Test rationale for clarity.", "confidence": 0.9},
        "value_proposition": {"score": scores["value_proposition"], "rationale": "Test rationale for vp.", "confidence": 0.9},
        "cta_strength": {"score": scores["cta_strength"], "rationale": "Test rationale for cta.", "confidence": 0.9},
        "brand_voice": {"score": scores["brand_voice"], "rationale": "Test rationale for bv.", "confidence": 0.9},
        "emotional_resonance": {"score": scores["emotional_resonance"], "rationale": "Test rationale for er.", "confidence": 0.9},
        "aggregate_score": agg,
        "meets_threshold": meets,
        "weakest_dimension": weakest,
        "improvement_suggestion": f"Improve {weakest} with more specificity.",
    }


@pytest.fixture
def high_eval_dict():
    return _make_eval(
        {"clarity": 9.0, "value_proposition": 8.5, "cta_strength": 8.0,
         "brand_voice": 8.5, "emotional_resonance": 8.0},
        meets=True, weakest="emotional_resonance",
    )


@pytest.fixture
def low_eval_dict():
    return _make_eval(
        {"clarity": 5.0, "value_proposition": 4.5, "cta_strength": 5.5,
         "brand_voice": 4.0, "emotional_resonance": 3.5},
        meets=False, weakest="emotional_resonance",
    )
