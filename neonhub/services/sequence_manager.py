from typing import Dict, List, Optional
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram
import json
from pathlib import Path

from ..schemas.lead_state import LeadState, SequenceStage, LeadStatus
from ..services.content_personalizer import ContentPersonalizer
from ..services.engagement_tracker import EngagementTracker
from ..utils.logging import get_logger
from ..config.settings import get_settings
from neonhub.services.trigger_manager import TriggerManager

# Prometheus metrics
SEQUENCE_PROGRESS = Counter(
    'neonhub_sequence_progress_total',
    'Number of leads progressing through sequence stages',
    ['campaign_id', 'stage_id']
)

SEQUENCE_DURATION = Histogram(
    'neonhub_sequence_duration_seconds',
    'Time spent in sequence stages',
    ['campaign_id', 'stage_id']
)

class SequenceManager:
    """Service for managing multi-stage outreach sequences."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger()
        self.content_personalizer = ContentPersonalizer()
        self.engagement_tracker = EngagementTracker()
        self.sequences_dir = Path("data/sequences")
        self.sequences_dir.mkdir(parents=True, exist_ok=True)
        self.trigger_manager = TriggerManager()
        
    def _get_sequence_path(self, campaign_id: str) -> Path:
        """Get the path for a campaign's sequence file."""
        return self.sequences_dir / f"{campaign_id}.json"
        
    def get_sequence(self, campaign_id: str) -> Optional[Dict]:
        """Load a campaign sequence from disk."""
        sequence_path = self._get_sequence_path(campaign_id)
        if not sequence_path.exists():
            return None
            
        try:
            with open(sequence_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(
                "Failed to load sequence",
                campaign_id=campaign_id,
                error=str(e)
            )
            return None
            
    def save_sequence(self, campaign_id: str, sequence: Dict) -> None:
        """Save a campaign sequence to disk."""
        try:
            sequence_path = self._get_sequence_path(campaign_id)
            with open(sequence_path, "w") as f:
                json.dump(sequence, f, indent=2)
        except Exception as e:
            self.logger.error(
                "Failed to save sequence",
                campaign_id=campaign_id,
                error=str(e)
            )
            
    async def initialize_lead_sequence(
        self,
        lead_id: str,
        campaign_id: str,
        sequence: Dict
    ) -> LeadState:
        """Initialize a lead's sequence state."""
        # Create sequence stages
        stages = []
        for stage in sequence["stages"]:
            stages.append(SequenceStage(
                stage_id=stage["id"],
                template_id=stage["template_id"],
                delay_hours=stage["delay_hours"],
                max_attempts=stage.get("max_attempts", 3)
            ))
            
        # Create lead state
        state = LeadState(
            lead_id=lead_id,
            campaign_id=campaign_id,
            sequence_stages=stages
        )
        
        # Save initial state
        self.engagement_tracker.save_lead_state(state)
        
        self.logger.info(
            "Lead sequence initialized",
            lead_id=lead_id,
            campaign_id=campaign_id
        )
        
        return state
        
    async def get_next_action(
        self,
        lead_id: str,
        campaign_id: str
    ) -> Optional[Dict]:
        """Get the next action for a lead in their sequence."""
        state = self.engagement_tracker.get_lead_state(lead_id)
        if not state or state.status != LeadStatus.ACTIVE:
            return None
            
        # Get current stage
        current_stage = state.get_next_stage()
        if not current_stage:
            state.status = LeadStatus.COMPLETED
            self.engagement_tracker.save_lead_state(state)
            return None
            
        # Check if we should wait for delay
        if current_stage.completed_at:
            delay_until = current_stage.completed_at + timedelta(hours=current_stage.delay_hours)
            if datetime.utcnow() < delay_until:
                return None
                
        # Check if lead should be paused
        if await self.engagement_tracker.should_pause_lead(lead_id):
            state.status = LeadStatus.PAUSED
            self.engagement_tracker.save_lead_state(state)
            return None
            
        # Get content for next action
        content = await self.content_personalizer.generate_content(
            current_stage.template_id,
            {"lead_id": lead_id},
            "segment_score"
        )
        
        # Update metrics
        SEQUENCE_PROGRESS.labels(
            campaign_id=campaign_id,
            stage_id=current_stage.stage_id
        ).inc()
        
        return {
            "stage_id": current_stage.stage_id,
            "template_id": current_stage.template_id,
            "content": content,
            "metadata": {
                "lead_id": lead_id,
                "campaign_id": campaign_id,
                "stage": current_stage.stage_id,
                "attempt": current_stage.attempts + 1
            }
        }
        
    async def complete_stage(
        self,
        lead_id: str,
        campaign_id: str,
        success: bool = True
    ) -> None:
        """Mark a stage as completed and update lead state."""
        state = self.engagement_tracker.get_lead_state(lead_id)
        if not state:
            return
            
        if success:
            state.complete_current_stage()
            
            # Check if sequence is complete
            if state.current_stage >= len(state.sequence_stages):
                state.status = LeadStatus.COMPLETED
        else:
            state.increment_attempts()
            
            # Check if max attempts reached
            if not state.should_retry_stage():
                state.status = LeadStatus.FAILED
                
        self.engagement_tracker.save_lead_state(state)
        
        self.logger.info(
            "Stage completed",
            lead_id=lead_id,
            campaign_id=campaign_id,
            success=success,
            new_status=state.status
        )
        
        # --- Trigger System Integration ---
        try:
            latest_state = self.engagement_tracker.get_lead_state(lead_id)
            self.trigger_manager.evaluate_and_trigger(latest_state)
            self.logger.info(
                "Trigger evaluation after stage advancement",
                lead_id=lead_id,
                campaign_id=campaign_id,
                stage=latest_state.current_stage,
                status=latest_state.status
            )
        except Exception as e:
            self.logger.error(
                "Trigger evaluation failed after stage advancement",
                lead_id=lead_id,
                campaign_id=campaign_id,
                error=str(e)
            )
        
    async def pause_sequence(self, lead_id: str) -> None:
        """Pause a lead's sequence."""
        state = self.engagement_tracker.get_lead_state(lead_id)
        if not state:
            return
            
        state.status = LeadStatus.PAUSED
        self.engagement_tracker.save_lead_state(state)
        
        self.logger.info(
            "Sequence paused",
            lead_id=lead_id,
            campaign_id=state.campaign_id
        )
        
    async def resume_sequence(self, lead_id: str) -> None:
        """Resume a lead's sequence."""
        state = self.engagement_tracker.get_lead_state(lead_id)
        if not state or state.status != LeadStatus.PAUSED:
            return
            
        state.status = LeadStatus.ACTIVE
        self.engagement_tracker.save_lead_state(state)
        
        self.logger.info(
            "Sequence resumed",
            lead_id=lead_id,
            campaign_id=state.campaign_id
        )
        
    async def terminate_sequence(
        self,
        lead_id: str,
        reason: str = "manual"
    ) -> None:
        """Terminate a lead's sequence."""
        state = self.engagement_tracker.get_lead_state(lead_id)
        if not state:
            return
            
        state.status = LeadStatus.UNSUBSCRIBED
        self.engagement_tracker.save_lead_state(state)
        
        self.logger.info(
            "Sequence terminated",
            lead_id=lead_id,
            campaign_id=state.campaign_id,
            reason=reason
        ) 