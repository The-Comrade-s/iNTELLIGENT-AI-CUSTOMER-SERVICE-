"""
services/customer_profile_service.py

Maintains the derived CustomerProfile row for each customer:
conversation counts, escalation counts, most frequent intent, and a
rolling average sentiment score. Called after each chat turn (cheap
aggregate queries) so admin/agent views always reflect current data.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter

from chatbot.text_processing import detect_language
from database import Conversation, CustomerProfile, Escalation, Message, get_db

_SENTIMENT_SCORES = {
    "happy": 80, "satisfied": 40, "neutral": 0, "confused": -10,
    "frustrated": -50, "angry": -80, "urgent": -30,
}


def refresh_profile(user_id: int, last_message_text: str | None = None) -> None:
    """Recompute a customer's derived profile from their conversation
    history. Cheap enough to call after every chat turn for a demo-
    scale dataset; a production system would do this in a background
    job (see ICS-005 background task notes)."""

    with get_db() as db:
        conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()
        conversation_ids = [c.id for c in conversations]

        total_conversations = len(conversations)
        total_escalations = (
            db.query(Escalation).filter(Escalation.conversation_id.in_(conversation_ids)).count()
            if conversation_ids else 0
        )

        messages = (
            db.query(Message)
            .filter(Message.conversation_id.in_(conversation_ids), Message.sender == "customer")
            .all()
            if conversation_ids else []
        )

        intents = Counter(m.intent for m in messages if m.intent and m.intent != "unknown")
        most_frequent_intent = intents.most_common(1)[0][0] if intents else None

        sentiment_scores = [_SENTIMENT_SCORES.get(m.sentiment, 0) for m in messages if m.sentiment]
        avg_sentiment = int(sum(sentiment_scores) / len(sentiment_scores)) if sentiment_scores else 0

        preferred_language = detect_language(last_message_text) if last_message_text else "en"

        profile = db.query(CustomerProfile).filter(CustomerProfile.user_id == user_id).first()
        if not profile:
            profile = CustomerProfile(user_id=user_id)
            db.add(profile)

        profile.total_conversations = total_conversations
        profile.total_escalations = total_escalations
        profile.most_frequent_intent = most_frequent_intent
        profile.average_sentiment_score = avg_sentiment
        profile.last_interaction_at = dt.datetime.utcnow()
        if last_message_text:
            profile.preferred_language = preferred_language


def get_profile(user_id: int) -> dict | None:
    with get_db() as db:
        profile = db.query(CustomerProfile).filter(CustomerProfile.user_id == user_id).first()
        if not profile:
            return None
        return {
            "preferred_language": profile.preferred_language,
            "total_conversations": profile.total_conversations,
            "total_escalations": profile.total_escalations,
            "most_frequent_intent": profile.most_frequent_intent,
            "average_sentiment_score": profile.average_sentiment_score,
            "last_interaction_at": profile.last_interaction_at,
        }


def list_all_profiles() -> list[dict]:
    from database import User

    with get_db() as db:
        rows = (
            db.query(CustomerProfile, User)
            .join(User, CustomerProfile.user_id == User.id)
            .order_by(CustomerProfile.last_interaction_at.desc())
            .all()
        )
        return [
            {
                "user_id": u.id,
                "username": u.username,
                "preferred_language": p.preferred_language,
                "total_conversations": p.total_conversations,
                "total_escalations": p.total_escalations,
                "most_frequent_intent": p.most_frequent_intent,
                "average_sentiment_score": p.average_sentiment_score,
                "last_interaction_at": p.last_interaction_at,
            }
            for p, u in rows
        ]
