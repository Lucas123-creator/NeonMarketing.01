from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl

class ConnectionStatus(str, Enum):
    NOT_CONNECTED = "not_connected"
    PENDING = "pending"
    CONNECTED = "connected"
    IGNORED = "ignored"
    BLOCKED = "blocked"

class MessageStatus(str, Enum):
    NOT_SENT = "not_sent"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    REPLIED = "replied"
    FAILED = "failed"

class LinkedInMessage(BaseModel):
    message_id: str
    content: str
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    status: MessageStatus = MessageStatus.NOT_SENT
    reply_content: Optional[str] = None
    reply_at: Optional[datetime] = None
    metadata: Dict[str, str] = Field(default_factory=dict)

class LinkedInProfile(BaseModel):
    profile_id: str
    name: str
    title: str
    company: str
    company_size: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    profile_url: Optional[HttpUrl] = None
    profile_image_url: Optional[HttpUrl] = None
    about: Optional[str] = None
    experience: List[Dict[str, str]] = Field(default_factory=list)
    education: List[Dict[str, str]] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    connection_status: ConnectionStatus = ConnectionStatus.NOT_CONNECTED
    connection_request_sent_at: Optional[datetime] = None
    connected_at: Optional[datetime] = None
    messages: List[LinkedInMessage] = Field(default_factory=list)
    last_profile_visit: Optional[datetime] = None
    last_interaction: Optional[datetime] = None
    metadata: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
    def add_message(self, content: str, metadata: Optional[Dict[str, str]] = None) -> LinkedInMessage:
        """Add a new message to the profile's message history."""
        message = LinkedInMessage(
            message_id=f"msg_{len(self.messages) + 1}",
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        return message
        
    def update_connection_status(self, status: ConnectionStatus) -> None:
        """Update the connection status and relevant timestamps."""
        self.connection_status = status
        now = datetime.utcnow()
        
        if status == ConnectionStatus.PENDING:
            self.connection_request_sent_at = now
        elif status == ConnectionStatus.CONNECTED:
            self.connected_at = now
            
        self.last_interaction = now
        
    def record_profile_visit(self) -> None:
        """Record a profile visit."""
        self.last_profile_visit = datetime.utcnow()
        self.last_interaction = self.last_profile_visit
        
    def get_last_message(self) -> Optional[LinkedInMessage]:
        """Get the most recent message."""
        return self.messages[-1] if self.messages else None
        
    def has_replied(self) -> bool:
        """Check if the profile has replied to any messages."""
        return any(msg.status == MessageStatus.REPLIED for msg in self.messages)
        
    def get_reply_rate(self) -> float:
        """Calculate the reply rate for messages."""
        if not self.messages:
            return 0.0
        replied = sum(1 for msg in self.messages if msg.status == MessageStatus.REPLIED)
        return replied / len(self.messages) 