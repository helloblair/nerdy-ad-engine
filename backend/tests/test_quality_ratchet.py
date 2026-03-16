"""Tests for quality_ratchet.py — the dynamic threshold computation."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quality_ratchet import compute_ratchet_threshold, FLOOR


def test_below_min_sample_returns_floor():
    """With fewer than 10 scores, ratchet stays dormant at 7.0."""
    result = compute_ratchet_threshold([8.0, 8.5, 9.0])
    assert result["threshold"] == FLOOR
    assert result["ratchet_active"] is False


def test_activates_at_min_sample():
    """With exactly 10 scores, ratchet activates."""
    scores = [7.5, 7.8, 8.0, 8.2, 8.1, 7.9, 8.3, 8.5, 7.6, 8.0]
    result = compute_ratchet_threshold(scores)
    assert result["ratchet_active"] is True
    assert result["threshold"] >= FLOOR


def test_never_goes_below_floor():
    """Even with low scores, threshold can't drop below 7.0."""
    scores = [5.0, 5.5, 6.0, 6.2, 5.8, 6.1, 5.9, 6.3, 5.5, 6.0]
    result = compute_ratchet_threshold(scores)
    assert result["threshold"] == FLOOR


def test_rises_with_high_quality_ads():
    """With consistently high scores, threshold climbs above floor."""
    scores = [8.5, 8.8, 9.0, 8.7, 8.9, 9.1, 8.6, 9.2, 8.8, 9.0]
    result = compute_ratchet_threshold(scores)
    assert result["threshold"] > FLOOR
    assert result["ratchet_active"] is True


def test_max_step_guardrail():
    """Threshold can't jump more than 0.5 per batch of 10 ads."""
    # 10 perfect scores — P25 would be 10.0, but max step is +0.5
    scores = [10.0] * 10
    result = compute_ratchet_threshold(scores)
    assert result["threshold"] <= FLOOR + 0.5


def test_gradual_ramp_with_more_batches():
    """With 20+ scores, the max step increases to allow +1.0."""
    scores = [10.0] * 20
    result = compute_ratchet_threshold(scores)
    assert result["threshold"] <= FLOOR + 1.0
    assert result["threshold"] > FLOOR + 0.5  # more headroom than 1 batch


def test_absolute_ceiling():
    """Threshold can never exceed FLOOR + 2.0 regardless of sample size."""
    scores = [10.0] * 100
    result = compute_ratchet_threshold(scores)
    assert result["threshold"] <= FLOOR + 2.0


def test_headroom_decreases_as_threshold_rises():
    """Headroom should shrink as threshold approaches the ceiling."""
    low = compute_ratchet_threshold([7.5] * 10)
    high = compute_ratchet_threshold([10.0] * 50)
    assert high["headroom"] <= low["headroom"]


def test_empty_scores():
    """Empty list returns floor with ratchet inactive."""
    result = compute_ratchet_threshold([])
    assert result["threshold"] == FLOOR
    assert result["ratchet_active"] is False
    assert result["sample_size"] == 0
