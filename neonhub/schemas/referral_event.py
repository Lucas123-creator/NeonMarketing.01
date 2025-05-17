from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ReferralEvent(BaseModel):
    event_type: str  # e.g., 'ugc_reward', 'influencer_share', 'referral_conversion'
    trigger_source: str  # e.g., 'ugc', 'influencer', 'referral_link'
    contact_id: str  # user or influencer id/handle
    channel: str  # 'whatsapp', 'email', 'sms', etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reward_type: Optional[str] = None  # e.g., 'discount', 'repost', 'affiliate_invite'
    status: Optional[str] = None  # e.g., 'sent', 'pending', 'failed'
    metadata: dict = Field(default_factory=dict) 