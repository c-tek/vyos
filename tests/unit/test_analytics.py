import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_usage_summary():
    resp = client.get("/v1/analytics/usage")
    assert resp.status_code == 200
    data = resp.json()
    assert "scheduled_tasks" in data
    assert "notification_rules" in data

def test_activity_report():
    resp = client.get("/v1/analytics/activity?days=1")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
