"""
reevaluate_all.py
-----------------
Re-evaluates all existing ads using the tuned EvaluatorAgent (v3 weights + prompt).
Updates evaluation scores in-place so the campaigns tab reflects the new logic.

Usage:
    python reevaluate_all.py              # re-evaluate all ads
    python reevaluate_all.py --dry-run    # preview without writing to DB
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from db import get_db
from evaluator_agent import EvaluatorAgent, AdContent

def reevaluate_all(dry_run: bool = False):
    db = get_db()
    evaluator = EvaluatorAgent()

    ads = db.list_all_ads()
    print(f"{'🧪 DRY RUN — ' if dry_run else ''}Re-evaluating {len(ads)} ads with tuned evaluator (threshold={evaluator.THRESHOLD})")
    print(f"Text weights: {evaluator.TEXT_WEIGHTS}")
    print(f"{'='*70}\n")

    results = {"improved": 0, "declined": 0, "unchanged": 0, "newly_flagged": 0, "errors": 0}

    for i, ad in enumerate(ads, 1):
        ad_id = ad["id"]
        old_eval = db.get_evaluation_for_ad(ad_id)

        if not old_eval:
            print(f"  [{i}/{len(ads)}] ⚠️  No existing evaluation for ad {ad_id[:8]}… — skipping")
            continue

        old_score = old_eval.get("aggregate_score", 0)

        # Rebuild AdContent from stored ad data
        # Look up campaign for audience/product/goal
        campaign = db.get_campaign(ad["campaign_id"])
        if not campaign:
            print(f"  [{i}/{len(ads)}] ⚠️  No campaign found for ad {ad_id[:8]}… — skipping")
            continue

        ad_content = AdContent(
            primary_text=ad["primary_text"],
            headline=ad["headline"],
            description=ad.get("description", ""),
            cta_button=ad["cta_button"],
            audience=campaign["audience"],
            product=campaign["product"],
            goal=campaign["goal"],
        )

        try:
            result = evaluator.evaluate(ad_content)
        except Exception as e:
            print(f"  [{i}/{len(ads)}] ❌ Error evaluating ad {ad_id[:8]}…: {e}")
            results["errors"] += 1
            continue

        new_score = result.aggregate_score
        delta = new_score - old_score
        direction = "📈" if delta > 0 else "📉" if delta < 0 else "➡️"

        if delta > 0:
            results["improved"] += 1
        elif delta < 0:
            results["declined"] += 1
        else:
            results["unchanged"] += 1

        old_passed = old_eval.get("meets_threshold", False)
        new_passed = result.meets_threshold
        flag_note = ""
        if old_passed and not new_passed:
            results["newly_flagged"] += 1
            flag_note = " ⚠️  NOW BELOW THRESHOLD"

        print(f"  [{i}/{len(ads)}] {direction} {ad['headline'][:50]:50s}  {old_score:.1f} → {new_score:.1f} ({delta:+.1f}){flag_note}")

        if not dry_run:
            update_data = {
                "clarity": result.clarity.score,
                "value_proposition": result.value_proposition.score,
                "cta_score": result.cta_strength.score,
                "brand_voice": result.brand_voice.score,
                "emotional_resonance": result.emotional_resonance.score,
                "aggregate_score": result.aggregate_score,
                "clarity_rationale": result.clarity.rationale,
                "value_proposition_rationale": result.value_proposition.rationale,
                "cta_rationale": result.cta_strength.rationale,
                "brand_voice_rationale": result.brand_voice.rationale,
                "emotional_resonance_rationale": result.emotional_resonance.rationale,
                "clarity_confidence": result.clarity.confidence,
                "value_proposition_confidence": result.value_proposition.confidence,
                "cta_confidence": result.cta_strength.confidence,
                "brand_voice_confidence": result.brand_voice.confidence,
                "emotional_resonance_confidence": result.emotional_resonance.confidence,
                "meets_threshold": 1 if result.meets_threshold else 0,
                "needs_human_review": 1 if result.needs_human_review else 0,
            }

            # Update ad status based on new threshold
            db.update_evaluation(ad_id, update_data)
            new_status = "approved" if result.meets_threshold else "flagged"
            if ad["status"] != new_status:
                db.update_ad(ad_id, {"status": new_status})

    print(f"\n{'='*70}")
    print(f"RE-EVALUATION COMPLETE {'(DRY RUN)' if dry_run else ''}")
    print(f"  Total ads:      {len(ads)}")
    print(f"  Score improved:  {results['improved']}")
    print(f"  Score declined:  {results['declined']}")
    print(f"  Unchanged:       {results['unchanged']}")
    print(f"  Newly flagged:   {results['newly_flagged']}")
    print(f"  Errors:          {results['errors']}")
    print(f"{'='*70}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    reevaluate_all(dry_run=dry_run)
