from typing import Dict, Optional
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge
import json
from pathlib import Path

from ..schemas.lead_state import LeadState, EngagementEvent
from ..utils.logging import get_logger
from ..config.settings import get_settings
from neonhub.services.trigger_manager import TriggerManager

# Prometheus metrics
ENGAGEMENT_EVENTS = Counter(
    'neonhub_engagement_events_total',
    'Number of engagement events by type',
    ['event_type']
)

LEAD_SCORES = Gauge(
    'neonhub_lead_scores',
    'Current engagement scores for leads',
    ['lead_id', 'campaign_id']
)

ENGAGEMENT_DURATION = Histogram(
    'neonhub_engagement_duration_seconds',
    'Time between engagement events',
    ['event_type']
)

class EngagementTracker:
    """Service for tracking and scoring lead engagement."""
    
    # Engagement scoring rules
    SCORE_RULES = {
        "email_open": 1,
        "email_click": 3,
        "email_reply": 5,
        "unsubscribe": -10,
        "bounce": -5,
        "spam_report": -15
    }
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger()
        self.states_dir = Path("data/lead_states")
        self.states_dir.mkdir(parents=True, exist_ok=True)
        self.trigger_manager = TriggerManager()
        
    def _get_state_path(self, lead_id: str) -> Path:
        """Get the path for a lead's state file."""
        return self.states_dir / f"{lead_id}.json"
        
    def get_lead_state(self, lead_id: str) -> Optional[LeadState]:
        """Load a lead's state from disk."""
        state_path = self._get_state_path(lead_id)
        if not state_path.exists():
            return None
            
        try:
            with open(state_path, "r") as f:
                data = json.load(f)
                return LeadState(**data)
        except Exception as e:
            self.logger.error(
                "Failed to load lead state",
                lead_id=lead_id,
                error=str(e)
            )
            return None
            
    def save_lead_state(self, state: LeadState) -> None:
        """Save a lead's state to disk."""
        try:
            state_path = self._get_state_path(state.lead_id)
            with open(state_path, "w") as f:
                json.dump(state.dict(), f, indent=2)
        except Exception as e:
            self.logger.error(
                "Failed to save lead state",
                lead_id=state.lead_id,
                error=str(e)
            )
            
    async def track_event(
        self,
        lead_id: str,
        event_type: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> None:
        """Track an engagement event and update the lead's score."""
        state = self.get_lead_state(lead_id)
        if not state:
            self.logger.warning(
                "Lead state not found for event",
                lead_id=lead_id,
                event_type=event_type
            )
            return
            
        # Get score delta from rules
        score_delta = self.SCORE_RULES.get(event_type, 0)
        
        # Add event and update score
        state.add_engagement_event(event_type, score_delta, metadata)
        
        # Update metrics
        ENGAGEMENT_EVENTS.labels(event_type=event_type).inc()
        LEAD_SCORES.labels(
            lead_id=lead_id,
            campaign_id=state.campaign_id
        ).set(state.engagement_score)
        
        # Save updated state
        self.save_lead_state(state)
        
        # Log event
        self.logger.info(
            "Engagement event tracked",
            lead_id=lead_id,
            event_type=event_type,
            score_delta=score_delta,
            new_score=state.engagement_score
        )
        
        # --- Trigger System Integration ---
        try:
            updated_state = self.get_lead_state(lead_id)
            trigger_result = self.trigger_manager.evaluate_and_trigger(updated_state)
            self.logger.info(
                "Trigger evaluation after engagement event",
                lead_id=lead_id,
                event_type=event_type,
                score_delta=score_delta,
                trigger_result=str(trigger_result)
            )
        except Exception as e:
            self.logger.error(
                "Trigger evaluation failed after engagement event",
                lead_id=lead_id,
                event_type=event_type,
                error=str(e)
            )
        
    async def get_lead_score(self, lead_id: str) -> int:
        """Get a lead's current engagement score."""
        state = self.get_lead_state(lead_id)
        return state.engagement_score if state else 0
        
    async def should_pause_lead(self, lead_id: str, min_score: int = 0) -> bool:
        """Check if a lead should be paused based on engagement score."""
        state = self.get_lead_state(lead_id)
        if not state:
            return False
        return state.should_pause(min_score)
        
    async def get_engagement_history(self, lead_id: str) -> list:
        """Get a lead's engagement history."""
        state = self.get_lead_state(lead_id)
        if not state:
            return []
        return [event.dict() for event in state.engagement_history]
        
    async def reset_lead_score(self, lead_id: str) -> None:
        """Reset a lead's engagement score."""
        state = self.get_lead_state(lead_id)
        if not state:
            return
            
        state.engagement_score = 0
        state.engagement_history = []
        self.save_lead_state(state)
        
        # Update metrics
        LEAD_SCORES.labels(
            lead_id=lead_id,
            campaign_id=state.campaign_id
        ).set(0)
        
        self.logger.info(
            "Lead score reset",
            lead_id=lead_id
        ) 