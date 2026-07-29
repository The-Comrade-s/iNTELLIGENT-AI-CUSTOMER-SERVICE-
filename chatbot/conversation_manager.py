"""
chatbot/conversation_manager.py

Owns all database reads/writes for conversations and messages, so
chatbot_engine.py and the UI never touch SQLAlchemy sessions
directly. Also handles conversation-level operations exposed in the
chat sidebar: create, rename, pin, favourite, delete, search.
"""

from __future__ import annotations

import datetime as dt

from database import Conversation, Escalation, Message, get_db


def create_conversation(user_id: int, title: str = "New Conversation") -> int:
    with get_db() as db:
        convo = Conversation(user_id=user_id, title=title)
        db.add(convo)
        db.flush()
        return convo.id


def list_conversations(user_id: int, include_archived: bool = False) -> list[dict]:
    with get_db() as db:
        query = db.query(Conversation).filter(Conversation.user_id == user_id)
        if not include_archived:
            query = query.filter(Conversation.is_archived.is_(False))
        conversations = query.order_by(
            Conversation.is_pinned.desc(), Conversation.updated_at.desc()
        ).all()
        return [
            {
                "id": c.id,
                "title": c.title,
                "is_pinned": c.is_pinned,
                "is_favourite": c.is_favourite,
                "updated_at": c.updated_at,
                "message_count": len(c.messages),
            }
            for c in conversations
        ]


def get_messages(conversation_id: int) -> list[dict]:
    with get_db() as db:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return []
        return [
            {
                "id": m.id,
                "sender": m.sender,
                "content": m.content,
                "intent": m.intent,
                "confidence": m.confidence,
                "sentiment": m.sentiment,
                "created_at": m.created_at,
            }
            for m in conversation.messages
        ]


def add_message(
    conversation_id: int,
    sender: str,
    content: str,
    intent: str | None = None,
    confidence: int | None = None,
    sentiment: str | None = None,
    response_time_ms: int | None = None,
) -> int:
    with get_db() as db:
        message = Message(
            conversation_id=conversation_id,
            sender=sender,
            content=content,
            intent=intent,
            confidence=confidence,
            sentiment=sentiment,
            response_time_ms=response_time_ms,
        )
        db.add(message)

        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            conversation.updated_at = dt.datetime.utcnow()
            if sender == "customer" and conversation.title == "New Conversation":
                conversation.title = content[:48] + ("..." if len(content) > 48 else "")

        db.flush()
        return message.id


def rename_conversation(conversation_id: int, new_title: str) -> None:
    with get_db() as db:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            conversation.title = new_title.strip()[:150] or conversation.title


def toggle_pin(conversation_id: int) -> None:
    with get_db() as db:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            conversation.is_pinned = not conversation.is_pinned


def toggle_favourite(conversation_id: int) -> None:
    with get_db() as db:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            conversation.is_favourite = not conversation.is_favourite


def delete_conversation(conversation_id: int) -> None:
    with get_db() as db:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            db.delete(conversation)


def search_conversations(user_id: int, query: str) -> list[dict]:
    query = query.strip().lower()
    if not query:
        return list_conversations(user_id)
    with get_db() as db:
        conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .filter(Conversation.title.ilike(f"%{query}%"))
            .order_by(Conversation.updated_at.desc())
            .all()
        )
        return [{"id": c.id, "title": c.title, "updated_at": c.updated_at} for c in conversations]


def create_escalation(conversation_id: int, reason: str) -> None:
    with get_db() as db:
        existing = db.query(Escalation).filter(Escalation.conversation_id == conversation_id).first()
        if existing:
            return
        db.add(Escalation(conversation_id=conversation_id, reason=reason, status="open"))
