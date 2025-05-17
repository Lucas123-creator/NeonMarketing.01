from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class LeadStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    UNSUBSCRIBED = "unsubscribed"
    FAILED = "failed"

class EngagementEvent(BaseModel):
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, str] = Field(default_factory=dict)
    score_delta: int = 0

class SequenceStage(BaseModel):
    stage_id: str
    template_id: str
    delay_hours: int
    completed_at: Optional[datetime] = None
    status: str = "pending"
    attempts: int = 0
    max_attempts: int = 3

class LeadState(BaseModel):
    lead_id: str
    campaign_id: str
    current_stage: int = 0
    status: LeadStatus = LeadStatus.ACTIVE
    engagement_score: int = 0
    last_touch: datetime = Field(default_factory=datetime.utcnow)
    sequence_stages: List[SequenceStage]
    engagement_history: List[EngagementEvent] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None
    source_platform: Optional[str] = None
    last_campaign_engaged: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
    def add_engagement_event(self, event_type: str, score_delta: int, metadata: Optional[Dict[str, str]] = None) -> None:
        """Add a new engagement event and update the score."""
        event = EngagementEvent(
            event_type=event_type,
            score_delta=score_delta,
            metadata=metadata or {}
        )
        self.engagement_history.append(event)
        self.engagement_score += score_delta
        self.last_touch = event.timestamp
        
    def get_next_stage(self) -> Optional[SequenceStage]:
        """Get the next pending stage in the sequence."""
        if self.current_stage >= len(self.sequence_stages):
            return None
        return self.sequence_stages[self.current_stage]
        
    def complete_current_stage(self) -> None:
        """Mark the current stage as completed and move to the next."""
        if self.current_stage < len(self.sequence_stages):
            self.sequence_stages[self.current_stage].completed_at = datetime.utcnow()
            self.sequence_stages[self.current_stage].status = "completed"
            self.current_stage += 1
            
    def should_pause(self, min_score: int = 0) -> bool:
        """Check if the lead should be paused based on engagement score."""
        return self.engagement_score < min_score
        
    def should_retry_stage(self) -> bool:
        """Check if the current stage should be retried."""
        if self.current_stage >= len(self.sequence_stages):
            return False
        current = self.sequence_stages[self.current_stage]
        return current.attempts < current.max_attempts
        
    def increment_attempts(self) -> None:
        """Increment the attempts counter for the current stage."""
        if self.current_stage < len(self.sequence_stages):
            self.sequence_stages[self.current_stage].attempts += 1 