"""Tests for A/B variant generation — creative approaches and prompt modification."""

import json
from unittest.mock import patch, MagicMock

import pytest

from writer_agent import CampaignBrief, GeneratedAd
from ab_variant_generator import (
    CREATIVE_APPROACHES,
    _modify_brief_for_approach,
    get_approaches_by_names,
    generate_ab_variants,
)


# ── Test: At least 4 creative approaches defined ─────────────────────────────

def test_minimum_creative_approaches():
    assert len(CREATIVE_APPROACHES) >= 4


def test_each_approach_has_name_and_description():
    for approach in CREATIVE_APPROACHES:
        assert "name" in approach
        assert "description" in approach
        assert len(approach["name"]) > 0
        assert len(approach["description"]) > 20


# ── Test: Each approach produces a different prompt context ──────────────────

def test_approaches_produce_different_tones():
    brief = CampaignBrief(
        audience="parents of high school juniors",
        product="1-on-1 SAT tutoring",
        goal="conversion",
        tone="warm, urgent",
    )

    modified_tones = set()
    for approach in CREATIVE_APPROACHES:
        modified = _modify_brief_for_approach(brief, approach)
        modified_tones.add(modified.tone)
        # Each modified tone should contain the approach name
        assert approach["name"].upper() in modified.tone
        # Original tone should be preserved within the modified tone
        assert "warm, urgent" in modified.tone

    # All approaches produce distinct tone strings
    assert len(modified_tones) == len(CREATIVE_APPROACHES)


# ── Test: Modified brief preserves all other fields ──────────────────────────

def test_modify_brief_preserves_fields():
    brief = CampaignBrief(
        audience="parents of middle schoolers",
        product="math tutoring",
        goal="awareness",
        tone="reassuring",
        key_benefit="builds confidence",
        proof_point="93% improve a letter grade",
    )
    approach = CREATIVE_APPROACHES[0]
    modified = _modify_brief_for_approach(brief, approach)

    assert modified.audience == brief.audience
    assert modified.product == brief.product
    assert modified.goal == brief.goal
    assert modified.key_benefit == brief.key_benefit
    assert modified.proof_point == brief.proof_point
    # Tone is modified, not identical
    assert modified.tone != brief.tone


# ── Test: get_approaches_by_names validates names ────────────────────────────

def test_get_approaches_by_names_valid():
    names = ["pain_point_hook", "urgency_hook"]
    result = get_approaches_by_names(names)
    assert len(result) == 2
    assert result[0]["name"] == "pain_point_hook"
    assert result[1]["name"] == "urgency_hook"


def test_get_approaches_by_names_invalid():
    with pytest.raises(ValueError, match="Unknown approach"):
        get_approaches_by_names(["nonexistent_hook"])


# ── Test: variant_approach field is populated on GeneratedAd ─────────────────

def test_generated_ad_variant_approach_field():
    ad = GeneratedAd(
        primary_text="Test ad text",
        headline="Test headline",
        description="Test description",
        cta_button="Book a Free Session",
        variant_approach="pain_point_hook",
    )
    assert ad.variant_approach == "pain_point_hook"


def test_generated_ad_variant_approach_defaults_none():
    ad = GeneratedAd(
        primary_text="Test ad text",
        headline="Test headline",
        description="Test description",
        cta_button="Book a Free Session",
    )
    assert ad.variant_approach is None


# ── Test: generate_ab_variants calls pipeline per approach ───────────────────

@patch("db.get_db")
@patch("ab_variant_generator.run_pipeline")
def test_generate_ab_variants_calls_pipeline_per_variant(mock_pipeline, mock_get_db):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db

    mock_pipeline.return_value = {
        "campaign_id": "test-123",
        "generated_ad": {
            "primary_text": "Test",
            "headline": "Test",
            "description": "Test",
            "cta_button": "Book a Free Session",
        },
        "evaluation": {"aggregate_score": 8.0, "meets_threshold": True},
        "all_evaluations": [{"aggregate_score": 8.0}],
        "iteration": 1,
        "approved": True,
        "escalated": False,
        "final_ad_id": "ad-456",
    }

    brief = CampaignBrief(
        audience="parents",
        product="tutoring",
        goal="conversion",
    )

    results = generate_ab_variants(
        "test-123", brief, num_variants=3,
        approach_names=["pain_point_hook", "urgency_hook", "question_hook"],
    )

    assert len(results) == 3
    assert mock_pipeline.call_count == 3
    assert results[0]["approach"] == "pain_point_hook"
    assert results[1]["approach"] == "urgency_hook"
    assert results[2]["approach"] == "question_hook"

    # Each pipeline call should get a different brief (different tone)
    call_briefs = [call.args[1] for call in mock_pipeline.call_args_list]
    tones = [b.tone for b in call_briefs]
    assert len(set(tones)) == 3, "Each variant should have a unique modified tone"

    # variant_approach should be saved to DB for each ad
    assert mock_db.update_ad.call_count == 3
    for i, call in enumerate(mock_db.update_ad.call_args_list):
        assert "variant_approach" in call.args[1]
