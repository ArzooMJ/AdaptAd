"""
API integration tests.

Run with: pytest backend/tests/test_api.py -v

Tests all major endpoints with an in-process test client.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["project"] == "AdaptAd"


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    d = r.json()
    assert d["users"] == 200
    assert d["ads"] == 80
    assert d["content"] == 100


def test_list_users():
    r = client.get("/api/users?limit=5")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] == 200
    assert len(d["users"]) == 5


def test_get_user():
    r = client.get("/api/users/1")
    assert r.status_code == 200
    assert r.json()["id"] == 1


def test_get_user_not_found():
    r = client.get("/api/users/9999")
    assert r.status_code == 404


def test_list_ads():
    r = client.get("/api/ads?limit=10")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] == 80
    assert len(d["ads"]) == 10


def test_list_ads_by_category():
    r = client.get("/api/ads?category=tech")
    assert r.status_code == 200
    for ad in r.json()["ads"]:
        assert ad["category"] == "tech"


def test_list_content():
    r = client.get("/api/content?limit=5")
    assert r.status_code == 200
    assert r.json()["total"] == 100


def test_list_chromosomes_empty():
    r = client.get("/api/chromosomes")
    assert r.status_code == 200
    assert "chromosomes" in r.json()


def test_single_decision():
    # Get first user and first ad to construct a valid request.
    users = client.get("/api/users?limit=1").json()["users"]
    ads = client.get("/api/ads?limit=1").json()["ads"]
    user_id = users[0]["id"]
    ad_id = ads[0]["id"]

    r = client.post("/api/decide", json={
        "user_id": user_id,
        "ad_id": ad_id,
        "time_of_day": "evening",
        "season": "Fall",
        "ads_shown_this_session": 0,
        "session_fatigue": 0.1,
        "use_llm": False,
    })
    assert r.status_code == 200
    d = r.json()
    assert d["decision"] in ("SHOW", "SOFTEN", "DELAY", "SUPPRESS")
    assert 0.0 <= d["combined_score"] <= 1.0
    assert "user_advocate" in d
    assert "advertiser_advocate" in d


def test_single_decision_user_not_found():
    r = client.post("/api/decide", json={
        "user_id": 9999,
        "ad_id": "ad_001",
        "time_of_day": "morning",
        "season": "Spring",
    })
    assert r.status_code == 404


def test_batch_decide():
    ads = client.get("/api/ads?limit=1").json()["ads"]
    ad_id = ads[0]["id"]
    r = client.post("/api/decide/batch", json={
        "ad_id": ad_id,
        "time_of_day": "evening",
        "season": "Summer",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["total_users"] == 200
    total = sum(d["decision_counts"].values())
    assert total == 200


def test_simulate_session():
    users = client.get("/api/users?limit=1").json()["users"]
    content = client.get("/api/content?limit=1").json()["content"]
    r = client.post("/api/simulate/session", json={
        "user_id": users[0]["id"],
        "content_id": content[0]["id"],
        "time_of_day": "evening",
        "season": "Fall",
    })
    assert r.status_code == 200
    d = r.json()
    assert "session_id" in d
    assert "decisions" in d
    assert "summary" in d
    assert d["summary"]["total_breaks"] >= 0


def test_ab_start():
    r = client.post("/api/ab/start", json={"seed": 42})
    assert r.status_code == 200
    d = r.json()
    assert "session_id" in d
    assert "session_x" in d
    assert "session_y" in d


def test_ab_rate_and_results():
    # Start a session.
    r = client.post("/api/ab/start", json={"seed": 7})
    session_id = r.json()["session_id"]

    # Rate both.
    client.post(f"/api/ab/{session_id}/rate", json={
        "session_label": "X", "annoyance": 2, "relevance": 4, "willingness": 4
    })
    client.post(f"/api/ab/{session_id}/rate", json={
        "session_label": "Y", "annoyance": 4, "relevance": 2, "willingness": 2
    })

    r = client.get("/api/ab/results")
    assert r.status_code == 200
    d = r.json()
    assert d["aggregate"]["completed_sessions"] >= 1


def test_start_evolution():
    r = client.post("/api/evolve", json={"max_generations": 2, "seed": 42})
    assert r.status_code == 200
    d = r.json()
    assert "job_id" in d
    assert d["status"] == "queued"

    job_id = d["job_id"]
    # Status endpoint should work immediately.
    r2 = client.get(f"/api/evolve/{job_id}")
    assert r2.status_code == 200
    assert r2.json()["job_id"] == job_id


def test_all_four_decisions_in_batch():
    """Batch decisions across all users should surface all 4 decision types."""
    ads = client.get("/api/ads?limit=1").json()["ads"]
    ad_id = ads[0]["id"]
    r = client.post("/api/decide/batch", json={
        "ad_id": ad_id,
        "time_of_day": "evening",
        "season": "Winter",
        "ads_shown_this_session": 3,
        "session_fatigue": 0.5,
    })
    counts = r.json()["decision_counts"]
    # With 200 users, fatigue=0.5, ads_shown=3, we should see multiple types.
    non_zero = sum(1 for v in counts.values() if v > 0)
    assert non_zero >= 2, f"Expected at least 2 decision types, got: {counts}"
