import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from neonhub.services.trigger_manager import TriggerManager, TRIGGERS_FIRED, TRIGGERS_SUPPRESSED
from neonhub.schemas.lead_state import LeadState, EngagementEvent, LeadStatus

@pytest.fixture
def trigger_manager():
    tm = TriggerManager()
    # Patch messenger to avoid real sends
    tm.messenger.send_whatsapp = MagicMock(return_value=MagicMock(status='sent'))
    tm.messenger.send_sms = MagicMock(return_value=MagicMock(status='sent'))
    return tm

@pytest.fixture
def base_lead_state():
    return LeadState(
        lead_id="lead_1",
        campaign_id="camp_1",
        current_stage=1,
        status=LeadStatus.ACTIVE,
        engagement_score=2,
        last_touch=datetime.utcnow(),
        sequence_stages=[],
        engagement_history=[],
        metadata={
            "first_name": "Alex",
            "persona": "Retail Buyer",
            "lang": "en",
            "phone": "+1234567890",
            "whatsapp": "+1234567890",
            "email": "alex@example.com"
        }
    )

def test_cart_abandonment_whatsapp(trigger_manager, base_lead_state):
    # Simulate cart abandoned 2 hours ago
    base_lead_state.metadata["cart_abandoned_at"] = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    base_lead_state.metadata["cart_product"] = "Neon Sign"
    base_lead_state.metadata["cart_offer_code"] = "SAVE20"
    base_lead_state.metadata["cart_url"] = "bit.ly/cart"
    result = trigger_manager.evaluate_and_trigger(base_lead_state)
    assert trigger_manager.messenger.send_whatsapp.called
    assert result is not None
    assert TRIGGERS_FIRED.labels(type="cart_recovery", channel="whatsapp")._value.get() >= 1

def test_low_engagement_sms(trigger_manager, base_lead_state):
    # Simulate 2 email sends, low score
    base_lead_state.engagement_score = 1
    base_lead_state.engagement_history = [
        EngagementEvent(event_type="email_sent"),
        EngagementEvent(event_type="email_sent")
    ]
    result = trigger_manager.evaluate_and_trigger(base_lead_state)
    assert trigger_manager.messenger.send_sms.called
    assert result is not None
    assert TRIGGERS_FIRED.labels(type="cold_lead_nudge", channel="sms")._value.get() >= 1

def test_reply_suppresses_triggers(trigger_manager, base_lead_state):
    # Simulate reply event
    base_lead_state.engagement_history = [
        EngagementEvent(event_type="email_reply")
    ]
    result = trigger_manager.evaluate_and_trigger(base_lead_state)
    assert result is None
    assert TRIGGERS_SUPPRESSED.labels(reason="reply_received")._value.get() >= 1

def test_unsubscribe_suppresses_triggers(trigger_manager, base_lead_state):
    # Simulate unsubscribe event
    base_lead_state.engagement_history = [
        EngagementEvent(event_type="unsubscribe")
    ]
    result = trigger_manager.evaluate_and_trigger(base_lead_state)
    assert result is None
    assert TRIGGERS_SUPPRESSED.labels(reason="unsubscribed")._value.get() >= 1

def test_cooldown_enforcement(trigger_manager, base_lead_state):
    # Simulate cart abandonment, first trigger fires
    base_lead_state.metadata["cart_abandoned_at"] = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    base_lead_state.metadata["cart_product"] = "Neon Sign"
    base_lead_state.metadata["cart_offer_code"] = "SAVE20"
    base_lead_state.metadata["cart_url"] = "bit.ly/cart"
    result1 = trigger_manager.evaluate_and_trigger(base_lead_state)
    assert trigger_manager.messenger.send_whatsapp.called
    # Second call within cooldown should suppress
    result2 = trigger_manager.evaluate_and_trigger(base_lead_state)
    assert result2 is None
    assert TRIGGERS_SUPPRESSED.labels(reason="cooldown_or_missing_whatsapp")._value.get() >= 1 