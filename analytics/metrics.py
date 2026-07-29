"""
analytics/metrics.py

Aggregation queries powering the ICS-003 analytics dashboard and
reports. Pure read-side logic -- no Streamlit imports -- so it can be
unit tested or reused by the reports exporter directly.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter

from database import Conversation, Escalation, Message, User, get_db


def date_range_days(days: int) -> tuple[dt.datetime, dt.datetime]:
    end = dt.datetime.utcnow()
    start = end - dt.timedelta(days=days)
    return start, end


def conversations_per_day(days: int = 14) -> dict[str, int]:
    start, _ = date_range_days(days)
    counts: Counter = Counter()
    with get_db() as db:
        conversations = db.query(Conversation).filter(Conversation.created_at >= start).all()
        for c in conversations:
            counts[c.created_at.strftime("%Y-%m-%d")] += 1
    # Ensure every day in range appears, even with zero conversations.
    result = {}
    for i in range(days, -1, -1):
        day = (dt.datetime.utcnow() - dt.timedelta(days=i)).strftime("%Y-%m-%d")
        result[day] = counts.get(day, 0)
    return result


def intent_distribution(days: int = 30) -> dict[str, int]:
    start, _ = date_range_days(days)
    with get_db() as db:
        messages = (
            db.query(Message)
            .filter(Message.sender == "customer", Message.created_at >= start, Message.intent.isnot(None))
            .all()
        )
        counts: Counter = Counter(m.intent for m in messages)
    return dict(counts.most_common(12))


def sentiment_distribution(days: int = 30) -> dict[str, int]:
    start, _ = date_range_days(days)
    with get_db() as db:
        messages = (
            db.query(Message)
            .filter(Message.sender == "customer", Message.created_at >= start, Message.sentiment.isnot(None))
            .all()
        )
        counts: Counter = Counter(m.sentiment for m in messages)
    return dict(counts)


def average_response_time_ms(days: int = 30) -> float:
    start, _ = date_range_days(days)
    with get_db() as db:
        messages = (
            db.query(Message)
            .filter(Message.sender == "ai", Message.created_at >= start, Message.response_time_ms.isnot(None))
            .all()
        )
        if not messages:
            return 0.0
        return round(sum(m.response_time_ms for m in messages) / len(messages), 1)


def ai_resolution_rate(days: int = 30) -> float:
    """Percentage of conversations in the period that were NOT escalated to a human."""

    start, _ = date_range_days(days)
    with get_db() as db:
        total = db.query(Conversation).filter(Conversation.created_at >= start).count()
        if total == 0:
            return 0.0
        escalated = (
            db.query(Escalation)
            .join(Conversation, Escalation.conversation_id == Conversation.id)
            .filter(Conversation.created_at >= start)
            .count()
        )
        return round((total - escalated) / total * 100, 1)


def summary_kpis(days: int = 30) -> dict:
    start, _ = date_range_days(days)
    with get_db() as db:
        total_customers = db.query(User).filter(User.role == "customer").count()
        total_conversations = db.query(Conversation).filter(Conversation.created_at >= start).count()
        conversations_today = db.query(Conversation).filter(
            Conversation.created_at >= dt.datetime.combine(dt.date.today(), dt.time.min)
        ).count()
        total_escalations = (
            db.query(Escalation)
            .join(Conversation, Escalation.conversation_id == Conversation.id)
            .filter(Conversation.created_at >= start)
            .count()
        )
    return {
        "total_customers": total_customers,
        "total_conversations": total_conversations,
        "conversations_today": conversations_today,
        "total_escalations": total_escalations,
        "ai_resolution_rate": ai_resolution_rate(days),
        "avg_response_time_ms": average_response_time_ms(days),
    }
