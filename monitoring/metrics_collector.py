from typing import Dict, Any
from prometheus_client import REGISTRY

class MetricsCollector:
    """Collects and summarizes system KPIs from Prometheus metrics."""
    def __init__(self):
        pass

    def get_metric(self, name: str) -> Any:
        for metric in REGISTRY.collect():
            if metric.name == name:
                return metric
        return None

    def summarize_email_metrics(self) -> Dict[str, Any]:
        open_rate = self._get_rate('neonhub_engagement_events_total', 'email_open')
        click_rate = self._get_rate('neonhub_engagement_events_total', 'email_click')
        reply_rate = self._get_rate('neonhub_engagement_events_total', 'email_reply')
        unsub_rate = self._get_rate('neonhub_engagement_events_total', 'unsubscribe')
        return {
            "open_rate": open_rate,
            "click_rate": click_rate,
            "reply_rate": reply_rate,
            "unsubscribe_rate": unsub_rate
        }

    def summarize_linkedin_metrics(self) -> Dict[str, Any]:
        connect = self._get_count('neonhub_linkedin_connections_sent_total', 'success')
        replies = self._get_count('neonhub_linkedin_replies_received_total')
        return {
            "connections_sent": connect,
            "replies_received": replies,
            "accept_rate": self._safe_div(replies, connect)
        }

    def summarize_content_metrics(self) -> Dict[str, Any]:
        # Placeholder for content metrics
        return {}

    def _get_rate(self, metric_name: str, event_type: str) -> float:
        metric = self.get_metric(metric_name)
        if not metric:
            return 0.0
        for sample in metric.samples:
            if sample.labels.get('event_type') == event_type:
                return float(sample.value)
        return 0.0

    def _get_count(self, metric_name: str, label_value: str = None) -> int:
        metric = self.get_metric(metric_name)
        if not metric:
            return 0
        for sample in metric.samples:
            if not label_value or label_value in sample.labels.values():
                return int(sample.value)
        return 0

    def _safe_div(self, a, b):
        try:
            return float(a) / float(b) if b else 0.0
        except Exception:
            return 0.0 