"""Tests for FastAPI endpoints using TestClient."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from db import get_db

client = TestClient(app)


def _get_any_ad_id() -> str | None:
    """Fetch a real ad ID from the database, or None if the table is empty."""
    db = get_db()
    campaigns = db.list_campaigns()
    for c in campaigns:
        ads = db.list_ads_for_campaign(c["id"])
        if ads:
            return ads[0]["id"]
    return None


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
        pytest.skip("No ads in database to rate")
    resp = client.post(f"/ads/{ad_id}/rate", json={"rating": "good"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["rating"] == "good"


# ── Test 4: POST /ads/{ad_id}/rate rejects invalid rating ─────────────────

def test_rate_ad_invalid():
    ad_id = _get_any_ad_id()
    if ad_id is None:
        pytest.skip("No ads in database to rate")
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
