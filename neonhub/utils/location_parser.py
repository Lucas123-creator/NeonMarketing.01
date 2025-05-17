from typing import Dict, Any, Optional, Tuple
import re
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

class LocationParser:
    """Parses and validates location information."""
    
    def __init__(self):
        self.geocoder = Nominatim(user_agent="neonhub_lead_scraper")
        self.location_pattern = re.compile(
            r'^(?P<city>[^,]+),\s*(?P<state>[^,]+)?,\s*(?P<country>[^,]+)$',
            re.IGNORECASE
        )
        
    def parse(self, location: str) -> Dict[str, Any]:
        """Parse location string into structured data."""
        try:
            # Try to parse using regex first
            match = self.location_pattern.match(location)
            if match:
                return self._parse_from_regex(match)
                
            # Fallback to geocoding
            return self._parse_from_geocoding(location)
            
        except Exception as e:
            # Return basic structure if parsing fails
            return {
                "city": location,
                "country": "Unknown",
                "coordinates": None,
                "formatted_address": location
            }
            
    def _parse_from_regex(self, match: re.Match) -> Dict[str, Any]:
        """Parse location from regex match."""
        city = match.group("city").strip()
        state = match.group("state")
        country = match.group("country").strip()
        
        # Try to get coordinates
        try:
            location = self.geocoder.geocode(f"{city}, {country}")
            coordinates = (location.latitude, location.longitude) if location else None
        except (GeocoderTimedOut, GeocoderServiceError):
            coordinates = None
            
        return {
            "city": city,
            "state": state.strip() if state else None,
            "country": country,
            "coordinates": coordinates,
            "formatted_address": f"{city}, {country}"
        }
        
    def _parse_from_geocoding(self, location: str) -> Dict[str, Any]:
        """Parse location using geocoding service."""
        try:
            # Get location data
            location_data = self.geocoder.geocode(location)
            
            if not location_data:
                return {
                    "city": location,
                    "country": "Unknown",
                    "coordinates": None,
                    "formatted_address": location
                }
                
            # Parse address components
            address = location_data.raw.get("address", {})
            
            return {
                "city": address.get("city") or address.get("town") or address.get("village"),
                "state": address.get("state"),
                "country": address.get("country"),
                "coordinates": (location_data.latitude, location_data.longitude),
                "formatted_address": location_data.address
            }
            
        except (GeocoderTimedOut, GeocoderServiceError):
            return {
                "city": location,
                "country": "Unknown",
                "coordinates": None,
                "formatted_address": location
            }
            
    def validate(self, location: Dict[str, Any]) -> bool:
        """Validate location data."""
        required_fields = ["city", "country"]
        
        # Check required fields
        if not all(field in location for field in required_fields):
            return False
            
        # Check if coordinates are valid
        if location.get("coordinates"):
            try:
                lat, lon = location["coordinates"]
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    return False
            except (ValueError, TypeError):
                return False
                
        return True
        
    def format_for_search(self, location: Dict[str, Any]) -> str:
        """Format location for search queries."""
        parts = []
        
        if location.get("city"):
            parts.append(location["city"])
        if location.get("state"):
            parts.append(location["state"])
        if location.get("country"):
            parts.append(location["country"])
            
        return ", ".join(parts) if parts else "Unknown Location" 