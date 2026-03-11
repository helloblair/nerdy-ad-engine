"""Tests for FixerAgent — targeting, preservation, and escalation."""

from unittest.mock import patch, MagicMock

import pytest

from fixer_agent import FixerAgent, FixerOutput, EvalSummary


def _mock_anthropic_response(text: str) -> MagicMock:
    text_block = MagicMock()
    text_block.text = text
    response = MagicMock()
    response.content = [text_block]
    return response


# ── Test 1: Targets the lowest-scoring dimension ───────────────────────────

@patch("fixer_agent.Anthropic")
def test_fixer_targets_weakest_dimension(mock_cls):
    mock_cls.return_value.messages.create.return_value = _mock_anthropic_response(
        "Rewrite the CTA to name the specific outcome: 'Book a Free SAT Strategy Session'."
    )

    fixer = FixerAgent()
    eval_summary = EvalSummary(
        clarity=9.0, value_proposition=8.5, cta_strength=5.5,
        brand_voice=8.0, emotional_resonance=7.5,
        aggregate_score=7.8, weakest_dimension="cta_strength",
        improvement_suggestion="Make the CTA more specific.", iteration=1,
    )
    fix = fixer.generate_fix(eval_summary)

    assert fix.dimension_to_fix == "cta_strength"
    assert len(fix.targeted_instruction) > 10


# ── Test 2: Preserves high-scoring dimensions ──────────────────────────────

@patch("fixer_agent.Anthropic")
def test_fixer_preserves_high_scores(mock_cls):
    mock_cls.return_value.messages.create.return_value = _mock_anthropic_response(
        "Add a specific fear about college rejection in the opening sentence."
    )

    fixer = FixerAgent()
    eval_summary = EvalSummary(
        clarity=9.0, value_proposition=8.5, cta_strength=8.0,
        brand_voice=9.5, emotional_resonance=5.0,
        aggregate_score=7.9, weakest_dimension="emotional_resonance",
        improvement_suggestion="Name the parent's specific fear.", iteration=1,
    )
    fix = fixer.generate_fix(eval_summary)

    # All dimensions ≥7.5 should be mentioned in preserve_elements
    for dim in ["clarity", "value_proposition", "cta_strength", "brand_voice"]:
        assert dim in fix.preserve_elements, f"{dim} should be preserved (scored ≥7.5)"


# ── Test 3: Escalates at max iterations ────────────────────────────────────

def test_fixer_escalates_at_max_iterations():
    """Escalation is deterministic — no LLM call needed."""
    fixer = FixerAgent()
    eval_summary = EvalSummary(
        clarity=6.0, value_proposition=5.5, cta_strength=6.5,
        brand_voice=5.0, emotional_resonance=4.5,
        aggregate_score=5.6, weakest_dimension="emotional_resonance",
        improvement_suggestion="Complete rewrite needed.", iteration=3,
    )
    fix = fixer.generate_fix(eval_summary)

    assert fix.escalate is True
    assert fix.escalation_reason is not None
    assert "human review" in fix.escalation_reason.lower()
