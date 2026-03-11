"""Tests for WriterAgent — output shape, field constraints, CTA validation."""

import json
from unittest.mock import patch, MagicMock

import pytest

from writer_agent import WriterAgent, GeneratedAd, WriterInput, CampaignBrief


APPROVED_CTAS = [
    "Book a Free Session",
    "Book a Free SAT Strategy Session",
    "Claim Your Free Trial Lesson",
    "Get Started",
    "Start Free Trial",
    "Schedule a Free Lesson",
    "Try a Free Lesson",
    "Book Free Consultation",
]


def _mock_gemini_response(ad_dict: dict) -> MagicMock:
    response = MagicMock()
    response.text = json.dumps(ad_dict)
    return response


SAMPLE_AD_DICT = {
    "primary_text": "Her SAT score jumped 360 points in 8 weeks. A tutor matched to how she learns.",
    "headline": "360-Point SAT Jump",
    "description": "Tutoring that actually works.",
    "cta_button": "Book a Free Session",
    "writer_notes": "Proof-point lead.",
}


# ── Test 1: Returns GeneratedAd with all required fields ───────────────────

@patch("writer_agent.genai")
def test_writer_returns_generated_ad(mock_genai, sample_writer_input):
    mock_genai.Client.return_value.models.generate_content.return_value = (
        _mock_gemini_response(SAMPLE_AD_DICT)
    )

    writer = WriterAgent()
    ad = writer.generate(sample_writer_input)

    assert isinstance(ad, GeneratedAd)
    assert ad.primary_text
    assert ad.headline
    assert ad.description
    assert ad.cta_button


# ── Test 2: primary_text is non-empty ───────────────────────────────────────

@patch("writer_agent.genai")
def test_primary_text_non_empty(mock_genai, sample_writer_input):
    mock_genai.Client.return_value.models.generate_content.return_value = (
        _mock_gemini_response(SAMPLE_AD_DICT)
    )

    writer = WriterAgent()
    ad = writer.generate(sample_writer_input)

    assert len(ad.primary_text.strip()) > 0


# ── Test 3: headline is ≤8 words ───────────────────────────────────────────

@patch("writer_agent.genai")
def test_headline_max_words(mock_genai, sample_writer_input):
    mock_genai.Client.return_value.models.generate_content.return_value = (
        _mock_gemini_response(SAMPLE_AD_DICT)
    )

    writer = WriterAgent()
    ad = writer.generate(sample_writer_input)

    word_count = len(ad.headline.split())
    assert word_count <= 8, f"Headline '{ad.headline}' has {word_count} words (max 8)"


# ── Test 4: cta_button is an approved option ───────────────────────────────

@patch("writer_agent.genai")
def test_cta_is_approved(mock_genai, sample_writer_input):
    mock_genai.Client.return_value.models.generate_content.return_value = (
        _mock_gemini_response(SAMPLE_AD_DICT)
    )

    writer = WriterAgent()
    ad = writer.generate(sample_writer_input)

    assert ad.cta_button in APPROVED_CTAS, (
        f"CTA '{ad.cta_button}' not in approved list"
    )
