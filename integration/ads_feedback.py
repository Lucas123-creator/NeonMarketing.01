import logging
from typing import Dict, List, Any
from collections import defaultdict, Counter

class AdsFeedback:
    def __init__(self):
        self.ad_events: List[Dict[str, Any]] = []
        self.performance_by_theme: Dict[str, List[float]] = defaultdict(list)
        self.logger = logging.getLogger("AdsFeedback")

    def log_ad_event(self, creative_id: str, region: str, channel: str, theme: str, clicks: int, conversions: int, spend: float):
        ctr = clicks / max(1, spend)
        cvr = conversions / max(1, clicks)
        self.ad_events.append({
            "creative_id": creative_id,
            "region": region,
            "channel": channel,
            "theme": theme,
            "clicks": clicks,
            "conversions": conversions,
            "spend": spend,
            "ctr": ctr,
            "cvr": cvr
        })
        self.performance_by_theme[theme].append(cvr)
        self.logger.info(f"Logged ad event for {creative_id} theme={theme}")

    def get_top_themes(self, top_n: int = 3) -> List[str]:
        # Return top N themes by average conversion rate
        avg_cvr = {theme: sum(cvr_list)/len(cvr_list) for theme, cvr_list in self.performance_by_theme.items() if cvr_list}
        return sorted(avg_cvr, key=avg_cvr.get, reverse=True)[:top_n] 