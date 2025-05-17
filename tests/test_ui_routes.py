import pytest
from fastapi.testclient import TestClient
from dashboard_server import app

client = TestClient(app)

@pytest.mark.parametrize("route,expected_keys", [
    ("/metrics/content", ["top_templates"]),
    ("/growth/ugc", ["ugc_feed"]),
    ("/growth/influencers", ["influencers"]),
    ("/growth/referrals", ["referrals"]),
    ("/logs", []),
    ("/status/agents", []),
    ("/metrics/email", []),
    ("/metrics/linkedin", []),
    ("/metrics/full", ["memory_mb", "cpu_percent"]),
])
def test_ui_routes(route, expected_keys):
    resp = client.get(route)
    assert resp.status_code == 200
    data = resp.json()
    for key in expected_keys:
        assert key in data 