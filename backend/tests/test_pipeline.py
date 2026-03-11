"""Tests for the LangGraph pipeline — generate→evaluate loop and fix cycles."""

import json
from unittest.mock import patch, MagicMock

import pytest

from writer_agent import CampaignBrief


# ── Helpers ─────────────────────────────────────────────────────────────────

def _mock_gemini_response(ad_dict: dict) -> MagicMock:
    response = MagicMock()
    response.text = json.dumps(ad_dict)
    return response


def _mock_anthropic_response(text: str) -> MagicMock:
    text_block = MagicMock()
    text_block.text = text
    response = MagicMock()
    response.content = [text_block]
    return response


GOOD_AD = {
    "primary_text": "Her SAT score jumped 360 points. A tutor matched to how she learns.",
    "headline": "360-Point SAT Jump",
    "description": "Results that speak for themselves.",
    "cta_button": "Book a Free Session",
    "writer_notes": "Proof-point lead.",
}

HIGH_EVAL = {
    "clarity": {"score": 9.0, "rationale": "Clear and direct message."},
    "value_proposition": {"score": 8.5, "rationale": "Strong outcome-focused value."},
    "cta_strength": {"score": 8.0, "rationale": "Specific and action-oriented."},
    "brand_voice": {"score": 8.5, "rationale": "Matches Varsity Tutors tone."},
    "emotional_resonance": {"score": 8.0, "rationale": "Connects with parent fears."},
    "aggregate_score": 8.5,
    "meets_threshold": True,
    "weakest_dimension": "emotional_resonance",
    "improvement_suggestion": "Could deepen the emotional hook.",
}

LOW_EVAL = {
    "clarity": {"score": 5.0, "rationale": "Confusing message structure."},
    "value_proposition": {"score": 4.5, "rationale": "No concrete benefit."},
    "cta_strength": {"score": 5.5, "rationale": "Generic CTA."},
    "brand_voice": {"score": 4.0, "rationale": "Too corporate."},
    "emotional_resonance": {"score": 3.5, "rationale": "No emotional connection."},
    "aggregate_score": 4.5,
    "meets_threshold": False,
    "weakest_dimension": "emotional_resonance",
    "improvement_suggestion": "Needs emotional rewrite.",
}


def _mock_db():
    """Return a mock db that simulates insert_ad and insert_evaluation."""
    mock = MagicMock()
    mock.insert_ad.return_value = {"id": "test-ad-id-1234"}
    mock.insert_evaluation.return_value = {"id": "test-eval-id-1234"}
    return mock


# ── Test 1: Approved ad returns aggregate_score ─────────────────────────────

@patch("pipeline.get_db")
@patch("pipeline.researcher")
@patch("pipeline.fixer")
@patch("pipeline.evaluator")
@patch("pipeline.writer")
def test_pipeline_returns_aggregate_score(
    mock_writer, mock_evaluator, mock_fixer, mock_researcher, mock_get_db,
    sample_brief,
):
    from writer_agent import GeneratedAd
    from evaluator_agent import EvaluationResult, DimensionScore

    mock_get_db.return_value = _mock_db()
    mock_researcher.extract_context.return_value = MagicMock()
    mock_researcher.format_for_prompt.return_value = "test context"
    mock_writer.generate.return_value = GeneratedAd(**GOOD_AD)
    mock_writer.print_ad = MagicMock()

    result = EvaluationResult(
        clarity=DimensionScore(score=9.0, rationale="Clear and direct message."),
        value_proposition=DimensionScore(score=8.5, rationale="Strong outcome-focused value."),
        cta_strength=DimensionScore(score=8.0, rationale="Specific and action-oriented CTA."),
        brand_voice=DimensionScore(score=8.5, rationale="Matches Varsity Tutors brand tone."),
        emotional_resonance=DimensionScore(score=8.0, rationale="Connects with parent emotions."),
        aggregate_score=8.5, meets_threshold=True,
        weakest_dimension="emotional_resonance",
        improvement_suggestion="Could deepen the emotional hook.",
    )
    mock_evaluator.evaluate.return_value = result
    mock_evaluator.print_result = MagicMock()

    from pipeline import run_pipeline
    state = run_pipeline("test-campaign-id", sample_brief)

    assert state["evaluation"]["aggregate_score"] == 8.5
    assert state["approved"] is True


# ── Test 2: Low score triggers fix cycle ────────────────────────────────────

@patch("pipeline.get_db")
@patch("pipeline.researcher")
@patch("pipeline.fixer")
@patch("pipeline.evaluator")
@patch("pipeline.writer")
def test_low_score_triggers_fix_cycle(
    mock_writer, mock_evaluator, mock_fixer, mock_researcher, mock_get_db,
    sample_brief,
):
    from writer_agent import GeneratedAd
    from evaluator_agent import EvaluationResult, DimensionScore
    from fixer_agent import FixerOutput

    mock_get_db.return_value = _mock_db()
    mock_researcher.extract_context.return_value = MagicMock()
    mock_researcher.format_for_prompt.return_value = "test context"
    mock_writer.generate.return_value = GeneratedAd(**GOOD_AD)
    mock_writer.print_ad = MagicMock()

    low_result = EvaluationResult(
        clarity=DimensionScore(score=5.0, rationale="Confusing message structure overall."),
        value_proposition=DimensionScore(score=4.5, rationale="No concrete benefit stated."),
        cta_strength=DimensionScore(score=5.5, rationale="Generic and uninspiring CTA."),
        brand_voice=DimensionScore(score=4.0, rationale="Too corporate and impersonal."),
        emotional_resonance=DimensionScore(score=3.5, rationale="No emotional connection at all."),
        aggregate_score=4.6, meets_threshold=False,
        weakest_dimension="emotional_resonance",
        improvement_suggestion="Needs emotional rewrite.",
    )
    high_result = EvaluationResult(
        clarity=DimensionScore(score=9.0, rationale="Clear and direct now."),
        value_proposition=DimensionScore(score=8.5, rationale="Strong outcome-focused value."),
        cta_strength=DimensionScore(score=8.0, rationale="Specific and action-oriented CTA."),
        brand_voice=DimensionScore(score=8.5, rationale="Matches Varsity Tutors brand tone."),
        emotional_resonance=DimensionScore(score=8.0, rationale="Connects with parent emotions."),
        aggregate_score=8.5, meets_threshold=True,
        weakest_dimension="emotional_resonance",
        improvement_suggestion="Minor polish.",
    )
    # First call: low score → fix. Second call: high score → approve.
    mock_evaluator.evaluate.side_effect = [low_result, high_result]
    mock_evaluator.print_result = MagicMock()

    mock_fixer.generate_fix.return_value = FixerOutput(
        targeted_instruction="Rewrite the opening with the parent's specific fear.",
        dimension_to_fix="emotional_resonance",
        preserve_elements="No elements scored above 7.5.",
        escalate=False,
    )
    mock_fixer.print_fix = MagicMock()

    from pipeline import run_pipeline
    state = run_pipeline("test-campaign-id", sample_brief)

    # Fixer should have been called once (for the low-score iteration)
    assert mock_fixer.generate_fix.call_count == 1
    # Writer called twice: initial + post-fix
    assert mock_writer.generate.call_count == 2
    assert state["approved"] is True
