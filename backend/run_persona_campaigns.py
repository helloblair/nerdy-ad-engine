"""
run_persona_campaigns.py
------------------------
Generates ads with images across 9 distinct parent personas.
Each campaign targets a different persona from Nerdy's SAT messaging guidance,
producing a diverse ad library that showcases persona-targeted copy + visuals.

Usage: python run_persona_campaigns.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db import get_db
from pipeline import run_pipeline
from writer_agent import CampaignBrief

PERSONA_CAMPAIGNS = [
    {
        "name": "Athlete Recruit — SAT as Scholarship Gatekeeper",
        "brief": CampaignBrief(
            audience="parents of 11th-grade athletes being recruited for college sports",
            product="1-on-1 SAT tutoring",
            goal="conversion",
            tone="urgent, direct, schedule-aware",
            key_benefit="SAT tutoring that fits around practice — first session within 48 hours",
            proof_point="our students improve 10x more than self-study",
            persona="athlete_recruit",
        ),
    },
    {
        "name": "Suburban Optimizer — GPA-SAT Mismatch",
        "brief": CampaignBrief(
            audience="parents of high-achieving juniors with 3.8+ GPA but mid-1200s SAT",
            product="1-on-1 SAT tutoring",
            goal="conversion",
            tone="confident, specific, data-driven",
            key_benefit="most mid-1200s students are 3-4 fixes away from a 1400+",
            proof_point="100 points/month at 2 sessions/week + 20 min/day practice",
            persona="suburban_optimizer",
        ),
    },
    {
        "name": "Scholarship Family — SAT as Tuition Lever",
        "brief": CampaignBrief(
            audience="cost-conscious parents exploring how SAT scores affect financial aid",
            product="1-on-1 SAT tutoring",
            goal="awareness",
            tone="informative, empowering, ROI-focused",
            key_benefit="every 100 SAT points can mean $10,000-$40,000 in scholarships",
            proof_point="for what Princeton Review charges for group classes, we charge for 1:1",
            persona="scholarship_family",
        ),
    },
    {
        "name": "Khan Academy Failure — Self-Study Didn't Work",
        "brief": CampaignBrief(
            audience="parents whose child used Khan Academy but score didn't improve",
            product="1-on-1 SAT tutoring",
            goal="conversion",
            tone="validating, direct, solution-focused",
            key_benefit="1:1 tutoring that diagnoses exactly why the score isn't moving",
            proof_point="our students improve 10x more than self-study apps",
            persona="khan_academy_failure",
        ),
    },
    {
        "name": "Bad Score Urgency — Disappointing PSAT/SAT",
        "brief": CampaignBrief(
            audience="parents who just received a disappointing SAT or PSAT score",
            product="1-on-1 SAT tutoring",
            goal="conversion",
            tone="empathetic, urgent, action-oriented",
            key_benefit="a clear path from current score to target score, week by week",
            proof_point="most students see 100 points/month with consistent sessions",
            persona="bad_score_urgency",
        ),
    },
    {
        "name": "Immigrant Navigator — New to US College System",
        "brief": CampaignBrief(
            audience="immigrant families navigating the US college admissions process for the first time",
            product="1-on-1 SAT tutoring",
            goal="awareness",
            tone="patient, reassuring, step-by-step",
            key_benefit="we walk you through the entire SAT process — scores, what they mean, and what to do next",
            proof_point="your child deserves the same preparation as kids whose families grew up with this system",
            persona="immigrant_navigator",
        ),
    },
    {
        "name": "Neurodivergent Advocate — Right Tutor Fit",
        "brief": CampaignBrief(
            audience="parents of students with ADHD or learning differences preparing for the SAT",
            product="1-on-1 SAT tutoring",
            goal="conversion",
            tone="warm, understanding, capability-focused",
            key_benefit="tutors matched to how your child actually learns, not a one-size-fits-all approach",
            proof_point="easy tutor switching if the fit isn't right — no awkward conversations",
            persona="neurodivergent_advocate",
        ),
    },
    {
        "name": "Burned Returner — Bad Prior Tutoring Experience",
        "brief": CampaignBrief(
            audience="parents who previously paid for tutoring that didn't improve their child's score",
            product="1-on-1 SAT tutoring",
            goal="conversion",
            tone="accountable, transparent, proof-first",
            key_benefit="we match, we measure, and if it's not working we change course",
            proof_point="weekly progress reports show exactly where your child stands — no more guessing",
            persona="burned_returner",
        ),
    },
    {
        "name": "Accountability Seeker — Can't Make My Kid Study",
        "brief": CampaignBrief(
            audience="parents whose teenager won't study without external accountability",
            product="1-on-1 SAT tutoring",
            goal="conversion",
            tone="relatable, slightly humorous, practical",
            key_benefit="a tutor your teenager will actually listen to — plus weekly progress reports for you",
            proof_point="assigned daily practice + weekly check-ins keep them on track so you don't have to",
            persona="accountability_seeker",
        ),
    },
]


def main():
    db = get_db()
    total = len(PERSONA_CAMPAIGNS)

    print("=" * 60)
    print(f"🎯 PERSONA-DIVERSE AD GENERATION — {total} campaigns")
    print("=" * 60)
    print("Each campaign generates copy + image + 7-dimension evaluation\n")

    results = []

    for i, campaign_data in enumerate(PERSONA_CAMPAIGNS, 1):
        name = campaign_data["name"]
        brief = campaign_data["brief"]
        persona = brief.persona or "general"

        print(f"\n{'━' * 60}")
        print(f"  Campaign {i}/{total}: {name}")
        print(f"  Persona: {persona}")
        print(f"{'━' * 60}")

        try:
            campaign = db.insert_campaign({
                "name": name,
                "audience": brief.audience,
                "product": brief.product,
                "goal": brief.goal,
                "tone": brief.tone,
                "status": "running",
            })
            campaign_id = campaign["id"]

            final_state = run_pipeline(campaign_id, brief)

            db.update_campaign_status(campaign_id, "completed")

            score = final_state["all_evaluations"][-1]["aggregate_score"] if final_state["all_evaluations"] else 0
            has_image = bool(final_state.get("generated_image", {}).get("image_path"))

            results.append({
                "campaign": name,
                "persona": persona,
                "approved": final_state["approved"],
                "iterations": final_state["iteration"],
                "score": score,
                "has_image": has_image,
                "ad_id": final_state["final_ad_id"],
            })

            status = "✅ APPROVED" if final_state["approved"] else "⚠️ FLAGGED"
            print(f"\n  {status} — Score: {score:.1f} | Iterations: {final_state['iteration']} | Image: {'yes' if has_image else 'no'}")

        except Exception as e:
            print(f"\n  ❌ FAILED: {e}")
            results.append({
                "campaign": name,
                "persona": persona,
                "approved": False,
                "iterations": 0,
                "score": 0,
                "has_image": False,
                "ad_id": None,
                "error": str(e),
            })

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n\n" + "=" * 60)
    print("📊 GENERATION SUMMARY")
    print("=" * 60)

    approved = sum(1 for r in results if r["approved"])
    with_images = sum(1 for r in results if r["has_image"])
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0
    total_iterations = sum(r["iterations"] for r in results)

    print(f"  Total campaigns:  {total}")
    print(f"  Approved:         {approved}/{total}")
    print(f"  With images:      {with_images}/{total}")
    print(f"  Avg score:        {avg_score:.1f}")
    print(f"  Total iterations: {total_iterations}")
    print()

    for r in results:
        icon = "✅" if r["approved"] else "❌"
        img = "🖼" if r["has_image"] else "  "
        print(f"  {icon} {img}  {r['score']:.1f}  iter:{r['iterations']}  {r['persona']:<25} {r['campaign']}")

    # Count total ads in DB
    total_ads = db.count_all_ads()
    print(f"\n  📦 Total ads in library: {total_ads}")
    if total_ads >= 50:
        print("  ✅ 50+ ad threshold met!")
    else:
        print(f"  ⚠️  Need {50 - total_ads} more ads to hit 50+ threshold")

    print("=" * 60)


if __name__ == "__main__":
    main()
