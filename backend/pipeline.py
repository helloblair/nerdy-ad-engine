"""
pipeline.py
-----------
The LangGraph pipeline that wires all four agents together.

Graph flow:
  researcher → writer → evaluator → decision gate
                  ↑                      ↓
                fixer ←── score < 7.0 ───┘
                                         ↓
                          score ≥ 7.0 → save to Supabase
"""

import json
import os
import time
from typing import TypedDict, Optional
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END

from db import get_db
from writer_agent import WriterAgent, WriterInput, CampaignBrief, GeneratedAd
from evaluator_agent import EvaluatorAgent, AdContent, EvaluationResult
from fixer_agent import FixerAgent, EvalSummary, FixerOutput
from researcher_agent import ResearcherAgent

load_dotenv()

# ─── Pipeline State ───────────────────────────────────────────────────────────

class AdState(TypedDict):
    campaign_id: str
    brief: dict
    iteration: int
    max_iterations: int
    generated_ad: Optional[dict]
    evaluation: Optional[dict]
    fix: Optional[dict]
    approved: bool
    escalated: bool
    final_ad_id: Optional[str]
    all_evaluations: list
    research_context: Optional[str]

# ─── Clients ─────────────────────────────────────────────────────────────────

writer = WriterAgent()
evaluator = EvaluatorAgent()
fixer = FixerAgent()
researcher = ResearcherAgent()

# ─── Nodes ────────────────────────────────────────────────────────────────────

def write_node(state: AdState) -> AdState:
    iteration = state.get("iteration", 1)
    fix = state.get("fix")
    print(f"\n✍️  WriterAgent — iteration {iteration}")
    writer_input = WriterInput(
        brief=CampaignBrief(**state["brief"]),
        fixer_feedback=fix["targeted_instruction"] if fix and not fix.get("escalate") else None,
        weakest_dimension=fix["dimension_to_fix"] if fix else None,
        research_context=state.get("research_context"),
        iteration=iteration,
    )
    raw_seed = os.getenv("WRITER_SEED")
    seed = int(raw_seed) if raw_seed and raw_seed.lower() != "none" else None
    ad = writer.generate(writer_input, seed=seed)
    writer.print_ad(ad, iteration=iteration)
    return {**state, "generated_ad": ad.model_dump(), "iteration": iteration}

def evaluate_node(state: AdState) -> AdState:
    iteration = state["iteration"]
    print(f"\n🔍 EvaluatorAgent — iteration {iteration}")
    ad_content = AdContent(
        primary_text=state["generated_ad"]["primary_text"],
        headline=state["generated_ad"]["headline"],
        description=state["generated_ad"].get("description", ""),
        cta_button=state["generated_ad"]["cta_button"],
        audience=state["brief"]["audience"],
        product=state["brief"]["product"],
        goal=state["brief"]["goal"],
    )
    result = evaluator.evaluate(ad_content)
    evaluator.print_result(ad_content, result)
    all_evals = state.get("all_evaluations", [])
    all_evals.append({
        "iteration": iteration,
        "aggregate_score": result.aggregate_score,
        "clarity": result.clarity.score,
        "value_proposition": result.value_proposition.score,
        "cta_strength": result.cta_strength.score,
        "brand_voice": result.brand_voice.score,
        "emotional_resonance": result.emotional_resonance.score,
        "meets_threshold": result.meets_threshold,
        "weakest_dimension": result.weakest_dimension,
    })
    return {**state, "evaluation": result.model_dump(), "all_evaluations": all_evals}

def _detect_dimension_regression(state: AdState) -> str | None:
    """Check if the weakest dimension failed to improve after the last fix attempt.

    Compares the current evaluation's weakest dimension score against the
    same dimension in the previous evaluation.  Returns an adaptation note
    when the score did not improve, or None when it did.
    """
    all_evals = state.get("all_evaluations", [])
    if len(all_evals) < 2:
        return None

    current = all_evals[-1]
    previous = all_evals[-2]
    dimension = current.get("weakest_dimension", "")

    # Map evaluator dimension names to all_evaluations keys
    dim_key = dimension if dimension != "cta_strength" else "cta_strength"
    current_score = current.get(dim_key, 0)
    previous_score = previous.get(dim_key, 0)

    if current_score <= previous_score:
        print(
            f"⚠️  Self-heal attempt {len(all_evals) - 1} did not improve "
            f"{dimension} — trying different strategy"
        )
        return (
            f"Previous fix attempt did not improve {dimension} "
            f"(was {previous_score:.1f}, now {current_score:.1f}). "
            f"Try a completely different approach."
        )
    return None

def fix_node(state: AdState) -> AdState:
    iteration = state["iteration"]
    print(f"\n🔧 FixerAgent — iteration {iteration}")
    eval_data = state["evaluation"]

    improvement_suggestion = eval_data["improvement_suggestion"]
    adaptation_note = _detect_dimension_regression(state)
    if adaptation_note:
        improvement_suggestion = f"{adaptation_note} {improvement_suggestion}"

    eval_summary = EvalSummary(
        clarity=eval_data["clarity"]["score"],
        value_proposition=eval_data["value_proposition"]["score"],
        cta_strength=eval_data["cta_strength"]["score"],
        brand_voice=eval_data["brand_voice"]["score"],
        emotional_resonance=eval_data["emotional_resonance"]["score"],
        aggregate_score=eval_data["aggregate_score"],
        weakest_dimension=eval_data["weakest_dimension"],
        improvement_suggestion=improvement_suggestion,
        iteration=iteration,
    )
    fix = fixer.generate_fix(eval_summary)
    fixer.print_fix(fix)
    return {**state, "fix": fix.model_dump(), "iteration": iteration + 1, "escalated": fix.escalate}

def _db_save_with_retry(operation, description: str, max_attempts: int = 3):
    """Execute a DB operation with retry logic for transient failures."""
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as e:
            if attempt < max_attempts:
                print(f"⚠️  {description} attempt {attempt} failed, retrying... ({e})")
                time.sleep(1)
            else:
                raise

def save_node(state: AdState) -> AdState:
    db = get_db()
    print(f"\n💾 Saving approved ad...")
    try:
        ad_result = _db_save_with_retry(
            lambda: db.insert_ad({
                "campaign_id": state["campaign_id"],
                "primary_text": state["generated_ad"]["primary_text"],
                "headline": state["generated_ad"]["headline"],
                "description": state["generated_ad"].get("description", ""),
                "cta_button": state["generated_ad"]["cta_button"],
                "iteration_number": state["iteration"],
                "status": "approved",
            }),
            "Supabase save (ad)",
        )
        ad_id = ad_result["id"]
        _db_save_with_retry(
            lambda: db.insert_evaluation({
                "ad_id": ad_id,
                "clarity": state["evaluation"]["clarity"]["score"],
                "value_proposition": state["evaluation"]["value_proposition"]["score"],
                "cta_score": state["evaluation"]["cta_strength"]["score"],
                "brand_voice": state["evaluation"]["brand_voice"]["score"],
                "emotional_resonance": state["evaluation"]["emotional_resonance"]["score"],
                "aggregate_score": state["evaluation"]["aggregate_score"],
                "clarity_rationale": state["evaluation"]["clarity"]["rationale"],
                "value_proposition_rationale": state["evaluation"]["value_proposition"]["rationale"],
                "cta_rationale": state["evaluation"]["cta_strength"]["rationale"],
                "brand_voice_rationale": state["evaluation"]["brand_voice"]["rationale"],
                "emotional_resonance_rationale": state["evaluation"]["emotional_resonance"]["rationale"],
                "clarity_confidence": state["evaluation"]["clarity"]["confidence"],
                "value_proposition_confidence": state["evaluation"]["value_proposition"]["confidence"],
                "cta_confidence": state["evaluation"]["cta_strength"]["confidence"],
                "brand_voice_confidence": state["evaluation"]["brand_voice"]["confidence"],
                "emotional_resonance_confidence": state["evaluation"]["emotional_resonance"]["confidence"],
                "meets_threshold": state["evaluation"]["meets_threshold"],
                "needs_human_review": state["evaluation"]["needs_human_review"],
            }),
            "Supabase save (evaluation)",
        )
        print(f"✅ Saved — ad_id: {ad_id}")
        return {**state, "approved": True, "final_ad_id": ad_id}
    except Exception as e:
        print(f"❌ Save failed after retries: {e}")
        return {**state, "approved": True, "final_ad_id": None}

def flag_node(state: AdState) -> AdState:
    db = get_db()
    print(f"\n⚠️  Flagging ad for human review...")
    try:
        ad_result = _db_save_with_retry(
            lambda: db.insert_ad({
                "campaign_id": state["campaign_id"],
                "primary_text": state["generated_ad"]["primary_text"],
                "headline": state["generated_ad"]["headline"],
                "description": state["generated_ad"].get("description", ""),
                "cta_button": state["generated_ad"]["cta_button"],
                "iteration_number": state["iteration"],
                "status": "flagged",
            }),
            "Supabase save (flagged ad)",
        )
        ad_id = ad_result["id"]
        print(f"⚠️  Flagged — ad_id: {ad_id}")
        return {**state, "approved": False, "final_ad_id": ad_id}
    except Exception as e:
        print(f"❌ Flag failed after retries: {e}")
        return {**state, "approved": False, "final_ad_id": None}

# ─── Routing ──────────────────────────────────────────────────────────────────

def should_fix_or_approve(state: AdState) -> str:
    eval_data = state["evaluation"]
    iteration = state["iteration"]
    max_iter = state.get("max_iterations", 3)
    if eval_data["meets_threshold"]:
        print(f"\n✅ Score {eval_data['aggregate_score']:.1f} ≥ 7.0 — APPROVED!")
        return "approve"
    if iteration >= max_iter:
        print(f"\n⚠️  Iteration {iteration} = max {max_iter} — ESCALATING")
        return "escalate"
    print(f"\n🔄 Score {eval_data['aggregate_score']:.1f} < 7.0 — fixing iteration {iteration + 1}")
    return "fix"

# ─── Graph ────────────────────────────────────────────────────────────────────

def build_pipeline():
    graph = StateGraph(AdState)
    graph.add_node("write", write_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("fix", fix_node)
    graph.add_node("save", save_node)
    graph.add_node("flag", flag_node)
    graph.set_entry_point("write")
    graph.add_edge("write", "evaluate")
    graph.add_edge("fix", "write")
    graph.add_edge("save", END)
    graph.add_edge("flag", END)
    graph.add_conditional_edges(
        "evaluate",
        should_fix_or_approve,
        {"approve": "save", "fix": "fix", "escalate": "flag"}
    )
    return graph.compile()

def run_pipeline(campaign_id: str, brief: CampaignBrief) -> AdState:
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
    return pipeline.invoke(initial_state)

# ─── Smoke Test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from progress_tracker import mark_complete

    print("🧪 PIPELINE SMOKE TEST")
    print("Running full generate → evaluate → fix → save loop...\n")

    db = get_db()
    try:
        campaign = db.insert_campaign({
            "name": "Pipeline Smoke Test",
            "audience": "parents of high school juniors preparing for SAT",
            "product": "1-on-1 SAT tutoring",
            "goal": "conversion",
            "tone": "urgent, empathetic, outcome-focused",
            "status": "running",
        })
        campaign_id = campaign["id"]
        print(f"✅ Created test campaign: {campaign_id}\n")
    except Exception as e:
        print(f"❌ Failed to create campaign: {e}")
        exit(1)

    brief = CampaignBrief(
        audience="parents of high school juniors preparing for SAT",
        product="1-on-1 SAT tutoring",
        goal="conversion",
        tone="urgent, empathetic, outcome-focused",
        key_benefit="personalized learning matched to your child's gaps",
        proof_point="students improve an average of 360 points in 8 weeks"
    )

    final_state = run_pipeline(campaign_id, brief)

    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print(f"  Approved:      {final_state['approved']}")
    print(f"  Escalated:     {final_state['escalated']}")
    print(f"  Iterations:    {final_state['iteration']}")
    print(f"  Final ad ID:   {final_state['final_ad_id']}")
    print(f"  Score history: {[e['aggregate_score'] for e in final_state['all_evaluations']]}")
    print("="*60)

    db.update_campaign_status(campaign_id, "completed")
    assert final_state["final_ad_id"] is not None, "No ad ID — save failed"

    mark_complete("langgraph_wired")
    mark_complete("max_iterations_guard")
    print("\n✅ PIPELINE SMOKE TEST PASSED!")
