from typing import Any, Dict, List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from datetime import datetime
from prometheus_client import Counter, Histogram

from .base_agent import BaseAgent, AgentError
from ..services.content_personalizer import ContentPersonalizer
from ..services.sequence_manager import SequenceManager
from ..services.engagement_tracker import EngagementTracker
from ..config.settings import get_settings
from ..utils.logging import get_logger

# Prometheus metrics
EMAILS_SENT = Counter(
    'neonhub_emails_sent_total',
    'Number of emails sent',
    ['campaign_id', 'stage_id', 'variant_id']
)

EMAIL_DURATION = Histogram(
    'neonhub_email_duration_seconds',
    'Time spent sending emails',
    ['campaign_id', 'stage_id']
)

class EmailOutreachAgent(BaseAgent[Dict[str, Any]]):
    """Agent for handling email outreach campaigns."""
    
    def __init__(self, agent_id: str = "email_outreach", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config)
        self.settings = get_settings()
        self.logger = get_logger()
        self.content_personalizer = ContentPersonalizer()
        self.sequence_manager = SequenceManager()
        self.engagement_tracker = EngagementTracker()
        self.smtp_connection = None
        self.campaign_queue: List[Dict[str, Any]] = []
        
    async def initialize(self) -> None:
        """Initialize the email outreach agent."""
        try:
            # Initialize SMTP connection
            self.smtp_connection = smtplib.SMTP(
                self.settings.smtp.host,
                self.settings.smtp.port
            )
            self.smtp_connection.starttls()
            self.smtp_connection.login(
                self.settings.smtp.username,
                self.settings.smtp.password
            )
            
            self.logger.info(
                "Email outreach agent initialized",
                agent_id=self.agent_id
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize email outreach agent",
                error=str(e)
            )
            raise AgentError(f"Failed to initialize email outreach agent: {str(e)}")
            
    async def execute(self, campaign_id: str, leads: List[Dict]) -> Dict:
        """Execute the email outreach campaign."""
        results = {
            "campaign_id": campaign_id,
            "total_leads": len(leads),
            "successful": 0,
            "failed": 0,
            "variants_used": {}
        }
        
        for lead in leads:
            try:
                # Get next action from sequence
                action = await self.sequence_manager.get_next_action(
                    lead["id"],
                    campaign_id
                )
                
                if not action:
                    continue
                    
                # Send email
                success = await self._send_email(
                    lead,
                    action["content"],
                    action["metadata"]
                )
                
                if success:
                    # Track email sent event
                    await self.engagement_tracker.track_event(
                        lead["id"],
                        "email_sent",
                        {
                            "campaign_id": campaign_id,
                            "stage_id": action["stage_id"],
                            "variant_id": action["content"]["metadata"]["variant_id"]
                        }
                    )
                    
                    # Complete stage
                    await self.sequence_manager.complete_stage(
                        lead["id"],
                        campaign_id,
                        success=True
                    )
                    
                    results["successful"] += 1
                    variant_id = action["content"]["metadata"]["variant_id"]
                    results["variants_used"][variant_id] = results["variants_used"].get(variant_id, 0) + 1
                    
                else:
                    # Track failure
                    await self.sequence_manager.complete_stage(
                        lead["id"],
                        campaign_id,
                        success=False
                    )
                    results["failed"] += 1
                    
            except Exception as e:
                self.logger.error(
                    "Failed to process lead",
                    lead_id=lead["id"],
                    error=str(e)
                )
                results["failed"] += 1
                
        return results
        
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.smtp_connection:
            try:
                self.smtp_connection.quit()
            except Exception as e:
                self.logger.error(
                    "Failed to close SMTP connection",
                    error=str(e)
                )
                
    async def _send_email(
        self,
        lead: Dict,
        content: Dict,
        metadata: Dict
    ) -> bool:
        """Send an email to a lead."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.settings.smtp.from_email
            msg["To"] = lead["email"]
            msg["Subject"] = content["subject"]
            
            # Add tracking pixel
            tracking_pixel = self._create_tracking_pixel(
                lead["id"],
                metadata["campaign_id"],
                metadata["stage_id"]
            )
            
            # Add body with tracking
            body = content["body"] + f"\n\n{tracking_pixel}"
            msg.attach(MIMEText(body, "html"))
            
            # Add unsubscribe link
            unsubscribe_link = self._create_unsubscribe_link(
                lead["id"],
                metadata["campaign_id"]
            )
            msg.attach(MIMEText(f"\n\n{unsubscribe_link}", "html"))
            
            # Send email
            with EMAIL_DURATION.labels(
                campaign_id=metadata["campaign_id"],
                stage_id=metadata["stage_id"]
            ).time():
                self.smtp_connection.send_message(msg)
                
            # Update metrics
            EMAILS_SENT.labels(
                campaign_id=metadata["campaign_id"],
                stage_id=metadata["stage_id"],
                variant_id=content["metadata"]["variant_id"]
            ).inc()
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to send email",
                lead_id=lead["id"],
                error=str(e)
            )
            return False
            
    def _create_tracking_pixel(
        self,
        lead_id: str,
        campaign_id: str,
        stage_id: str
    ) -> str:
        """Create HTML tracking pixel."""
        return f'<img src="{self.settings.tracking.base_url}/track?lead_id={lead_id}&campaign_id={campaign_id}&stage_id={stage_id}" width="1" height="1" />'
        
    def _create_unsubscribe_link(
        self,
        lead_id: str,
        campaign_id: str
    ) -> str:
        """Create unsubscribe link."""
        return f'<a href="{self.settings.tracking.base_url}/unsubscribe?lead_id={lead_id}&campaign_id={campaign_id}">Unsubscribe</a>'
        
    async def schedule_campaign(self, campaign_data: Dict[str, Any]) -> None:
        """Schedule a new email campaign."""
        self.campaign_queue.append(campaign_data)
        self.logger.info(
            "Campaign scheduled",
            campaign_id=campaign_data.get("campaign_id"),
            queue_size=len(self.campaign_queue)
        )
        
    async def get_campaign_status(self, campaign_id: str) -> Dict[str, Any]:
        """Get the status of a specific campaign."""
        return {
            "campaign_id": campaign_id,
            "status": "scheduled",
            "scheduled_time": datetime.utcnow().isoformat(),
            "recipients_count": len(self.campaign_queue),
            "metrics": self.metrics
        } 