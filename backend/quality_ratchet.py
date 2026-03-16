"""
quality_ratchet.py
------------------
Computes a dynamic quality threshold from historical approved ad scores.
The ratchet only goes up — standards never decrease.

Algorithm:
  threshold = max(FLOOR, P25 of approved ad aggregate scores)

Guardrails:
  - Minimum 10 approved ads before ratchet activates
  - Maximum increase capped at +0.5 per 10 ads (gradual ramp)
  - Absolute ceiling of FLOOR + 2.0 (e.g. 9.0 when floor is 7.0)
  - Stateless: threshold is a pure function of (scores, floor)
"""

import statistics


FLOOR = 7.0
MIN_SAMPLE = 10
MAX_STEP_PER_BATCH = 0.5
ABSOLUTE_CEILING = FLOOR + 2.0


def compute_ratchet_threshold(
    scores: list[float],
    floor: float = FLOOR,
    min_sample: int = MIN_SAMPLE,
) -> dict:
    """Compute the dynamic quality threshold from approved ad scores.

    Returns a dict with:
      - threshold: the current dynamic threshold (>= floor)
      - floor: the hard minimum (never goes below this)
      - sample_size: how many approved scores were used
      - ratchet_active: whether the ratchet has enough data to engage
      - headroom: how much higher the threshold could still climb
    """
    sample_size = len(scores)

    if sample_size < min_sample:
        return {
            "threshold": floor,
            "floor": floor,
            "sample_size": sample_size,
            "ratchet_active": False,
            "headroom": round(ABSOLUTE_CEILING - floor, 1),
        }

    # P25 of approved scores — conservative, won't spike from outliers
    p25 = statistics.quantiles(sorted(scores), n=4)[0]

    # Gradual ramp: max increase = +0.5 per batch of 10 ads
    num_batches = sample_size // min_sample
    max_allowed = floor + (num_batches * MAX_STEP_PER_BATCH)

    # Apply ceiling
    max_allowed = min(max_allowed, ABSOLUTE_CEILING)

    # Final threshold: P25 clamped between floor and max_allowed
    threshold = round(max(floor, min(p25, max_allowed)), 1)

    return {
        "threshold": threshold,
        "floor": floor,
        "sample_size": sample_size,
        "ratchet_active": True,
        "headroom": round(ABSOLUTE_CEILING - threshold, 1),
    }


def get_current_threshold(db) -> dict:
    """Convenience: pull scores from DB and compute the ratchet threshold."""
    scores = db.get_approved_scores()
    return compute_ratchet_threshold(scores)
