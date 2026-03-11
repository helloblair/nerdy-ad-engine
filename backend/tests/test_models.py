"""Tests for Pydantic model validation — CampaignBrief, GeneratedAd, EvaluationResult."""

import pytest
from pydantic import ValidationError

from writer_agent import CampaignBrief, GeneratedAd
from evaluator_agent import EvaluationResult, DimensionScore


# ── Test 1: CampaignBrief validates required fields ────────────────────────

def test_campaign_brief_requires_audience_product_goal():
    with pytest.raises(ValidationError):
        CampaignBrief(audience="parents", product="tutoring")  # missing goal


# ── Test 2: CampaignBrief defaults work ────────────────────────────────────

def test_campaign_brief_defaults():
    brief = CampaignBrief(audience="parents", product="tutoring", goal="conversion")
    assert brief.tone == "warm, urgent, outcome-focused"
    assert brief.key_benefit is None
    assert brief.proof_point is None


# ── Test 3: GeneratedAd requires all fields ────────────────────────────────

def test_generated_ad_requires_fields():
    with pytest.raises(ValidationError):
        GeneratedAd(primary_text="text", headline="headline")  # missing description, cta_button


# ── Test 4: DimensionScore rejects out-of-range scores ────────────────────

def test_dimension_score_rejects_out_of_range():
    with pytest.raises(ValidationError):
        DimensionScore(score=11.0, rationale="This score is too high for the range.")

    with pytest.raises(ValidationError):
        DimensionScore(score=0.5, rationale="This score is too low for the range.")


# ── Test 5: DimensionScore rejects short rationale ────────────────────────

def test_dimension_score_rejects_short_rationale():
    with pytest.raises(ValidationError):
        DimensionScore(score=7.0, rationale="Short")


# ── Test 6: EvaluationResult aggregate validator rounds to 1 decimal ──────

def test_evaluation_result_rounds_aggregate():
    result = EvaluationResult(
        clarity=DimensionScore(score=8.0, rationale="Clear and direct message targeting parents."),
        value_proposition=DimensionScore(score=7.5, rationale="Strong outcome-focused proposition."),
        cta_strength=DimensionScore(score=7.0, rationale="Specific call to action."),
        brand_voice=DimensionScore(score=8.0, rationale="Matches brand tone well."),
        emotional_resonance=DimensionScore(score=7.0, rationale="Reasonable emotional connection."),
        aggregate_score=7.5555,
        meets_threshold=True,
        weakest_dimension="cta_strength",
        improvement_suggestion="Make the CTA more specific to the product.",
    )
    assert result.aggregate_score == 7.6  # rounded to 1 decimal
