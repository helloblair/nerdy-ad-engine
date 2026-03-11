import csv
import io
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pipeline import run_pipeline
from writer_agent import CampaignBrief
from db import get_db

load_dotenv()

@asynccontextmanager
async def lifespan(app):
    db = get_db()
    backend_type = type(db).__name__
    print(f"🚀 Nerdy Ad Engine API starting up... (db: {backend_type})")
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
    db = get_db()
    try:
        db.update_campaign_status(campaign_id, "running")
        for i in range(num_ads):
            print(f"🔄 Generating ad {i+1}/{num_ads} for campaign {campaign_id}")
            run_pipeline(campaign_id, brief)
        db.update_campaign_status(campaign_id, "completed")
        print(f"✅ Campaign {campaign_id} completed")
    except Exception as e:
        print(f"❌ Campaign {campaign_id} failed: {e}")
        db.update_campaign_status(campaign_id, "failed")

@app.get("/health")
def health():
    return {"status": "ok", "service": "nerdy-ad-engine"}

@app.post("/campaigns", status_code=202)
def create_campaign(req: CreateCampaignRequest, background_tasks: BackgroundTasks):
    db = get_db()
    try:
        result = db.insert_campaign({
            "name": req.name, "audience": req.audience, "product": req.product,
            "goal": req.goal, "tone": req.tone, "status": "pending",
        })
        campaign_id = result["id"]
        brief = CampaignBrief(audience=req.audience, product=req.product, goal=req.goal,
                              tone=req.tone, key_benefit=req.key_benefit, proof_point=req.proof_point)
        background_tasks.add_task(run_campaign_pipeline, campaign_id, brief, req.num_ads)
        return {"campaign_id": campaign_id, "status": "pending",
                "message": f"Pipeline started — generating {req.num_ads} ad(s). Poll GET /campaigns/{campaign_id} for status."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaigns")
def list_campaigns():
    db = get_db()
    try:
        campaigns = db.list_campaigns()
        results = []
        for c in campaigns:
            ad_count = db.count_ads_for_campaign(c["id"])
            results.append({**c, "ad_count": ad_count})
        return {"campaigns": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: str):
    db = get_db()
    try:
        campaign = db.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        ads = db.list_ads_for_campaign(campaign_id)
        ads_with_evals = []
        for ad in ads:
            ev = db.get_evaluation_for_ad(ad["id"])
            ads_with_evals.append({**ad, "evaluation": ev})
        return {"campaign": campaign, "ads": ads_with_evals, "ad_count": len(ads_with_evals)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ads/{ad_id}")
def get_ad(ad_id: str):
    db = get_db()
    try:
        ad = db.get_ad(ad_id)
        if not ad:
            raise HTTPException(status_code=404, detail="Ad not found")
        ev = db.get_evaluation_for_ad(ad_id)
        return {"ad": ad, "evaluation": ev}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/trends")
def get_trends():
    db = get_db()
    try:
        evaluations = db.get_evaluations_with_ads()
        if not evaluations:
            return {"trends": [], "summary": {}}
        by_campaign = {}
        all_scores = []
        for ev in evaluations:
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
    db = get_db()
    try:
        r = rating.get("rating")
        if r not in ["good", "bad", "unsure"]:
            raise HTTPException(status_code=400, detail="Rating must be good, bad, or unsure")
        ad = db.get_ad(ad_id)
        if not ad:
            raise HTTPException(status_code=404, detail="Ad not found")
        db.insert_human_rating({"ad_id": ad_id, "rating": r})
        return {"success": True, "ad_id": ad_id, "rating": r}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/confusion-matrix")
def get_confusion_matrix():
    db = get_db()
    try:
        ratings = db.get_ratings_with_ads()
        if not ratings:
            return {"matrix": {}, "metrics": {}, "total_ratings": 0}
        tp = fp = tn = fn = 0
        for r in ratings:
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

def _build_report_data() -> dict:
    db = get_db()
    evaluations = db.get_evaluations_with_ads()
    campaigns = db.list_campaigns()
    campaign_names = {c["id"]: c.get("name", "") for c in campaigns}

    if not evaluations:
        return {
            "total_ads": 0, "avg_score": 0, "pass_rate": 0,
            "dimension_averages": {}, "quality_trajectory": [], "per_ad": [],
        }

    dims = ["clarity", "value_proposition", "cta_score", "brand_voice", "emotional_resonance"]
    all_scores = []
    dim_totals: dict[str, list[float]] = {d: [] for d in dims}
    by_iteration: dict[int, list[float]] = {}
    per_ad = []

    for ev in evaluations:
        ad = ev.get("ads", {})
        if not ad:
            continue
        score = ev.get("aggregate_score", 0)
        all_scores.append(score)
        iteration = ad.get("iteration_number", 1)
        by_iteration.setdefault(iteration, []).append(score)
        for d in dims:
            dim_totals[d].append(ev.get(d, 0))
        per_ad.append({
            "ad_id": ev.get("ad_id", ""),
            "headline": ad.get("headline", ""),
            "campaign_name": campaign_names.get(ad.get("campaign_id", ""), ""),
            "iteration_number": iteration,
            "clarity": ev.get("clarity", 0),
            "value_proposition": ev.get("value_proposition", 0),
            "cta_score": ev.get("cta_score", 0),
            "brand_voice": ev.get("brand_voice", 0),
            "emotional_resonance": ev.get("emotional_resonance", 0),
            "aggregate_score": score,
            "passed_threshold": score >= 7.0,
        })

    avg = lambda lst: round(sum(lst) / len(lst), 2) if lst else 0
    quality_trajectory = sorted(
        [{"cycle": k, "avg_score": avg(v)} for k, v in by_iteration.items()],
        key=lambda x: x["cycle"],
    )

    return {
        "total_ads": len(all_scores),
        "avg_score": avg(all_scores),
        "pass_rate": round(sum(1 for s in all_scores if s >= 7.0) / len(all_scores) * 100, 1),
        "dimension_averages": {d: avg(dim_totals[d]) for d in dims},
        "quality_trajectory": quality_trajectory,
        "per_ad": per_ad,
    }

@app.get("/analytics/report")
def get_report():
    try:
        return _build_report_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/export/csv")
def export_csv():
    try:
        data = _build_report_data()
        output = io.StringIO()
        cols = ["ad_id", "headline", "campaign_name", "iteration_number",
                "clarity", "value_proposition", "cta_score", "brand_voice",
                "emotional_resonance", "aggregate_score", "passed_threshold"]
        writer = csv.DictWriter(output, fieldnames=cols)
        writer.writeheader()
        for row in data["per_ad"]:
            writer.writerow({c: row[c] for c in cols})
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="nerdy_ad_report.csv"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
