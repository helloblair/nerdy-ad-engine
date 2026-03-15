"""
migrate_v2_images.py
--------------------
Database migration to support v2 image generation and 7-dimension evaluation.

Adds:
  - ads.image_url — path/URL to generated ad creative image
  - evaluations.visual_brand_consistency — score for visual brand alignment
  - evaluations.visual_brand_consistency_rationale
  - evaluations.visual_brand_consistency_confidence
  - evaluations.scroll_stopping_power — score for scroll-stopping visual impact
  - evaluations.scroll_stopping_power_rationale
  - evaluations.scroll_stopping_power_confidence

Safe to run multiple times — checks if columns exist before adding.
"""

import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()


def get_db_path() -> str:
    return os.getenv(
        "SQLITE_DB_PATH",
        os.path.join(os.path.dirname(__file__), "data", "ads.db"),
    )


def migrate_sqlite():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"⚠️  Database not found at {db_path} — it will be created on first run")
        return

    conn = sqlite3.connect(db_path)
    try:
        # Check existing columns in ads table
        ads_cols = [r[1] for r in conn.execute("PRAGMA table_info(ads)").fetchall()]
        eval_cols = [r[1] for r in conn.execute("PRAGMA table_info(evaluations)").fetchall()]

        migrations = []

        # ── Ads table ────────────────────────────────────────────────────
        if "image_url" not in ads_cols:
            conn.execute("ALTER TABLE ads ADD COLUMN image_url TEXT DEFAULT ''")
            migrations.append("ads.image_url")

        # ── Evaluations table — visual_brand_consistency ─────────────────
        if "visual_brand_consistency" not in eval_cols:
            conn.execute("ALTER TABLE evaluations ADD COLUMN visual_brand_consistency REAL")
            migrations.append("evaluations.visual_brand_consistency")

        if "visual_brand_consistency_rationale" not in eval_cols:
            conn.execute("ALTER TABLE evaluations ADD COLUMN visual_brand_consistency_rationale TEXT")
            migrations.append("evaluations.visual_brand_consistency_rationale")

        if "visual_brand_consistency_confidence" not in eval_cols:
            conn.execute("ALTER TABLE evaluations ADD COLUMN visual_brand_consistency_confidence REAL")
            migrations.append("evaluations.visual_brand_consistency_confidence")

        # ── Evaluations table — scroll_stopping_power ────────────────────
        if "scroll_stopping_power" not in eval_cols:
            conn.execute("ALTER TABLE evaluations ADD COLUMN scroll_stopping_power REAL")
            migrations.append("evaluations.scroll_stopping_power")

        if "scroll_stopping_power_rationale" not in eval_cols:
            conn.execute("ALTER TABLE evaluations ADD COLUMN scroll_stopping_power_rationale TEXT")
            migrations.append("evaluations.scroll_stopping_power_rationale")

        if "scroll_stopping_power_confidence" not in eval_cols:
            conn.execute("ALTER TABLE evaluations ADD COLUMN scroll_stopping_power_confidence REAL")
            migrations.append("evaluations.scroll_stopping_power_confidence")

        conn.commit()

        if migrations:
            print(f"✅ Migration complete — added {len(migrations)} columns:")
            for m in migrations:
                print(f"   + {m}")
        else:
            print("✅ All v2 columns already exist — nothing to migrate")

    finally:
        conn.close()


if __name__ == "__main__":
    print("🔧 Running v2 image migration...")
    migrate_sqlite()
