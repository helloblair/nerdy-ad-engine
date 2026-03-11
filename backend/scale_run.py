"""
scale_run.py
------------
Fires the pipeline across 5 audience segments to populate Supabase
with 50+ ads for the frontend and confusion matrix survey.
"""
from dotenv import load_dotenv
from pipeline import run_pipeline
from writer_agent import CampaignBrief
from db import get_db

load_dotenv()

CAMPAIGNS = [
    {
        "name": "SAT Conversion — Juniors",
        "audience": "parents of high school juniors preparing for SAT",
        "product": "1-on-1 SAT tutoring",
        "goal": "conversion",
        "tone": "urgent, empathetic, outcome-focused",
        "key_benefit": "personalized learning matched to your child's gaps",
        "proof_point": "students improve an average of 360 points in 8 weeks",
        "num_ads": 4,
    },
    {
        "name": "GPA vs SAT Reframe — High Achievers",
        "audience": "parents of high-achieving students with disappointing SAT scores",
        "product": "1-on-1 SAT tutoring",
        "goal": "conversion",
        "tone": "reframe-focused, empathetic, specific",
        "key_benefit": "your child is smart — the SAT is a learnable test",
        "proof_point": "3.8 GPA students average 1380+ after 8 weeks of targeted prep",
        "num_ads": 4,
    },
    {
        "name": "Middle School Math — Awareness",
        "audience": "parents of middle school students struggling with math",
        "product": "1-on-1 math tutoring",
        "goal": "awareness",
        "tone": "warm, reassuring, reframe-focused",
        "key_benefit": "tutors who explain math the way your child's brain works",
        "proof_point": "93% of students improve at least one letter grade",
        "num_ads": 4,
    },
    {
        "name": "ACT Countdown — Seniors",
        "audience": "parents of high school seniors with ACT retake coming up",
        "product": "1-on-1 ACT tutoring",
        "goal": "conversion",
        "tone": "urgent, deadline-focused, outcome-driven",
        "key_benefit": "targeted ACT prep in the time you have left",
        "proof_point": "students improve an average of 4 composite points in 4 weeks",
        "num_ads": 4,
    },
    {
        "name": "Reading Comprehension — Elementary",
        "audience": "parents of elementary school students falling behind in reading",
        "product": "1-on-1 reading tutoring",
        "goal": "awareness",
        "tone": "warm, nurturing, parent-pain focused",
        "key_benefit": "build reading confidence before it becomes a bigger gap",
        "proof_point": "students gain an average of 1.5 grade levels in 10 weeks",
        "num_ads": 4,
    },
]

def run_scale():
    total_ads = sum(c["num_ads"] for c in CAMPAIGNS)
    print(f"🚀 SCALE RUN — {len(CAMPAIGNS)} campaigns, {total_ads} ads total\n")

    db = get_db()
    results = []
    for i, cfg in enumerate(CAMPAIGNS):
        print(f"\n{'='*60}")
        print(f"Campaign {i+1}/{len(CAMPAIGNS)}: {cfg['name']}")
        print(f"{'='*60}")

        try:
            campaign = db.insert_campaign({
                "name": cfg["name"],
                "audience": cfg["audience"],
                "product": cfg["product"],
                "goal": cfg["goal"],
                "tone": cfg["tone"],
                "status": "running",
            })
            campaign_id = campaign["id"]
            print(f"✅ Campaign created: {campaign_id}")

            brief = CampaignBrief(
                audience=cfg["audience"],
                product=cfg["product"],
                goal=cfg["goal"],
                tone=cfg["tone"],
                key_benefit=cfg["key_benefit"],
                proof_point=cfg["proof_point"],
            )

            approved = 0
            for j in range(cfg["num_ads"]):
                print(f"\n  Ad {j+1}/{cfg['num_ads']}...")
                state = run_pipeline(campaign_id, brief)
                if state["approved"]:
                    approved += 1

            db.update_campaign_status(campaign_id, "completed")

            results.append({
                "campaign": cfg["name"],
                "campaign_id": campaign_id,
                "approved": approved,
                "total": cfg["num_ads"],
            })
            print(f"\n✅ {cfg['name']} — {approved}/{cfg['num_ads']} approved")

        except Exception as e:
            print(f"❌ Campaign failed: {e}")
            continue

    print(f"\n{'='*60}")
    print("SCALE RUN COMPLETE")
    print(f"{'='*60}")
    total_approved = sum(r["approved"] for r in results)
    print(f"  Total ads generated: {sum(r['total'] for r in results)}")
    print(f"  Total approved:      {total_approved}")
    print(f"  Overall pass rate:   {round(total_approved / sum(r['total'] for r in results) * 100)}%")
    for r in results:
        print(f"  {r['campaign'][:45]:45} {r['approved']}/{r['total']} approved")

if __name__ == "__main__":
    from progress_tracker import mark_complete
    run_scale()
    mark_complete("fifty_ads")

