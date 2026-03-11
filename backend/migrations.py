"""
migrations.py
-------------
Run this once to add cost_usd to Supabase production.
SQLite handles it automatically via _init_tables() migration.

Usage:
    python3 migrations.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

if os.getenv("SUPABASE_URL"):
    print("Run this in Supabase SQL editor:")
    print("ALTER TABLE ads ADD COLUMN IF NOT EXISTS cost_usd FLOAT DEFAULT 0;")
else:
    print("SQLite: cost_usd column handled by _init_tables() in db/sqlite_db.py")
