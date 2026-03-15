"""
image_agent.py
--------------
ImageAgent generates ad creative images using Imagen via Gemini API.
Plugs into the LangGraph pipeline between the writer and evaluator nodes.

Takes the generated ad copy + campaign brief and produces a visually
compelling ad image that complements the copy.
"""

import os
import base64
import uuid
from typing import Optional
from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class ImageInput(BaseModel):
    """Input for image generation — ad copy + brief context."""
    primary_text: str
    headline: str
    audience: str
    product: str
    goal: str
    persona: Optional[str] = "general"


class GeneratedImage(BaseModel):
    """Output from ImageAgent."""
    image_path: str           # Local filesystem path to saved image
    image_url: Optional[str] = None  # URL if uploaded to cloud storage
    prompt_used: str          # The prompt sent to Imagen
    model: str = "imagen-4.0-generate-001"


class ImageAgent:
    """
    Generates ad creative images using Imagen 3 via the Gemini API.
    
    Design decision: We use Imagen (not Gemini's native image gen) because
    Imagen produces higher-quality, more photorealistic images suited for
    ad creatives. The Gemini API client we already use for WriterAgent
    supports Imagen natively — no new dependencies needed.
    """

    # Maps personas to visual style guidance
    PERSONA_VISUAL_STYLE = {
        "athlete_recruit": "athletic teenager in a focused study moment, sports equipment subtly visible in background, warm lighting, aspirational",
        "suburban_optimizer": "bright, clean study space, motivated teenager with laptop, suburban home feel, organized and optimistic",
        "scholarship_family": "graduation cap and diploma imagery, college campus in soft focus, hopeful and aspirational, warm golden tones",
        "khan_academy_failure": "teenager looking frustrated at a screen, then transitioning to engaged 1-on-1 video call with tutor, before/after energy",
        "online_skeptic": "modern digital learning setup, teenager on laptop with engaged tutor on screen, clean tech aesthetic, professional",
        "bad_score_urgency": "calendar with test date circled, determined teenager studying, warm but urgent lighting, focused energy",
        "immigrant_navigator": "diverse family looking hopeful, educational setting, welcoming and inclusive atmosphere, warm tones",
        "neurodivergent_advocate": "patient tutor working 1-on-1 with engaged student, calm and supportive environment, soft natural lighting",
        "test_anxiety": "confident teenager walking into a testing room, calm and prepared expression, bright reassuring lighting",
        "accountability_seeker": "teenager in a productive video tutoring session, parent relaxing in background, structured and organized feel",
        "school_failed_them": "contrast between empty classroom and engaged 1-on-1 tutoring session, personal attention, warm lighting",
        "education_investor": "organized study plan on screen, professional tutoring session, data and progress charts subtly visible",
        "burned_returner": "fresh start energy, new tutor introduction moment, trust and professionalism, clean modern setting",
        "parent_relationship": "happy parent and teenager, no textbooks in sight, natural family moment, stress-free atmosphere",
        "sibling_second_child": "two siblings, older one in graduation attire, younger one studying with determination, family support",
        "general": "engaged teenager in 1-on-1 online tutoring session, bright and modern, educational but not boring",
    }

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.output_dir = os.path.join(os.path.dirname(__file__), "data", "images")
        os.makedirs(self.output_dir, exist_ok=True)

    def _build_image_prompt(self, input: ImageInput) -> str:
        """Build an Imagen prompt from ad copy + persona context."""
        visual_style = self.PERSONA_VISUAL_STYLE.get(
            input.persona or "general",
            self.PERSONA_VISUAL_STYLE["general"]
        )

        goal_style = (
            "direct response, clear call-to-action energy, conversion-focused"
            if input.goal == "conversion"
            else "brand awareness, aspirational, emotional connection"
        )

        prompt = f"""Professional Facebook/Instagram ad creative for Varsity Tutors SAT tutoring.

Visual concept: {visual_style}

Ad context: "{input.headline}" — targeting {input.audience}
Campaign goal: {goal_style}

Style requirements:
- Clean, modern, professional — NOT stock photo generic
- Warm color palette (blues, whites, warm accents) consistent with education brand
- No text overlays or words in the image (text is handled separately in the ad)
- 1:1 aspect ratio optimized for Instagram/Facebook feed
- Photorealistic, high quality, well-lit
- Emotionally resonant — should complement the ad copy's hook
- NOT clipart, NOT illustrated, NOT cartoonish"""

        return prompt

    def generate(self, input: ImageInput) -> GeneratedImage:
        """Generate an ad creative image using Imagen 3."""
        prompt = self._build_image_prompt(input)
        print(f"\n🎨 ImageAgent — generating creative for: {input.headline}")

        for attempt in range(3):
            try:
                response = self.client.models.generate_images(
                    model="imagen-4.0-generate-001",
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="1:1",
                        safety_filter_level="BLOCK_LOW_AND_ABOVE",
                    ),
                )

                if not response.generated_images:
                    raise ValueError("Imagen returned no images")

                # Save the image to local filesystem
                image_data = response.generated_images[0].image.image_bytes
                filename = f"ad_{uuid.uuid4().hex[:12]}.png"
                filepath = os.path.join(self.output_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(image_data)

                print(f"✅ Image saved: {filepath}")

                return GeneratedImage(
                    image_path=filepath,
                    prompt_used=prompt,
                )

            except Exception as e:
                if attempt == 2:
                    print(f"❌ ImageAgent failed after 3 attempts: {e}")
                    # Return a placeholder instead of crashing the pipeline
                    return GeneratedImage(
                        image_path="",
                        prompt_used=prompt,
                        model="imagen-4.0-generate-001",
                    )
                print(f"⚠️  Image generation attempt {attempt + 1} failed, retrying... ({e})")

    def get_image_base64(self, image_path: str) -> Optional[str]:
        """Read a saved image and return base64-encoded string for evaluation."""
        if not image_path or not os.path.exists(image_path):
            return None
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


# ─── Smoke Test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = ImageAgent()

    test_input = ImageInput(
        primary_text="3.8 GPA. 1260 SAT. Something's off. Most mid-1200s students are 3-4 targeted fixes away from a 1400+.",
        headline="Your Child's SAT Gap Is Fixable",
        audience="parents of high-achieving juniors with GPA-SAT mismatch",
        product="1-on-1 SAT tutoring",
        goal="conversion",
        persona="suburban_optimizer",
    )

    print("🧪 SMOKE TEST — ImageAgent")
    result = agent.generate(test_input)
    print(f"\n  Image path:  {result.image_path}")
    print(f"  Model:       {result.model}")
    print(f"  Prompt used: {result.prompt_used[:100]}...")

    if result.image_path and os.path.exists(result.image_path):
        size_kb = os.path.getsize(result.image_path) / 1024
        print(f"  File size:   {size_kb:.1f} KB")
        print("✅ SMOKE TEST PASSED — ImageAgent is generating images!")
    else:
        print("⚠️  Image file not found — check Imagen API access")
