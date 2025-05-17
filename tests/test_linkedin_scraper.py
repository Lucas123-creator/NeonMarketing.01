import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from neonhub.services.linkedin_scraper import LinkedInScraper
from neonhub.schemas.linkedin_lead import LinkedInProfile

@pytest.fixture
def linkedin_scraper():
    return LinkedInScraper()

@pytest.fixture
def sample_profile():
    return LinkedInProfile(
        profile_id="profile_123",
        name="John Doe",
        title="Software Engineer",
        company="Tech Corp",
        profile_url="https://linkedin.com/in/johndoe"
    )

@pytest.mark.asyncio
async def test_search_profiles(linkedin_scraper):
    """Test searching for LinkedIn profiles."""
    with patch("serpapi.GoogleSearch") as mock_search:
        # Mock search results
        mock_search.return_value.get_dict.return_value = {
            "profiles": [
                {
                    "profile_id": "profile_1",
                    "name": "John Doe",
                    "title": "Software Engineer",
                    "company": "Tech Corp",
                    "profile_url": "https://linkedin.com/in/johndoe",
                    "location": "San Francisco",
                    "industry": "Technology"
                }
            ]
        }
        
        # Search profiles
        profiles = await linkedin_scraper.search_profiles(
            keywords=["software engineer"],
            location="San Francisco"
        )
        
        assert len(profiles) == 1
        assert profiles[0].name == "John Doe"
        assert profiles[0].title == "Software Engineer"
        
@pytest.mark.asyncio
async def test_enrich_profile(linkedin_scraper, sample_profile):
    """Test enriching a profile with additional data."""
    with patch("requests.post") as mock_post:
        # Mock PhantomBuster response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "company_size": "1000+",
            "about": "Experienced software engineer",
            "experience": [
                {
                    "title": "Senior Engineer",
                    "company": "Tech Corp",
                    "duration": "2 years"
                }
            ],
            "education": [
                {
                    "school": "Stanford",
                    "degree": "BS Computer Science"
                }
            ],
            "skills": ["Python", "JavaScript"],
            "profile_image_url": "https://example.com/photo.jpg"
        }
        
        # Enrich profile
        enriched = await linkedin_scraper.enrich_profile(sample_profile)
        
        assert enriched.company_size == "1000+"
        assert enriched.about == "Experienced software engineer"
        assert len(enriched.experience) == 1
        assert len(enriched.education) == 1
        assert len(enriched.skills) == 2
        
@pytest.mark.asyncio
async def test_get_company_info(linkedin_scraper):
    """Test getting company information."""
    with patch("serpapi.GoogleSearch") as mock_search:
        # Mock search results
        mock_search.return_value.get_dict.return_value = {
            "company": {
                "name": "Tech Corp",
                "website": "https://techcorp.com",
                "size": "1000+",
                "industry": "Technology",
                "description": "Leading tech company",
                "founded": "2010",
                "headquarters": "San Francisco"
            }
        }
        
        # Get company info
        info = await linkedin_scraper.get_company_info("Tech Corp")
        
        assert info["name"] == "Tech Corp"
        assert info["website"] == "https://techcorp.com"
        assert info["size"] == "1000+"
        
@pytest.mark.asyncio
async def test_get_company_employees(linkedin_scraper):
    """Test getting company employees."""
    with patch("serpapi.GoogleSearch") as mock_search:
        # Mock search results
        mock_search.return_value.get_dict.return_value = {
            "employees": [
                {
                    "profile_id": "profile_1",
                    "name": "John Doe",
                    "title": "Software Engineer",
                    "profile_url": "https://linkedin.com/in/johndoe"
                }
            ]
        }
        
        # Get employees
        employees = await linkedin_scraper.get_company_employees("Tech Corp")
        
        assert len(employees) == 1
        assert employees[0].name == "John Doe"
        assert employees[0].company == "Tech Corp"
        
@pytest.mark.asyncio
async def test_save_load_profile(linkedin_scraper, sample_profile):
    """Test saving and loading a profile."""
    # Save profile
    linkedin_scraper.save_profile(sample_profile)
    
    # Load profile
    loaded = linkedin_scraper.load_profile(sample_profile.profile_id)
    
    assert loaded is not None
    assert loaded.name == sample_profile.name
    assert loaded.title == sample_profile.title
    assert loaded.company == sample_profile.company
    
@pytest.mark.asyncio
async def test_error_handling(linkedin_scraper):
    """Test error handling in profile operations."""
    with patch("serpapi.GoogleSearch") as mock_search:
        # Mock search error
        mock_search.side_effect = Exception("API Error")
        
        # Search profiles
        profiles = await linkedin_scraper.search_profiles(["software engineer"])
        
        assert len(profiles) == 0
        
    # Test loading non-existent profile
    profile = linkedin_scraper.load_profile("non_existent")
    assert profile is None 