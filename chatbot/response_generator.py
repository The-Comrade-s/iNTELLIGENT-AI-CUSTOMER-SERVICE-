"""
chatbot/response_generator.py

Turns (intent, sentiment, FAQ match, memory context) into a final
response string, and decides whether the conversation should be
flagged for human escalation.

Order of precedence:
    1. A confident FAQ/knowledge-base match -> use its answer.
    2. Otherwise, an intent-specific template (several variants per
       intent, chosen deterministically-but-variedly so replies don't
       feel robotic across a session).
    3. Otherwise, a graceful "I'm not sure" fallback that still offers
       a path forward (escalate / rephrase).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from chatbot.faq_engine import FAQMatch
from chatbot.intent_classifier import IntentResult
from chatbot.memory_manager import ConversationMemory
from chatbot.sentiment_analyzer import SentimentResult

_FAQ_CONFIDENCE_THRESHOLD = 0.15

_EMERGENCY_KEYWORDS = {"legal action", "lawsuit", "lawyer", "fraud", "emergency", "suicide", "threat"}

_INTENT_TEMPLATES: dict[str, list[str]] = {
    "greeting": [
        "Hello! How can I help you today?",
        "Hi there! What can I do for you?",
        "Hey! I'm here to help -- what's going on?",
    ],
    "goodbye": [
        "Take care! Reach out anytime you need help.",
        "Goodbye for now -- I'm here whenever you need me.",
    ],
    "thanks": [
        "You're very welcome!",
        "Happy to help. Anything else I can do for you?",
    ],
    "complaint": [
        "I'm sorry to hear that -- that's not the experience we want for you. Could you share a few more details so I can help make it right?",
        "That sounds frustrating, and I understand your concern. Let's get this sorted -- can you tell me more about what happened?",
    ],
    "refund": [
        "I can help with that. Refunds are typically processed within 5-7 business days once approved. Could you share your order number?",
    ],
    "payment": [
        "I can help with billing questions. Could you tell me more about the issue -- a failed charge, an invoice question, or something else?",
    ],
    "delivery": [
        "Let's check on that shipment. Could you share your order number so I can look into the delivery status?",
    ],
    "order_status": [
        "I can help track your order -- could you share your order number?",
    ],
    "pricing": [
        "I'd be glad to walk you through pricing. Which product or plan are you asking about?",
    ],
    "business_hours": [
        "Our AI assistant is available 24/7, and our human support team is online Monday-Friday, 8am-6pm.",
    ],
    "technical_support": [
        "Sorry you're running into that. Can you describe what's happening and, if possible, any error message you're seeing?",
    ],
    "account_issue": [
        "I can help with your account. What's happening -- can't log in, account locked, or something else?",
    ],
    "password_reset": [
        "No problem -- go to the login page and select 'Forgot password?' to receive reset instructions by email.",
    ],
    "product_information": [
        "Happy to help -- which product or feature would you like more information about?",
    ],
    "recommendation": [
        "I can suggest a few options -- what are you trying to accomplish?",
    ],
    "contact_information": [
        "You can reach our support team right here in chat, or by email once your conversation is escalated to an agent.",
    ],
    "capabilities": [
        "I'm your AI customer support assistant. I can help with things like order status and shipping, refunds, billing and payments, password resets and account issues, technical problems, and general product questions. Just tell me what you need, and I can connect you with a human agent at any point if that's a better fit.",
    ],
    "general_question": [
        "Good question -- could you give me a bit more detail so I can point you in the right direction?",
    ],
    "unknown": [
        "I'm not fully sure I understood that. Could you rephrase, or would you like me to connect you with a human agent?",
        "I want to make sure I get this right for you -- could you say that a little differently?",
    ],
}


@dataclass
class GeneratedResponse:
    text: str
    used_faq_id: int | None
    should_escalate: bool
    escalation_reason: str | None


def _pick_template(intent: str) -> str:
    templates = _INTENT_TEMPLATES.get(intent, _INTENT_TEMPLATES["unknown"])
    return random.choice(templates)


def _check_escalation(
    message: str,
    intent_result: IntentResult,
    sentiment_result: SentimentResult,
    consecutive_unknowns: int,
) -> tuple[bool, str | None]:
    lowered = message.lower()
    if any(keyword in lowered for keyword in _EMERGENCY_KEYWORDS):
        return True, "Sensitive or legal keyword detected"
    if sentiment_result.label == "angry":
        return True, "Customer sentiment detected as angry"
    if intent_result.intent == "refund" and sentiment_result.label in {"angry", "frustrated"}:
        return True, "Frustrated refund request"
    if intent_result.confidence < 0.15 and consecutive_unknowns >= 2:
        return True, "Repeated low-confidence responses"
    return False, None


def generate(
    message: str,
    intent_result: IntentResult,
    sentiment_result: SentimentResult,
    faq_match: FAQMatch | None,
    memory: ConversationMemory,
    consecutive_unknowns: int = 0,
) -> GeneratedResponse:
    """Produce the final bot reply plus an escalation decision."""

    should_escalate, reason = _check_escalation(message, intent_result, sentiment_result, consecutive_unknowns)

    if faq_match and faq_match.score >= _FAQ_CONFIDENCE_THRESHOLD:
        text = faq_match.answer
        used_faq_id = faq_match.faq_id
    else:
        text = _pick_template(intent_result.intent)
        used_faq_id = None

    if intent_result.intent == "business_hours":
        from utils.automation_service import is_within_business_hours

        status = "Our human team is online right now." if is_within_business_hours() else "Our human team is currently offline, but I'm here 24/7 for common questions."
        text += f" {status}"

    if sentiment_result.label in {"frustrated", "angry"} and not text.startswith("I'm sorry") and not text.startswith("That sounds"):
        text = "I understand this is frustrating. " + text

    if should_escalate:
        text += "\n\nI'm connecting you with a member of our human support team who can take it from here."

    return GeneratedResponse(
        text=text,
        used_faq_id=used_faq_id,
        should_escalate=should_escalate,
        escalation_reason=reason,
    )
