"""
progress_tracker.py
-------------------
Drop this in your backend/ folder.
Call mark_complete(step_id) anywhere in your agent code to update the roadmap.

Usage:
    from progress_tracker import mark_complete

    # At the end of a successful agent build/step:
    await mark_complete("evaluator_agent_built")
    mark_complete("writer_agent_built")  # sync version also works
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Path to progress.json — relative to project root
# Assumes you're running from nerdy-ad-engine/backend/
PROGRESS_FILE = Path(__file__).parent.parent / "docs" / "progress.json"

# Master step registry — maps step_id to phase and display name
STEPS = {
    # Phase 1 — Foundation (all pre-completed)
    "repo_created":              {"phase": 1, "name": "GitHub repo created (private)"},
    "frontend_scaffolded":       {"phase": 1, "name": "Next.js frontend scaffolded"},
    "frontend_deployed":         {"phase": 1, "name": "Frontend deployed → Vercel"},
    "backend_scaffolded":        {"phase": 1, "name": "FastAPI backend scaffolded"},
    "backend_deployed":          {"phase": 1, "name": "Backend deployed → Fly.io"},
    "supabase_created":          {"phase": 1, "name": "Supabase project created"},
    "fly_secrets_set":           {"phase": 1, "name": "Fly.io secrets set"},
    "supabase_schema_created":   {"phase": 1, "name": "Supabase schema created"},
    "dockerfile_created":        {"phase": 1, "name": "Dockerfile for Fly.io containerization"},
    "fly_toml_created":          {"phase": 1, "name": "fly.toml deployment config"},
    "reference_ads_dataset":     {"phase": 1, "name": "Reference ads dataset (varsity_tutors.json)"},

    # Phase 2 — Agent Pipeline
    "deps_installed":            {"phase": 2, "name": "Install Python dependencies"},
    "evaluator_agent_built":     {"phase": 2, "name": "Build EvaluatorAgent (Claude Sonnet)"},
    "evaluator_calibrated":      {"phase": 2, "name": "Calibrate evaluator against reference_ads JSON"},
    "researcher_agent_built":    {"phase": 2, "name": "Build ResearcherAgent (Gemini Flash)"},
    "writer_agent_built":        {"phase": 2, "name": "Build WriterAgent (Gemini Flash)"},
    "fixer_agent_built":         {"phase": 2, "name": "Build FixerAgent (Gemini Flash)"},
    "langgraph_wired":           {"phase": 2, "name": "Wire LangGraph graph (researcher→writer→evaluator→fixer)"},
    "max_iterations_guard":      {"phase": 2, "name": "Add max_iterations=3 hard cap guard"},
    "langfuse_added":            {"phase": 2, "name": "Add Langfuse observability + cost tracking"},
    "progress_tracker_built":    {"phase": 2, "name": "Build progress_tracker.py for milestone tracking"},

    # Phase 3 — Backend API
    "api_post_campaigns":        {"phase": 3, "name": "POST /campaigns — create brief, kick off agent graph"},
    "api_get_campaign":          {"phase": 3, "name": "GET /campaigns/{id} — poll status"},
    "api_get_ads":               {"phase": 3, "name": "GET /ads — paginated ad library with filters"},
    "api_get_ad":                {"phase": 3, "name": "GET /ads/{id} — single ad + full eval breakdown"},
    "api_get_trends":            {"phase": 3, "name": "GET /analytics/trends — quality trend data"},
    "api_get_campaigns_list":    {"phase": 3, "name": "GET /campaigns — list all campaigns with ad counts"},
    "api_post_rate":             {"phase": 3, "name": "POST /ads/{id}/rate — human rating submission"},
    "api_confusion_matrix":      {"phase": 3, "name": "GET /analytics/confusion-matrix — AI vs human agreement"},
    "api_health":                {"phase": 3, "name": "GET /health — service status endpoint"},
    "api_post_regenerate":       {"phase": 3, "name": "POST /ads/{id}/regenerate — human-in-loop trigger"},
    "pydantic_validation":       {"phase": 3, "name": "Pydantic validation on all LLM outputs"},
    "rate_limiting":             {"phase": 3, "name": "Rate limiting per campaign (cost protection)"},

    # Phase 4 — Scale
    "multi_audience":            {"phase": 4, "name": "Run pipeline across 3+ audience segments"},
    "fifty_ads":                 {"phase": 4, "name": "Generate 50+ ads with full evaluation scores"},
    "three_cycles":              {"phase": 4, "name": "Complete 3+ iteration cycles with measurable improvement"},
    "cost_tracking":             {"phase": 4, "name": "Track cost-per-ad via Langfuse"},
    "eval_export":               {"phase": 4, "name": "Export evaluation report (JSON/CSV)"},
    "scale_run_script":          {"phase": 4, "name": "Build scale_run.py batch generation script"},

    # Phase 5 — Frontend UI
    "campaign_dashboard":        {"phase": 5, "name": "Campaign Dashboard — control room"},
    "ad_library_ui":             {"phase": 5, "name": "Ad Library — filterable grid, Facebook ad card mockup"},
    "radar_charts":              {"phase": 5, "name": "Radar charts — 5-dimension score per ad"},
    "trend_analytics":           {"phase": 5, "name": "Trend Analytics — quality improvement line charts"},
    "cost_display":              {"phase": 5, "name": "Cost-per-ad tracking display"},
    "survey_page":               {"phase": 5, "name": "Survey page — human rating collection UI"},
    "insights_page":             {"phase": 5, "name": "Insights page — confusion matrix + precision/recall"},
    "campaign_detail_page":      {"phase": 5, "name": "Campaign detail page — per-campaign ad view"},
    "nav_bar":                   {"phase": 5, "name": "Navigation bar with route links"},
    "dark_light_theme":          {"phase": 5, "name": "Dark/light theme toggle with localStorage"},
    "frontend_connected":        {"phase": 5, "name": "Connect frontend to FastAPI backend"},
    "vercel_env_vars":           {"phase": 5, "name": "Add env vars to Vercel dashboard"},

    # Phase 6 — Documentation
    "decision_log":              {"phase": 6, "name": "Decision log — written as you go"},
    "live_roadmap":              {"phase": 6, "name": "Live roadmap (roadmap.html + progress.json)"},
    "limitations_doc":           {"phase": 6, "name": "Limitations doc"},
    "readme":                    {"phase": 6, "name": "README — one-command setup + usage"},
    "tests":                     {"phase": 6, "name": "10+ unit/integration tests"},
    "technical_writeup":         {"phase": 6, "name": "Technical writeup (1–2 pages)"},
    "demo_video":                {"phase": 6, "name": "Record 1–5 min demo video"},
    "repo_public":               {"phase": 6, "name": "Make repo public for submission"},
}

# Steps already completed before agent pipeline begins
BOOTSTRAP_COMPLETE = [
    "repo_created", "frontend_scaffolded", "frontend_deployed",
    "backend_scaffolded", "backend_deployed", "supabase_created",
    "fly_secrets_set", "supabase_schema_created",
    "dockerfile_created", "fly_toml_created", "reference_ads_dataset"
]


def _load() -> dict:
    """Load current progress state, initializing if needed."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)

    # First run — bootstrap Phase 1 as complete
    state = {
        "completed": {
            step_id: datetime.utcnow().isoformat()
            for step_id in BOOTSTRAP_COMPLETE
        },
        "last_updated": datetime.utcnow().isoformat()
    }
    _save(state)
    return state


def _save(state: dict):
    """Save progress state to disk."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.utcnow().isoformat()
    with open(PROGRESS_FILE, "w") as f:
        json.dump(state, f, indent=2)


def mark_complete(step_id: str):
    """
    Mark a step as complete. Call this at the end of each agent/feature build.

    Example:
        mark_complete("evaluator_agent_built")
        mark_complete("writer_agent_built")
    """
    if step_id not in STEPS:
        raise ValueError(
            f"Unknown step_id: '{step_id}'\n"
            f"Valid step IDs: {list(STEPS.keys())}"
        )

    state = _load()
    if step_id not in state["completed"]:
        state["completed"][step_id] = datetime.utcnow().isoformat()
        _save(state)
        step_name = STEPS[step_id]["name"]
        phase = STEPS[step_id]["phase"]
        print(f"✅ Phase {phase} — {step_name}")
    else:
        print(f"⏭️  Already complete: {step_id}")


def get_progress() -> dict:
    """
    Returns a summary of current progress.
    Useful for logging at the start of a run.
    """
    state = _load()
    completed = set(state["completed"].keys())
    total = len(STEPS)
    done = len(completed)

    by_phase = {}
    for step_id, meta in STEPS.items():
        phase = meta["phase"]
        if phase not in by_phase:
            by_phase[phase] = {"total": 0, "done": 0}
        by_phase[phase]["total"] += 1
        if step_id in completed:
            by_phase[phase]["done"] += 1

    return {
        "total_steps": total,
        "completed_steps": done,
        "percent": round((done / total) * 100),
        "by_phase": by_phase,
        "last_updated": state.get("last_updated")
    }


if __name__ == "__main__":
    # Quick test — run with: python progress_tracker.py
    progress = get_progress()
    print(f"\n📊 Project Progress: {progress['completed_steps']}/{progress['total_steps']} steps ({progress['percent']}%)")
    for phase_num, counts in progress["by_phase"].items():
        bar = "█" * counts["done"] + "░" * (counts["total"] - counts["done"])
        print(f"   Phase {phase_num}: [{bar}] {counts['done']}/{counts['total']}")
