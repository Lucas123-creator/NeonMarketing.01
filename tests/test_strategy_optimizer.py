import pytest
from ai.strategy_optimizer import StrategyOptimizer
from optimization.content_feedback_loop import ContentFeedbackLoop
from neonhub.config.settings import get_settings

def test_strategy_optimizer_cycle(monkeypatch):
    optimizer = StrategyOptimizer()
    feedback = optimizer.content_feedback
    settings = get_settings()

    # Simulate performance logs
    feedback.performance_data = {
        'welcome_email': [
            {'template_id': 'welcome_email', 'variant_id': 'v1', 'channel': 'email', 'reply_rate': 0.25, 'open_rate': 0.5, 'click_rate': 0.1, 'timestamp': '2024-01-01T00:00:00Z'},
            {'template_id': 'welcome_email', 'variant_id': 'v2', 'channel': 'email', 'reply_rate': 0.05, 'open_rate': 0.2, 'click_rate': 0.02, 'timestamp': '2024-01-01T00:00:00Z'}
        ]
    }
    # Populate template_metadata
    feedback.analyze_performance('welcome_email')
    # Ensure the template_metadata dict exists
    if 'welcome_email' not in feedback.template_metadata:
        feedback.template_metadata['welcome_email'] = {}
    # Manually set boost_flag and archived for deterministic test
    feedback.template_metadata['welcome_email']['v1'] = {'performance_score': 0.25, 'boost_flag': True, 'archived': False}
    feedback.template_metadata['welcome_email']['v2'] = {'performance_score': 0.05, 'boost_flag': False, 'archived': True}
    # Simulate UGC spike
    monkeypatch.setattr(optimizer.ugc_detector, 'detect_ugc', lambda platform: [{}]*5 if platform=='instagram' else [{}]*3)
    # Simulate influencer scoring
    class MockProfile:
        def __init__(self, followers, engagement_rate, niche):
            self.followers = followers
            self.engagement_rate = engagement_rate
            self.niche = niche
            self.language = 'en'
            self.platform = 'instagram'
            self.region = 'US'
    monkeypatch.setattr(optimizer.influencer_scout, 'scan_social_for_influencers', lambda platform, kw, region=None: [MockProfile(12000, 0.09, 'neon')])
    monkeypatch.setattr(optimizer.influencer_scout, 'score_influencer', lambda p: {'score': 85, 'niche': p.niche, 'risk_flag': None})
    # Simulate referral event log
    optimizer.referral_trigger.event_log = [{}]*25

    # Run optimizer
    params = optimizer.analyze_and_optimize()

    # Validate template_weights
    assert params['template_weights']['v1'] == 1.0
    assert params['template_weights']['v2'] == 0.0
    # Validate offer_timing
    assert params['offer_timing']['ugc_spike'] == 'immediate'
    # Validate influencer_criteria
    assert params['influencer_criteria']['min_score'] == 60
    # Validate trigger_suppression
    assert params['trigger_suppression']['referral'] is True
    # Confirm config updated
    assert settings.strategy_params == params
    print('Optimizer params:', params) 