from typing import Any, Dict, List, Optional
import json
from datetime import datetime
from prometheus_client import Counter, Histogram
import openai
from langdetect import detect
from deep_translator import GoogleTranslator

from ..config.settings import get_settings
from ..utils.logging import get_logger

# Prometheus metrics
TRANSLATION_REQUESTS = Counter(
    'neonhub_translation_requests_total',
    'Number of translation requests',
    ['source_lang', 'target_lang']
)

TRANSLATION_DURATION = Histogram(
    'neonhub_translation_duration_seconds',
    'Time spent translating content',
    ['source_lang', 'target_lang']
)

class LocalizationService:
    """Service for handling content localization and translation."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger()
        self.supported_languages = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "nl": "Dutch",
            "pl": "Polish",
            "ru": "Russian",
            "ja": "Japanese",
            "zh": "Chinese",
            "ar": "Arabic"
        }
        
    async def detect_language(self, text: str) -> str:
        """Detect the language of the given text."""
        try:
            return detect(text)
        except Exception as e:
            self.logger.error(
                "Language detection failed",
                error=str(e)
            )
            return "en"
            
    async def translate_content(
        self,
        content: Dict[str, str],
        target_language: str
    ) -> Dict[str, str]:
        """Translate content to target language."""
        if target_language not in self.supported_languages:
            self.logger.warning(
                "Unsupported target language",
                language=target_language
            )
            return content
            
        with TRANSLATION_DURATION.labels(
            source_lang="auto",
            target_lang=target_language
        ).time():
            try:
                translated_content = {}
                
                # Detect source language from first content item
                first_text = next(iter(content.values()))
                source_language = await self.detect_language(first_text)
                
                # Translate each content item
                for key, text in content.items():
                    translated_text = await self._translate_text(
                        text,
                        source_language,
                        target_language
                    )
                    translated_content[key] = translated_text
                    
                # Apply cultural adaptations
                translated_content = await self._apply_cultural_adaptations(
                    translated_content,
                    target_language
                )
                
                TRANSLATION_REQUESTS.labels(
                    source_lang=source_language,
                    target_lang=target_language
                ).inc()
                
                return translated_content
                
            except Exception as e:
                self.logger.error(
                    "Translation failed",
                    error=str(e)
                )
                return content
                
    async def _translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> str:
        """Translate text using Google Translate API."""
        try:
            translator = GoogleTranslator(
                source=source_language,
                target=target_language
            )
            return translator.translate(text)
        except Exception as e:
            self.logger.error(
                "Text translation failed",
                error=str(e)
            )
            return text
            
    async def _apply_cultural_adaptations(
        self,
        content: Dict[str, str],
        target_language: str
    ) -> Dict[str, str]:
        """Apply cultural adaptations to translated content."""
        try:
            # Prepare prompt for cultural adaptation
            prompt = self._create_cultural_adaptation_prompt(
                content,
                target_language
            )
            
            # Call OpenAI API for cultural adaptation
            response = await openai.ChatCompletion.acreate(
                model=self.settings.openai.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a cultural adaptation expert."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Parse and apply cultural adaptations
            adapted_content = json.loads(response.choices[0].message.content)
            return adapted_content
            
        except Exception as e:
            self.logger.error(
                "Cultural adaptation failed",
                error=str(e)
            )
            return content
            
    def _create_cultural_adaptation_prompt(
        self,
        content: Dict[str, str],
        target_language: str
    ) -> str:
        """Create prompt for cultural adaptation."""
        return f"""
        Please adapt the following content for {self.supported_languages[target_language]} culture.
        Consider:
        - Cultural norms and values
        - Business etiquette
        - Local expressions and idioms
        - Date and number formats
        - Units of measurement
        
        Content: {json.dumps(content)}
        Target language: {target_language}
        
        Return the culturally adapted content in the same JSON format.
        """
        
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages."""
        return self.supported_languages.copy()
        
    def is_language_supported(self, language: str) -> bool:
        """Check if language is supported."""
        return language in self.supported_languages 