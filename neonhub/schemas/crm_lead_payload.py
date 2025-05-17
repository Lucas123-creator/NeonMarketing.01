from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class CRMLeadPayload(BaseModel):
    lead_id: str
    email: str
    phone: Optional[str] = None
    name: Optional[str] = None
    company: Optional[str] = None
    engagement_score: float
    engagement_history: List[Dict[str, Any]] = Field(default_factory=list)
    ugc_posts: List[Dict[str, Any]] = Field(default_factory=list)
    trigger_history: List[Dict[str, Any]] = Field(default_factory=list)
    offer_response: Optional[Dict[str, Any]] = None
    handoff_time: datetime = Field(default_factory=datetime.utcnow)
    handoff_status: str = "pending"
    crm_destination: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict) 