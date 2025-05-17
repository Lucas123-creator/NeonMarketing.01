import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from neonhub.services.content_personalizer import ContentPersonalizer
from neonhub.utils.localization import LocalizationService

@pytest.fixture
def content_personalizer():
    return ContentPersonalizer()

@pytest.fixture
def sample_lead_data():
    return {
        "id": "lead_123",
        "first_name": "John",
        "company_name": "Test Corp",
        "industry": "Retail",
        "persona": "Retail Buyer",
        "preferred_language": "en",
        "segment_score": 0.8
    }

@pytest.fixture
def sample_template():
    return {
        "template_id": "demo_outreach_email",
        "name": "Initial Outreach Email",
        "languages": ["en", "es"],
        "variants": [
            {
                "id": "variant_1",
                "language": "en",
                "segment_score": 0.7,
                "use_ai_personalization": True,
                "content": {
                    "subject": "Transform Your Business with {{company_name}}'s Neon Signs",
                    "body": "Dear {{first_name}},\n\nI noticed {{company_name}}'s work in {{industry}}."
                }
            },
            {
                "id": "variant_2",
                "language": "es",
                "segment_score": 0.7,
                "use_ai_personalization": True,
                "content": {
                    "subject": "Transforma tu Negocio con Letreros de Neón de {{company_name}}",
                    "body": "Estimado/a {{first_name}},\n\nHe notado el trabajo de {{company_name}} en {{industry}}."
                }
            }
        ]
    }

@pytest.mark.asyncio
async def test_generate_content_basic(content_personalizer, sample_lead_data, sample_template):
    """Test basic content generation without AI personalization."""
    with patch.object(content_personalizer, 'templates', {'demo_outreach_email': sample_template}):
        result = await content_personalizer.generate_content(
            "demo_outreach_email",
            sample_lead_data,
            "A/B"
        )
        
        assert result["content"]["subject"] == "Transform Your Business with Test Corp's Neon Signs"
        assert "Dear John" in result["content"]["body"]
        assert "Test Corp" in result["content"]["body"]
        assert "Retail" in result["content"]["body"]
        assert result["metadata"]["template_id"] == "demo_outreach_email"
        assert result["metadata"]["language"] == "en"
        
@pytest.mark.asyncio
async def test_generate_content_with_translation(content_personalizer, sample_lead_data, sample_template):
    """Test content generation with translation."""
    sample_lead_data["preferred_language"] = "es"
    
    with patch.object(content_personalizer, 'templates', {'demo_outreach_email': sample_template}):
        with patch.object(content_personalizer.localization, 'translate_content') as mock_translate:
            mock_translate.return_value = {
                "subject": "Translated Subject",
                "body": "Translated Body"
            }
            
            result = await content_personalizer.generate_content(
                "demo_outreach_email",
                sample_lead_data,
                "A/B"
            )
            
            assert result["content"]["subject"] == "Translated Subject"
            assert result["content"]["body"] == "Translated Body"
            assert result["metadata"]["language"] == "es"
            
@pytest.mark.asyncio
async def test_generate_content_with_ai_personalization(content_personalizer, sample_lead_data, sample_template):
    """Test content generation with AI personalization."""
    with patch.object(content_personalizer, 'templates', {'demo_outreach_email': sample_template}):
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value.choices = [
                Mock(message=Mock(content='{"subject": "AI Personalized Subject", "body": "AI Personalized Body"}'))
            ]
            
            result = await content_personalizer.generate_content(
                "demo_outreach_email",
                sample_lead_data,
                "segment_score"
            )
            
            assert result["content"]["subject"] == "AI Personalized Subject"
            assert result["content"]["body"] == "AI Personalized Body"
            
@pytest.mark.asyncio
async def test_generate_content_fallback(content_personalizer, sample_lead_data):
    """Test content generation fallback when template not found."""
    result = await content_personalizer.generate_content(
        "non_existent_template",
        sample_lead_data,
        "A/B"
    )
    
    assert result["metadata"]["is_fallback"] is True
    assert result["metadata"]["language"] == "en"
    
@pytest.mark.asyncio
async def test_variant_selection(content_personalizer, sample_lead_data, sample_template):
    """Test variant selection based on strategy."""
    with patch.object(content_personalizer, 'templates', {'demo_outreach_email': sample_template}):
        # Test A/B strategy
        result_ab = await content_personalizer.generate_content(
            "demo_outreach_email",
            sample_lead_data,
            "A/B"
        )
        assert result_ab["metadata"]["variant_id"] in ["variant_1", "variant_2"]
        
        # Test segment score strategy
        result_score = await content_personalizer.generate_content(
            "demo_outreach_email",
            sample_lead_data,
            "segment_score"
        )
        assert result_score["metadata"]["variant_id"] == "variant_1"
        
@pytest.mark.asyncio
async def test_metrics_tracking(content_personalizer, sample_lead_data, sample_template):
    """Test metrics tracking for content generation."""
    with patch.object(content_personalizer, 'templates', {'demo_outreach_email': sample_template}):
        result = await content_personalizer.generate_content(
            "demo_outreach_email",
            sample_lead_data,
            "A/B"
        )
        
        # Check that metrics were updated
        assert content_personalizer.metrics.get("total_leads") is not None
        assert content_personalizer.metrics.get("variants_used") is not None
        
@pytest.mark.asyncio
async def test_error_handling(content_personalizer, sample_lead_data):
    """Test error handling in content generation."""
    # Test with invalid template
    result = await content_personalizer.generate_content(
        "invalid_template",
        sample_lead_data,
        "A/B"
    )
    
    assert result["metadata"]["is_fallback"] is True
    assert "error" in result["metadata"]
    
    # Test with invalid lead data
    result = await content_personalizer.generate_content(
        "demo_outreach_email",
        {},
        "A/B"
    )
    
    assert result["metadata"]["is_fallback"] is True
    assert "error" in result["metadata"]

@pytest.fixture
def personalizer():
    return ContentPersonalizer()

@pytest.mark.parametrize("channel,template_id", [
    ("sms", "mobile_demo_sms"),
    ("whatsapp", "mobile_demo_whatsapp")
])
def test_mobile_personalization_basic(personalizer, channel, template_id):
    content = personalizer.generate_content(
        template_id=template_id,
        personalization={
            "first_name": "Alex",
            "product": "Neon Sign",
            "offer_code": "SAVE20",
            "short_url": "bit.ly/neon"
        },
        channel=channel,
        lang="en",
        persona="Retail Buyer"
    )
    assert content["body"]
    assert len(content["body"]) <= 320
    assert any(emoji in content["body"] for emoji in ["🎉", "👋", "👉"])
    assert content["metadata"]["tone"] in ("informal", "friendly", "universal")
    assert content["metadata"]["channel"] == channel
    assert content["metadata"]["char_count"] <= 320

@pytest.mark.parametrize("channel,template_id", [
    ("sms", "mobile_demo_sms"),
    ("whatsapp", "mobile_demo_whatsapp")
])
def test_mobile_overflow_truncation(personalizer, channel, template_id):
    long_product = "Super Bright Neon Sign with Customizable Colors and Extra Long Description to Force Truncation " * 3
    content = personalizer.generate_content(
        template_id=template_id,
        personalization={
            "first_name": "Alex",
            "product": long_product,
            "offer_code": "SAVE20",
            "short_url": "bit.ly/neon"
        },
        channel=channel,
        lang="en",
        persona="Retail Buyer"
    )
    assert content["metadata"]["truncated"] is True
    assert len(content["body"]) <= 320

@pytest.mark.parametrize("channel,template_id,lang,persona", [
    ("sms", "mobile_demo_sms", "es", None),
    ("whatsapp", "mobile_demo_whatsapp", "it", "UnknownPersona")
])
def test_mobile_fallback(personalizer, channel, template_id, lang, persona):
    content = personalizer.generate_content(
        template_id=template_id,
        personalization={
            "first_name": "Alex",
            "product": "Neon Sign",
            "offer_code": "SAVE20",
            "short_url": "bit.ly/neon"
        },
        channel=channel,
        lang=lang,
        persona=persona
    )
    assert content["body"]
    assert content["metadata"]["variant_id"] in ("universal", "fallback")

@pytest.mark.parametrize("channel,template_id,lang,persona,expected_tone", [
    ("sms", "mobile_demo_sms", "en", "Retail Buyer", "informal"),
    ("whatsapp", "mobile_demo_whatsapp", "fr", "Distributor", "informal")
])
def test_mobile_emoji_and_tone(personalizer, channel, template_id, lang, persona, expected_tone):
    content = personalizer.generate_content(
        template_id=template_id,
        personalization={
            "first_name": "Alex",
            "product": "Neon Sign",
            "offer_code": "SAVE20",
            "short_url": "bit.ly/neon"
        },
        channel=channel,
        lang=lang,
        persona=persona
    )
    assert content["metadata"]["tone"] == expected_tone
    assert any(emoji in content["body"] for emoji in ["🎉", "👋", "👉"]) 