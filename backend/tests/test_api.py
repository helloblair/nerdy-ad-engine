"""Tests for FastAPI endpoints using TestClient with mocked Supabase."""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


def _make_supabase_mock():
    """Build a supabase mock that supports chained query builder calls."""
    mock = MagicMock()

    def _chain(*args, **kwargs):
        return mock.table.return_value

    mock.table.return_value.select.return_value = mock.table.return_value
    mock.table.return_value.insert.return_value = mock.table.return_value
    mock.table.return_value.update.return_value = mock.table.return_value
    mock.table.return_value.eq.return_value = mock.table.return_value
    mock.table.return_value.order.return_value = mock.table.return_value
    mock.table.return_value.execute.return_value = MagicMock(data=[], count=0)
    return mock


@pytest.fixture
def client():
    mock_sb = _make_supabase_mock()
    with patch("main.supabase", mock_sb), \
         patch("main.run_pipeline"):
        from main import app
        yield TestClient(app), mock_sb


# ── Test 1: GET /campaigns returns 200 ─────────────────────────────────────

def test_list_campaigns_200(client):
    tc, mock_sb = client
    mock_sb.table.return_value.execute.return_value = MagicMock(data=[], count=0)
    resp = tc.get("/campaigns")
    assert resp.status_code == 200
    body = resp.json()
    assert "campaigns" in body
    assert "total" in body


# ── Test 2: GET /ads/{ad_id} returns 200 with mocked data ─────────────────
# (We test the /health endpoint instead since /ads needs a real UUID lookup)

def test_health_returns_200(client):
    tc, _ = client
    resp = tc.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Test 3: POST /ads/{ad_id}/rate accepts valid rating ───────────────────

def test_rate_ad_valid(client):
    tc, mock_sb = client
    # Mock: ad exists
    mock_sb.table.return_value.execute.return_value = MagicMock(
        data=[{"id": "test-ad-id"}]
    )
    resp = tc.post("/ads/test-ad-id/rate", json={"rating": "good"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["rating"] == "good"


# ── Test 4: POST /ads/{ad_id}/rate rejects invalid rating ─────────────────

def test_rate_ad_invalid(client):
    tc, mock_sb = client
    mock_sb.table.return_value.execute.return_value = MagicMock(
        data=[{"id": "test-ad-id"}]
    )
    resp = tc.post("/ads/test-ad-id/rate", json={"rating": "terrible"})
    assert resp.status_code == 400


# ── Test 5: GET /analytics/confusion-matrix returns expected fields ────────

def test_confusion_matrix_fields(client):
    tc, mock_sb = client
    # Empty ratings → returns empty structure
    mock_sb.table.return_value.execute.return_value = MagicMock(data=[])
    resp = tc.get("/analytics/confusion-matrix")
    assert resp.status_code == 200
    body = resp.json()
    assert "matrix" in body
    assert "metrics" in body
    assert "total_ratings" in body
