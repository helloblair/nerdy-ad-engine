"""
db/interface.py
---------------
Abstract base class defining every database operation used across the codebase.
All implementations (SQLite, Supabase) must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Optional


class DatabaseInterface(ABC):

    # ── Campaigns ────────────────────────────────────────────────────────────

    @abstractmethod
    def insert_campaign(self, data: dict) -> dict:
        """Insert a campaign row. Returns the full row dict (including generated id, created_at)."""
        ...

    @abstractmethod
    def update_campaign_status(self, campaign_id: str, status: str) -> None:
        """Update the status field of a campaign."""
        ...

    @abstractmethod
    def list_campaigns(self) -> list[dict]:
        """Return all campaigns ordered by created_at DESC."""
        ...

    @abstractmethod
    def get_campaign(self, campaign_id: str) -> Optional[dict]:
        """Return a single campaign by id, or None."""
        ...

    # ── Ads ──────────────────────────────────────────────────────────────────

    @abstractmethod
    def insert_ad(self, data: dict) -> dict:
        """Insert an ad row. Returns the full row dict (including generated id)."""
        ...

    @abstractmethod
    def count_ads_for_campaign(self, campaign_id: str) -> int:
        """Return the count of ads belonging to a campaign."""
        ...

    @abstractmethod
    def count_all_ads(self) -> int:
        """Return the total count of all ads across all campaigns."""
        ...

    @abstractmethod
    def list_ads_for_campaign(self, campaign_id: str) -> list[dict]:
        """Return all ads for a campaign, ordered by created_at ASC."""
        ...

    @abstractmethod
    def get_ad(self, ad_id: str) -> Optional[dict]:
        """Return a single ad by id, or None."""
        ...

    @abstractmethod
    def update_ad(self, ad_id: str, updates: dict) -> dict:
        """Update an ad row by id. Returns the updated row dict."""
        ...

    @abstractmethod
    def list_all_ads(self) -> list[dict]:
        """Return all ads across all campaigns."""
        ...

    # ── Evaluations ──────────────────────────────────────────────────────────

    @abstractmethod
    def insert_evaluation(self, data: dict) -> dict:
        """Insert an evaluation row. Returns the full row dict."""
        ...

    @abstractmethod
    def get_evaluation_for_ad(self, ad_id: str) -> Optional[dict]:
        """Return the evaluation for a given ad_id, or None."""
        ...

    @abstractmethod
    def get_evaluations_with_ads(self) -> list[dict]:
        """
        Return all evaluations joined with their ad's campaign_id, headline,
        iteration_number, and status. Each dict has an 'ads' sub-dict.
        Used by the /analytics/trends endpoint.
        """
        ...

    # ── Human Ratings ────────────────────────────────────────────────────────

    @abstractmethod
    def insert_human_rating(self, data: dict) -> dict:
        """Insert a human rating row. Returns the full row dict."""
        ...

    @abstractmethod
    def get_ratings_with_ads(self) -> list[dict]:
        """
        Return all human ratings joined with their ad's status.
        Each dict has an 'ads' sub-dict with 'status'.
        Used by the /analytics/confusion-matrix endpoint.
        """
        ...
