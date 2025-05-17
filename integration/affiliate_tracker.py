import logging
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime

class AffiliateTracker:
    def __init__(self):
        self.referrals: List[Dict] = []
        self.affiliate_scores: Dict[str, int] = defaultdict(int)
        self.logger = logging.getLogger("AffiliateTracker")

    def log_referral(self, affiliate_code: str, lead_id: str, source_url: str, timestamp: Optional[datetime] = None):
        event = {
            "affiliate_code": affiliate_code,
            "lead_id": lead_id,
            "source_url": source_url,
            "timestamp": timestamp or datetime.utcnow()
        }
        self.referrals.append(event)
        self.affiliate_scores[affiliate_code] += 1
        self.logger.info(f"Logged referral for {affiliate_code}")

    def get_affiliate_score(self, affiliate_code: str) -> int:
        return self.affiliate_scores.get(affiliate_code, 0)

    def reward_affiliate(self, affiliate_code: str, reward: str):
        self.logger.info(f"Rewarded affiliate {affiliate_code} with {reward}")
        # Extend: integrate with payout system 