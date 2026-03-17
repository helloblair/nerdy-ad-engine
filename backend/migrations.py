"""
migrations.py
-------------
Add missing columns to Supabase production tables.
Safe to run multiple times — uses IF NOT EXISTS.

Usage:
    python3 migrations.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

MIGRATION_SQL = """
-- Ads: add cost_usd, variant_approach, image_url
ALTER TABLE ads ADD COLUMN IF NOT EXISTS cost_usd FLOAT DEFAULT 0;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS variant_approach TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS image_url TEXT DEFAULT '';

-- Evaluations: add confidence columns
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS clarity_confidence NUMERIC(3,2);
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS value_proposition_confidence NUMERIC(3,2);
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS cta_confidence NUMERIC(3,2);
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS brand_voice_confidence NUMERIC(3,2);
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS emotional_resonance_confidence NUMERIC(3,2);

-- Evaluations: add visual_brand_consistency dimension
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS visual_brand_consistency NUMERIC(3,1);
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS visual_brand_consistency_rationale TEXT;
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS visual_brand_consistency_confidence NUMERIC(3,2);

-- Evaluations: add scroll_stopping_power dimension
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS scroll_stopping_power NUMERIC(3,1);
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS scroll_stopping_power_rationale TEXT;
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS scroll_stopping_power_confidence NUMERIC(3,2);

-- Evaluations: add needs_human_review
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS needs_human_review BOOLEAN DEFAULT FALSE;
"""


def run_migrations():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        print("No SUPABASE_URL/SUPABASE_ANON_KEY set.")
        print("\nTo run manually, paste this SQL into the Supabase SQL editor:")
        print(MIGRATION_SQL)
        return

    print("Run the following SQL in your Supabase SQL editor")
    print("(Dashboard → SQL Editor → New query):\n")
    print(MIGRATION_SQL)
    print("\n✅ Copy-paste the above into Supabase SQL editor and click 'Run'.")


if __name__ == "__main__":
    run_migrations()
