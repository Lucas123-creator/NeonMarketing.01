import asyncio
import logging
from typing import Dict, Any
import os
from dotenv import load_dotenv

from agents.email_outreach_agent import EmailOutreachAgent
from agents.lead_scrape_agent import LeadScrapeAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("neonhub")

# Load environment variables
load_dotenv()

class NeonHub:
    """Main NeonHub application class."""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        return {
            "smtp": {
                "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
                "port": int(os.getenv("SMTP_PORT", "587")),
                "username": os.getenv("SMTP_USERNAME"),
                "password": os.getenv("SMTP_PASSWORD"),
                "from_email": os.getenv("SMTP_FROM_EMAIL")
            },
            "linkedin": {
                "username": os.getenv("LINKEDIN_USERNAME"),
                "password": os.getenv("LINKEDIN_PASSWORD")
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY")
            }
        }
        
    async def initialize(self):
        """Initialize all agents."""
        try:
            # Initialize email outreach agent
            self.agents["email_outreach"] = EmailOutreachAgent(
                config=self.config
            )
            await self.agents["email_outreach"].initialize()
            
            # Initialize lead scrape agent
            self.agents["lead_scrape"] = LeadScrapeAgent(
                config=self.config
            )
            await self.agents["lead_scrape"].initialize()
            
            logger.info("All agents initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing agents: {str(e)}")
            raise
            
    async def run_outreach_campaign(self, campaign_data: Dict[str, Any]):
        """Run an outreach campaign."""
        try:
            # First, find leads
            leads = await self.agents["lead_scrape"].execute({
                "location": campaign_data["location"],
                "industry": campaign_data["industry"],
                "company_size": campaign_data.get("company_size", "medium")
            })
            
            # Then, run email outreach
            if leads["validated_leads"]:
                campaign_result = await self.agents["email_outreach"].execute({
                    "campaign_id": campaign_data["campaign_id"],
                    "recipients": leads["validated_leads"],
                    "template_name": campaign_data["template_name"]
                })
                
                logger.info(f"Campaign completed: {campaign_result}")
                return campaign_result
                
        except Exception as e:
            logger.error(f"Error running campaign: {str(e)}")
            raise
            
    async def cleanup(self):
        """Clean up all agents."""
        for agent in self.agents.values():
            await agent.cleanup()
            
async def main():
    """Main entry point."""
    neonhub = NeonHub()
    
    try:
        await neonhub.initialize()
        
        # Example campaign
        campaign_data = {
            "campaign_id": "test_campaign_001",
            "location": "New York, USA",
            "industry": "retail",
            "company_size": "medium",
            "template_name": "initial_outreach"
        }
        
        result = await neonhub.run_outreach_campaign(campaign_data)
        logger.info(f"Campaign result: {result}")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        
    finally:
        await neonhub.cleanup()
        
if __name__ == "__main__":
    asyncio.run(main()) 