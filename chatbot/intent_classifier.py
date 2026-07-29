"""
chatbot/intent_classifier.py

Rule-based intent recognition with confidence scoring. Each intent is
defined by a set of trigger phrases/keywords; the classifier scores
every intent by lemma overlap with the user's message and returns the
best match plus a confidence score in [0, 1].

This keeps the platform fully functional with zero training data or
GPU/embedding dependencies. Swapping in a trained transformer
classifier later only requires changing ``classify()``'s
implementation -- the return type (IntentResult) stays the same.
"""

from __future__ import annotations

from dataclasses import dataclass

from chatbot.text_processing import clean_text, preprocess

INTENT_DEFINITIONS: dict[str, list[str]] = {
    "greeting": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"],
    "goodbye": ["bye", "goodbye", "see you", "farewell", "take care"],
    "thanks": ["thank", "thanks", "appreciate", "grateful"],
    "complaint": ["complaint", "complain", "unhappy", "disappointed", "terrible", "worst", "bad experience"],
    "refund": ["refund", "money back", "return item", "reimburse"],
    "payment": ["payment", "pay", "charge", "billing", "invoice", "card declined", "transaction"],
    "delivery": ["delivery", "shipping", "shipment", "courier", "dispatch", "arrive"],
    "order_status": ["order status", "track order", "where is my order", "order number"],
    "pricing": ["price", "pricing", "cost", "how much", "fee", "plan"],
    "business_hours": ["business hours", "open", "closing time", "working hours", "when are you open"],
    "technical_support": ["not working", "error", "bug", "crash", "broken", "technical issue", "glitch"],
    "account_issue": ["account", "login issue", "can't log in", "locked out", "suspended"],
    "password_reset": ["password", "reset password", "forgot password", "change password"],
    "product_information": ["product", "feature", "specification", "details about", "tell me about"],
    "recommendation": ["recommend", "suggest", "which one should i", "best option"],
    "contact_information": ["contact", "phone number", "email address", "reach you", "support number"],
    "capabilities": [
        "what can you do", "what can you do for me", "what do you do", "how can you help",
        "how can you help me", "what are you", "who are you", "what is this", "your purpose",
        "what is your purpose", "are you a bot", "are you human", "what can i ask you",
    ],
    "general_question": ["how do i", "what is", "can you explain", "help me understand"],
}

_INTENT_LEMMAS = {
    intent: {tuple(preprocess(phrase)) for phrase in phrases}
    for intent, phrases in INTENT_DEFINITIONS.items()
}


@dataclass
class IntentResult:
    intent: str
    confidence: float
    matched_terms: list[str]


def classify(message: str) -> IntentResult:
    """Return the best-matching intent for ``message``."""

    # Exact-phrase pass first. Some of the most common short questions
    # (e.g. "what can you do for me", "what's your purpose") are made
    # up entirely of stopwords once lemmatized below, so the bag-of-words
    # pass has nothing left to score against and would always miss them.
    # Checking the raw trigger phrases against the cleaned text catches
    # these before that happens.
    cleaned = clean_text(message)
    for intent, phrases in INTENT_DEFINITIONS.items():
        for phrase in phrases:
            if phrase in cleaned:
                return IntentResult(intent, 0.95, [phrase])

    message_tokens = set(preprocess(message))
    if not message_tokens:
        return IntentResult("unknown", 0.0, [])

    best_intent = "unknown"
    best_score = 0.0
    best_matches: list[str] = []

    for intent, phrase_tuples in _INTENT_LEMMAS.items():
        phrase_tokens: set[str] = set()
        for phrase in phrase_tuples:
            phrase_tokens.update(phrase)
        if not phrase_tokens:
            continue

        overlap = message_tokens & phrase_tokens
        if not overlap:
            continue

        # Confidence: fraction of the intent's vocabulary that showed
        # up, boosted by fraction of the message it explains.
        precision = len(overlap) / len(phrase_tokens)
        recall = len(overlap) / len(message_tokens)
        score = (precision + recall) / 2

        if score > best_score:
            best_intent, best_score = intent, score
            best_matches = sorted(overlap)

    if best_score < 0.12:
        return IntentResult("unknown", round(best_score, 2), best_matches)

    return IntentResult(best_intent, round(min(best_score, 0.99), 2), best_matches)
