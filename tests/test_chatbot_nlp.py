"""
tests/test_chatbot_nlp.py

Covers the dependency-free NLP pipeline: text preprocessing, intent
classification, and sentiment analysis.
"""

from chatbot.intent_classifier import classify
from chatbot.sentiment_analyzer import analyze
from chatbot.text_processing import extract_keywords, preprocess, tokenize


def test_tokenize_and_preprocess():
    tokens = tokenize("Hello there! How's it going?")
    assert "hello" in tokens
    processed = preprocess("The customers were running quickly")
    assert "the" not in processed  # stopword removed
    assert "were" not in processed


def test_extract_keywords_returns_relevant_terms():
    keywords = extract_keywords("I need help resetting my password, my password is not working", top_n=3)
    assert "password" in keywords


def test_classify_greeting_intent():
    result = classify("Hello, good morning!")
    assert result.intent == "greeting"
    assert result.confidence > 0


def test_classify_password_reset_intent():
    result = classify("How do I reset my password?")
    assert result.intent == "password_reset"


def test_classify_unknown_for_gibberish():
    result = classify("purple elephant orbit galaxy")
    assert result.intent == "unknown"


def test_sentiment_detects_positive():
    result = analyze("Thank you so much, this was excellent and very helpful!")
    assert result.label in {"happy", "satisfied"}
    assert result.score > 0


def test_sentiment_detects_negative():
    result = analyze("This is terrible and broken, I am so frustrated and angry!")
    assert result.label in {"angry", "frustrated"}
    assert result.score < 0
