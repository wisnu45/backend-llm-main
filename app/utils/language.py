"""Language utilities.

This backend intentionally supports only two user-facing languages:
- Indonesian (``id``)
- English (``en``)

The detection layer may receive arbitrary language codes from upstream
providers. We normalize and clamp those outputs so that *only* ``id`` or ``en``
can propagate into the application, preventing prompt drift and mixed-language
responses.
"""
import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional, Tuple

from googletrans import Translator

logger = logging.getLogger('agent.language')

# Only these languages are supported for detection + response.
# Everything else is normalized to one of these to avoid prompt drift.
_SUPPORTED_LANGUAGE_CODES = {"id", "en"}

# Language codes that should always be treated as Indonesian (Bahasa Indonesia)
# These include close dialects, legacy codes, and common misdetections.
_FORCE_TO_INDONESIAN_CODES = {
    'id', 'id-id', 'id_latn', 'id-latn',
    'in', 'ind',  # Legacy ISO codes for Indonesian
    'ms', 'ms-id', 'ms-my', 'ms-latn',
    'jw', 'jv',  # Javanese variations often confused with Indonesian
    'su',  # Sundanese
    'min', 'ace', 'ban', 'bug',  # Regional languages frequently intertwined with Indonesian content
}

# Prefixes that, when detected, should be normalized to Indonesian.
_FORCE_TO_INDONESIAN_PREFIXES = {
    'id', 'in', 'ms', 'jw', 'jv', 'su', 'min', 'ace', 'ban', 'bug'
}

# Initialize translator instance cache
_translator: Optional[Translator] = None
_translator_loop: Optional[asyncio.AbstractEventLoop] = None


def _reset_translator() -> None:
    """Reset the cached translator so it can be re-created safely."""
    global _translator, _translator_loop
    _translator = None
    _translator_loop = None


def _get_translator() -> Translator:
    """Get or create translator instance tied to the active event loop."""
    global _translator, _translator_loop

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _translator is None:
        _translator = Translator()
        _translator_loop = current_loop
        return _translator

    if _translator_loop is not None:
        if _translator_loop.is_closed():
            logger.debug("� Cached translator loop closed, reinitializing instance")
            _translator = Translator()
            _translator_loop = current_loop
            return _translator

        if current_loop is not None and current_loop is not _translator_loop:
            logger.debug("📝 Translator accessed from new event loop, creating fresh instance")
            _translator = Translator()
            _translator_loop = current_loop
            return _translator

    return _translator


async def _execute_with_retry(operation: Callable[[Translator], Awaitable[Any]]) -> Any:
    """
    Execute translator operation with automatic reinitialization on loop errors.
    
    Note: googletrans methods are async and need to be awaited.
    """
    try:
        translator = _get_translator()
        result = operation(translator)
        # If the operation returns a coroutine, await it
        if asyncio.iscoroutine(result):
            return await result
        return result
    except RuntimeError as runtime_error:
        if "event loop is closed" in str(runtime_error).lower():
            logger.debug("� Translator event loop closed during operation; retrying with fresh instance")
            _reset_translator()
            translator = _get_translator()
            result = operation(translator)
            if asyncio.iscoroutine(result):
                return await result
            return result
        raise


def _check_indonesian_markers(text: str) -> int:
    """
    Check for Indonesian-specific words and patterns in the text.
    
    Args:
        text: Text to check for Indonesian markers
        
    Returns:
        Count of Indonesian markers found
    """
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Common Indonesian words that are distinctive from Malay/Vietnamese/Filipino
    indonesian_markers = [
        # Question words
        'apa', 'bagaimana', 'kenapa', 'mengapa', 'siapa', 'kapan', 'dimana', 'kemana',
        # Pronouns
        'saya', 'kami', 'kamu', 'anda', 'mereka', 'dia', 'kita',
        # Common verbs
        'adalah', 'sudah', 'belum', 'akan', 'sedang', 'telah',
        'bisa', 'dapat', 'harus', 'mau', 'ingin', 'perlu',
        # Conjunctions and prepositions
        'yang', 'dan', 'atau', 'tetapi', 'namun', 'karena', 'sebab',
        'di', 'ke', 'dari', 'untuk', 'dengan', 'oleh', 'pada',
        # Demonstratives
        'ini', 'itu', 'tersebut',
        # Other common words
        'tidak', 'bukan', 'juga', 'hanya', 'sangat', 'sekali',
        'ada', 'ada', 'seperti', 'jika', 'kalau', 'bila',
        # Formal/business words
        'perusahaan', 'kebijakan', 'produk', 'layanan', 'informasi',
        'mohon', 'terima', 'kasih', 'silakan', 'harap'
    ]
    
    # Count how many markers are found
    marker_count = 0
    words = text_lower.split()
    
    for marker in indonesian_markers:
        # Check for exact word match (with word boundaries)
        if marker in words:
            marker_count += 1
        # Also check for markers as part of longer words (common in Indonesian)
        elif any(marker in word for word in words if len(word) > len(marker)):
            marker_count += 0.5  # Count partial matches as half
    
    return int(marker_count)


def _check_english_markers(text: str) -> int:
    """Check for common English markers in the text."""
    text_lower = (text or "").lower()
    words = text_lower.split()
    if not words:
        return 0

    english_markers = [
        # Question words
        "what", "how", "why", "when", "where", "who", "which",
        # Pronouns
        "i", "you", "we", "they", "he", "she", "it", "my", "your", "our",
        # Common verbs / auxiliaries
        "is", "are", "was", "were", "be", "been", "being",
        "do", "does", "did", "can", "could", "should", "would", "will",
        # Common function words
        "the", "a", "an", "and", "or", "but", "because", "to", "of", "in", "on", "for", "with",
        # Politeness / conversational
        "please", "thanks", "thank", "hello", "hi",
    ]

    marker_count = 0.0
    for marker in english_markers:
        if marker in words:
            marker_count += 1
        elif any(marker in word for word in words if len(word) > len(marker)):
            marker_count += 0.5

    return int(marker_count)


def _normalize_language_detection(detected_lang: str, confidence: float, text: str) -> str:
    """
    Normalize language detection to correct common misidentifications.
    
    Indonesian (id) is often misdetected as:
    - Malay (ms) - very similar languages
    - Vietnamese (vi) - some word similarities
    - Filipino/Tagalog (tl) - some word similarities
    
    This function applies heuristics to correct these misidentifications.
    
    Args:
        detected_lang: Initially detected language code
        confidence: Detection confidence (0.0 - 1.0)
        text: Original text that was analyzed
        
    Returns:
        Corrected language code
    """
    normalized_lang = (detected_lang or '').lower()
    base_lang = normalized_lang.split('-')[0] if normalized_lang else ''

    # Force-map known aliases and closely related dialects to Indonesian
    if normalized_lang in _FORCE_TO_INDONESIAN_CODES or base_lang in _FORCE_TO_INDONESIAN_PREFIXES:
        if base_lang != 'id':
            logger.info(
                f"🔄 Force-mapping detected language {detected_lang} to id (Indonesian alias/dialect)"
            )
        return 'id'

    # Languages that are commonly confused with Indonesian and need heuristic checks
    confusable_languages = {'vi', 'tl'}  # Vietnamese, Filipino/Tagalog
    if base_lang not in confusable_languages:
        return detected_lang
    
    # Check for Indonesian markers in the text
    marker_count = _check_indonesian_markers(text)
    text_word_count = len(text.split())
    
    # Calculate marker ratio (markers per word)
    marker_ratio = marker_count / max(text_word_count, 1)
    
    logger.debug(
        "🔍 Language normalization check: detected=%s, normalized=%s, base=%s, confidence=%.2f, markers=%s/%s (ratio=%.2f)",
        detected_lang,
        normalized_lang,
        base_lang,
        confidence,
        marker_count,
        text_word_count,
        marker_ratio,
    )
    
    # Apply correction based on marker ratio and confidence
    if marker_ratio >= 0.2:  # At least 20% of words are Indonesian markers
        logger.info(f"🔄 Correcting language detection from {detected_lang} to id "
                   f"(high Indonesian marker ratio: {marker_ratio:.2f})")
        return 'id'
    elif marker_ratio >= 0.15 and confidence < 0.9:  # 15%+ markers with low confidence
        logger.info(f"🔄 Correcting language detection from {detected_lang} to id "
                   f"(moderate markers: {marker_ratio:.2f}, low confidence: {confidence:.2f})")
        return 'id'
    
    # No correction needed
    logger.debug(f"✓ Keeping detected language: {detected_lang}")
    return detected_lang


def _normalize_supported_language(detected_lang: str, confidence: float, text: str, default: str = 'id') -> str:
    """
    Normalize arbitrary detection output to a supported language code (id/en).

    Policy:
    - Prefer Indonesian when Indonesian markers are present.
    - Otherwise prefer English when English markers are present.
    - If detection reports English, accept it unless Indonesian markers dominate.
    - Everything else falls back to `default` (clamped to id/en).
    """
    default_norm = (default or 'id').lower()
    if default_norm not in _SUPPORTED_LANGUAGE_CODES:
        default_norm = 'id'

    normalized_lang = (detected_lang or '').lower()
    base_lang = normalized_lang.split('-')[0] if normalized_lang else ''

    # Quick force-map: Indonesian aliases/dialects are always Indonesian.
    if normalized_lang in _FORCE_TO_INDONESIAN_CODES or base_lang in _FORCE_TO_INDONESIAN_PREFIXES:
        return 'id'

    words_count = max(len((text or '').split()), 1)
    ind_markers = _check_indonesian_markers(text)
    en_markers = _check_english_markers(text)

    ind_ratio = ind_markers / words_count
    en_ratio = en_markers / words_count

    # If the text looks Indonesian, always return Indonesian.
    if ind_ratio >= 0.12 and ind_ratio >= (en_ratio + 0.03):
        return 'id'

    # If the text looks English, return English.
    if en_ratio >= 0.12 and en_ratio >= (ind_ratio + 0.03):
        return 'en'

    # If detector says English and we don't have strong Indonesian signals, accept English.
    if base_lang == 'en':
        return 'en'

    # Otherwise, clamp to supported default.
    return default_norm


async def detect_language_async(text: str, default: str = 'id') -> str:
    """
    Detect the language of the input text asynchronously.
    
    Args:
        text: The text to detect language from
        default: Default language code if detection fails (default: 'id' for Indonesian)
        
    Returns:
        Language code (e.g., 'id', 'en', 'ms')
    """
    try:
        if not text or not text.strip():
            logger.warning("⚠️ Empty text provided for language detection, using default")
            return default

        detected = await _execute_with_retry(lambda client: client.detect(text))
        raw_lang_code = detected.lang
        confidence = detected.confidence if hasattr(detected, 'confidence') else 1.0
        
        # Apply normalization to correct common misidentifications
        normalized_lang_code = _normalize_language_detection(raw_lang_code, confidence, text)

        # Clamp to supported languages only (id/en)
        supported_lang_code = _normalize_supported_language(normalized_lang_code, confidence, text, default=default)
        
        if raw_lang_code != normalized_lang_code:
            logger.info(f"🌍 Detected language: {raw_lang_code} → {normalized_lang_code} (corrected) "
                       f"(confidence: {confidence:.2f}) for text: {text[:50]}...")
        else:
            logger.info(f"🌍 Detected language: {normalized_lang_code} (confidence: {confidence:.2f}) "
                       f"for text: {text[:50]}...")

        if supported_lang_code != normalized_lang_code:
            logger.info(f"🌐 Language clamped: {normalized_lang_code} → {supported_lang_code} (supported-only)")

        return supported_lang_code
    except Exception as e:
        logger.error(f"❌ Language detection failed: {e}, using default: {default}")
        return default

def detect_language(text: str, default: str = 'id') -> str:
    """
    Detect the language of the input text (synchronous wrapper).
    
    Args:
        text: The text to detect language from
        default: Default language code if detection fails (default: 'id' for Indonesian)
        
    Returns:
        Language code (e.g., 'id', 'en', 'ms')
    """
    try:
        return asyncio.run(detect_language_async(text, default))
    except Exception as e:
        logger.error(f"❌ Unexpected error in language detection: {e}, using default: {default}")
        return default

async def translate_to_indonesian_async(text: str) -> Tuple[str, str]:
    """
    Translate text to Indonesian and return both translated text and original language.
    
    Args:
        text: The text to translate
        
    Returns:
        Tuple of (translated_text, original_language_code)
    """
    try:
        if not text or not text.strip():
            logger.warning("⚠️ Empty text provided for translation")
            return text, 'id'
        
        # Detect original language
        detected = await _execute_with_retry(lambda client: client.detect(text))
        raw_lang = detected.lang
        confidence = detected.confidence if hasattr(detected, 'confidence') else 1.0
        
        # Apply normalization to correct common misidentifications
        original_lang = _normalize_language_detection(raw_lang, confidence, text)
        original_lang = _normalize_supported_language(original_lang, confidence, text, default='id')
        
        if raw_lang != original_lang:
            logger.info(f"🌍 Detected language: {raw_lang} → {original_lang} (corrected, confidence: {confidence:.2f})")
        else:
            logger.info(f"🌍 Detected language: {original_lang} (confidence: {confidence:.2f})")
        
        # If already Indonesian, no translation needed
        if original_lang == 'id':
            logger.debug("📝 Text is already in Indonesian, no translation needed")
            return text, original_lang
        
        # Translate to Indonesian
        translated = await _execute_with_retry(lambda client: client.translate(text, dest='id'))
        translated_text = translated.text
        
        logger.info(f"🔄 Translated from {original_lang} to Indonesian")
        logger.debug(f"📝 Original: {text[:100]}...")
        logger.debug(f"📝 Translated: {translated_text[:100]}...")
        
        return translated_text, original_lang
        
    except Exception as e:
        logger.error(f"❌ Translation to Indonesian failed: {e}")
        return text, 'id'

async def translate_to_original_language_async(text: str, target_language: str) -> str:
    """
    Translate text from Indonesian back to the original language.
    
    Args:
        text: The text in Indonesian to translate back
        target_language: The target language code to translate to
        
    Returns:
        Translated text in the original language
    """
    try:
        if not text or not text.strip():
            logger.warning("⚠️ Empty text provided for translation")
            return text
        
        target_norm = (target_language or 'id').lower()
        if target_norm not in _SUPPORTED_LANGUAGE_CODES:
            logger.debug("📝 Target language not supported (%s); returning Indonesian text", target_language)
            return text

        # If target language is Indonesian, no translation needed
        if target_norm == 'id':
            logger.debug("📝 Target language is Indonesian, no translation needed")
            return text
        
        # Translate from Indonesian to target language
        translated = await _execute_with_retry(
            lambda client: client.translate(text, src='id', dest=target_norm)
        )
        translated_text = translated.text
        
        logger.info(f"🔄 Translated from Indonesian back to {target_norm}")
        logger.debug(f"📝 Indonesian: {text[:100]}...")
        logger.debug(f"📝 Translated: {translated_text[:100]}...")
        
        return translated_text
        
    except Exception as e:
        logger.error(f"❌ Translation to original language failed: {e}")
        return text


def get_language_name(lang_code: str) -> str:
    """
    Get the full language name from language code.
    
    Args:
        lang_code: Language code (e.g., 'id', 'en', 'ms')
        
    Returns:
        Full language name
    """
    # This backend intentionally focuses on Indonesian and English only.
    language_names = {
        'id': 'Bahasa Indonesia',
        'id-id': 'Bahasa Indonesia',
        'id-latn': 'Bahasa Indonesia',
        'id_latn': 'Bahasa Indonesia',
        'in': 'Bahasa Indonesia',
        'ind': 'Bahasa Indonesia',
        'en': 'English',
    }
    
    normalized_code = (lang_code or '').lower()
    if normalized_code in _SUPPORTED_LANGUAGE_CODES:
        return language_names.get(normalized_code, normalized_code.upper())
    return language_names.get(normalized_code, lang_code.upper())
