"""
chatbot/chatbot_engine.py

Top-level entry point for turning one customer message into a bot
reply. Wires together every stage of the pipeline described in the
ICS-002 spec:

    input -> preprocessing -> intent detection -> sentiment analysis
    -> knowledge search -> context retrieval -> response generation
    -> memory update -> persisted + returned response

Callers (the Streamlit chat page) only need ``process_message()``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from chatbot import conversation_manager
from chatbot.faq_engine import search as faq_search
from chatbot.intent_classifier import classify
from chatbot.memory_manager import ConversationMemory, MemoryStore
from chatbot.recommendation_engine import Recommendation, recommend_related
from chatbot.response_generator import generate
from chatbot.sentiment_analyzer import analyze

logger = logging.getLogger("ics.chatbot_engine")

_memory_store = MemoryStore()


@dataclass
class ChatTurnResult:
    reply: str
    intent: str
    confidence: float
    sentiment: str
    escalated: bool
    recommendations: list[Recommendation]


def _consecutive_unknown_count(memory: ConversationMemory) -> int:
    count = 0
    for role, text in reversed(memory.recent_turns):
        if role != "bot_intent_unknown":
            break
        count += 1
    return count


def process_message(conversation_id: int, message: str) -> ChatTurnResult:
    """Run the full pipeline for one customer message and persist
    both the customer message and the bot's reply."""

    start = time.perf_counter()

    if not message or not message.strip():
        return ChatTurnResult(
            reply="It looks like your message was empty -- could you type your question?",
            intent="unknown",
            confidence=0.0,
            sentiment="neutral",
            escalated=False,
            recommendations=[],
        )

    memory = _memory_store.get(conversation_id)

    try:
        intent_result = classify(message)
        sentiment_result = analyze(message)
        faq_matches = faq_search(message, top_n=1)
        best_faq = faq_matches[0] if faq_matches else None

        consecutive_unknowns = _consecutive_unknown_count(memory)
        generated = generate(
            message=message,
            intent_result=intent_result,
            sentiment_result=sentiment_result,
            faq_match=best_faq,
            memory=memory,
            consecutive_unknowns=consecutive_unknowns,
        )

        recommendations = recommend_related(message, primary_faq_id=generated.used_faq_id)

    except Exception:  # pragma: no cover - defensive, chatbot must never crash the UI
        logger.exception("Chatbot pipeline failed for conversation %s", conversation_id)
        intent_result = classify("")
        sentiment_result = analyze("")
        generated_reply = "Sorry, something went wrong on my end. Let me connect you with a human agent."
        conversation_manager.add_message(conversation_id, "customer", message)
        conversation_manager.add_message(conversation_id, "ai", generated_reply)
        conversation_manager.create_escalation(conversation_id, "AI processing failure")
        return ChatTurnResult(
            reply=generated_reply, intent="unknown", confidence=0.0,
            sentiment="neutral", escalated=True, recommendations=[],
        )

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    conversation_manager.add_message(
        conversation_id, "customer", message,
        intent=intent_result.intent, confidence=int(intent_result.confidence * 100),
        sentiment=sentiment_result.label,
    )
    conversation_manager.add_message(
        conversation_id, "ai", generated.text,
        intent=intent_result.intent, confidence=int(intent_result.confidence * 100),
        sentiment=sentiment_result.label, response_time_ms=elapsed_ms,
    )

    memory.remember_turn("customer", message)
    memory.remember_turn("bot_intent_unknown" if intent_result.intent == "unknown" else "bot", generated.text)
    if intent_result.intent not in {"greeting", "goodbye", "thanks", "unknown"}:
        memory.set_topic(intent_result.intent.replace("_", " "))

    if generated.should_escalate:
        conversation_manager.create_escalation(conversation_id, generated.escalation_reason or "Unspecified")

    try:
        from database import Conversation, get_db as _get_db
        from services.customer_profile_service import refresh_profile

        with _get_db() as db:
            convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if convo:
                refresh_profile(convo.user_id, last_message_text=message)
    except Exception:  # pragma: no cover - profiling must never break chat
        logger.exception("Failed to refresh customer profile for conversation %s", conversation_id)

    return ChatTurnResult(
        reply=generated.text,
        intent=intent_result.intent,
        confidence=intent_result.confidence,
        sentiment=sentiment_result.label,
        escalated=generated.should_escalate,
        recommendations=recommendations,
    )


def reset_conversation_memory(conversation_id: int) -> None:
    _memory_store.reset(conversation_id)
