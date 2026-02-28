"""Translation service.

Policy: this backend focuses on Indonesian and English only.

Workflow:
1) Detect user language (clamped to ``id``/``en``)
2) Translate question to Indonesian for internal processing (if needed)
3) Translate the Indonesian response back to English when the user language is ``en``
"""

import logging
import re
from typing import Optional, Tuple, Dict, Any
from deep_translator import GoogleTranslator
from app.utils.language import detect_language

logger = logging.getLogger('agent.translation')

class TranslationService:
    """
    Centralized translation service for handling multi-language conversations.
    
    Workflow:
    1. Detect user's original language
    2. Translate question to Indonesian for processing
    3. Process the question in Indonesian
    4. Translate response back to user's original language
    """
    
    def __init__(self):
        """Initialize the translation service."""
        self._translators = {}  # Cache translators for performance
    
    def _get_translator(self, source: str, target: str) -> GoogleTranslator:
        """
        Get or create a cached translator for the given language pair.
        
        Args:
            source: Source language code
            target: Target language code
            
        Returns:
            GoogleTranslator instance
        """
        key = f"{source}-{target}"
        if key not in self._translators:
            self._translators[key] = GoogleTranslator(source=source, target=target)
        return self._translators[key]
    
    def detect_and_translate_to_indonesian(self, text: str, language_hint: Optional[str] = None) -> Tuple[str, str]:
        """
        Detect the original language and translate text to Indonesian.
        
        Args:
            text: User input text
            
        Returns:
            Tuple of (translated_text, original_language_code)
        """
        try:
            hint_norm = (language_hint or '').lower().strip()
            if hint_norm not in {'id', 'en'}:
                hint_norm = ''

            # Normalize short replies (common in confirmation flows)
            normalized = re.sub(r"\s+", " ", str(text or "").strip().lower())
            normalized = re.sub(r"[^\w\s]", " ", normalized)
            normalized = re.sub(r"\s+", " ", normalized).strip()

            is_short_reply = len(normalized) <= 24 or len(normalized.split()) <= 3

            # If we have a language hint for this chat and the reply is short,
            # trust the hint to avoid flip-flopping (e.g. "benar" misdetected as English).
            if hint_norm and is_short_reply:
                original_language = hint_norm
            else:
                # Detect original language (clamped by app.utils.language to id/en)
                original_language = (detect_language(text) or 'id').lower()

            # Extra stabilization for Indonesian-style short replies
            ind_short = {
                'benar', 'bener', 'betul', 'ya', 'iya', 'y', 'oke', 'ok', 'sip', 'siap', 'setuju', 'lanjut',
                'tidak', 'gak', 'ga', 'nggak', 'enggak', 'bukan', 'batal'
            }
            if normalized in ind_short:
                original_language = hint_norm or 'id'

            # Detect original language (clamped by app.utils.language to id/en)
            if original_language not in {'id', 'en'}:
                original_language = 'id'
            
            logger.info(f"🌍 Detected user language: {original_language}")
            
            # If already Indonesian, no translation needed
            if original_language == 'id':
                logger.debug("📝 Text is already in Indonesian, no translation needed")
                return text, original_language

            # Only English is supported besides Indonesian.
            if original_language != 'en':
                logger.info("🌐 Unsupported language '%s' treated as Indonesian", original_language)
                return text, 'id'
            
            # Translate to Indonesian
            translator = self._get_translator('auto', 'id')
            translated_text = translator.translate(text)
            
            logger.info(f"🔄 Translated from {original_language} to Indonesian")
            logger.debug(f"📝 Original: {text[:100]}...")
            logger.debug(f"📝 Translated: {translated_text[:100]}...")
            
            return translated_text, original_language
            
        except Exception as e:
            logger.error(f"❌ Translation to Indonesian failed: {e}")
            # Fallback: use original text and assume Indonesian
            return text, detect_language(text, default='id')
    
    def translate_response_to_user_language(self, response_text: str, target_language: str) -> str:
        """
        Translate the Indonesian response back to the user's original language.
        
        Args:
            response_text: Response text in Indonesian
            target_language: User's original language code
            
        Returns:
            Translated response text
        """
        try:
            target_norm = (target_language or 'id').lower()

            # If target language is Indonesian, no translation needed
            if target_norm == 'id':
                logger.debug("📝 Target language is Indonesian, no translation needed")
                return response_text

            # Only English is supported besides Indonesian.
            if target_norm != 'en':
                logger.info("🌐 Unsupported target language '%s'; returning Indonesian", target_language)
                return response_text
            
            # Translate from Indonesian to English
            translator = self._get_translator('id', 'en')
            translated_response = translator.translate(response_text)
            
            logger.info(f"🔄 Translated response from Indonesian to {target_norm}")
            logger.debug(f"📝 Indonesian: {response_text[:100]}...")
            logger.debug(f"📝 Translated: {translated_response[:100]}...")
            
            return translated_response
            
        except Exception as e:
            logger.error(f"❌ Translation to user language failed: {e}")
            # Fallback: return original Indonesian text
            logger.warning(f"⚠️ Returning response in Indonesian due to translation failure")
            return response_text
    
    def translate_with_fallback(self, text: str, source: str, target: str, fallback_text: Optional[str] = None) -> str:
        """
        Translate text with fallback handling.
        
        Args:
            text: Text to translate
            source: Source language code
            target: Target language code
            fallback_text: Fallback text if translation fails
            
        Returns:
            Translated text or fallback
        """
        try:
            if source == target:
                return text
            
            translator = self._get_translator(source, target)
            return translator.translate(text)
            
        except Exception as e:
            logger.error(f"❌ Translation failed ({source} -> {target}): {e}")
            return fallback_text or text
    
    def clear_cache(self) -> None:
        """Clear the translator cache."""
        self._translators.clear()
        logger.debug("🗑️ Translation cache cleared")
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get list of supported languages.
        
        Returns:
            Dictionary mapping language codes to language names
        """
        # This backend intentionally focuses on Indonesian and English only.
        return {
            'id': 'Bahasa Indonesia',
            'en': 'English',
        }

# Global instance for easy access
translation_service = TranslationService()

# Export for external use
__all__ = ['TranslationService', 'translation_service']