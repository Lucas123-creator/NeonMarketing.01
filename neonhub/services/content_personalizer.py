from typing import Any, Dict, List, Optional, Tuple
import yaml
import json
from pathlib import Path
from datetime import datetime
from prometheus_client import Counter, Histogram
import openai
from jinja2 import Template
import random
import os
import re

from ..utils.localization import LocalizationService
from ..config.settings import get_settings
from ..utils.logging import get_logger

# Prometheus metrics
CONTENT_VARIANT_PERFORMANCE = Counter(
    'neonhub_content_variant_performance_total',
    'Content variant performance metrics',
    ['template_id', 'variant_id', 'lang']
)

CONTENT_FALLBACKS = Counter(
    'neonhub_content_fallbacks_total',
    'Number of content generation fallbacks',
    ['template_id', 'reason']
)

CONTENT_GENERATION_DURATION = Histogram(
    'neonhub_content_generation_duration_seconds',
    'Time spent generating personalized content',
    ['template_id']
)

MOBILE_TEMPLATE_USED = Counter(
    'mobile_template_used_total',
    'Number of mobile templates used',
    ['template_id', 'lang', 'variant_id']
)
MOBILE_CONTENT_TRUNCATED = Counter(
    'mobile_content_truncated_total',
    'Number of times mobile content was truncated',
    ['template_id', 'lang']
)

class ContentPersonalizer:
    """Service for generating personalized content using AI and rules-based logic."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger()
        self.localization = LocalizationService()
        self.templates_dir = Path("neonhub/templates")
        self.mobile_templates_dir = os.path.join(self.templates_dir, "mobile_templates")
        self.persona_rules = self._load_persona_rules()
        self.templates = self._load_templates()
        
    def _load_persona_rules(self) -> Dict[str, Any]:
        """Load persona rules from YAML file."""
        try:
            with open(self.templates_dir / "persona_rules.yaml", "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(
                "Failed to load persona rules",
                error=str(e)
            )
            return {}
            
    def _load_templates(self) -> Dict[str, Any]:
        """Load all content templates."""
        templates = {}
        for template_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(template_file, "r") as f:
                    templates[template_file.stem] = yaml.safe_load(f)
            except Exception as e:
                self.logger.error(
                    "Failed to load template",
                    template=template_file.name,
                    error=str(e)
                )
        return templates
        
    def _load_template(self, template_id: str, channel: Optional[str] = None) -> Dict:
        if channel in ("sms", "whatsapp"):
            path = os.path.join(self.mobile_templates_dir, f"{template_id}.yaml")
        else:
            path = os.path.join(self.templates_dir, f"{template_id}.yaml")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
        
    def _shorten_cta(self, text: str) -> str:
        # Replace common CTAs with short forms
        cta_map = {
            r"(?i)click here": "Tap!",
            r"(?i)learn more": "More info",
            r"(?i)shop now": "Shop!",
            r"(?i)see details": "Details",
            r"(?i)contact us": "Msg us!",
            r"(?i)reply now": "Reply!"
        }
        for pattern, repl in cta_map.items():
            text = re.sub(pattern, repl, text)
        return text

    def _enforce_mobile_rules(self, text: str, max_len: int = 320) -> (str, bool):
        # Shorten CTAs, allow emojis, truncate if needed
        text = self._shorten_cta(text)
        truncated = False
        if len(text) > max_len:
            text = text[:max_len-3] + "..."
            truncated = True
        return text, truncated

    def _select_variant(
        self,
        template: Dict[str, Any],
        lead_data: Dict[str, Any],
        language: str,
        campaign_strategy: Optional[str]
    ) -> Dict[str, Any]:
        """Select content variant based on strategy and lead data."""
        variants = template.get("variants", [])
        if not variants:
            raise ValueError("No variants found in template")
        # Filter variants by language
        language_variants = [
            v for v in variants
            if v.get("language", "en") == language
        ]
        if not language_variants:
            # Fallback to default language variants
            language_variants = variants
        # Select variant based on strategy
        if campaign_strategy == "A/B":
            # Random selection for A/B testing
            return random.choice(language_variants)
        elif campaign_strategy == "segment_score":
            # Select based on lead's segment score
            segment_score = lead_data.get("segment_score", 0)
            return max(
                language_variants,
                key=lambda v: v.get("segment_score", 0) <= segment_score
            )
        else:
            # Default to first variant
            return language_variants[0]

    def generate_content(
        self,
        template_id: str,
        personalization: Dict[str, Any],
        strategy: str = "segment_score",
        channel: Optional[str] = None,
        lang: str = "en",
        persona: Optional[str] = None
    ) -> Dict:
        try:
            template = self._load_template(template_id, channel)
        except Exception as e:
            self.logger.error("Template load failed", template_id=template_id, channel=channel, error=str(e))
            return {"subject": "", "body": "", "metadata": {"variant_id": "fallback", "truncated": False}}

        variant = self._select_variant(template, personalization, lang, strategy)
        if not variant:
            self.logger.warning("No variant found, using fallback", template_id=template_id, lang=lang, channel=channel)
            variant = {"subject": "", "body": "", "variant_id": "fallback"}
        # If variant_id is not in ("universal", "fallback") and lang is not 'en', treat as fallback
        if lang != "en" and variant.get("variant_id") not in ("universal", "fallback"):
            variant["variant_id"] = "fallback"

        # Render with Jinja2
        subject = Template(variant.get("subject", "")).render(**personalization)
        body = Template(variant.get("body", "")).render(**personalization)

        # Add UTM tracking to all links
        utm_params = personalization.get("utm_params")
        if utm_params:
            def add_utm(url):
                sep = '&' if '?' in url else '?'
                return f"{url}{sep}{utm_params}"
            body = re.sub(r'(https?://[\w\.-/\?=&%]+)', lambda m: add_utm(m.group(1)), body)

        truncated = False
        char_count = len(body)
        if channel in ("sms", "whatsapp"):
            body, truncated = self._enforce_mobile_rules(body)
            char_count = len(body)
            MOBILE_TEMPLATE_USED.labels(template_id=template_id, lang=lang, variant_id=variant.get("variant_id", "unknown")).inc()
            if truncated:
                MOBILE_CONTENT_TRUNCATED.labels(template_id=template_id, lang=lang).inc()
                self.logger.warning(
                    "Mobile content truncated",
                    template_id=template_id,
                    lang=lang,
                    char_count=char_count,
                    personalization_fields=list(personalization.keys())
                )
        else:
            # Log for non-mobile as well
            self.logger.info(
                "Content generated",
                template_id=template_id,
                lang=lang,
                channel=channel,
                char_count=char_count,
                personalization_fields=list(personalization.keys())
            )

        return {
            "subject": subject,
            "body": body,
            "metadata": {
                "variant_id": variant.get("variant_id", "unknown"),
                "truncated": truncated,
                "char_count": char_count,
                "channel": channel,
                "tone": variant.get("tone", "informal"),
                "fields": list(personalization.keys())
            }
        }
        
    async def _determine_language(
        self,
        lead_data: Dict[str, Any],
        template: Dict[str, Any]
    ) -> str:
        """Determine the language to use for content."""
        # Check if lead has preferred language
        if lead_data.get("preferred_language"):
            return lead_data["preferred_language"]
            
        # Check if template has language-specific content
        if template.get("languages"):
            # Use template's default language
            return template["languages"][0]
            
        # Default to English
        return "en"
        
    async def _generate_personalized_content(
        self,
        variant: Dict[str, Any],
        lead_data: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """Generate personalized content using AI and template variables."""
        try:
            # Get base content
            content = variant["content"].copy()
            
            # Replace template variables
            content = self._replace_template_variables(content, lead_data)
            
            # Apply AI personalization if enabled
            if variant.get("use_ai_personalization"):
                content = await self._apply_ai_personalization(
                    content,
                    lead_data,
                    language
                )
                
            # Translate if needed
            if language != "en":
                content = await self.localization.translate_content(
                    content,
                    language
                )
                
            return content
            
        except Exception as e:
            self.logger.error(
                "Content personalization failed",
                error=str(e)
            )
            raise
            
    def _replace_template_variables(
        self,
        content: Dict[str, str],
        lead_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Replace template variables with lead data."""
        result = {}
        for key, value in content.items():
            try:
                template = Template(value)
                result[key] = template.render(**lead_data)
            except Exception as e:
                self.logger.error(
                    "Template variable replacement failed",
                    key=key,
                    error=str(e)
                )
                result[key] = value
        return result
        
    async def _apply_ai_personalization(
        self,
        content: Dict[str, str],
        lead_data: Dict[str, Any],
        language: str
    ) -> Dict[str, str]:
        """Apply AI-powered personalization to content."""
        try:
            # Prepare prompt for OpenAI
            prompt = self._create_personalization_prompt(
                content,
                lead_data,
                language
            )
            
            # Call OpenAI API
            response = await openai.ChatCompletion.acreate(
                model=self.settings.openai.model,
                messages=[
                    {"role": "system", "content": "You are a professional content personalizer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.settings.openai.temperature,
                max_tokens=self.settings.openai.max_tokens
            )
            
            # Parse and apply AI suggestions
            personalized_content = json.loads(response.choices[0].message.content)
            return personalized_content
            
        except Exception as e:
            self.logger.error(
                "AI personalization failed",
                error=str(e)
            )
            return content
            
    def _create_personalization_prompt(
        self,
        content: Dict[str, str],
        lead_data: Dict[str, Any],
        language: str
    ) -> str:
        """Create prompt for AI personalization."""
        return f"""
        Please personalize the following content for a {lead_data.get('persona', 'business')} lead.
        Lead data: {json.dumps(lead_data)}
        Language: {language}
        Original content: {json.dumps(content)}
        
        Return the personalized content in the same JSON format.
        """
        
    async def _generate_fallback_content(
        self,
        template_id: str,
        lead_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate fallback content when personalization fails."""
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
            
        # Use first variant of default language
        variant = template["variants"][0]
        content = variant["content"].copy()
        
        # Only replace basic variables
        content = self._replace_template_variables(content, lead_data)
        
        return {
            "content": content,
            "metadata": {
                "template_id": template_id,
                "variant_id": variant["id"],
                "language": "en",
                "is_fallback": True,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    def _log_personalization(
        self,
        template_id: str,
        variant_id: str,
        language: str,
        lead_data: Dict[str, Any]
    ) -> None:
        """Log personalization decision."""
        self.logger.info(
            "Content personalized",
            template_id=template_id,
            variant_id=variant_id,
            language=language,
            persona=lead_data.get("persona"),
            lead_id=lead_data.get("id")
        )
        
        CONTENT_VARIANT_PERFORMANCE.labels(
            template_id=template_id,
            variant_id=variant_id,
            lang=language
        ).inc() 