import pytest
from fastapi.testclient import TestClient
from dashboard_server import app

client = TestClient(app)

def test_get_agent_status():
    response = client.get("/status/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

def test_get_high_error_agents():
    response = client.get("/status/agents/high-error?threshold=1")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

def test_get_email_metrics():
    response = client.get("/metrics/email")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

def test_get_linkedin_metrics():
    response = client.get("/metrics/linkedin")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

def test_get_content_metrics():
    response = client.get("/metrics/content")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

def test_get_logs():
    response = client.get("/logs?limit=5")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_lead_sequence_not_found():
    response = client.get("/sequences/nonexistent_lead")
    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"

def test_get_top_templates():
    response = client.get("/insights/top-performing-templates")
    assert response.status_code == 200
    assert "top_templates" in response.json()

def test_export_leads_csv():
    response = client.get("/export/leads.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "lead_id" in response.text 