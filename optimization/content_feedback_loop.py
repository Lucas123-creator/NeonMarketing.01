from typing import Dict, Any, List, Optional
from prometheus_client import Gauge, Counter
import statistics
import logging
from datetime import datetime

CONTENT_PERFORMANCE_SCORE = Gauge(
    'content_performance_score',
    'Performance score for content variants',
    ['template_id', 'variant_id', 'channel']
)
HIGH_PERFORMERS_PROMOTED = Counter(
    'high_performers_promoted_total',
    'Number of high-performing content variants promoted',
    ['template_id', 'variant_id', 'channel']
)
LOW_PERFORMERS_ARCHIVED = Counter(
    'low_performers_archived_total',
    'Number of low-performing content variants archived',
    ['template_id', 'variant_id', 'channel']
)

class ContentFeedbackLoop:
    def __init__(self):
        self.logger = logging.getLogger("ContentFeedbackLoop")
        self.performance_data: Dict[str, List[Dict[str, Any]]] = {}  # template_id -> list of variant stats
        self.template_metadata: Dict[str, Dict[str, Any]] = {}  # template_id -> variant_id -> metadata

    def record_performance(self, template_id: str, variant_id: str, channel: str, reply_rate: float, open_rate: float, click_rate: float):
        # Store stats for analysis
        key = f"{template_id}:{variant_id}:{channel}"
        entry = {
            "template_id": template_id,
            "variant_id": variant_id,
            "channel": channel,
            "reply_rate": reply_rate,
            "open_rate": open_rate,
            "click_rate": click_rate,
            "timestamp": datetime.utcnow()
        }
        self.performance_data.setdefault(template_id, []).append(entry)
        CONTENT_PERFORMANCE_SCORE.labels(template_id=template_id, variant_id=variant_id, channel=channel).set(reply_rate)
        self.logger.info(f"Recorded performance for {key}: reply_rate={reply_rate}")

    def analyze_performance(self, template_id: str) -> Dict[str, Any]:
        # Analyze all variants for a template
        stats = self.performance_data.get(template_id, [])
        if not stats:
            return {}
        reply_rates = [s["reply_rate"] for s in stats]
        avg = statistics.mean(reply_rates)
        stddev = statistics.stdev(reply_rates) if len(reply_rates) > 1 else 0
        high_performers = [s for s in stats if s["reply_rate"] > avg + stddev]
        low_performers = [s for s in stats if s["reply_rate"] < avg - stddev]
        for s in high_performers:
            self._mark_boosted(s)
        for s in low_performers:
            self._mark_archived(s)
        return {
            "avg": avg,
            "stddev": stddev,
            "high_performers": high_performers,
            "low_performers": low_performers
        }

    def _mark_boosted(self, stat: Dict[str, Any]):
        tid, vid, ch = stat["template_id"], stat["variant_id"], stat["channel"]
        self.template_metadata.setdefault(tid, {})[vid] = {
            "performance_score": stat["reply_rate"],
            "boost_flag": True,
            "archived": False
        }
        HIGH_PERFORMERS_PROMOTED.labels(template_id=tid, variant_id=vid, channel=ch).inc()
        self.logger.info(f"Boosted content: {tid}:{vid}:{ch}")

    def _mark_archived(self, stat: Dict[str, Any]):
        tid, vid, ch = stat["template_id"], stat["variant_id"], stat["channel"]
        self.template_metadata.setdefault(tid, {})[vid] = {
            "performance_score": stat["reply_rate"],
            "boost_flag": False,
            "archived": True
        }
        LOW_PERFORMERS_ARCHIVED.labels(template_id=tid, variant_id=vid, channel=ch).inc()
        self.logger.info(f"Archived content: {tid}:{vid}:{ch}")

    def get_best_variant(self, template_id: str, channel: str) -> Optional[str]:
        # Return the variant_id with boost_flag for this template/channel
        variants = self.template_metadata.get(template_id, {})
        for vid, meta in variants.items():
            if meta.get("boost_flag") and not meta.get("archived"):
                return vid
        return None

    def get_archived_variants(self, template_id: str) -> List[str]:
        variants = self.template_metadata.get(template_id, {})
        return [vid for vid, meta in variants.items() if meta.get("archived")] 