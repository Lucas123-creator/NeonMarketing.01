from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
from prometheus_client import Counter, Histogram
import requests

from ..schemas.linkedin_lead import LinkedInProfile, ConnectionStatus, MessageStatus
from ..services.content_personalizer import ContentPersonalizer
from ..services.engagement_tracker import EngagementTracker
from ..utils.logging import get_logger
from ..config.settings import get_settings

# Prometheus metrics
CONNECTIONS_SENT = Counter(
    'neonhub_linkedin_connections_sent_total',
    'Number of LinkedIn connection requests sent',
    ['status']
)

MESSAGES_SENT = Counter(
    'neonhub_linkedin_messages_sent_total',
    'Number of LinkedIn messages sent',
    ['status']
)

REPLIES_RECEIVED = Counter(
    'neonhub_linkedin_replies_received_total',
    'Number of LinkedIn message replies received'
)

ENGAGEMENT_DURATION = Histogram(
    'neonhub_linkedin_engagement_duration_seconds',
    'Time spent on LinkedIn engagement actions',
    ['action']
)

class LinkedInEngager:
    """Agent for managing LinkedIn engagement and messaging."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger()
        self.content_personalizer = ContentPersonalizer()
        self.engagement_tracker = EngagementTracker()
        
        # Initialize API client
        self.phantom_buster_key = self.settings.phantombuster_api_key
        
        # Rate limiting
        self.max_connections_per_day = 100
        self.max_messages_per_day = 50
        self.connection_cooldown = timedelta(hours=24)
        self.message_cooldown = timedelta(hours=12)
        
    async def send_connection_request(
        self,
        profile: LinkedInProfile,
        message: Optional[str] = None
    ) -> bool:
        """Send a LinkedIn connection request."""
        with ENGAGEMENT_DURATION.labels(action="connection").time():
            try:
                # Check rate limits
                if not await self._check_connection_limits():
                    self.logger.warning(
                        "Connection request rate limit reached",
                        profile_id=profile.profile_id
                    )
                    return False
                    
                # Generate personalized message if not provided
                if not message:
                    message = await self.content_personalizer.generate_content(
                        "linkedin_connection_request",
                        {
                            "name": profile.name,
                            "title": profile.title,
                            "company": profile.company
                        }
                    )
                    
                # Send connection request via PhantomBuster
                response = requests.post(
                    "https://api.phantombuster.com/api/v2/agents/launch",
                    headers={"X-Phantombuster-Key": self.phantom_buster_key},
                    json={
                        "id": "linkedin-connection-requester",
                        "argument": {
                            "profileUrl": profile.profile_url,
                            "message": message
                        }
                    }
                )
                
                if response.status_code == 200:
                    # Update profile status
                    profile.update_connection_status(ConnectionStatus.PENDING)
                    
                    # Track metrics
                    CONNECTIONS_SENT.labels(status="success").inc()
                    
                    self.logger.info(
                        "Connection request sent",
                        profile_id=profile.profile_id
                    )
                    return True
                    
                CONNECTIONS_SENT.labels(status="error").inc()
                return False
                
            except Exception as e:
                self.logger.error(
                    "Failed to send connection request",
                    profile_id=profile.profile_id,
                    error=str(e)
                )
                CONNECTIONS_SENT.labels(status="error").inc()
                return False
                
    async def send_message(
        self,
        profile: LinkedInProfile,
        content: Optional[str] = None,
        template_id: Optional[str] = None
    ) -> bool:
        """Send a LinkedIn message."""
        with ENGAGEMENT_DURATION.labels(action="message").time():
            try:
                # Check if connected
                if profile.connection_status != ConnectionStatus.CONNECTED:
                    self.logger.warning(
                        "Cannot send message to unconnected profile",
                        profile_id=profile.profile_id
                    )
                    return False
                    
                # Check rate limits
                if not await self._check_message_limits():
                    self.logger.warning(
                        "Message rate limit reached",
                        profile_id=profile.profile_id
                    )
                    return False
                    
                # Generate message content
                if template_id:
                    content = await self.content_personalizer.generate_content(
                        template_id,
                        {
                            "name": profile.name,
                            "title": profile.title,
                            "company": profile.company
                        }
                    )
                elif not content:
                    content = await self.content_personalizer.generate_content(
                        "linkedin_message",
                        {
                            "name": profile.name,
                            "title": profile.title,
                            "company": profile.company
                        }
                    )
                    
                # Send message via PhantomBuster
                response = requests.post(
                    "https://api.phantombuster.com/api/v2/agents/launch",
                    headers={"X-Phantombuster-Key": self.phantom_buster_key},
                    json={
                        "id": "linkedin-messenger",
                        "argument": {
                            "profileUrl": profile.profile_url,
                            "message": content
                        }
                    }
                )
                
                if response.status_code == 200:
                    # Add message to profile
                    message = profile.add_message(content)
                    message.status = MessageStatus.SENT
                    
                    # Track metrics
                    MESSAGES_SENT.labels(status="success").inc()
                    
                    self.logger.info(
                        "Message sent",
                        profile_id=profile.profile_id,
                        message_id=message.message_id
                    )
                    return True
                    
                MESSAGES_SENT.labels(status="error").inc()
                return False
                
            except Exception as e:
                self.logger.error(
                    "Failed to send message",
                    profile_id=profile.profile_id,
                    error=str(e)
                )
                MESSAGES_SENT.labels(status="error").inc()
                return False
                
    async def check_messages(self, profile: LinkedInProfile) -> None:
        """Check for new message replies."""
        with ENGAGEMENT_DURATION.labels(action="check_messages").time():
            try:
                # Get messages via PhantomBuster
                response = requests.post(
                    "https://api.phantombuster.com/api/v2/agents/launch",
                    headers={"X-Phantombuster-Key": self.phantom_buster_key},
                    json={
                        "id": "linkedin-message-checker",
                        "argument": {
                            "profileUrl": profile.profile_url
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Update message statuses
                    for msg in profile.messages:
                        if msg.status == MessageStatus.SENT:
                            msg.status = MessageStatus.DELIVERED
                            
                        # Check for replies
                        if msg.status == MessageStatus.DELIVERED:
                            reply = data.get("replies", {}).get(msg.message_id)
                            if reply:
                                msg.status = MessageStatus.REPLIED
                                msg.reply_content = reply["content"]
                                msg.reply_at = datetime.utcnow()
                                
                                # Track metrics
                                REPLIES_RECEIVED.inc()
                                
                                # Track engagement
                                await self.engagement_tracker.track_event(
                                    profile.profile_id,
                                    "linkedin_reply",
                                    {
                                        "message_id": msg.message_id,
                                        "profile_id": profile.profile_id
                                    }
                                )
                                
            except Exception as e:
                self.logger.error(
                    "Failed to check messages",
                    profile_id=profile.profile_id,
                    error=str(e)
                )
                
    async def _check_connection_limits(self) -> bool:
        """Check if we're within connection request rate limits."""
        # TODO: Implement rate limit checking
        return True
        
    async def _check_message_limits(self) -> bool:
        """Check if we're within message rate limits."""
        # TODO: Implement rate limit checking
        return True
        
    async def retry_failed_actions(self, profile: LinkedInProfile) -> None:
        """Retry failed connection requests and messages."""
        # Retry failed connection requests
        if (
            profile.connection_status == ConnectionStatus.PENDING
            and profile.connection_request_sent_at
            and datetime.utcnow() - profile.connection_request_sent_at > self.connection_cooldown
        ):
            await self.send_connection_request(profile)
            
        # Retry failed messages
        for message in profile.messages:
            if (
                message.status == MessageStatus.FAILED
                and message.sent_at
                and datetime.utcnow() - message.sent_at > self.message_cooldown
            ):
                await self.send_message(profile, message.content) 