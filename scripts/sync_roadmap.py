"""
sync_roadmap.py
---------------
Scans the codebase for evidence of completed milestones and updates
docs/progress.json accordingly.  Designed to run in CI (GitHub Actions)
on every push to main, but also works locally:

    python scripts/sync_roadmap.py          # dry-run (prints diff)
    python scripts/sync_roadmap.py --apply  # writes progress.json
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROGRESS_FILE = ROOT / "docs" / "progress.json"

# ─── Detection rules ────────────────────────────────────────────────────────
# Each rule maps a step_id to a callable that returns True when the step
# is detectably complete.  Add new rules here as the project grows.


def _file_exists(*parts: str) -> bool:
    return (ROOT / Path(*parts)).exists()


def _file_contains(path: str, pattern: str) -> bool:
    fp = ROOT / path
    if not fp.exists():
        return False
    return bool(re.search(pattern, fp.read_text(errors="ignore")))


def _dir_has_files(path: str, glob: str, min_count: int = 1) -> bool:
    d = ROOT / path
    if not d.is_dir():
        return False
    return len(list(d.glob(glob))) >= min_count


RULES: dict[str, callable] = {
    # Phase 1 — Foundation
    "repo_created":            lambda: _file_exists(".git"),
    "frontend_scaffolded":     lambda: _file_exists("frontend", "package.json"),
    "frontend_deployed":       lambda: _file_exists("frontend", "next.config.js") or _file_exists("frontend", "next.config.mjs") or _file_exists("frontend", "next.config.ts"),
    "backend_scaffolded":      lambda: _file_exists("backend", "main.py"),
    "backend_deployed":        lambda: _file_exists("fly.toml"),
    "supabase_created":        lambda: _file_exists("backend", "schema.sql"),
    "fly_secrets_set":         lambda: _file_exists("fly.toml"),
    "supabase_schema_created": lambda: _file_exists("backend", "schema.sql"),
    "dockerfile_created":      lambda: _file_exists("Dockerfile") or _file_exists("backend", "Dockerfile"),
    "fly_toml_created":        lambda: _file_exists("fly.toml"),
    "reference_ads_dataset":   lambda: _file_exists("backend", "varsity_tutors.json"),

    # Phase 2 — Agent Pipeline
    "deps_installed":          lambda: _file_exists("backend", "requirements.txt"),
    "evaluator_agent_built":   lambda: _file_exists("backend", "evaluator_agent.py"),
    "evaluator_calibrated":    lambda: _file_contains("backend/evaluator_agent.py", r"calibrat|reference_ads|varsity_tutors"),
    "researcher_agent_built":  lambda: _file_exists("backend", "researcher_agent.py"),
    "writer_agent_built":      lambda: _file_exists("backend", "writer_agent.py"),
    "fixer_agent_built":       lambda: _file_exists("backend", "fixer_agent.py"),
    "langgraph_wired":         lambda: _file_contains("backend/pipeline.py", r"StateGraph|build_pipeline"),
    "max_iterations_guard":    lambda: _file_contains("backend/pipeline.py", r"max_iterations"),
    "confidence_scoring":      lambda: _file_contains("backend/evaluator_agent.py", r"confidence"),
    "deterministic_seeds":     lambda: _file_contains("backend/writer_agent.py", r"seed"),
    "progress_tracker_built":  lambda: _file_exists("backend", "progress_tracker.py"),

    # Phase 3 — Backend API
    "api_post_campaigns":      lambda: _file_contains("backend/main.py", r'@app\.post\("/campaigns"'),
    "api_get_campaign":        lambda: _file_contains("backend/main.py", r'@app\.get\("/campaigns/\{campaign_id\}"'),
    "api_get_ads":             lambda: _file_contains("backend/main.py", r'@app\.get\("/ads"') or _file_contains("backend/main.py", r"def list_ads"),
    "api_get_ad":              lambda: _file_contains("backend/main.py", r'@app\.get\("/ads/\{ad_id\}"'),
    "api_get_trends":          lambda: _file_contains("backend/main.py", r"/analytics/trends"),
    "api_get_campaigns_list":  lambda: _file_contains("backend/main.py", r'@app\.get\("/campaigns"\)'),
    "api_post_rate":           lambda: _file_contains("backend/main.py", r"/ads/\{ad_id\}/rate"),
    "api_confusion_matrix":    lambda: _file_contains("backend/main.py", r"confusion.matrix"),
    "api_health":              lambda: _file_contains("backend/main.py", r"/health"),
    "api_post_regenerate":     lambda: _file_contains("backend/main.py", r"/ads/\{ad_id\}/regenerate"),
    "pydantic_validation":     lambda: _file_contains("backend/evaluator_agent.py", r"BaseModel"),
    "sqlite_fallback":         lambda: _file_exists("backend", "db", "sqlite_db.py"),

    # Phase 4 — Scale
    "multi_audience":          lambda: _file_exists("backend", "scale_run.py") and _file_contains("backend/scale_run.py", r"audience"),
    "fifty_ads":               lambda: _file_contains("backend/scale_run.py", r"50|num_ads"),
    "scale_run_script":        lambda: _file_exists("backend", "scale_run.py"),
    "eval_export":             lambda: _file_contains("backend/main.py", r"/analytics/export/csv"),
    "self_healing_loop":       lambda: _file_contains("backend/pipeline.py", r"_detect_dimension_regression"),

    # Phase 5 — Frontend UI
    "campaign_dashboard":      lambda: _dir_has_files("frontend/app", "page.*"),
    "ad_library_ui":           lambda: _file_exists("frontend", "app", "ads", "page.tsx") or _file_exists("frontend", "app", "library", "page.tsx"),
    "trend_analytics":         lambda: _file_exists("frontend", "app", "analytics", "page.tsx") or _file_exists("frontend", "app", "trends", "page.tsx"),
    "survey_page":             lambda: _file_exists("frontend", "app", "survey", "page.tsx"),
    "insights_page":           lambda: _file_exists("frontend", "app", "insights", "page.tsx"),
    "campaign_detail_page":    lambda: _file_exists("frontend", "app", "campaigns", "[id]", "page.tsx"),
    "nav_bar":                 lambda: _file_contains("frontend/app/layout.tsx", r"nav|Nav"),
    "dark_light_theme":        lambda: _file_contains("frontend/app/layout.tsx", r"theme|dark"),
    "frontend_connected":      lambda: _file_contains("frontend/app/page.tsx", r"fetch|API_URL|api"),

    # Phase 6 — Documentation
    "decision_log":            lambda: _file_exists("docs", "decisions.md") or _file_exists("docs", "decision_log.md"),
    "live_roadmap":            lambda: _file_exists("docs", "progress.json"),
    "readme":                  lambda: _file_exists("README.md") and _file_contains("README.md", r"make|setup|install"),
    "tests":                   lambda: _dir_has_files("backend/tests", "test_*.py", min_count=3),
    "makefile_setup":          lambda: _file_exists("Makefile"),
}


def sync(apply: bool = False) -> dict:
    """Scan codebase and return {newly_completed: [...], already: [...]}."""
    if PROGRESS_FILE.exists():
        state = json.loads(PROGRESS_FILE.read_text())
    else:
        state = {"completed": {}, "last_updated": None}

    completed = state.setdefault("completed", {})
    newly = []
    already = list(completed.keys())

    for step_id, check in RULES.items():
        if step_id in completed:
            continue
        try:
            if check():
                now = datetime.now(timezone.utc).isoformat()
                completed[step_id] = now
                newly.append(step_id)
        except Exception as e:
            print(f"⚠️  Rule '{step_id}' failed: {e}", file=sys.stderr)

    if newly and apply:
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PROGRESS_FILE.write_text(json.dumps(state, indent=2) + "\n")

    return {"newly_completed": newly, "already_complete": len(already), "total_rules": len(RULES)}


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    result = sync(apply=apply)

    print(f"\n📊 Roadmap Sync {'(applied)' if apply else '(dry-run)'}")
    print(f"   Rules checked:    {result['total_rules']}")
    print(f"   Already complete: {result['already_complete']}")
    print(f"   Newly detected:   {len(result['newly_completed'])}")

    if result["newly_completed"]:
        for s in result["newly_completed"]:
            print(f"   ✅ {s}")
    else:
        print("   (no new completions)")

    if not apply and result["newly_completed"]:
        print("\n   Run with --apply to write changes to progress.json")
