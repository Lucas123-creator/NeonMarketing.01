from typing import Dict, Any, Optional
from prometheus_client import Counter, Gauge
import random
import logging
from datetime import datetime
from neonhub.config.settings import get_settings

OFFERS_SENT = Counter(
    'offers_sent_total',
    'Number of offers sent',
    ['type']
)
OFFER_CONVERSION_RATE = Gauge(
    'offer_conversion_rate',
    'Conversion rate for offer variants',
    ['variant']
)
LIFT_FROM_CRO = Gauge(
    'lift_from_cro_total',
    'Conversion lift from CRO',
    ['experiment']
)

class ConversionEngine:
    def __init__(self):
        self.logger = logging.getLogger("ConversionEngine")
        self.offer_stats: Dict[str, Dict[str, Any]] = {}  # variant -> stats
        self.control_group: Dict[str, int] = {"views": 0, "conversions": 0}
        self.experiment_group: Dict[str, int] = {"views": 0, "conversions": 0}
        self.settings = get_settings()

    def serve_offer(self, lead_state: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # Use optimizer's offer timing if available
        strategy_params = self.settings.strategy_params or {}
        offer_timing = strategy_params.get('offer_timing', {})
        if offer_timing.get('ugc_spike') == 'immediate':
            # Example: prioritize urgency offer
            offer_type = "urgency"
            offer_code = "HURRY10"
            cta_variants = ["Act Now!", "Limited Time!", "Don't Miss Out!"]
        elif lead_state.get("status") == "hesitant":
            offer_type = "urgency"
            offer_code = "HURRY10"
            cta_variants = ["Act Now!", "Limited Time!", "Don't Miss Out!"]
        elif lead_state.get("status") == "cold":
            offer_type = "reactivation"
            offer_code = "COME_BACK"
            cta_variants = ["Welcome Back!", "Here's a Special Deal!", "We Miss You!"]
        else:
            offer_type = "standard"
            offer_code = "WELCOME"
            cta_variants = ["Shop Now!", "See Offer", "Get Started"]
        # Use template_weights to prefer best CTA if available
        weights = strategy_params.get('template_weights', {})
        weighted_ctas = [(cta, weights.get(f"{offer_type}_{cta.replace(' ', '_').lower()}", 0)) for cta in cta_variants]
        weighted_ctas.sort(key=lambda x: x[1], reverse=True)
        cta = weighted_ctas[0][0] if weighted_ctas and weighted_ctas[0][1] > 0 else random.choice(cta_variants)
        variant = f"{offer_type}_{cta.replace(' ', '_').lower()}"
        OFFERS_SENT.labels(type=offer_type).inc()
        self.logger.info(f"Served offer: {offer_type}, CTA: {cta}, code: {offer_code}")
        # Track view for A/B
        self._record_offer_view(variant)
        return {
            "offer_type": offer_type,
            "offer_code": offer_code,
            "cta": cta,
            "variant": variant
        }

    def record_conversion(self, variant: str, is_experiment: bool):
        # Track conversion for variant and group
        self._record_offer_conversion(variant)
        if is_experiment:
            self.experiment_group["conversions"] += 1
        else:
            self.control_group["conversions"] += 1
        self.logger.info(f"Conversion recorded for variant: {variant}, experiment: {is_experiment}")
        self._update_lift()

    def _record_offer_view(self, variant: str):
        stats = self.offer_stats.setdefault(variant, {"views": 0, "conversions": 0})
        stats["views"] += 1
        self._update_conversion_rate(variant)
        # Randomly assign to control/experiment for test
        if random.random() < 0.5:
            self.control_group["views"] += 1
        else:
            self.experiment_group["views"] += 1

    def _record_offer_conversion(self, variant: str):
        stats = self.offer_stats.setdefault(variant, {"views": 0, "conversions": 0})
        stats["conversions"] += 1
        self._update_conversion_rate(variant)

    def _update_conversion_rate(self, variant: str):
        stats = self.offer_stats[variant]
        rate = stats["conversions"] / stats["views"] if stats["views"] else 0.0
        OFFER_CONVERSION_RATE.labels(variant=variant).set(rate)

    def _update_lift(self):
        control_rate = self.control_group["conversions"] / self.control_group["views"] if self.control_group["views"] else 0.0
        exp_rate = self.experiment_group["conversions"] / self.experiment_group["views"] if self.experiment_group["views"] else 0.0
        lift = exp_rate - control_rate
        LIFT_FROM_CRO.labels(experiment="offer_ab").set(lift)
        self.logger.info(f"CRO lift updated: {lift}")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "offer_stats": self.offer_stats,
            "control_group": self.control_group,
            "experiment_group": self.experiment_group
        } 