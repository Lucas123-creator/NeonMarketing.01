import pytest
from fastapi.testclient import TestClient
from dashboard_server import app

client = TestClient(app)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_uptime():
    resp = client.get("/uptime")
    assert resp.status_code == 200
    assert "uptime_seconds" in resp.json()

def test_metrics_full():
    resp = client.get("/metrics/full")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "memory_mb" in data
    assert "cpu_percent" in data

def test_campaign_launch_and_crm_handoff(monkeypatch):
    from neonhub.services.content_personalizer import ContentPersonalizer
    from neonhub.services.crm_handoff import push_lead_to_crm
    from neonhub.schemas.lead_state import LeadState
    personalizer = ContentPersonalizer()
    lead = LeadState(
        lead_id="launch1",
        campaign_id="b2b_onboard",
        sequence_stages=[],
        metadata={"first_name": "Alex"},
        utm_source="newsletter",
        utm_medium="email",
        utm_campaign="b2b_launch"
    )
    utm_params = "utm_source=newsletter&utm_medium=email&utm_campaign=b2b_launch"
    content = personalizer.generate_content(
        template_id="welcome_email",
        personalization={"first_name": "Alex", "utm_params": utm_params},
        channel="email",
        lang="en"
    )
    assert "utm_source=newsletter" in content["body"]
    def mock_post(url, json, timeout):
        class Resp:
            def raise_for_status(self): pass
            status_code = 200
        return Resp()
    monkeypatch.setattr("requests.post", mock_post)
    assert push_lead_to_crm(lead, "http://mock-crm") is True 