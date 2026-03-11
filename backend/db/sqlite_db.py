"""
db/sqlite_db.py
---------------
SQLite implementation of DatabaseInterface.
Uses Python's built-in sqlite3 — no extra dependencies.
Auto-creates the database file and all tables on first run.
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from db.interface import DatabaseInterface


class SQLiteDatabase(DatabaseInterface):

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = os.getenv(
                "SQLITE_DB_PATH",
                os.path.join(os.path.dirname(__file__), "..", "data", "ads.db"),
            )
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_tables(self):
        conn = self._connect()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    audience TEXT NOT NULL,
                    product TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    tone TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ads (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    primary_text TEXT NOT NULL,
                    headline TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    cta_button TEXT NOT NULL,
                    iteration_number INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'approved',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
                );

                CREATE TABLE IF NOT EXISTS evaluations (
                    id TEXT PRIMARY KEY,
                    ad_id TEXT NOT NULL,
                    clarity REAL NOT NULL,
                    value_proposition REAL NOT NULL,
                    cta_score REAL NOT NULL,
                    brand_voice REAL NOT NULL,
                    emotional_resonance REAL NOT NULL,
                    aggregate_score REAL NOT NULL,
                    clarity_rationale TEXT,
                    value_proposition_rationale TEXT,
                    cta_rationale TEXT,
                    brand_voice_rationale TEXT,
                    emotional_resonance_rationale TEXT,
                    clarity_confidence REAL,
                    value_proposition_confidence REAL,
                    cta_confidence REAL,
                    brand_voice_confidence REAL,
                    emotional_resonance_confidence REAL,
                    meets_threshold INTEGER NOT NULL DEFAULT 0,
                    needs_human_review INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (ad_id) REFERENCES ads(id)
                );

                CREATE TABLE IF NOT EXISTS human_ratings (
                    id TEXT PRIMARY KEY,
                    ad_id TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (ad_id) REFERENCES ads(id)
                );
            """)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        d = dict(row)
        # Convert SQLite integer booleans back to Python bools for meets_threshold
        if "meets_threshold" in d:
            d["meets_threshold"] = bool(d["meets_threshold"])
        return d

    # ── Campaigns ────────────────────────────────────────────────────────────

    def insert_campaign(self, data: dict) -> dict:
        row_id = str(uuid.uuid4())
        now = self._now()
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO campaigns (id, name, audience, product, goal, tone, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (row_id, data["name"], data["audience"], data["product"],
                 data["goal"], data.get("tone"), data.get("status", "pending"), now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (row_id,)).fetchone()
            return self._row_to_dict(row)
        finally:
            conn.close()

    def update_campaign_status(self, campaign_id: str, status: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE campaigns SET status = ? WHERE id = ?",
                (status, campaign_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_campaigns(self) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM campaigns ORDER BY created_at DESC"
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def get_campaign(self, campaign_id: str) -> Optional[dict]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
            ).fetchone()
            return self._row_to_dict(row)
        finally:
            conn.close()

    # ── Ads ──────────────────────────────────────────────────────────────────

    def insert_ad(self, data: dict) -> dict:
        row_id = str(uuid.uuid4())
        now = self._now()
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO ads (id, campaign_id, primary_text, headline, description,
                   cta_button, iteration_number, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (row_id, data["campaign_id"], data["primary_text"], data["headline"],
                 data.get("description", ""), data["cta_button"],
                 data.get("iteration_number", 1), data.get("status", "approved"), now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM ads WHERE id = ?", (row_id,)).fetchone()
            return self._row_to_dict(row)
        finally:
            conn.close()

    def count_ads_for_campaign(self, campaign_id: str) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM ads WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()
            return row["cnt"]
        finally:
            conn.close()

    def list_ads_for_campaign(self, campaign_id: str) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM ads WHERE campaign_id = ? ORDER BY created_at ASC",
                (campaign_id,),
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def get_ad(self, ad_id: str) -> Optional[dict]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM ads WHERE id = ?", (ad_id,)
            ).fetchone()
            return self._row_to_dict(row)
        finally:
            conn.close()

    # ── Evaluations ──────────────────────────────────────────────────────────

    def insert_evaluation(self, data: dict) -> dict:
        row_id = str(uuid.uuid4())
        now = self._now()
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO evaluations (id, ad_id, clarity, value_proposition, cta_score,
                   brand_voice, emotional_resonance, aggregate_score,
                   clarity_rationale, value_proposition_rationale, cta_rationale,
                   brand_voice_rationale, emotional_resonance_rationale,
                   clarity_confidence, value_proposition_confidence, cta_confidence,
                   brand_voice_confidence, emotional_resonance_confidence,
                   meets_threshold, needs_human_review, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (row_id, data["ad_id"], data["clarity"], data["value_proposition"],
                 data["cta_score"], data["brand_voice"], data["emotional_resonance"],
                 data["aggregate_score"],
                 data.get("clarity_rationale"), data.get("value_proposition_rationale"),
                 data.get("cta_rationale"), data.get("brand_voice_rationale"),
                 data.get("emotional_resonance_rationale"),
                 data.get("clarity_confidence"), data.get("value_proposition_confidence"),
                 data.get("cta_confidence"), data.get("brand_voice_confidence"),
                 data.get("emotional_resonance_confidence"),
                 1 if data.get("meets_threshold") else 0,
                 1 if data.get("needs_human_review") else 0, now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM evaluations WHERE id = ?", (row_id,)).fetchone()
            return self._row_to_dict(row)
        finally:
            conn.close()

    def get_evaluation_for_ad(self, ad_id: str) -> Optional[dict]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM evaluations WHERE ad_id = ?", (ad_id,)
            ).fetchone()
            return self._row_to_dict(row)
        finally:
            conn.close()

    def get_evaluations_with_ads(self) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute("""
                SELECT e.*, a.campaign_id, a.headline, a.iteration_number, a.status as ad_status
                FROM evaluations e
                JOIN ads a ON e.ad_id = a.id
            """).fetchall()
            results = []
            for r in rows:
                d = self._row_to_dict(r)
                # Reshape to match Supabase's nested join format
                d["ads"] = {
                    "campaign_id": d.pop("campaign_id"),
                    "headline": d.pop("headline"),
                    "iteration_number": d.pop("iteration_number"),
                    "status": d.pop("ad_status"),
                }
                results.append(d)
            return results
        finally:
            conn.close()

    # ── Human Ratings ────────────────────────────────────────────────────────

    def insert_human_rating(self, data: dict) -> dict:
        row_id = str(uuid.uuid4())
        now = self._now()
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO human_ratings (id, ad_id, rating, created_at)
                   VALUES (?, ?, ?, ?)""",
                (row_id, data["ad_id"], data["rating"], now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM human_ratings WHERE id = ?", (row_id,)).fetchone()
            return self._row_to_dict(row)
        finally:
            conn.close()

    def get_ratings_with_ads(self) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute("""
                SELECT hr.*, a.status as ad_status
                FROM human_ratings hr
                JOIN ads a ON hr.ad_id = a.id
            """).fetchall()
            results = []
            for r in rows:
                d = self._row_to_dict(r)
                d["ads"] = {"status": d.pop("ad_status")}
                results.append(d)
            return results
        finally:
            conn.close()
