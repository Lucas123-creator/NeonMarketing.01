import pytest
from integration.ads_feedback import AdsFeedback
from integration.affiliate_tracker import AffiliateTracker
from integration.partner_outreach_agent import PartnerOutreachAgent
import asyncio

# AdsFeedback tests
def test_ads_feedback_top_themes():
    ads = AdsFeedback()
    ads.log_ad_event("ad1", "US", "google", "summer", 100, 10, 50)
    ads.log_ad_event("ad2", "US", "meta", "summer", 200, 30, 100)
    ads.log_ad_event("ad3", "EU", "google", "winter", 50, 2, 30)
    top = ads.get_top_themes(top_n=1)
    assert top[0] == "summer"

# AffiliateTracker tests
def test_affiliate_tracker_log_and_score():
    tracker = AffiliateTracker()
    tracker.log_referral("aff123", "lead1", "https://ref.com/?aff=aff123")
    tracker.log_referral("aff123", "lead2", "https://ref.com/?aff=aff123")
    assert tracker.get_affiliate_score("aff123") == 2

# PartnerOutreachAgent tests
@pytest.mark.asyncio
def test_partner_outreach_agent(monkeypatch):
    agent = PartnerOutreachAgent()
    partner = {"name": "Acme Inc", "email": "acme@example.com", "region": "US"}
    def mock_send_email(to, subject, body):
        assert "partner program" in body
        return True
    monkeypatch.setattr(agent.messenger, "send_email", mock_send_email)
    result = asyncio.run(agent.contact_partner(partner, channel="email"))
    assert result is None or result is True 