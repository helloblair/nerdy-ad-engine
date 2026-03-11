"""
run_iteration_demo.py
---------------------
Generates ads from deliberately weak briefs to demonstrate iterative improvement.
Each brief targets a specific dimension weakness, forcing the fixer loop to activate.

Outputs:
  - Terminal: full iteration story with score progression
  - docs/iteration_proof.json: structured data for the frontend
"""

import json
import os
import sys
import uuid
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from db import get_db
from pipeline import (
    build_pipeline,
    AdState,
    researcher,
)
from writer_agent import CampaignBrief

# ─── Weak Briefs ─────────────────────────────────────────────────────────────

WEAK_BRIEFS = [
    {
        "name": "Weak Emotional Resonance — SAT",
        "brief": CampaignBrief(
            audience="students taking the SAT",
            product="SAT tutoring",
            goal="conversion",
            tone="informational",
            key_benefit="tutoring services available",
            proof_point=None,
        ),
        "expected_weakness": "emotional_resonance",
        "max_ads": 2,
    },
    {
        "name": "Weak Value Proposition — Math",
        "brief": CampaignBrief(
            audience="parents",
            product="math help",
            goal="awareness",
            tone="general",
            key_benefit="we can help with math",
            proof_point=None,
        ),
        "expected_weakness": "value_proposition",
        "max_ads": 2,
    },
    {
        "name": "Weak CTA — Reading",
        "brief": CampaignBrief(
            audience="parents of young readers",
            product="reading support",
            goal="awareness",
            tone="soft",
            key_benefit="reading improvement",
            proof_point=None,
        ),
        "expected_weakness": "cta_strength",
        "max_ads": 2,
    },
]

# ─── Run Demo ─────────────────────────────────────────────────────────────────


def run_single_ad(campaign_id: str, brief: CampaignBrief, ad_number: int) -> dict:
    """Run the pipeline for one ad and return iteration-level data."""
    pipeline = build_pipeline()
    initial_state: AdState = {
        "campaign_id": campaign_id,
        "brief": brief.model_dump(),
        "iteration": 1,
        "max_iterations": 3,
        "generated_ad": None,
        "evaluation": None,
        "fix": None,
        "approved": False,
        "escalated": False,
        "final_ad_id": None,
        "all_evaluations": [],
        "research_context": researcher.format_for_prompt(researcher.extract_context()),
    }
    final_state = pipeline.invoke(initial_state)

    # Build iteration log from all_evaluations
    iterations = []
    all_evals = final_state.get("all_evaluations", [])
    for i, ev in enumerate(all_evals):
        fix_applied = "none (first pass)"
        if i > 0:
            # Describe the fix that was applied before this evaluation
            fix_data = final_state.get("fix")
            if fix_data:
                fix_applied = fix_data.get("targeted_instruction", "targeted fix applied")
            else:
                fix_applied = "fixer feedback applied"
        iterations.append({
            "iteration": ev["iteration"],
            "score": round(ev["aggregate_score"], 1),
            "weakest_dimension": ev.get("weakest_dimension", ""),
            "fix_applied": fix_applied,
            "dimension_scores": {
                "clarity": round(ev.get("clarity", 0), 1),
                "value_proposition": round(ev.get("value_proposition", 0), 1),
                "cta_strength": round(ev.get("cta_strength", 0), 1),
                "brand_voice": round(ev.get("brand_voice", 0), 1),
                "emotional_resonance": round(ev.get("emotional_resonance", 0), 1),
            },
        })

    first_score = iterations[0]["score"] if iterations else 0
    final_score = iterations[-1]["score"] if iterations else 0

    return {
        "ad_number": ad_number,
        "iterations": iterations,
        "total_lift": round(final_score - first_score, 1),
        "final_score": final_score,
        "passed_threshold": final_score >= 7.0,
    }


def main():
    db = get_db()
    print("=" * 60)
    print("  ITERATION DEMO — Weak Briefs × 3 Campaigns × 2 Ads Each")
    print("=" * 60)

    campaigns_data = []
    all_iter1_scores = []
    all_iter2_scores = []
    all_iter3_scores = []

    for campaign_info in WEAK_BRIEFS:
        name = campaign_info["name"]
        brief = campaign_info["brief"]
        expected = campaign_info["expected_weakness"]
        max_ads = campaign_info["max_ads"]

        print(f"\n{'─' * 60}")
        print(f"  CAMPAIGN: {name}")
        print(f"  Expected weakness: {expected}")
        print(f"{'─' * 60}")

        # Create campaign in DB
        campaign = db.insert_campaign({
            "name": name,
            "audience": brief.audience,
            "product": brief.product,
            "goal": brief.goal,
            "tone": brief.tone,
            "status": "running",
        })
        campaign_id = campaign["id"]

        ads_data = []
        for ad_num in range(1, max_ads + 1):
            print(f"\n>>> Ad {ad_num}/{max_ads} for '{name}'")
            ad_result = run_single_ad(campaign_id, brief, ad_num)
            ads_data.append(ad_result)

            # Collect scores by iteration index
            for it in ad_result["iterations"]:
                idx = it["iteration"]
                if idx == 1:
                    all_iter1_scores.append(it["score"])
                elif idx == 2:
                    all_iter2_scores.append(it["score"])
                elif idx == 3:
                    all_iter3_scores.append(it["score"])

            scores = [it["score"] for it in ad_result["iterations"]]
            print(f"    Score trajectory: {' → '.join(str(s) for s in scores)}")
            print(f"    Lift: +{ad_result['total_lift']}  Final: {ad_result['final_score']}")

        db.update_campaign_status(campaign_id, "completed")

        campaigns_data.append({
            "campaign_name": name,
            "expected_weakness": expected,
            "ads": ads_data,
        })

    # ─── Build summary ────────────────────────────────────────────────────────
    avg = lambda lst: round(sum(lst) / len(lst), 1) if lst else 0.0
    avg_iter1 = avg(all_iter1_scores)
    avg_iter2 = avg(all_iter2_scores) if all_iter2_scores else avg_iter1
    avg_iter3 = avg(all_iter3_scores) if all_iter3_scores else avg_iter2

    proof = {
        "summary": {
            "total_campaigns": len(campaigns_data),
            "total_ads": sum(len(c["ads"]) for c in campaigns_data),
            "avg_score_iter1": avg_iter1,
            "avg_score_iter2": avg_iter2,
            "avg_score_iter3": avg_iter3,
            "total_lift": round(avg_iter3 - avg_iter1, 1) if all_iter3_scores else round(avg_iter2 - avg_iter1, 1),
            "methodology": "Weak briefs designed to trigger specific dimension failures, then targeted fixer cycles applied",
        },
        "campaigns": campaigns_data,
    }

    # Write to docs/iteration_proof.json
    proof_path = os.path.join(os.path.dirname(__file__), "..", "docs", "iteration_proof.json")
    os.makedirs(os.path.dirname(proof_path), exist_ok=True)
    with open(proof_path, "w") as f:
        json.dump(proof, f, indent=2)

    print("\n" + "=" * 60)
    print("  ITERATION DEMO COMPLETE")
    print("=" * 60)
    print(f"  Campaigns:     {proof['summary']['total_campaigns']}")
    print(f"  Total ads:     {proof['summary']['total_ads']}")
    print(f"  Iter 1 avg:    {avg_iter1}")
    print(f"  Iter 2 avg:    {avg_iter2}")
    print(f"  Iter 3 avg:    {avg_iter3}")
    print(f"  Total lift:    +{proof['summary']['total_lift']}")
    print(f"  Saved to:      {os.path.abspath(proof_path)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
