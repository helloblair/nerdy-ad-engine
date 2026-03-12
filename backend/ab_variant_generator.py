"""
ab_variant_generator.py
-----------------------
A/B variant generation: given a single CampaignBrief, generates multiple ads
using different creative approaches (hooks/angles). Each variant runs through
the full pipeline (write -> evaluate -> fix/save/flag) independently.

This is NOT the iteration loop (which fixes weaknesses in ONE ad).
This generates DIFFERENT ads from scratch with different strategies.
"""

import random
from typing import Optional

from writer_agent import CampaignBrief, GeneratedAd
from pipeline import run_pipeline, AdState


# ─── Creative Approaches ─────────────────────────────────────────────────────
# Each approach has a name and a prompt modifier that gets prepended to the
# brief's tone field to steer the WriterAgent toward a different creative angle.

CREATIVE_APPROACHES = [
    {
        "name": "pain_point_hook",
        "description": (
            "Lead with the audience's biggest frustration or fear. "
            "Open by naming the specific pain they feel — falling grades, "
            "test anxiety, feeling lost in class — then position the product "
            "as the direct solution to that pain."
        ),
    },
    {
        "name": "social_proof_hook",
        "description": (
            "Lead with a testimonial-style stat, quote, or concrete result. "
            "Open with a specific number or outcome from a real student, "
            "then bridge naturally to the offer. Let the proof do the selling."
        ),
    },
    {
        "name": "urgency_hook",
        "description": (
            "Lead with a deadline, scarcity angle, or time-sensitive framing. "
            "Create genuine time pressure — upcoming test dates, registration "
            "windows closing, semester deadlines. Make waiting feel costly."
        ),
    },
    {
        "name": "aspirational_hook",
        "description": (
            "Lead with the dream outcome. Paint a vivid picture of success — "
            "the acceptance letter, the confident kid, the relieved parent. "
            "Start with where the student WILL be, then show how to get there."
        ),
    },
    {
        "name": "question_hook",
        "description": (
            "Open with a provocative question that forces the reader to stop "
            "scrolling. Ask something they can't ignore — a question that "
            "mirrors their inner doubt or curiosity. Then answer it with the offer."
        ),
    },
]


def get_approaches_by_names(names: list[str]) -> list[dict]:
    """Return approaches matching the given names, preserving order."""
    by_name = {a["name"]: a for a in CREATIVE_APPROACHES}
    result = []
    for name in names:
        if name in by_name:
            result.append(by_name[name])
        else:
            raise ValueError(
                f"Unknown approach '{name}'. "
                f"Available: {list(by_name.keys())}"
            )
    return result


def _modify_brief_for_approach(
    brief: CampaignBrief, approach: dict
) -> CampaignBrief:
    """Create a new CampaignBrief with the approach injected into the tone."""
    modified_tone = (
        f"CREATIVE APPROACH — {approach['name'].upper()}: "
        f"{approach['description']} | "
        f"Original tone: {brief.tone}"
    )
    return CampaignBrief(
        audience=brief.audience,
        product=brief.product,
        goal=brief.goal,
        tone=modified_tone,
        key_benefit=brief.key_benefit,
        proof_point=brief.proof_point,
    )


def generate_ab_variants(
    campaign_id: str,
    brief: CampaignBrief,
    num_variants: int = 3,
    approach_names: Optional[list[str]] = None,
) -> list[dict]:
    """
    Generate multiple ad variants using different creative approaches.

    Each variant runs through the full pipeline (write -> evaluate -> fix/save).
    Returns a list of pipeline result states, one per variant.

    Args:
        campaign_id: The campaign to generate variants for.
        brief: The original campaign brief.
        num_variants: How many variants to generate (default 3, max 5).
        approach_names: Optional list of specific approach names to use.
                       If None, randomly selects from available approaches.
    """
    num_variants = min(num_variants, len(CREATIVE_APPROACHES))

    if approach_names:
        approaches = get_approaches_by_names(approach_names)
        num_variants = len(approaches)
    else:
        approaches = random.sample(CREATIVE_APPROACHES, num_variants)

    results = []
    for i, approach in enumerate(approaches):
        print(f"\n{'='*60}")
        print(f"A/B VARIANT {i+1}/{num_variants} — {approach['name']}")
        print(f"{'='*60}")

        modified_brief = _modify_brief_for_approach(brief, approach)
        state = run_pipeline(campaign_id, modified_brief)

        # Tag the saved ad with the approach name
        if state.get("final_ad_id"):
            from db import get_db
            db = get_db()
            db.update_ad(state["final_ad_id"], {
                "variant_approach": approach["name"],
            })

        results.append({
            "variant_index": i + 1,
            "approach": approach["name"],
            "approach_description": approach["description"],
            "final_ad_id": state.get("final_ad_id"),
            "approved": state.get("approved", False),
            "escalated": state.get("escalated", False),
            "iterations": state.get("iteration", 1),
            "generated_ad": state.get("generated_ad"),
            "evaluation": state.get("evaluation"),
            "all_evaluations": state.get("all_evaluations", []),
        })

    return results
