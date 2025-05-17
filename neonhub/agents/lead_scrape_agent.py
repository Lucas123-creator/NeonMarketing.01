from typing import Any, Dict, List, Optional
import asyncio
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
import requests
from linkedin_api import Linkedin

from .base_agent import BaseAgent, AgentError
from ..utils.data_validator import LeadValidator
from ..utils.location_parser import LocationParser
from ..config.settings import get_settings

# Prometheus metrics
LEADS_FOUND = Counter(
    'neonhub_leads_found_total',
    'Total number of leads found',
    ['source', 'status']
)

LEAD_SCRAPE_DURATION = Histogram(
    'neonhub_lead_scrape_duration_seconds',
    'Time spent scraping leads',
    ['source']
)

ACTIVE_SCRAPERS = Gauge(
    'neonhub_active_scrapers',
    'Number of active scraper instances'
)

class LeadScrapeAgent(BaseAgent[Dict[str, Any]]):
    """Agent responsible for finding and validating potential distributor leads."""
    
    def __init__(self, agent_id: str = "lead_scrape", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config)
        self.settings = get_settings()
        self.validator = LeadValidator()
        self.location_parser = LocationParser()
        self.linkedin_api = None
        self.browser: Optional[Browser] = None
        self.context = None
        ACTIVE_SCRAPERS.inc()
        
    async def initialize(self) -> None:
        """Initialize browser and API connections."""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context()
            
            # Initialize LinkedIn API
            self.linkedin_api = Linkedin(
                self.settings.linkedin.username,
                self.settings.linkedin.password
            )
            
            self.logger.info(
                "Lead scrape agent initialized",
                browser_type="chromium"
            )
            
        except Exception as e:
            self.logger.exception(
                "Failed to initialize lead scrape agent",
                error=str(e)
            )
            raise AgentError(f"Failed to initialize lead scrape agent: {str(e)}")
            
    async def execute(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute lead scraping based on search parameters."""
        location = search_params.get("location")
        industry = search_params.get("industry")
        company_size = search_params.get("company_size")
        
        results = {
            "total_found": 0,
            "validated_leads": [],
            "errors": [],
            "start_time": datetime.utcnow().isoformat()
        }
        
        try:
            # Parse location for better search
            parsed_location = self.location_parser.parse(location)
            
            # Search LinkedIn
            with LEAD_SCRAPE_DURATION.labels(source="linkedin").time():
                linkedin_leads = await self._search_linkedin(
                    parsed_location,
                    industry,
                    company_size
                )
                
            # Search Google Maps
            with LEAD_SCRAPE_DURATION.labels(source="google_maps").time():
                google_leads = await self._search_google_maps(
                    parsed_location,
                    industry
                )
                
            # Combine and deduplicate leads
            all_leads = self._combine_leads(linkedin_leads, google_leads)
            
            # Validate leads
            for lead in all_leads:
                if await self.validator.validate(lead):
                    results["validated_leads"].append(lead)
                    results["total_found"] += 1
                    LEADS_FOUND.labels(
                        source=lead["source"],
                        status="valid"
                    ).inc()
                    
            # Update metrics
            self.update_metrics({
                "total_leads": results["total_found"],
                "linkedin_leads": len(linkedin_leads),
                "google_leads": len(google_leads)
            })
            
        except Exception as e:
            self.logger.exception(
                "Error during lead scraping",
                error=str(e)
            )
            results["errors"].append({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            
        results["end_time"] = datetime.utcnow().isoformat()
        return results
        
    async def cleanup(self) -> None:
        """Clean up browser and API connections."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        ACTIVE_SCRAPERS.dec()
        self.logger.info("Lead scrape agent cleaned up")
        
    async def _search_linkedin(
        self,
        location: Dict[str, Any],
        industry: str,
        company_size: str
    ) -> List[Dict[str, Any]]:
        """Search for leads on LinkedIn."""
        leads = []
        
        try:
            # Search companies
            companies = self.linkedin_api.search_companies(
                keywords=f"{industry} {location['city']}",
                regions=[location["country"]]
            )
            
            for company in companies:
                company_data = self.linkedin_api.get_company(company["urn_id"])
                
                if self._matches_criteria(company_data, company_size):
                    lead = {
                        "source": "linkedin",
                        "company_name": company_data.get("name"),
                        "website": company_data.get("website"),
                        "industry": company_data.get("industry"),
                        "employee_count": company_data.get("staff_count"),
                        "location": {
                            "city": location["city"],
                            "country": location["country"]
                        },
                        "contact_info": self._extract_contact_info(company_data)
                    }
                    leads.append(lead)
                    LEADS_FOUND.labels(
                        source="linkedin",
                        status="found"
                    ).inc()
                    
        except Exception as e:
            self.logger.error(
                "LinkedIn search error",
                error=str(e)
            )
            
        return leads
        
    async def _search_google_maps(
        self,
        location: Dict[str, Any],
        industry: str
    ) -> List[Dict[str, Any]]:
        """Search for leads on Google Maps."""
        leads = []
        
        try:
            # Use Playwright to scrape Google Maps
            page = await self.context.new_page()
            await page.goto(
                f"https://www.google.com/maps/search/{industry}+in+{location['city']}+{location['country']}"
            )
            
            # Wait for results to load
            await page.wait_for_selector(".section-result")
            
            # Extract business information
            elements = await page.query_selector_all(".section-result")
            
            for element in elements:
                business_data = await self._extract_business_data(element)
                if business_data:
                    lead = {
                        "source": "google_maps",
                        **business_data,
                        "location": location
                    }
                    leads.append(lead)
                    LEADS_FOUND.labels(
                        source="google_maps",
                        status="found"
                    ).inc()
                    
            await page.close()
            
        except Exception as e:
            self.logger.error(
                "Google Maps search error",
                error=str(e)
            )
            
        return leads
        
    def _combine_leads(
        self,
        linkedin_leads: List[Dict[str, Any]],
        google_leads: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Combine and deduplicate leads from different sources."""
        all_leads = linkedin_leads + google_leads
        unique_leads = {}
        
        for lead in all_leads:
            key = f"{lead['company_name']}_{lead['location']['city']}"
            if key not in unique_leads:
                unique_leads[key] = lead
                
        return list(unique_leads.values())
        
    def _matches_criteria(
        self,
        company_data: Dict[str, Any],
        target_size: str
    ) -> bool:
        """Check if company matches search criteria."""
        if not company_data:
            return False
            
        # Implement size matching logic
        employee_count = company_data.get("staff_count", 0)
        if target_size == "small" and employee_count > 50:
            return False
        if target_size == "medium" and (employee_count < 50 or employee_count > 500):
            return False
        if target_size == "large" and employee_count < 500:
            return False
            
        return True
        
    def _extract_contact_info(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract contact information from company data."""
        return {
            "email": company_data.get("email"),
            "phone": company_data.get("phone"),
            "linkedin_url": company_data.get("linkedin_url")
        }
        
    async def _extract_business_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract business information from Google Maps element."""
        try:
            name = await element.query_selector(".section-result-title")
            name_text = await name.inner_text() if name else ""
            
            address = await element.query_selector(".section-result-location")
            address_text = await address.inner_text() if address else ""
            
            phone = await element.query_selector(".section-result-phone")
            phone_text = await phone.inner_text() if phone else ""
            
            website = await element.query_selector(".section-result-website")
            website_text = await website.inner_text() if website else ""
            
            return {
                "company_name": name_text,
                "address": address_text,
                "phone": phone_text,
                "website": website_text
            }
            
        except Exception as e:
            self.logger.error(
                "Error extracting business data",
                error=str(e)
            )
            return None 