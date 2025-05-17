from typing import List, Dict, Any, Optional
from datetime import datetime
from prometheus_client import Counter
import logging
from neonhub.schemas.influencer_profile import InfluencerProfile

INFLUENCERS_SCANNED = Counter(
    'influencers_scanned_total',
    'Number of influencer profiles scanned',
    ['platform']
)
INFLUENCERS_QUALIFIED = Counter(
    'influencers_qualified_total',
    'Number of influencers qualified for outreach',
    ['platform', 'niche']
)
INFLUENCERS_QUEUED = Counter(
    'influencers_queued_total',
    'Number of influencers queued for outreach',
    ['platform', 'niche']
)

class InfluencerScout:
    def __init__(self):
        self.logger = logging.getLogger("InfluencerScout")
        self.outreach_queue: List[InfluencerProfile] = []

    def scan_social_for_influencers(self, platform: str, keywords: List[str], region: Optional[str] = None) -> List[InfluencerProfile]:
        # In production, replace with real API/scraper
        INFLUENCERS_SCANNED.labels(platform=platform).inc()
        now = datetime.utcnow()
        mock_profiles = [
            InfluencerProfile(
                name="Jane Neon",
                handle="@janeneon",
                platform=platform,
                followers=12000,
                engagement_rate=0.085,
                tags=["neon", "decor"],
                language="en",
                region=region or "US",
                niche="neon decor",
                last_scanned=now
            ),
            InfluencerProfile(
                name="LED Guru",
                handle="@ledguru",
                platform=platform,
                followers=55000,
                engagement_rate=0.025,
                tags=["led", "signs"],
                language="en",
                region=region or "US",
                niche="led signs",
                last_scanned=now
            ),
            InfluencerProfile(
                name="Event Queen",
                handle="@eventqueen",
                platform=platform,
                followers=8000,
                engagement_rate=0.12,
                tags=["events", "neon"],
                language="en",
                region=region or "US",
                niche="event signage",
                last_scanned=now
            )
        ]
        self.logger.info(f"Scanned {len(mock_profiles)} influencer profiles on {platform}")
        return mock_profiles

    def score_influencer(self, profile: InfluencerProfile) -> Dict[str, Any]:
        # Score: prioritize micro-influencers (1k-50k), high engagement
        score = 0
        risk_flag = None
        if 1000 <= profile.followers <= 50000:
            score += 40
        elif profile.followers > 50000:
            score += 10
        else:
            score += 5
        if profile.engagement_rate >= 0.08:
            score += 40
        elif profile.engagement_rate >= 0.04:
            score += 20
        else:
            score += 5
        if any(k in (profile.niche or "") for k in ["neon", "led", "event"]):
            score += 15
        if profile.engagement_rate < 0.02:
            risk_flag = "low_engagement"
        if profile.followers > 100000:
            risk_flag = "macro_influencer"
        score = min(score, 100)
        self.logger.info(f"Scored influencer {profile.handle}: {score} (risk: {risk_flag})")
        return {"score": score, "niche": profile.niche, "risk_flag": risk_flag}

    def queue_for_outreach(self, profile: InfluencerProfile, score: float):
        if score >= 60:
            profile.outreach_score = score
            profile.outreach_queued = True
            profile.outreach_tags = [profile.language or "en", profile.niche or "general", profile.platform]
            self.outreach_queue.append(profile)
            INFLUENCERS_QUALIFIED.labels(platform=profile.platform, niche=profile.niche or "general").inc()
            INFLUENCERS_QUEUED.labels(platform=profile.platform, niche=profile.niche or "general").inc()
            self.logger.info(f"Queued influencer for outreach: {profile.handle} (score: {score})")
            return True
        else:
            self.logger.info(f"Influencer {profile.handle} not qualified for outreach (score: {score})")
            return False 