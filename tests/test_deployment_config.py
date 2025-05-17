import os
import pytest
from neonhub.config.settings import get_settings

def test_prod_settings_load(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SMTP_USERNAME", "produser@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "prodpass")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "produser@example.com")
    monkeypatch.setenv("LINKEDIN_USERNAME", "prodlinkedin")
    monkeypatch.setenv("LINKEDIN_PASSWORD", "prodlinkedinpass")
    monkeypatch.setenv("OPENAI_API_KEY", "prodaikey")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db:5432/neonhub")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("PHANTOMBUSTER_API_KEY", "prodphantom")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.smtp.username
    assert settings.smtp.password
    assert settings.smtp.from_email
    assert settings.linkedin.username
    assert settings.linkedin.password
    assert settings.openai.api_key
    assert settings.database.url
    assert settings.redis.url
    assert settings.phantombuster_api_key
    assert settings.environment == "production"

def test_crm_handoff_success(monkeypatch):
    from neonhub.services.crm_handoff import push_lead_to_crm
    from neonhub.schemas.lead_state import LeadState
    lead = LeadState(
        lead_id="test123",
        campaign_id="camp1",
        sequence_stages=[],
        metadata={}
    )
    def mock_post(url, json, timeout):
        class Resp:
            def raise_for_status(self): pass
            status_code = 200
        return Resp()
    monkeypatch.setattr("requests.post", mock_post)
    assert push_lead_to_crm(lead, "http://mock-crm") is True 