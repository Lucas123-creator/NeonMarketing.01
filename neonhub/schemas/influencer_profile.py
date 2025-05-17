from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class InfluencerProfile(BaseModel):
    name: str
    handle: str
    platform: str
    followers: int
    engagement_rate: float
    tags: List[str] = Field(default_factory=list)
    language: Optional[str] = None
    region: Optional[str] = None
    niche: Optional[str] = None
    last_scanned: Optional[datetime] = None
    risk_flag: Optional[str] = None
    outreach_score: Optional[float] = None
    outreach_queued: bool = False
    outreach_tags: List[str] = Field(default_factory=list) 