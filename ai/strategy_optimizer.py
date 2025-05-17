import time
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram
from neonhub.config.settings import get_settings
from optimization.content_feedback_loop import ContentFeedbackLoop
from growth.ugc_detector import UGCDetector
from growth.influencer_scout import InfluencerScout
from growth.referral_trigger import ReferralTrigger
from neonhub.utils.logging import get_logger

# Prometheus metrics
STRATEGY_UPDATES_TOTAL = Counter(
    'strategy_updates_total',
    'Total number of strategy updates performed'
)
AI_WEIGHT_SHIFTS_TOTAL = Counter(
    'ai_weight_shifts_total',
    'Number of AI-driven weight shifts',
    ['strategy', 'source']
)
OPTIMIZER_CYCLE_DURATION = Histogram(
    'optimizer_cycle_duration_seconds',
    'Duration of optimizer cycle in seconds'
)

class StrategyOptimizer:
    def __init__(self):
        self.logger = get_logger()
        self.settings = get_settings()
        self.content_feedback = ContentFeedbackLoop()
        self.ugc_detector = UGCDetector()
        self.influencer_scout = InfluencerScout()
        self.referral_trigger = ReferralTrigger()
        self.strategy_params = {
            'template_weights': {},
            'offer_timing': {},
            'trigger_suppression': {},
            'influencer_criteria': {}
        }

    def analyze_and_optimize(self):
        start = time.time()
        # 1. Analyze content feedback
        for template_id, variants in self.content_feedback.template_metadata.items():
            for variant_id, meta in variants.items():
                if meta.get('boost_flag'):
                    self.strategy_params['template_weights'][variant_id] = 1.0
                    AI_WEIGHT_SHIFTS_TOTAL.labels(strategy='template', source='content').inc()
                elif meta.get('archived'):
                    self.strategy_params['template_weights'][variant_id] = 0.0
                    AI_WEIGHT_SHIFTS_TOTAL.labels(strategy='template', source='content').inc()
        # 2. Analyze UGC engagement (mock: boost timing if UGC spikes)
        ugc_feed = []
        for platform in ['instagram', 'tiktok', 'pinterest']:
            ugc_feed.extend(self.ugc_detector.detect_ugc(platform))
        if len(ugc_feed) > 10:
            self.strategy_params['offer_timing']['ugc_spike'] = 'immediate'
            AI_WEIGHT_SHIFTS_TOTAL.labels(strategy='offer_timing', source='ugc').inc()
        # 3. Analyze influencer conversions (mock: adjust criteria)
        influencers = []
        for platform in ['instagram', 'tiktok', 'youtube']:
            influencers.extend(self.influencer_scout.scan_social_for_influencers(platform, ['neon', 'led', 'event']))
        # Example: if high conversion, lower threshold
        for inf in influencers:
            score_info = self.influencer_scout.score_influencer(inf)
            if score_info['score'] > 80:
                self.strategy_params['influencer_criteria']['min_score'] = 60
                AI_WEIGHT_SHIFTS_TOTAL.labels(strategy='influencer', source='conversion').inc()
        # 4. Analyze referral triggers (mock: suppress if too frequent)
        if hasattr(self.referral_trigger, 'event_log') and len(self.referral_trigger.event_log) > 20:
            self.strategy_params['trigger_suppression']['referral'] = True
            AI_WEIGHT_SHIFTS_TOTAL.labels(strategy='trigger', source='referral').inc()
        # 5. Output to config update pipeline (here: update settings in-memory)
        self._update_config()
        STRATEGY_UPDATES_TOTAL.inc()
        OPTIMIZER_CYCLE_DURATION.observe(time.time() - start)
        self.logger.info('Strategy optimization cycle complete', params=self.strategy_params)
        return self.strategy_params

    def _update_config(self):
        # In production, push to DB, config file, or distributed cache
        # Here, we update the settings object in-memory (mock)
        self.settings.strategy_params = self.strategy_params

    def get_strategy_params(self) -> Dict[str, Any]:
        return self.strategy_params 