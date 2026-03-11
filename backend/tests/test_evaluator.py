"""Tests for EvaluatorAgent — scoring dimensions, weights, and thresholds."""

import json
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

import pytest

from evaluator_agent import EvaluatorAgent, EvaluationResult, DimensionScore, AdContent


DIMENSIONS = ["clarity", "value_proposition", "cta_strength", "brand_voice", "emotional_resonance"]


def _mock_anthropic_response(scores: dict, weakest: str = "cta_strength") -> MagicMock:
    """Build a mock Anthropic Messages response returning the given scores."""
    payload = {
        dim: {"score": scores[dim], "rationale": f"Solid rationale for {dim} scoring."}
        for dim in DIMENSIONS
    }
    payload["aggregate_score"] = 0  # evaluator recalculates
    payload["meets_threshold"] = False
    payload["weakest_dimension"] = weakest
    payload["improvement_suggestion"] = "Be more specific in the CTA."

    text_block = MagicMock()
    text_block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [text_block]
    return response


# ── Test 1: All 5 dimensions present ────────────────────────────────────────

@patch("evaluator_agent.Anthropic")
def test_evaluator_returns_all_five_dimensions(mock_cls, good_ad_content):
    scores = {d: 8.0 for d in DIMENSIONS}
    mock_cls.return_value.messages.create.return_value = _mock_anthropic_response(scores)

    evaluator = EvaluatorAgent()
    result = evaluator.evaluate(good_ad_content)

    for dim in DIMENSIONS:
        assert hasattr(result, dim), f"Missing dimension: {dim}"
        assert isinstance(getattr(result, dim), DimensionScore)


# ── Test 2: Scores are floats 0-10 ─────────────────────────────────────────

@patch("evaluator_agent.Anthropic")
def test_scores_are_floats_in_range(mock_cls, good_ad_content):
    scores = {"clarity": 7.5, "value_proposition": 8.2, "cta_strength": 6.1,
              "brand_voice": 9.0, "emotional_resonance": 5.5}
    mock_cls.return_value.messages.create.return_value = _mock_anthropic_response(scores)

    evaluator = EvaluatorAgent()
    result = evaluator.evaluate(good_ad_content)

    for dim in DIMENSIONS:
        s = getattr(result, dim).score
        assert isinstance(s, float)
        assert 1.0 <= s <= 10.0, f"{dim} score {s} out of range"


# ── Test 3: Aggregate is weighted average ───────────────────────────────────

@patch("evaluator_agent.Anthropic")
def test_aggregate_is_weighted_average(mock_cls, good_ad_content):
    scores = {"clarity": 9.0, "value_proposition": 8.0, "cta_strength": 7.0,
              "brand_voice": 6.0, "emotional_resonance": 5.0}
    mock_cls.return_value.messages.create.return_value = _mock_anthropic_response(scores)

    evaluator = EvaluatorAgent()
    result = evaluator.evaluate(good_ad_content)

    expected = round(
        9.0 * 0.20 + 8.0 * 0.25 + 7.0 * 0.20 + 6.0 * 0.20 + 5.0 * 0.15, 1
    )
    assert result.aggregate_score == expected


# ── Test 4: Low-quality ad scores below 7.0 ────────────────────────────────

@patch("evaluator_agent.Anthropic")
def test_low_quality_ad_below_threshold(mock_cls, bad_ad_content):
    scores = {"clarity": 4.0, "value_proposition": 3.5, "cta_strength": 4.5,
              "brand_voice": 3.0, "emotional_resonance": 3.0}
    mock_cls.return_value.messages.create.return_value = _mock_anthropic_response(
        scores, weakest="brand_voice"
    )

    evaluator = EvaluatorAgent()
    result = evaluator.evaluate(bad_ad_content)

    assert result.aggregate_score < 7.0
    assert result.meets_threshold is False


# ── Test 5: High-quality ad scores above 7.0 ───────────────────────────────

@patch("evaluator_agent.Anthropic")
def test_high_quality_ad_above_threshold(mock_cls, good_ad_content):
    scores = {"clarity": 9.0, "value_proposition": 8.5, "cta_strength": 8.0,
              "brand_voice": 8.5, "emotional_resonance": 8.0}
    mock_cls.return_value.messages.create.return_value = _mock_anthropic_response(scores)

    evaluator = EvaluatorAgent()
    result = evaluator.evaluate(good_ad_content)

    assert result.aggregate_score > 7.0
    assert result.meets_threshold is True
