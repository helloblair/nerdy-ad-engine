import csv
import io
import os
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from pipeline import run_pipeline
from writer_agent import CampaignBrief
from ab_variant_generator import generate_ab_variants, CREATIVE_APPROACHES
from evaluator_agent import EvaluatorAgent
from db import get_db

load_dotenv()

def _check_env():
    """Warn about missing env vars at startup."""
    backend = os.getenv("DB_BACKEND", "sqlite").lower()
    use_supabase = backend == "supabase"
    required_prod = ["SUPABASE_URL", "SUPABASE_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    required_local = ["ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    required = required_prod if use_supabase else required_local
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"⚠️  Missing env vars: {missing}")
        print("   Set these in .env (local) or fly secrets (production)")
    else:
        env_type = "Supabase (production)" if use_supabase else "SQLite (local)"
        print(f"✅ All required env vars set — using {env_type}")

_check_env()

@asynccontextmanager
async def lifespan(app):
    db = get_db()
    backend_type = type(db).__name__
    print(f"🚀 Nerdy Ad Engine API starting up... (db: {backend_type})")
    yield

app = FastAPI(title="Nerdy Autonomous Ad Engine", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Serve generated ad images as static files
import os as _os
_images_dir = _os.path.join(_os.path.dirname(__file__), "data", "images")
_os.makedirs(_images_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=_images_dir), name="images")

class CreateCampaignRequest(BaseModel):
    name: str
    audience: str
    product: str
    goal: str
    tone: Optional[str] = "warm, urgent, outcome-focused"
    key_benefit: Optional[str] = None
    proof_point: Optional[str] = None
    num_ads: Optional[int] = 1
    persona: Optional[str] = "general"

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

# Mapping from evaluator dimension names → DB column names
# (cta_strength is stored as cta_score in the DB schema)
EVAL_TO_DB_DIM = {
    "clarity": "clarity",
    "value_proposition": "value_proposition",
    "cta_strength": "cta_score",
    "brand_voice": "brand_voice",
    "emotional_resonance": "emotional_resonance",
    "visual_brand_consistency": "visual_brand_consistency",
    "scroll_stopping_power": "scroll_stopping_power",
}
DB_TEXT_DIMS = [EVAL_TO_DB_DIM[d] for d in EvaluatorAgent.TEXT_WEIGHTS]
DB_ALL_DIMS = [EVAL_TO_DB_DIM[d] for d in EvaluatorAgent.FULL_WEIGHTS]

@app.get("/evaluator/config")
def evaluator_config():
    """Expose evaluator configuration so frontend stays in sync."""
    from quality_ratchet import get_current_threshold
    ratchet = get_current_threshold(get_db())
    return {
        "threshold": ratchet["threshold"],
        "floor": ratchet["floor"],
        "ratchet_active": ratchet["ratchet_active"],
        "ratchet_sample_size": ratchet["sample_size"],
        "ratchet_headroom": ratchet["headroom"],
        "text_weights": EvaluatorAgent.TEXT_WEIGHTS,
        "full_weights": EvaluatorAgent.FULL_WEIGHTS,
        "text_dimensions": list(EvaluatorAgent.TEXT_WEIGHTS.keys()),
        "all_dimensions": list(EvaluatorAgent.FULL_WEIGHTS.keys()),
        "db_text_dimensions": DB_TEXT_DIMS,
        "db_all_dimensions": DB_ALL_DIMS,
        "max_iterations": 3,
    }

@app.post("/campaigns", status_code=202)
def create_campaign(req: CreateCampaignRequest, background_tasks: BackgroundTasks):
    db = get_db()
    try:
        # Global safety check
        total_ads = db.count_all_ads()
        if total_ads >= 500:
            raise HTTPException(
                status_code=429,
                detail="System ad limit reached (500). Contact admin to increase quota.",
            )

        result = db.insert_campaign({
            "name": req.name, "audience": req.audience, "product": req.product,
            "goal": req.goal, "tone": req.tone, "status": "pending",
        })
        campaign_id = result["id"]

        # Per-campaign rate limit
        existing_count = db.count_ads_for_campaign(campaign_id)
        if existing_count >= 10:
            raise HTTPException(
                status_code=429,
                detail=f"Max 10 ads per campaign. This campaign already has {existing_count} ads.",
            )

        brief = CampaignBrief(audience=req.audience, product=req.product, goal=req.goal,
                              tone=req.tone, key_benefit=req.key_benefit, proof_point=req.proof_point,
                              persona=req.persona)
        background_tasks.add_task(run_campaign_pipeline, campaign_id, brief, req.num_ads)
        return {"campaign_id": campaign_id, "status": "pending",
                "message": f"Pipeline started — generating {req.num_ads} ad(s). Poll GET /campaigns/{campaign_id} for status."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaigns")
def list_campaigns():
    db = get_db()
    try:
        campaigns = db.list_campaigns()
        results = []
        for c in campaigns:
            ads = db.list_ads_for_campaign(c["id"])
            thumbnail = next((a.get("image_url") for a in ads if a.get("image_url")), None)
            results.append({**c, "ad_count": len(ads), "thumbnail": thumbnail})
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

@app.get("/ads")
def list_all_ads():
    db = get_db()
    try:
        ads = db.list_all_ads()
        campaign_cache: dict[str, dict] = {}
        results = []
        for ad in ads:
            cid = ad.get("campaign_id", "")
            if cid not in campaign_cache:
                campaign_cache[cid] = db.get_campaign(cid) or {}
            campaign = campaign_cache[cid]
            ev = db.get_evaluation_for_ad(ad["id"])
            results.append({
                **ad,
                "evaluation": ev,
                "campaign_name": campaign.get("name"),
                "campaign_product": campaign.get("product"),
                "campaign_audience": campaign.get("audience"),
                "campaign_goal": campaign.get("goal"),
            })
        return {"ads": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ads/recent")
def get_recent_ads(limit: int = 6):
    db = get_db()
    try:
        ads = db.list_all_ads()[:limit]
        results = []
        for ad in ads:
            ev = db.get_evaluation_for_ad(ad["id"])
            campaign = db.get_campaign(ad.get("campaign_id", ""))
            results.append({**ad, "evaluation": ev, "campaign_name": campaign.get("name") if campaign else None})
        return {"ads": results}
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

@app.get("/analytics/cost")
def get_cost_analytics():
    db = get_db()
    try:
        ads = db.list_all_ads()
        total = sum(a.get("cost_usd") or 0 for a in ads)
        avg = total / len(ads) if ads else 0
        return {
            "total_spend_usd": round(total, 4),
            "avg_cost_per_ad": round(avg, 6),
            "cost_by_model": {
                "gemini_flash": round(total * 0.15, 4),
                "claude_sonnet": round(total * 0.85, 4),
            },
            "ads_analyzed": len(ads),
        }
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
                    "dims": {d: [] for d in DB_ALL_DIMS},
                    "approved_count": 0, "flagged_count": 0}
            by_campaign[campaign_id]["scores"].append(score)
            for dim in DB_ALL_DIMS:
                val = ev.get(dim)
                if val is None or val == 0:
                    continue
                by_campaign[campaign_id]["dims"][dim].append(val)
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
                   "pass_rate": round(sum(1 for s in all_scores if s >= EvaluatorAgent.THRESHOLD) / len(all_scores) * 100, 1) if all_scores else 0}
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
        unique_ads = len({r["ad_id"] for r in ratings})
        precision = round(tp / (tp + fp), 3) if (tp + fp) > 0 else 0
        recall = round(tp / (tp + fn), 3) if (tp + fn) > 0 else 0
        accuracy = round((tp + tn) / total, 3) if total > 0 else 0
        return {
            "matrix": {"true_positive": tp, "false_positive": fp, "true_negative": tn, "false_negative": fn},
            "metrics": {"precision": precision, "recall": recall, "accuracy": accuracy},
            "total_ratings": total,
            "unique_ads_rated": unique_ads
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/iterations")
def get_iteration_analytics():
    """Returns documented proof of iterative improvement across fixer cycles."""
    import json as _json
    proof_path = os.path.join(os.path.dirname(__file__), "..", "docs", "iteration_proof.json")
    if os.path.exists(proof_path):
        with open(proof_path) as f:
            return _json.load(f)
    # Fallback: calculate from DB
    db = get_db()
    try:
        evaluations = db.get_evaluations_with_ads()
        if not evaluations:
            return {"summary": {"total_campaigns": 0, "total_ads": 0, "avg_score_iter1": 0,
                                "avg_score_iter2": 0, "avg_score_iter3": 0, "total_lift": 0,
                                "methodology": "No iteration data available"}, "campaigns": []}
        by_iter: dict[int, list[float]] = {}
        for ev in evaluations:
            ad = ev.get("ads", {})
            iteration = ad.get("iteration_number", 1) if ad else 1
            by_iter.setdefault(iteration, []).append(ev.get("aggregate_score", 0))
        avg = lambda lst: round(sum(lst) / len(lst), 1) if lst else 0.0
        iter1 = avg(by_iter.get(1, []))
        iter2 = avg(by_iter.get(2, [])) if 2 in by_iter else iter1
        iter3 = avg(by_iter.get(3, [])) if 3 in by_iter else iter2
        return {
            "summary": {
                "total_campaigns": len(set(
                    ev.get("ads", {}).get("campaign_id") for ev in evaluations if ev.get("ads")
                )),
                "total_ads": len(evaluations),
                "avg_score_iter1": iter1,
                "avg_score_iter2": iter2,
                "avg_score_iter3": iter3,
                "total_lift": round(iter3 - iter1, 1),
                "methodology": "Calculated from DB evaluation records grouped by iteration number",
            },
            "campaigns": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ads/{ad_id}/regenerate")
def regenerate_ad(ad_id: str, background_tasks: BackgroundTasks):
    db = get_db()
    try:
        ad = db.get_ad(ad_id)
        if not ad:
            raise HTTPException(status_code=404, detail="Ad not found")
        campaign = db.get_campaign(ad["campaign_id"])
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        brief = CampaignBrief(
            audience=campaign["audience"],
            product=campaign["product"],
            goal=campaign["goal"],
            tone=campaign.get("tone"),
        )

        def _regenerate():
            result = run_pipeline(campaign["id"], brief)
            new_iteration = ad.get("iteration_number", 1) + 1
            updates = {
                "primary_text": result["generated_ad"]["primary_text"],
                "headline": result["generated_ad"]["headline"],
                "description": result["generated_ad"].get("description", ""),
                "cta_button": result["generated_ad"]["cta_button"],
                "iteration_number": new_iteration,
                "status": "approved" if result["approved"] else "flagged",
            }
            db.update_ad(ad_id, updates)

        background_tasks.add_task(_regenerate)
        return {
            "status": "regenerating",
            "ad_id": ad_id,
            "campaign_id": campaign["id"],
            "message": "Pipeline re-entered. Ad will be updated with new content.",
        }
    except HTTPException:
        raise
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

    dims = DB_ALL_DIMS
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
            val = ev.get(d)
            if val is not None and val != 0:
                dim_totals[d].append(val)
        ad_row = {
            "ad_id": ev.get("ad_id", ""),
            "headline": ad.get("headline", ""),
            "campaign_name": campaign_names.get(ad.get("campaign_id", ""), ""),
            "iteration_number": iteration,
            **{d: ev.get(d, 0) if d in DB_TEXT_DIMS else ev.get(d) for d in dims},
            "aggregate_score": score,
            "passed_threshold": score >= EvaluatorAgent.THRESHOLD,
        }
        per_ad.append(ad_row)

    avg = lambda lst: round(sum(lst) / len(lst), 2) if lst else 0
    quality_trajectory = sorted(
        [{"cycle": k, "avg_score": avg(v)} for k, v in by_iteration.items()],
        key=lambda x: x["cycle"],
    )

    return {
        "total_ads": len(all_scores),
        "avg_score": avg(all_scores),
        "pass_rate": round(sum(1 for s in all_scores if s >= EvaluatorAgent.THRESHOLD) / len(all_scores) * 100, 1),
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
                *DB_ALL_DIMS, "aggregate_score", "passed_threshold"]
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

# ─── A/B Variant Endpoints ──────────────────────────────────────────────────

class ABTestRequest(BaseModel):
    num_variants: Optional[int] = 3
    approach_names: Optional[list[str]] = None

@app.post("/campaigns/{campaign_id}/ab-test", status_code=202)
def create_ab_test(campaign_id: str, req: ABTestRequest, background_tasks: BackgroundTasks):
    db = get_db()
    try:
        campaign = db.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        brief = CampaignBrief(
            audience=campaign["audience"],
            product=campaign["product"],
            goal=campaign["goal"],
            tone=campaign.get("tone"),
        )

        # Validate approach names up front if provided
        if req.approach_names:
            valid_names = {a["name"] for a in CREATIVE_APPROACHES}
            invalid = [n for n in req.approach_names if n not in valid_names]
            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown approaches: {invalid}. Valid: {sorted(valid_names)}",
                )

        def _run_ab_test():
            db_inner = get_db()
            try:
                db_inner.update_campaign_status(campaign_id, "running")
                generate_ab_variants(
                    campaign_id, brief,
                    num_variants=req.num_variants,
                    approach_names=req.approach_names,
                )
                db_inner.update_campaign_status(campaign_id, "completed")
            except Exception as e:
                print(f"❌ A/B test for {campaign_id} failed: {e}")
                db_inner.update_campaign_status(campaign_id, "failed")

        background_tasks.add_task(_run_ab_test)
        num = len(req.approach_names) if req.approach_names else req.num_variants
        return {
            "campaign_id": campaign_id,
            "status": "pending",
            "num_variants": num,
            "message": f"A/B test started — generating {num} variant(s). Poll GET /campaigns/{campaign_id} for status.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaigns/{campaign_id}/variants")
def get_campaign_variants(campaign_id: str):
    db = get_db()
    try:
        campaign = db.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        ads = db.list_ads_for_campaign(campaign_id)
        by_approach: dict[str, list[dict]] = {}
        for ad in ads:
            approach = ad.get("variant_approach") or "default"
            ev = db.get_evaluation_for_ad(ad["id"])
            ad_with_eval = {**ad, "evaluation": ev}
            by_approach.setdefault(approach, []).append(ad_with_eval)

        return {
            "campaign_id": campaign_id,
            "campaign": campaign,
            "variants": by_approach,
            "total_ads": len(ads),
            "approaches_used": list(by_approach.keys()),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
