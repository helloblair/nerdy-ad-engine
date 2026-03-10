"""
writer_agent.py
---------------
WriterAgent generates Facebook/Instagram ad copy using Gemini 2.5 Flash.
"""

import os
import json
import re
from typing import Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class CampaignBrief(BaseModel):
    audience: str
    product: str
    goal: str
    tone: Optional[str] = "warm, urgent, outcome-focused"
    key_benefit: Optional[str] = None
    proof_point: Optional[str] = None

class WriterInput(BaseModel):
    brief: CampaignBrief
    fixer_feedback: Optional[str] = None
    weakest_dimension: Optional[str] = None
    iteration: int = 1
    research_context: Optional[str] = None

class GeneratedAd(BaseModel):
    primary_text: str
    headline: str
    description: str
    cta_button: str
    writer_notes: Optional[str] = None

class WriterAgent:

    SYSTEM_PROMPT = """You are an expert copywriter for Varsity Tutors Facebook/Instagram ads.
RULES: Lead with specific outcomes and numbers. Address parent pain directly.
Never use corporate language. CTAs must be specific.
IMPORTANT: Respond with raw JSON only. No markdown. No backticks. No explanation."""

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    def _build_prompt(self, input: WriterInput) -> str:
        brief = input.brief
        prompt = f"""Write a Facebook ad for Varsity Tutors.
Audience: {brief.audience}
Product: {brief.product}
Goal: {brief.goal}
Tone: {brief.tone}"""
        if brief.key_benefit:
            prompt += f"\nKey Benefit: {brief.key_benefit}"
        if brief.proof_point:
            prompt += f"\nProof Point: {brief.proof_point}"
        if input.research_context:
            prompt += f"\n\n{input.research_context}"

        if input.fixer_feedback:
            prompt += f"\nREVISION #{input.iteration} — Fix this: {input.fixer_feedback}"
        prompt += """

Return ONLY a raw JSON object, no markdown, no backticks:
{"primary_text":"2-4 sentences","headline":"max 7 words","description":"one line","cta_button":"Book a Free Session","writer_notes":"brief note"}"""
        return prompt

    def generate(self, input: WriterInput) -> GeneratedAd:
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=self._build_prompt(input),
                    config=types.GenerateContentConfig(
                        system_instruction=self.SYSTEM_PROMPT,
                        temperature=0.8,
                        max_output_tokens=2048,
                    )
                )
                raw = response.text.strip()
                # Extract JSON between first { and last }
                start = raw.find('{')
                end = raw.rfind('}')
                if start != -1 and end != -1:
                    raw = raw[start:end+1]
                data = json.loads(raw)
                return GeneratedAd(
                    primary_text=data["primary_text"],
                    headline=data["headline"],
                    description=data["description"],
                    cta_button=data["cta_button"],
                    writer_notes=data.get("writer_notes"),
                )
            except (json.JSONDecodeError, KeyError) as e:
                if attempt == 2:
                    raise ValueError(f"WriterAgent failed after 3 attempts: {e}\nRaw: {raw}")
                print(f"⚠️  Writer attempt {attempt + 1} failed, retrying... ({e})")

    def print_ad(self, ad: GeneratedAd, iteration: int = 1):
        print(f"\n{'='*60}")
        print(f"GENERATED AD (iteration {iteration})")
        print(f"{'='*60}")
        print(f"  Primary Text: {ad.primary_text}")
        print(f"  Headline:     {ad.headline}")
        print(f"  Description:  {ad.description}")
        print(f"  CTA:          [{ad.cta_button}]")
        if ad.writer_notes:
            print(f"  Notes:        {ad.writer_notes}")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    from progress_tracker import mark_complete
    writer = WriterAgent()

    sat_brief = WriterInput(
        brief=CampaignBrief(
            audience="parents of high school juniors preparing for the SAT",
            product="1-on-1 SAT tutoring",
            goal="conversion",
            tone="urgent, empathetic, outcome-focused",
            key_benefit="personalized learning matched to your child's gaps",
            proof_point="students improve an average of 360 points in 8 weeks"
        ), iteration=1
    )
    math_brief = WriterInput(
        brief=CampaignBrief(
            audience="parents of middle school students struggling with math",
            product="1-on-1 math tutoring",
            goal="awareness",
            tone="warm, reassuring, reframe-focused",
            key_benefit="tutors who explain math the way your child's brain works",
            proof_point="93% of students improve at least one letter grade"
        ), iteration=1
    )

    print("🧪 SMOKE TEST — WriterAgent")
    print("\nGenerating SAT campaign ad...")
    sat_ad = writer.generate(sat_brief)
    writer.print_ad(sat_ad)

    print("Generating math awareness ad...")
    math_ad = writer.generate(math_brief)
    writer.print_ad(math_ad)

    assert len(sat_ad.primary_text) > 50
    assert sat_ad.cta_button
    assert len(math_ad.primary_text) > 50
    print("✅ SMOKE TEST PASSED — WriterAgent is generating valid ad copy!")
    mark_complete("writer_agent_built")
