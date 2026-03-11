"""
db/supabase_db.py
-----------------
Supabase implementation of DatabaseInterface.
Wraps the existing Supabase client calls — extracted from main.py/pipeline.py.
"""

import os
from typing import Optional

from supabase import create_client
from db.interface import DatabaseInterface


class SupabaseDatabase(DatabaseInterface):

    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError(
                "DB_BACKEND=supabase requires SUPABASE_URL and SUPABASE_ANON_KEY env vars"
            )
        self.client = create_client(url, key)

    # ── Campaigns ────────────────────────────────────────────────────────────

    def insert_campaign(self, data: dict) -> dict:
        result = self.client.table("campaigns").insert(data).execute()
        return result.data[0]

    def update_campaign_status(self, campaign_id: str, status: str) -> None:
        self.client.table("campaigns").update({"status": status}).eq("id", campaign_id).execute()

    def list_campaigns(self) -> list[dict]:
        result = self.client.table("campaigns").select("*").order("created_at", desc=True).execute()
        return result.data

    def get_campaign(self, campaign_id: str) -> Optional[dict]:
        result = self.client.table("campaigns").select("*").eq("id", campaign_id).execute()
        return result.data[0] if result.data else None

    # ── Ads ──────────────────────────────────────────────────────────────────

    def insert_ad(self, data: dict) -> dict:
        result = self.client.table("ads").insert(data).execute()
        return result.data[0]

    def count_ads_for_campaign(self, campaign_id: str) -> int:
        result = self.client.table("ads").select("id", count="exact").eq("campaign_id", campaign_id).execute()
        return result.count or 0

    def list_ads_for_campaign(self, campaign_id: str) -> list[dict]:
        result = self.client.table("ads").select("*").eq("campaign_id", campaign_id).order("created_at").execute()
        return result.data

    def get_ad(self, ad_id: str) -> Optional[dict]:
        result = self.client.table("ads").select("*").eq("id", ad_id).execute()
        return result.data[0] if result.data else None

    # ── Evaluations ──────────────────────────────────────────────────────────

    def insert_evaluation(self, data: dict) -> dict:
        result = self.client.table("evaluations").insert(data).execute()
        return result.data[0]

    def get_evaluation_for_ad(self, ad_id: str) -> Optional[dict]:
        result = self.client.table("evaluations").select("*").eq("ad_id", ad_id).execute()
        return result.data[0] if result.data else None

    def get_evaluations_with_ads(self) -> list[dict]:
        result = self.client.table("evaluations").select(
            "*, ads(campaign_id, headline, iteration_number, status)"
        ).execute()
        return result.data

    # ── Human Ratings ────────────────────────────────────────────────────────

    def insert_human_rating(self, data: dict) -> dict:
        result = self.client.table("human_ratings").insert(data).execute()
        return result.data[0]

    def get_ratings_with_ads(self) -> list[dict]:
        result = self.client.table("human_ratings").select("*, ads(status)").execute()
        return result.data
