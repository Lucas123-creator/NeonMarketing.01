from typing import Dict, Any, List, Optional
import re
import dns.resolver
from email_validator import validate_email, EmailNotValidError
import requests
from urllib.parse import urlparse

class LeadValidator:
    """Validates and enriches lead data."""
    
    def __init__(self):
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.phone_pattern = re.compile(r'^\+?1?\d{9,15}$')
        
    async def validate(self, lead_data: Dict[str, Any]) -> bool:
        """Validate lead data and return True if valid."""
        try:
            # Check required fields
            if not self._check_required_fields(lead_data):
                return False
                
            # Validate company information
            if not self._validate_company_info(lead_data):
                return False
                
            # Validate contact information
            if not self._validate_contact_info(lead_data):
                return False
                
            # Validate website
            if not self._validate_website(lead_data.get("website")):
                return False
                
            # Enrich lead data
            await self._enrich_lead_data(lead_data)
            
            return True
            
        except Exception as e:
            return False
            
    def _check_required_fields(self, lead_data: Dict[str, Any]) -> bool:
        """Check if all required fields are present."""
        required_fields = [
            "company_name",
            "location",
            "contact_info"
        ]
        
        return all(field in lead_data for field in required_fields)
        
    def _validate_company_info(self, lead_data: Dict[str, Any]) -> bool:
        """Validate company information."""
        company_name = lead_data.get("company_name", "")
        
        # Check if company name is valid
        if not company_name or len(company_name) < 2:
            return False
            
        # Check if location is valid
        location = lead_data.get("location", {})
        if not location.get("city") or not location.get("country"):
            return False
            
        return True
        
    def _validate_contact_info(self, lead_data: Dict[str, Any]) -> bool:
        """Validate contact information."""
        contact_info = lead_data.get("contact_info", {})
        
        # Validate email if present
        email = contact_info.get("email")
        if email:
            try:
                validate_email(email)
            except EmailNotValidError:
                return False
                
        # Validate phone if present
        phone = contact_info.get("phone")
        if phone and not self.phone_pattern.match(phone):
            return False
            
        return True
        
    def _validate_website(self, website: Optional[str]) -> bool:
        """Validate website URL."""
        if not website:
            return True  # Website is optional
            
        try:
            result = urlparse(website)
            return all([result.scheme, result.netloc])
        except:
            return False
            
    async def _enrich_lead_data(self, lead_data: Dict[str, Any]) -> None:
        """Enrich lead data with additional information."""
        # Add timestamp
        lead_data["validated_at"] = datetime.utcnow().isoformat()
        
        # Add confidence score
        lead_data["confidence_score"] = self._calculate_confidence_score(lead_data)
        
        # Add data source
        lead_data["data_source"] = lead_data.get("source", "unknown")
        
    def _calculate_confidence_score(self, lead_data: Dict[str, Any]) -> float:
        """Calculate confidence score for the lead."""
        score = 0.0
        
        # Company name
        if lead_data.get("company_name"):
            score += 0.2
            
        # Location
        if lead_data.get("location", {}).get("city"):
            score += 0.2
            
        # Contact info
        contact_info = lead_data.get("contact_info", {})
        if contact_info.get("email"):
            score += 0.2
        if contact_info.get("phone"):
            score += 0.2
        if contact_info.get("linkedin_url"):
            score += 0.2
            
        return min(score, 1.0) 