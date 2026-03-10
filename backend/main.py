import os
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv
from pipeline import run_pipeline
from writer_agent import CampaignBrief

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

@asynccontextmanager
async def lifespan(app):
    print("🚀 Nerdy Ad Engine API starting up...")
    yield

app = FastAPI(title="Nerdy Autonomous Ad Engine", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class CreateCampaignRequest(BaseModel):
    name: str
    audience: str
    product: str
    goal: str
    tone: Optional[str] = "warm, urgent, outcome-focused"
    key_benefit: Optional[str] = None
    proof_point: Optional[str] = None
    num_ads: Optional[int] = 1

def run_campaign_pipeline(campaign_id: str, brief: CampaignBrief, num_ads: int):
    try:
        supabase.table("campaigns").update({"status": "running"}).eq("id", campaign_id).execute()
        for i in range(num_ads):
            print(f"🔄 Generating ad {i+1}/{num_ads} for campaign {campaign_id}")
            run_pipeline(campaign_id, brief)
        supabase.table("campaigns").update({"status": "completed"}).eq("id", campaign_id).execute()
        print(f"✅ Campaign {campaign_id} completed")
    except Exception as e:
        print(f"❌ Campaign {campaign_id} failed: {e}")
        supabase.table("campaigns").update({"status": "failed"}).eq("id", campaign_id).execute()

@app.get("/health")
def health():
    return {"status": "ok", "service": "nerdy-ad-engine"}

@app.post("/campaigns", status_code=202)
def create_campaign(req: CreateCampaignRequest, background_tasks: BackgroundTasks):
    try:
        result = supabase.table("campaigns").insert({
            "name": req.name, "audience": req.audience, "product": req.product,
            "goal": req.goal, "tone": req.tone, "status": "pending",
        }).execute()
        campaign_id = result.data[0]["id"]
        brief = CampaignBrief(audience=req.audience, product=req.product, goal=req.goal,
                              tone=req.tone, key_benefit=req.key_benefit, proof_point=req.proof_point)
        background_tasks.add_task(run_campaign_pipeline, campaign_id, brief, req.num_ads)
        return {"campaign_id": campaign_id, "status": "pending",
                "message": f"Pipeline started — generating {req.num_ads} ad(s). Poll GET /campaigns/{campaign_id} for status."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaigns")
def list_campaigns():
    try:
        campaigns = supabase.table("campaigns").select("*").order("created_at", desc=True).execute()
        results = []
        for c in campaigns.data:
            ad_count = supabase.table("ads").select("id", count="exact").eq("campaign_id", c["id"]).execute()
            results.append({**c, "ad_count": ad_count.count or 0})
        return {"campaigns": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: str):
    try:
        campaign = supabase.table("campaigns").select("*").eq("id", campaign_id).execute()
        if not campaign.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        ads = supabase.table("ads").select("*").eq("campaign_id", campaign_id).order("created_at").execute()
        ads_with_evals = []
        for ad in ads.data:
            ev = supabase.table("evaluations").select("*").eq("ad_id", ad["id"]).execute()
            ads_with_evals.append({**ad, "evaluation": ev.data[0] if ev.data else None})
        return {"campaign": campaign.data[0], "ads": ads_with_evals, "ad_count": len(ads_with_evals)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ads/{ad_id}")
def get_ad(ad_id: str):
    try:
        ad = supabase.table("ads").select("*").eq("id", ad_id).execute()
        if not ad.data:
            raise HTTPException(status_code=404, detail="Ad not found")
        ev = supabase.table("evaluations").select("*").eq("ad_id", ad_id).execute()
        return {"ad": ad.data[0], "evaluation": ev.data[0] if ev.data else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/trends")
def get_trends():
    try:
        evaluations = supabase.table("evaluations").select("*, ads(campaign_id, headline, iteration_number, status)").execute()
        if not evaluations.data:
            return {"trends": [], "summary": {}}
        by_campaign = {}
        all_scores = []
        for ev in evaluations.data:
            ad = ev.get("ads", {})
            campaign_id = ad.get("campaign_id") if ad else None
            if not campaign_id:
                continue
            score = ev.get("aggregate_score", 0)
            all_scores.append(score)
            if campaign_id not in by_campaign:
                by_campaign[campaign_id] = {"campaign_id": campaign_id, "scores": [],
                    "dims": {"clarity": [], "value_proposition": [], "cta_score": [], "brand_voice": [], "emotional_resonance": []},
                    "approved_count": 0, "flagged_count": 0}
            by_campaign[campaign_id]["scores"].append(score)
            for dim in ["clarity", "value_proposition", "cta_score", "brand_voice", "emotional_resonance"]:
                by_campaign[campaign_id]["dims"][dim].append(ev.get(dim, 0))
            if ad.get("status") == "approved":
                by_campaign[campaign_id]["approved_count"] += 1
            elif ad.get("status") == "flagged":
                by_campaign[campaign_id]["flagged_count"] += 1
        avg = lambda lst: round(sum(lst) / len(lst), 2) if lst else 0
        trends = [{"campaign_id": cid, "avg_score": avg(d["scores"]), "ad_count": len(d["scores"]),
                   "approved_count": d["approved_count"], "flagged_count": d["flagged_count"],
                   "dimension_averages": {k: avg(v) for k, v in d["dims"].items()}}
                  for cid, d in by_campaign.items()]
        summary = {"total_ads": len(all_scores),
                   "overall_avg_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else 0,
                   "pass_rate": round(sum(1 for s in all_scores if s >= 7.0) / len(all_scores) * 100, 1) if all_scores else 0}
        return {"trends": trends, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ads/{ad_id}/rate")
def rate_ad(ad_id: str, rating: dict):
    try:
        r = rating.get("rating")
        if r not in ["good", "bad", "unsure"]:
            raise HTTPException(status_code=400, detail="Rating must be good, bad, or unsure")
        ad = supabase.table("ads").select("id").eq("id", ad_id).execute()
        if not ad.data:
            raise HTTPException(status_code=404, detail="Ad not found")
        supabase.table("human_ratings").insert({"ad_id": ad_id, "rating": r}).execute()
        return {"success": True, "ad_id": ad_id, "rating": r}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/confusion-matrix")
def get_confusion_matrix():
    try:
        ratings = supabase.table("human_ratings").select("*, ads(aggregate_score, status)").execute()
        if not ratings.data:
            return {"matrix": {}, "metrics": {}, "total_ratings": 0}
        tp = fp = tn = fn = 0
        for r in ratings.data:
            ad = r.get("ads", {})
            human_good = r["rating"] == "good"
            ai_approved = ad.get("status") == "approved"
            if human_good and ai_approved: tp += 1
            elif not human_good and ai_approved: fp += 1
            elif human_good and not ai_approved: fn += 1
            else: tn += 1
        total = tp + fp + tn + fn
        precision = round(tp / (tp + fp), 3) if (tp + fp) > 0 else 0
        recall = round(tp / (tp + fn), 3) if (tp + fn) > 0 else 0
        accuracy = round((tp + tn) / total, 3) if total > 0 else 0
        return {
            "matrix": {"true_positive": tp, "false_positive": fp, "true_negative": tn, "false_negative": fn},
            "metrics": {"precision": precision, "recall": recall, "accuracy": accuracy},
            "total_ratings": total
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
