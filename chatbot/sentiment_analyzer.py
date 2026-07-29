"""
chatbot/sentiment_analyzer.py

Lexicon-based sentiment scoring. Returns one of the seven customer
sentiment labels the platform tracks, plus a numeric score in
[-1, 1] for trend charts. Dependency-free by design; upgrading to a
trained sentiment model later is a drop-in replacement for
``analyze()``.
"""

from __future__ import annotations

from dataclasses import dataclass

from chatbot.text_processing import tokenize

_POSITIVE_WORDS = {
    "great", "good", "excellent", "awesome", "love", "happy", "thanks",
    "thank", "perfect", "amazing", "helpful", "satisfied", "wonderful",
    "fantastic", "pleased", "nice", "appreciate", "resolved", "fast",
}

_NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "hate", "angry", "annoyed", "upset",
    "frustrated", "frustrating", "disappointed", "disappointing", "worst",
    "broken", "slow", "useless", "horrible", "unacceptable", "refund",
    "complaint", "scam", "cheated", "furious", "ridiculous",
}

_URGENT_WORDS = {"urgent", "immediately", "asap", "emergency", "now", "critical"}

_CONFUSED_WORDS = {"confused", "unclear", "don't understand", "not sure", "lost", "how"}

_INTENSIFIERS = {"very", "extremely", "really", "so", "absolutely"}


@dataclass
class SentimentResult:
    label: str  # happy | satisfied | neutral | confused | frustrated | angry | urgent
    score: float  # -1.0 (very negative) .. 1.0 (very positive)


def analyze(message: str) -> SentimentResult:
    tokens = tokenize(message)
    if not tokens:
        return SentimentResult("neutral", 0.0)

    token_set = set(tokens)
    pos_hits = sum(1 for t in tokens if t in _POSITIVE_WORDS)
    neg_hits = sum(1 for t in tokens if t in _NEGATIVE_WORDS)
    intensity = 1.3 if token_set & _INTENSIFIERS else 1.0
    exclaim_boost = 1.15 if message.count("!") >= 1 else 1.0

    raw_score = (pos_hits - neg_hits) / max(len(tokens), 1)
    score = max(-1.0, min(1.0, raw_score * 4 * intensity * exclaim_boost))

    if token_set & _URGENT_WORDS:
        return SentimentResult("urgent", round(min(score, -0.2), 2))

    if neg_hits >= 2 or (neg_hits >= 1 and (message.count("!") >= 2 or message.isupper())):
        return SentimentResult("angry", round(min(score, -0.5), 2))

    if token_set & _CONFUSED_WORDS or "?" in message and neg_hits == 0 and pos_hits == 0:
        if neg_hits == 0 and pos_hits == 0:
            return SentimentResult("confused", 0.0)

    if neg_hits > pos_hits:
        return SentimentResult("frustrated", round(score, 2))

    if pos_hits >= 2:
        return SentimentResult("happy", round(score, 2))

    if pos_hits == 1:
        return SentimentResult("satisfied", round(score, 2))

    return SentimentResult("neutral", round(score, 2))
