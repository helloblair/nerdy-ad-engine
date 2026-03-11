"""Tests for FastAPI endpoints using TestClient against real Supabase."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app, supabase

client = TestClient(app)


def _get_any_ad_id() -> str | None:
    """Fetch a real ad ID from Supabase, or None if the table is empty."""
    result = supabase.table("ads").select("id").limit(1).execute()
    return result.data[0]["id"] if result.data else None


# ── Test 1: GET /health returns 200 ────────────────────────────────────────

def test_health_returns_200():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Test 2: GET /campaigns returns 200 ─────────────────────────────────────

def test_list_campaigns_200():
    resp = client.get("/campaigns")
    assert resp.status_code == 200
    body = resp.json()
    assert "campaigns" in body
    assert "total" in body
    assert isinstance(body["campaigns"], list)


# ── Test 3: POST /ads/{ad_id}/rate accepts a valid rating ─────────────────

def test_rate_ad_valid():
    ad_id = _get_any_ad_id()
    if ad_id is None:
        pytest.skip("No ads in Supabase to rate")
    resp = client.post(f"/ads/{ad_id}/rate", json={"rating": "good"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["rating"] == "good"


# ── Test 4: POST /ads/{ad_id}/rate rejects invalid rating ─────────────────

def test_rate_ad_invalid():
    ad_id = _get_any_ad_id()
    if ad_id is None:
        pytest.skip("No ads in Supabase to rate")
    resp = client.post(f"/ads/{ad_id}/rate", json={"rating": "terrible"})
    assert resp.status_code == 400


# ── Test 5: GET /analytics/confusion-matrix returns expected fields ────────

def test_confusion_matrix_fields():
    resp = client.get("/analytics/confusion-matrix")
    assert resp.status_code == 200
    body = resp.json()
    assert "matrix" in body
    assert "metrics" in body
    assert "total_ratings" in body
