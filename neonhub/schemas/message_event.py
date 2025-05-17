from typing import Optional, Dict
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class MessageChannel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    SMS = "sms"
    WHATSAPP = "whatsapp"

class MessageType(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"
    REPLY = "reply"
    OPT_OUT = "opt_out"

class MessageStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    REPLIED = "replied"
    OPTED_OUT = "opted_out"

class MessageEvent(BaseModel):
    message_id: str
    lead_id: str
    channel: MessageChannel
    type: MessageType
    status: MessageStatus = MessageStatus.QUEUED
    content: Optional[str] = None
    response_text: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    opt_out_at: Optional[datetime] = None
    metadata: Dict[str, str] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        } 