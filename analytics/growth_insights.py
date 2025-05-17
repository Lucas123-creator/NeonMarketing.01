from typing import List, Dict, Any
from growth.ugc_detector import UGCDetector
from growth.influencer_scout import InfluencerScout
from growth.referral_trigger import ReferralTrigger
from optimization.content_feedback_loop import ContentFeedbackLoop

class GrowthInsights:
    def __init__(self):
        self.ugc_detector = UGCDetector()
        self.influencer_scout = InfluencerScout()
        self.referral_trigger = ReferralTrigger()
        self.content_feedback = ContentFeedbackLoop()

    def get_ugc_feed(self, limit: int = 20) -> List[Dict[str, Any]]:
        # In production, aggregate from DB or cache
        ugc = []
        for platform in ["instagram", "tiktok", "pinterest"]:
            ugc.extend(self.ugc_detector.detect_ugc(platform))
        ugc = sorted(ugc, key=lambda x: x.get("ugc_score", 0), reverse=True)
        return ugc[:limit]

    def get_influencers(self, limit: int = 20) -> List[Dict[str, Any]]:
        # In production, aggregate from DB or cache
        influencers = []
        for platform in ["instagram", "tiktok", "youtube"]:
            profiles = self.influencer_scout.scan_social_for_influencers(platform, ["neon", "led", "event"])
            for p in profiles:
                score_info = self.influencer_scout.score_influencer(p)
                influencers.append({**p.dict(), **score_info})
        influencers = sorted(influencers, key=lambda x: x.get("score", 0), reverse=True)
        return influencers[:limit]

    def get_referrals(self, limit: int = 20) -> List[Dict[str, Any]]:
        # In production, aggregate from DB or cache
        return [e.dict() for e in self.referral_trigger.event_log][-limit:][::-1]

    def get_top_content(self, limit: int = 10) -> List[Dict[str, Any]]:
        # In production, aggregate from metrics or DB
        top = []
        for template_id, variants in self.content_feedback.template_metadata.items():
            for variant_id, meta in variants.items():
                if meta.get("boost_flag") and not meta.get("archived"):
                    top.append({
                        "template_id": template_id,
                        "variant_id": variant_id,
                        "performance_score": meta.get("performance_score"),
                        "channel": "email",  # Placeholder
                        "boosted": True
                    })
        top = sorted(top, key=lambda x: x.get("performance_score", 0), reverse=True)
        return top[:limit] 