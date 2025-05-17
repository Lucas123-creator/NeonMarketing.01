from typing import Dict, Any, Optional
from datetime import datetime
from prometheus_client import Counter
import logging
from neonhub.schemas.referral_event import ReferralEvent
from messaging.personal_messenger import PersonalMessenger

REFERRAL_TRIGGERS_SENT = Counter(
    'referral_triggers_sent_total',
    'Number of referral triggers sent',
    ['type', 'channel']
)
UGC_REWARD_TRIGGERED = Counter(
    'ugc_reward_triggered_total',
    'Number of UGC reward triggers',
    ['platform', 'reward_type']
)
INFLUENCER_THANK_YOU_SENT = Counter(
    'influencer_thank_you_sent_total',
    'Number of influencer thank-you messages sent',
    ['platform']
)
REFERRAL_CONVERSION = Counter(
    'referral_conversion_total',
    'Number of successful referral conversions',
    ['reward_type']
)

class ReferralTrigger:
    def __init__(self):
        self.logger = logging.getLogger("ReferralTrigger")
        self.messenger = PersonalMessenger()
        self.event_log = []  # In production, use DB or persistent log

    def handle_ugc_engagement(self, post_data: Dict[str, Any]):
        # Decide reward type
        reward_type = "discount" if post_data.get("likes", 0) > 50 else "repost"
        channel = "whatsapp" if post_data.get("platform") == "instagram" else "email"
        contact_id = post_data.get("user")
        message = f"Thanks for sharing your neon! 🎉 Here's a {reward_type} just for you."
        # Trigger reward message
        if channel == "whatsapp":
            result = self.messenger.send_whatsapp(contact_id, contact_id, message)
        else:
            result = self.messenger.send_sms(contact_id, contact_id, message)
        event = ReferralEvent(
            event_type="ugc_reward",
            trigger_source="ugc",
            contact_id=contact_id,
            channel=channel,
            reward_type=reward_type,
            status="sent",
            metadata={"post_url": post_data.get("url")}
        )
        self.event_log.append(event)
        UGC_REWARD_TRIGGERED.labels(platform=post_data.get("platform"), reward_type=reward_type).inc()
        REFERRAL_TRIGGERS_SENT.labels(type="ugc_reward", channel=channel).inc()
        self.logger.info(f"UGC reward triggered for {contact_id} on {channel} ({reward_type})")
        return event

    def handle_influencer_share(self, profile_data: Dict[str, Any]):
        # Detect repost/affiliate share
        contact_id = profile_data.get("handle")
        platform = profile_data.get("platform")
        channel = "whatsapp"
        message = f"Thank you for sharing NeonHub! 🌟 You're now an active promoter."
        result = self.messenger.send_whatsapp(contact_id, contact_id, message)
        event = ReferralEvent(
            event_type="influencer_share",
            trigger_source="influencer",
            contact_id=contact_id,
            channel=channel,
            reward_type="thank_you",
            status="sent",
            metadata={"profile": profile_data}
        )
        self.event_log.append(event)
        INFLUENCER_THANK_YOU_SENT.labels(platform=platform).inc()
        REFERRAL_TRIGGERS_SENT.labels(type="influencer_share", channel=channel).inc()
        self.logger.info(f"Influencer thank-you sent to {contact_id} on {platform}")
        return event

    def track_referral_conversion(self, referral_code: str, lead_id: str):
        # Match referral to lead, reward referrer
        reward_type = "affiliate_bonus"
        channel = "email"
        contact_id = referral_code  # In production, map code to user
        message = f"Congrats! Your referral {lead_id} joined NeonHub. Enjoy your {reward_type}!"
        result = self.messenger.send_sms(contact_id, contact_id, message)
        event = ReferralEvent(
            event_type="referral_conversion",
            trigger_source="referral_link",
            contact_id=contact_id,
            channel=channel,
            reward_type=reward_type,
            status="sent",
            metadata={"referred_lead": lead_id}
        )
        self.event_log.append(event)
        REFERRAL_CONVERSION.labels(reward_type=reward_type).inc()
        REFERRAL_TRIGGERS_SENT.labels(type="referral_conversion", channel=channel).inc()
        self.logger.info(f"Referral conversion tracked for {contact_id} (lead: {lead_id})")
        return event 