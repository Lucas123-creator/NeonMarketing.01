import pytest
from unittest.mock import MagicMock, patch
from growth.referral_trigger import ReferralTrigger, REFERRAL_TRIGGERS_SENT, UGC_REWARD_TRIGGERED, INFLUENCER_THANK_YOU_SENT, REFERRAL_CONVERSION
from neonhub.schemas.referral_event import ReferralEvent
from datetime import datetime

def make_post(likes=100, platform="instagram", user="@user1"):
    return {
        "user": user,
        "platform": platform,
        "likes": likes,
        "url": "https://instagram.com/p/abc123"
    }

def make_profile(handle="@influencer", platform="instagram"):
    return {
        "handle": handle,
        "platform": platform
    }

def test_handle_ugc_engagement_discount():
    trigger = ReferralTrigger()
    with patch.object(trigger.messenger, 'send_whatsapp', return_value=MagicMock(status='sent')) as mock_wa:
        post = make_post(likes=100)
        event = trigger.handle_ugc_engagement(post)
        assert isinstance(event, ReferralEvent)
        assert event.reward_type == "discount"
        assert event.channel == "whatsapp"
        assert mock_wa.called
        assert UGC_REWARD_TRIGGERED.labels(platform="instagram", reward_type="discount")._value.get() >= 1
        assert REFERRAL_TRIGGERS_SENT.labels(type="ugc_reward", channel="whatsapp")._value.get() >= 1

def test_handle_ugc_engagement_repost():
    trigger = ReferralTrigger()
    with patch.object(trigger.messenger, 'send_sms', return_value=MagicMock(status='sent')) as mock_sms:
        post = make_post(likes=10, platform="tiktok")
        event = trigger.handle_ugc_engagement(post)
        assert isinstance(event, ReferralEvent)
        assert event.reward_type == "repost"
        assert event.channel == "email"
        assert mock_sms.called
        assert UGC_REWARD_TRIGGERED.labels(platform="tiktok", reward_type="repost")._value.get() >= 1
        assert REFERRAL_TRIGGERS_SENT.labels(type="ugc_reward", channel="email")._value.get() >= 1

def test_handle_influencer_share():
    trigger = ReferralTrigger()
    with patch.object(trigger.messenger, 'send_whatsapp', return_value=MagicMock(status='sent')) as mock_wa:
        profile = make_profile()
        event = trigger.handle_influencer_share(profile)
        assert isinstance(event, ReferralEvent)
        assert event.event_type == "influencer_share"
        assert event.reward_type == "thank_you"
        assert event.channel == "whatsapp"
        assert mock_wa.called
        assert INFLUENCER_THANK_YOU_SENT.labels(platform="instagram")._value.get() >= 1
        assert REFERRAL_TRIGGERS_SENT.labels(type="influencer_share", channel="whatsapp")._value.get() >= 1

def test_track_referral_conversion():
    trigger = ReferralTrigger()
    with patch.object(trigger.messenger, 'send_sms', return_value=MagicMock(status='sent')) as mock_sms:
        event = trigger.track_referral_conversion("ref123", "lead_456")
        assert isinstance(event, ReferralEvent)
        assert event.event_type == "referral_conversion"
        assert event.reward_type == "affiliate_bonus"
        assert event.channel == "email"
        assert mock_sms.called
        assert REFERRAL_CONVERSION.labels(reward_type="affiliate_bonus")._value.get() >= 1
        assert REFERRAL_TRIGGERS_SENT.labels(type="referral_conversion", channel="email")._value.get() >= 1 