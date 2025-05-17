import re
from typing import List, Dict, Any
from prometheus_client import Counter
from datetime import datetime
import logging

# Prometheus metrics
UGC_DETECTED = Counter(
    'ugc_detected_total',
    'Number of UGC posts detected',
    ['platform', 'hashtag']
)
UGC_PROMOTED = Counter(
    'ugc_promoted_total',
    'Number of UGC posts promoted',
    ['platform', 'hashtag']
)

class UGCDetector:
    """Detects and scores user-generated content (UGC) from social platforms."""
    def __init__(self, brand_keywords=None, hashtags=None):
        self.brand_keywords = brand_keywords or ["neonhub", "neonsigns", "neonhubai"]
        self.hashtags = hashtags or ["#neonhub", "#neonsigns", "#neonhubai"]
        self.logger = logging.getLogger("UGCDetector")

    def _mock_scrape(self, platform: str) -> List[Dict[str, Any]]:
        # In production, replace with real API/scraper
        now = datetime.utcnow().isoformat()
        return [
            {
                "platform": platform,
                "user": "@user1",
                "content": "Loving my new sign from #neonhub!",
                "hashtags": ["#neonhub"],
                "mentions": ["@neonhub"],
                "likes": 120,
                "comments": 10,
                "timestamp": now,
                "url": "https://instagram.com/p/abc123"
            },
            {
                "platform": platform,
                "user": "@user2",
                "content": "Check out these neon vibes! #neonsigns",
                "hashtags": ["#neonsigns"],
                "mentions": [],
                "likes": 45,
                "comments": 2,
                "timestamp": now,
                "url": "https://tiktok.com/@user2/video/xyz456"
            }
        ]

    def detect_ugc(self, platform: str) -> List[Dict[str, Any]]:
        posts = self._mock_scrape(platform)
        detected = []
        for post in posts:
            if any(h in post["hashtags"] for h in self.hashtags) or \
               any(re.search(rf"\\b{k}\\b", post["content"], re.IGNORECASE) for k in self.brand_keywords):
                score = self.score_ugc(post)
                post["ugc_score"] = score
                detected.append(post)
                for h in post["hashtags"]:
                    if h in self.hashtags:
                        UGC_DETECTED.labels(platform=platform, hashtag=h).inc()
                self.logger.info(f"UGC detected: {post['url']} score={score}")
        return detected

    def score_ugc(self, post: Dict[str, Any]) -> float:
        # Simple scoring: likes + 2*comments, bonus for brand mention
        score = post.get("likes", 0) + 2 * post.get("comments", 0)
        if any(k in post["content"].lower() for k in self.brand_keywords):
            score += 20
        return score

    def promote_ugc(self, post: Dict[str, Any]):
        # In production, trigger reward, repost, or message
        for h in post["hashtags"]:
            if h in self.hashtags:
                UGC_PROMOTED.labels(platform=post["platform"], hashtag=h).inc()
        self.logger.info(f"UGC promoted: {post['url']}")
        return True 