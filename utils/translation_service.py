"""
utils/translation_service.py

Supports the platform's multilingual requirement with a curated
phrase dictionary for common bot replies across the languages listed
in the ICS-004 spec (English, French, Spanish, German, Arabic,
Portuguese, Chinese, Hindi, Yoruba, Igbo, Hausa). This is honest
about its scope: it is NOT a general-purpose machine translator --
free-text customer messages are still processed in the language they
were written (chatbot.text_processing.detect_language identifies
which one). Swapping in a real translation API (e.g. an MT model or
cloud translation service) is a drop-in replacement for
``translate_phrase()`` since callers only depend on its signature.
"""

from __future__ import annotations

SUPPORTED_LANGUAGES = {
    "en": "English", "fr": "French", "es": "Spanish", "de": "German",
    "ar": "Arabic", "pt": "Portuguese", "zh": "Chinese", "hi": "Hindi",
    "yo": "Yoruba", "ig": "Igbo", "ha": "Hausa",
}

_PHRASES = {
    "greeting": {
        "en": "Hello! How can I help you today?",
        "fr": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
        "es": "¡Hola! ¿Cómo puedo ayudarte hoy?",
        "de": "Hallo! Wie kann ich Ihnen heute helfen?",
        "ar": "مرحبًا! كيف يمكنني مساعدتك اليوم؟",
        "pt": "Olá! Como posso ajudá-lo hoje?",
        "zh": "您好！今天我能帮您什么？",
        "hi": "नमस्ते! आज मैं आपकी कैसे मदद कर सकता हूँ?",
        "yo": "Bawo! Bawo ni mo se le ran e lowo loni?",
        "ig": "Ndewo! Kedu ka m ga-esi nyere gị aka taa?",
        "ha": "Sannu! Yaya zan iya taimaka maka yau?",
    },
    "thanks": {
        "en": "You're very welcome!",
        "fr": "Je vous en prie !",
        "es": "¡De nada!",
        "de": "Gerne geschehen!",
        "ar": "على الرحب والسعة!",
        "pt": "De nada!",
        "zh": "不客气！",
        "hi": "आपका स्वागत है!",
        "yo": "O yo mi lati ran e lowo!",
        "ig": "Ọ dị mma!",
        "ha": "Babu komai!",
    },
    "goodbye": {
        "en": "Take care! Reach out anytime you need help.",
        "fr": "Prenez soin de vous ! Contactez-nous si besoin.",
        "es": "¡Cuídate! Contáctanos cuando lo necesites.",
        "de": "Pass auf dich auf! Melde dich jederzeit.",
        "ar": "اعتنِ بنفسك! تواصل معنا في أي وقت.",
        "pt": "Cuide-se! Fale conosco quando precisar.",
        "zh": "保重！随时联系我们。",
        "hi": "अपना ख्याल रखें! जब भी ज़रूरत हो संपर्क करें।",
        "yo": "Alaafia! Kan si wa nigbakugba ti o ba nilo iranlowo.",
        "ig": "Lezie anya! Kpọtụrụ anyị mgbe ọ bụla ị chọrọ enyemaka.",
        "ha": "Kula da kanka! Tuntube mu duk lokacin da kake bukatar taimako.",
    },
}


def translate_phrase(phrase_key: str, language_code: str) -> str:
    """Return the localized version of a known phrase key, falling
    back to English if the phrase or language isn't in the
    dictionary."""

    entries = _PHRASES.get(phrase_key, {})
    return entries.get(language_code) or entries.get("en", "")


def language_label(code: str) -> str:
    return SUPPORTED_LANGUAGES.get(code, code)
