"""
backfill_images.py
------------------
Generate images for all existing ads that don't have one yet.
Uses ImageAgent (Imagen 4.0) with persona detection from campaign names.

Usage:
    python backfill_images.py              # run for real
    python backfill_images.py --dry-run    # preview what would be generated
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

from db import get_db
from image_agent import ImageAgent, ImageInput

# Map campaign name keywords to persona slugs
PERSONA_KEYWORDS = {
    "athlete": "athlete_recruit",
    "suburban": "suburban_optimizer",
    "scholarship": "scholarship_family",
    "khan": "khan_academy_failure",
    "skeptic": "online_skeptic",
    "bad score": "bad_score_urgency",
    "urgency": "bad_score_urgency",
    "immigrant": "immigrant_navigator",
    "neurodivergent": "neurodivergent_advocate",
    "anxiety": "test_anxiety",
    "accountability": "accountability_seeker",
    "school failed": "school_failed_them",
    "investor": "education_investor",
    "burned": "burned_returner",
    "relationship": "parent_relationship",
    "sibling": "sibling_second_child",
}


def detect_persona(campaign_name: str) -> str:
    """Infer persona from campaign name keywords."""
    name_lower = (campaign_name or "").lower()
    for keyword, persona in PERSONA_KEYWORDS.items():
        if keyword in name_lower:
            return persona
    return "general"


def main():
    dry_run = "--dry-run" in sys.argv
    db = get_db()
    agent = ImageAgent()

    all_ads = db.list_all_ads()
    needs_image = [a for a in all_ads if not a.get("image_url")]

    print(f"{'🔍 DRY RUN' if dry_run else '🎨 BACKFILL'} — {len(needs_image)} ads need images (of {len(all_ads)} total)\n")

    if not needs_image:
        print("Nothing to do — all ads already have images!")
        return

    # Cache campaigns to avoid repeated lookups
    campaign_cache: dict[str, dict] = {}
    success = 0
    failed = 0

    for i, ad in enumerate(needs_image, 1):
        campaign_id = ad["campaign_id"]
        if campaign_id not in campaign_cache:
            campaign_cache[campaign_id] = db.get_campaign(campaign_id) or {}
        campaign = campaign_cache[campaign_id]

        persona = detect_persona(campaign.get("name", ""))
        headline = ad.get("headline", "Ad")

        print(f"[{i}/{len(needs_image)}] {headline[:60]:<60}  persona={persona}")

        if dry_run:
            continue

        try:
            image_input = ImageInput(
                primary_text=ad.get("primary_text", ""),
                headline=ad.get("headline", ""),
                audience=campaign.get("audience", "parents"),
                product=campaign.get("product", "tutoring"),
                goal=campaign.get("goal", "conversion"),
                persona=persona,
            )

            result = agent.generate(image_input)

            if result.image_path and os.path.exists(result.image_path):
                filename = os.path.basename(result.image_path)
                image_url = f"/images/{filename}"
                db.update_ad(ad["id"], {"image_url": image_url})
                success += 1
                print(f"   ✅ {image_url}")
            else:
                failed += 1
                print(f"   ❌ Image generation returned empty path")

        except Exception as e:
            failed += 1
            print(f"   ❌ {e}")

        # Small delay to avoid rate limits
        if not dry_run and i < len(needs_image):
            time.sleep(1)

    if not dry_run:
        print(f"\n{'='*60}")
        print(f"BACKFILL COMPLETE")
        print(f"  ✅ Success: {success}")
        print(f"  ❌ Failed:  {failed}")
        print(f"  Total:     {len(needs_image)}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
