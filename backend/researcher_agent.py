"""
researcher_agent.py
-------------------
The ResearcherAgent reads the reference ads library and extracts creative
patterns to pass to the WriterAgent as context.

Without it: WriterAgent generates from brief alone.
With it:    WriterAgent knows "use math as urgency, tension reframes with
            two specific numbers, zero adjectives" — patterns from the actual
            highest-performing Nerdy creatives.

This runs once per campaign (not per iteration) since the reference patterns
don't change. Results are cached in the campaign brief as ResearchContext.
"""

import os
import json
from typing import Optional
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ─── Data Models ─────────────────────────────────────────────────────────────

class ReferencePattern(BaseModel):
    pattern_name: str
    description: str
    example: str
    strength: str          # "high" | "medium"

class ResearchContext(BaseModel):
    """
    Distilled creative intelligence from reference ads.
    Passed into WriterAgent to ground generation in real brand patterns.
    """
    top_patterns: list[ReferencePattern]
    hook_types: list[str]
    proof_points_available: list[str]
    avoid: list[str]
    winning_example: str   # Best headline from reference set


# ─── Researcher Agent ─────────────────────────────────────────────────────────

class ResearcherAgent:
    """
    Reads reference_ads/varsity_tutors.json and extracts creative patterns.

    This is intentionally NOT an LLM call — the patterns are already
    documented in the JSON with quality scores and rationale. Parsing them
    directly is faster, cheaper, and more reliable than asking an LLM to
    re-derive them every run.

    This is a deliberate architectural choice: use LLMs where judgment is
    needed (writing, evaluating, fixing), use deterministic code where
    the answer is already known (pattern extraction from documented data).
    """

    def __init__(self, reference_path: Optional[str] = None):
        if reference_path:
            self.reference_path = Path(reference_path)
        else:
            # Walk up from backend/ to find reference_ads/
            base = Path(__file__).parent.parent
            self.reference_path = base / "reference_ads" / "varsity_tutors.json"

    def load_reference_ads(self) -> dict:
        """Load and parse the reference ads JSON."""
        if not self.reference_path.exists():
            raise FileNotFoundError(
                f"Reference ads not found at {self.reference_path}. "
                "Run: cp ~/Downloads/varsity_tutors.json ~/nerdy-ad-engine/reference_ads/"
            )
        with open(self.reference_path) as f:
            return json.load(f)

    def extract_context(self) -> ResearchContext:
        """
        Extract creative patterns from reference ads.
        Returns a ResearchContext ready to inject into WriterAgent prompts.
        """
        data = self.load_reference_ads()
        ads = data.get("ads", [])
        key_patterns = data.get("key_patterns_for_writer_agent", [])

        # Build pattern objects from the documented ads
        patterns = []
        hook_types = []
        proof_points = []

        for ad in ads:
            hook_types.append(ad.get("hook_type", ""))

            # Extract proof points from notes
            if "360 points" in ad.get("notes", ""):
                proof_points.append("students improve an average of 360 points in 8 weeks")
            if "93%" in ad.get("notes", ""):
                proof_points.append("93% of students improve at least one letter grade")
            if "1170 to 1410" in ad.get("notes", ""):
                proof_points.append("score improvement from 1170 to 1410 (real student result)")

            # Build pattern from brand_voice_patterns
            for bp in ad.get("brand_voice_patterns", []):
                patterns.append(ReferencePattern(
                    pattern_name=bp,
                    description=ad.get("notes", ""),
                    example=ad.get("primary_text", ad.get("headline", "")),
                    strength="high" if ad.get("quality_score", 0) >= 9.0 else "medium"
                ))

        # Deduplicate hook types
        hook_types = list(set(h for h in hook_types if h))

        # Best headline from highest scoring ad
        best_ad = max(ads, key=lambda a: a.get("quality_score", 0))
        winning_example = best_ad.get("primary_text", best_ad.get("headline", ""))

        return ResearchContext(
            top_patterns=patterns[:8],   # Top 8 to keep prompt lean
            hook_types=hook_types,
            proof_points_available=list(set(proof_points)),
            avoid=[
                "vague adjectives (e.g. 'amazing', 'great', 'incredible')",
                "corporate language (e.g. 'leverage', 'holistic', 'solutions')",
                "passive voice",
                "generic CTAs without specificity",
                "claims without numbers",
            ],
            winning_example=winning_example,
        )

    def format_for_prompt(self, context: ResearchContext) -> str:
        """
        Format ResearchContext as a string block to inject into WriterAgent's prompt.
        Kept concise — LLMs perform better with dense signal than long prose.
        """
        patterns_str = "\n".join(
            f"  - [{p.strength.upper()}] {p.pattern_name}"
            for p in context.top_patterns[:6]
        )
        hooks_str = ", ".join(context.hook_types)
        proofs_str = "\n".join(f"  - {p}" for p in context.proof_points_available)
        avoid_str = "\n".join(f"  - {a}" for a in context.avoid)

        return f"""REFERENCE AD INTELLIGENCE (from highest-performing Nerdy creatives):

Winning creative patterns:
{patterns_str}

Proven hook types: {hooks_str}

Available proof points:
{proofs_str}

NEVER use:
{avoid_str}

Best performing example: "{context.winning_example}"
"""

    def print_context(self, context: ResearchContext):
        print(f"\n{'='*60}")
        print("RESEARCH CONTEXT")
        print(f"{'='*60}")
        print(f"  Patterns extracted: {len(context.top_patterns)}")
        print(f"  Hook types:         {', '.join(context.hook_types)}")
        print(f"  Proof points:       {len(context.proof_points_available)}")
        print(f"  Winning example:    {context.winning_example[:80]}...")
        print(f"{'='*60}\n")


# ─── Smoke Test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from progress_tracker import mark_complete

    print("🧪 SMOKE TEST — ResearcherAgent")

    researcher = ResearcherAgent()

    print("\nExtracting patterns from reference ads...")
    context = researcher.extract_context()
    researcher.print_context(context)

    print("Formatted prompt injection:\n")
    print(researcher.format_for_prompt(context))

    assert len(context.top_patterns) > 0, "No patterns extracted"
    assert len(context.hook_types) > 0, "No hook types found"
    assert len(context.proof_points_available) > 0, "No proof points found"
    assert len(context.winning_example) > 10, "Winning example too short"

    print("✅ SMOKE TEST PASSED — ResearcherAgent extracting patterns correctly!")
    mark_complete("researcher_agent_built")
