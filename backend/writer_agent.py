"""
writer_agent.py
---------------
WriterAgent generates Facebook/Instagram ad copy using Gemini 2.5 Flash.
Integrated with Nerdy SAT messaging guidance, persona targeting, and competitive positioning.
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

# Valid personas from Nerdy's SAT messaging guidance
VALID_PERSONAS = [
    "athlete_recruit",        # Mom of 11th-grade athlete, SAT as scholarship gatekeeper
    "suburban_optimizer",     # Upper-middle-class mom, 3.8 GPA but mid-1200s SAT
    "scholarship_family",     # SAT = tuition discount lever
    "khan_academy_failure",   # Tried free resources, score didn't move
    "online_skeptic",         # Needs the "SAT is digital now" reframe
    "bad_score_urgency",      # Just got a disappointing score, emotional spike
    "immigrant_navigator",    # First-gen, unfamiliar with US college system
    "neurodivergent_advocate",# ADHD/dyslexia/processing differences, needs right fit
    "test_anxiety",           # Knows material but freezes on test day
    "accountability_seeker",  # "I can't make my kid study"
    "school_failed_them",     # School's SAT prep was useless
    "education_investor",     # Already tried everything, wants one system that works
    "burned_returner",        # Bad prior tutoring experience, trust deficit
    "parent_relationship",    # SAT causing family tension
    "sibling_second_child",   # Learned from first child's experience
    "general",                # No specific persona targeting
]

class CampaignBrief(BaseModel):
    audience: str
    product: str
    goal: str
    tone: Optional[str] = "warm, urgent, outcome-focused"
    key_benefit: Optional[str] = None
    proof_point: Optional[str] = None
    persona: Optional[str] = "general"  # One of VALID_PERSONAS

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
    variant_approach: Optional[str] = None

class WriterAgent:

    SYSTEM_PROMPT = """You are an expert copywriter for Varsity Tutors (a Nerdy company) Facebook/Instagram ads.
You write ads that sound like a real parent talking to another parent — never like a marketing team.

═══ MESSAGING DO'S ═══
- Say "your child" — NEVER "your student" (parents think of them as children, not students)
- Say "SAT tutoring" — NEVER "SAT prep"
- Use avg/typical score gains with CONDITIONS: "100 points/month at 2 sessions/week + 20 min/day practice"
- Show MECHANISM, not just claims: explain HOW (e.g. "the digital SAT has built-in calculator + formulas that 60% of students don't know exist — our tutors teach your child to use them")
- Make claims credible with specifics: "16 sessions → 200 points" or "if your SAT is between 1100-1300, you can gain 200 points in 8 weeks"
- Use real competitive comparisons: "Our students improve 10x more than self-study and 2.6x more than Princeton Review, Kaplan, Sylvan, or Kumon"
- Tie SAT points to dollars: "Every 100 points can mean $10,000-$40,000 in scholarships"
- Lead with the hook — first line stops the scroll or you've lost them
- Hook patterns that work: question hooks, stat hooks, story hooks, GPA-vs-SAT mismatch hooks

═══ MESSAGING DON'TS ═══
- NEVER use corporate language: "unlock potential", "maximize score potential", "tailored support", "custom strategies", "growth areas", "concrete score gains", "dream college within reach"
- NEVER use fake scarcity: "spots filling fast", "limited enrollment", "secure their spot", "don't miss out"
- NEVER be vague: "personalized/expert/data-driven" is telling not showing
- NEVER promise "200 points" without conditions — it's impossible for anyone over 1400 and stretches believability above 1350
- NEVER say "SAT prep" — say "SAT tutoring"
- NEVER market as "online tutoring" without reframing why online is BETTER

═══ COMPETITIVE POSITIONING ═══
- vs. Khan Academy/self-study: "Free SAT resources are great… until you get your score back. Our students improve 10x more."
- vs. Princeton Review/Kaplan: "They charge $1,500-$2,500 for group classes + $199-$252/hr for 1:1. We include 1:1 sessions starting at $349/month."
- vs. local tutors/Sylvan/Kumon: "A person in a room with no platform, no diagnostics, no plan. Our students improve 2.6x more."
- The online reframe: "The SAT is digital now. Training on paper is the real risk. You wouldn't practice football on a baseball field."

═══ WHAT WE ACTUALLY OFFER ═══
- Monthly SAT tutoring membership ($349-$1,099/mo), not a course or class
- 1:1 expert tutors vetted for the Digital SAT specifically
- Full diagnostic → personalized study plan → weekly progress reports
- 6 full-length practice tests, 20,000+ practice questions
- Training on the actual Digital SAT interface (built-in tools, calculator, formulas)
- College essay support after scores are in
- Cancel anytime, flexible rescheduling, 24/7 instant tutors

═══ AD STRUCTURE ═══
- Primary text: 2-4 sentences. First line is the hook — this is what stops the scroll.
- Headline: 5-8 words max. Benefit-driven, punchy.
- Description: One line of reinforcement. Don't rely on it (often truncated on mobile).
- CTA button: Match the funnel. "Book a Free Session" or "Get a Free Diagnostic" for conversion. "See What Score Is Realistic" for awareness. NEVER just "Learn More".

IMPORTANT: Respond with raw JSON only. No markdown. No backticks. No explanation."""

    # Persona-specific psychology and hook guidance injected into prompts
    PERSONA_CONTEXT = {
        "athlete_recruit": """PERSONA: Athlete-Recruit Gatekeeper
PSYCHOLOGY: Mom of 11th-grade recruited athlete. SAT is the gating factor for scholarships/NCAA eligibility. Late funnel, urgency-driven. Fear: SAT kills the scholarship window while recruiting is still open.
HOOK STYLE: "The coach wants him. The admissions office needs an SAT score." / "Recruiting windows don't care about SAT score excuses."
KEY ANGLE: Fit tutoring around intense practice schedule. Late evening availability. Fast start (first session within 48 hours). Targeted 1:1 on specific gaps.""",

        "suburban_optimizer": """PERSONA: Proactive Suburban Optimizer
PSYCHOLOGY: Upper-middle-class mom, 11th grader with 3.8+ GPA but mid-1200s SAT. Not panicked but motivated by a clear gap. Mid-funnel, comparison shopping.
HOOK STYLE: "3.8 GPA. 1260 SAT. Something's off." / "If she's capable of a 1450, why is she stuck in the 1200s?"
KEY ANGLE: Specificity over hype. Clear plan: diagnostic → gap analysis → 30-40 hours over 8-10 weeks → 1400+. Social proof from similar high-performing districts.""",

        "scholarship_family": """PERSONA: Scholarship/Financial Family
PSYCHOLOGY: SAT = money lever. Every point has a dollar value. College cost is the primary concern.
HOOK STYLE: "A 100-point SAT increase can mean $10,000-$40,000 in scholarships." / "Every SAT point has a dollar value."
KEY ANGLE: Frame SAT tutoring as an investment with measurable ROI. Compare tutoring cost to potential scholarship dollars.""",

        "khan_academy_failure": """PERSONA: Khan Academy / Self-Study Failure
PSYCHOLOGY: Tried free resources, score barely moved. Frustrated. Needs validation that it's not their child's fault + a clear alternative.
HOOK STYLE: "Khan Academy raised her score 10 points. That was the problem." / "Free SAT resources are great… until you get your score back."
KEY ANGLE: Why self-study fails (no accountability, no diagnosis, no one explaining WHY they're getting questions wrong). 1:1 as the fix.""",

        "online_skeptic": """PERSONA: Online Skeptic
PSYCHOLOGY: Believes in-person is better. Needs the reframe that digital SAT = digital training.
HOOK STYLE: "The SAT is digital now. Why prep on paper?" / "You wouldn't practice football on a baseball field."
KEY ANGLE: The SAT is taken on a laptop. Training should mirror the test environment. Online isn't a Zoom class — it's one tutor focused entirely on your child.""",

        "bad_score_urgency": """PERSONA: Bad Score Just Hit
PSYCHOLOGY: Emotional spike. Just got a disappointing score. Need immediate action.
HOOK STYLE: "Not the score you expected?" / "She got the exact same score again. Now what?" / "1250 isn't going to cut it."
KEY ANGLE: Urgency + clear path forward. What's still possible in the remaining weeks. Talk to a specialist today.""",

        "immigrant_navigator": """PERSONA: Immigrant Family Navigator
PSYCHOLOGY: First-gen, unfamiliar with US college/SAT system. Overwhelmed. Fear of making the wrong choice. Values credentials and structured guidance.
HOOK STYLE: "The SAT process is confusing. We walk you through all of it." / "Your child deserves the same shot as kids whose parents grew up with this system."
KEY ANGLE: Step-by-step guidance. Explain the SAT clearly. Credibility first (tutor qualifications, success stories). Patient, respectful tone.""",

        "neurodivergent_advocate": """PERSONA: Neurodivergent Advocate
PSYCHOLOGY: Mom of student with ADHD/dyslexia/processing differences. Protective. Needs a tutor who understands her child, not just the SAT. Fear of wrong fit damaging confidence.
HOOK STYLE: "Standard SAT tutoring doesn't work for every kid. We know that." / "ADHD doesn't mean they can't score high. It means they need the right tutor."
KEY ANGLE: Right-fit matching. Extended time awareness. Structured, predictable sessions. Easy tutor switching. Confidence-building before content.""",

        "test_anxiety": """PERSONA: Test Anxiety
PSYCHOLOGY: Knows the material, freezes on test day. Identity: "I'm just not a good test taker." Needs confidence + familiarity.
HOOK STYLE: "She knows the material. She freezes on the test." / "'I'm just not a good test taker' — that's fixable."
KEY ANGLE: By test day, nothing on the screen is unfamiliar. 6 full-length practice tests. Desensitization through repetition. It's preparation, not intelligence.""",

        "accountability_seeker": """PERSONA: Accountability Seeker
PSYCHOLOGY: Parental exhaustion. Can't make their teenager study. Needs external authority.
HOOK STYLE: "Tired of being the homework police?" / "A 16-year-old won't listen to Mom. They'll listen to their tutor."
KEY ANGLE: Weekly progress reports. Tutor as accountability partner. Study plan with assigned daily work. Parent gets visibility without being the enforcer.""",

        "school_failed_them": """PERSONA: School Failed Them
PSYCHOLOGY: Frustrated that school's SAT class was just videos/books. Betrayal.
HOOK STYLE: "Their school gave them a book. That's not SAT tutoring." / "If the school's SAT program was working, you wouldn't be here."
KEY ANGLE: Real tutoring vs. school's token effort. 1:1 instruction. Actual diagnostic and targeted plan.""",

        "education_investor": """PERSONA: Education-First Cultural Investor
PSYCHOLOGY: Already invested in multiple resources (books, apps, tutors). Process-oriented. Wants to consolidate into one system. Often STEM parents.
HOOK STYLE: "Already tried Khan Academy, prep books, and a tutor — and the score hasn't moved?" / "You don't need more tools. You need one plan that ties everything together."
KEY ANGLE: Replace 5 tools with 1 system. Build on existing foundation. Show the methodology behind each session.""",

        "burned_returner": """PERSONA: Burned Returner
PSYCHOLOGY: Bad prior tutoring experience. Trust deficit. Conditional willingness. Needs accountability and proof things will be different.
HOOK STYLE: "Tutoring didn't work last time? That's why you're here." / "Wasted $100/hr on a tutor who didn't move the needle? You're not alone."
KEY ANGLE: Acknowledge what went wrong. Transparent matching process. Quality check after first session. Easy tutor switching. "We match, we measure, and if it's not working we change course."
""",

        "parent_relationship": """PERSONA: Parent-Child Relationship
PSYCHOLOGY: SAT causing family tension. Parent can't help anymore without fighting.
HOOK STYLE: "She doesn't want your help with math anymore. That's normal." / "The SAT shouldn't be the thing you fight about at dinner."
KEY ANGLE: Tutor as neutral expert. Preserve the parent-child relationship. Let someone else be the authority on studying.""",

        "sibling_second_child": """PERSONA: Sibling / Second Child
PSYCHOLOGY: Learned from first child. Knows free resources don't cut it. Different child needs different plan.
HOOK STYLE: "Her older sister didn't prep. It cost her. Don't let it happen twice." / "Second child taking the SAT? You already know free resources don't cut it."
KEY ANGLE: Different child, different plan. Leverage what you learned. Start earlier this time.""",

        "general": "",  # No persona-specific context
    }

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    def _build_prompt(self, input: WriterInput) -> str:
        brief = input.brief
        prompt = f"""Write a Facebook/Instagram ad for Varsity Tutors.
Audience: {brief.audience}
Product: {brief.product}
Goal: {brief.goal}
Tone: {brief.tone}"""
        if brief.key_benefit:
            prompt += f"\nKey Benefit: {brief.key_benefit}"
        if brief.proof_point:
            prompt += f"\nProof Point: {brief.proof_point}"

        # Inject persona-specific psychology and hook guidance
        persona = brief.persona or "general"
        persona_ctx = self.PERSONA_CONTEXT.get(persona, "")
        if persona_ctx:
            prompt += f"\n\n{persona_ctx}"

        if input.research_context:
            prompt += f"\n\n{input.research_context}"

        if input.fixer_feedback:
            prompt += f"\nREVISION #{input.iteration} — Fix this: {input.fixer_feedback}"
        prompt += """

Return ONLY a raw JSON object, no markdown, no backticks:
{"primary_text":"2-4 sentences, first line MUST be a scroll-stopping hook","headline":"5-8 words max, benefit-driven","description":"one reinforcement line","cta_button":"specific action verb, NOT Learn More","writer_notes":"brief note on approach","variant_approach":"which hook/angle you chose and why"}"""
        return prompt

    def generate(self, input: WriterInput, seed: int = None) -> GeneratedAd:
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=self._build_prompt(input),
                    config=types.GenerateContentConfig(
                        system_instruction=self.SYSTEM_PROMPT,
                        temperature=0.8,
                        max_output_tokens=2048,
                        **({"seed": seed} if seed is not None else {}),
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
                    variant_approach=data.get("variant_approach"),
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
        if ad.variant_approach:
            print(f"  Approach:     {ad.variant_approach}")
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
            key_benefit="100 points/month at 2 sessions/week + 20 min/day practice",
            proof_point="our students improve 10x more than self-study and 2.6x more than group classes",
            persona="suburban_optimizer"
        ), iteration=1
    )
    math_brief = WriterInput(
        brief=CampaignBrief(
            audience="parents of middle school students struggling with math",
            product="1-on-1 math tutoring",
            goal="awareness",
            tone="warm, reassuring, reframe-focused",
            key_benefit="tutors who explain math the way your child's brain works",
            proof_point="93% of students improve at least one letter grade",
            persona="general"
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
