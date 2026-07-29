"""
chatbot/text_processing.py

Lightweight NLP preprocessing built on the Python standard library so
the platform runs with zero extra native dependencies out of the box.
If spaCy / NLTK are installed (see requirements.txt), swap the
functions below for their pipelines without changing any caller --
every function here returns plain Python types (str / list[str]).
"""

from __future__ import annotations

import re
from collections import Counter

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can",
    "could", "did", "do", "does", "doing", "for", "from", "had", "has",
    "have", "having", "he", "her", "here", "hers", "him", "his", "how",
    "i", "if", "in", "into", "is", "it", "its", "just", "me", "my", "of",
    "on", "or", "our", "ours", "out", "over", "own", "please", "shall",
    "she", "should", "so", "some", "than", "that", "the", "their", "them",
    "then", "there", "these", "they", "this", "to", "too", "up", "us",
    "very", "was", "we", "were", "what", "when", "where", "which", "who",
    "why", "will", "with", "would", "you", "your", "yours",
}

_TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")

# A tiny handful of high-value irregular stems + a suffix-stripping
# fallback. This is not a linguistically complete lemmatizer, but it
# is dependency-free and good enough for FAQ/intent matching.
_IRREGULAR_LEMMAS = {
    "is": "be", "are": "be", "was": "be", "were": "be", "been": "be",
    "has": "have", "had": "have", "having": "have",
    "did": "do", "does": "do", "doing": "do",
    "went": "go", "gone": "go",
    "bought": "buy", "buying": "buy",
    "paid": "pay", "paying": "pay",
}


def clean_text(text: str) -> str:
    """Lowercase, strip URLs/extra punctuation and whitespace."""

    text = text.strip()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def tokenize(text: str) -> list[str]:
    """Split cleaned text into alphanumeric word tokens."""

    return _TOKEN_RE.findall(clean_text(text))


def remove_stopwords(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t not in _STOPWORDS]


def lemmatize_token(token: str) -> str:
    """Best-effort stem/lemma for a single token."""

    if token in _IRREGULAR_LEMMAS:
        return _IRREGULAR_LEMMAS[token]
    for suffix in ("ing", "edly", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


def lemmatize(tokens: list[str]) -> list[str]:
    return [lemmatize_token(t) for t in tokens]


def preprocess(text: str, drop_stopwords: bool = True) -> list[str]:
    """Full pipeline: clean -> tokenize -> (stopwords) -> lemmatize."""

    tokens = tokenize(text)
    if drop_stopwords:
        tokens = remove_stopwords(tokens)
    return lemmatize(tokens)


def extract_keywords(text: str, top_n: int = 5) -> list[str]:
    """Return the most frequent non-stopword lemmas in ``text``."""

    tokens = preprocess(text)
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(top_n)]


_LANGUAGE_HINTS = {
    "en": {"the", "is", "and", "you", "please", "hello", "thanks"},
    "fr": {"le", "la", "est", "vous", "merci", "bonjour", "svp"},
    "es": {"el", "la", "es", "usted", "gracias", "hola", "por"},
    "yo": {"bawo", "e", "se", "jowo", "oruko"},
    "ha": {"sannu", "yaya", "don", "allah", "nagode"},
    "ig": {"kedu", "biko", "daalu", "ndewo"},
}


def detect_language(text: str) -> str:
    """Very lightweight keyword-overlap language guess. Returns an
    ISO-ish code; defaults to 'en'. A real deployment should swap
    this for langdetect/fastText -- the call signature won't change."""

    tokens = set(tokenize(text))
    best_lang, best_score = "en", 0
    for lang, hints in _LANGUAGE_HINTS.items():
        score = len(tokens & hints)
        if score > best_score:
            best_lang, best_score = lang, score
    return best_lang
