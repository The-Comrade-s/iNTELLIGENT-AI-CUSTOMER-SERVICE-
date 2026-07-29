"""
utils/automation_service.py

Small rule-based automations: business-hours detection (so the bot
can prepend an "away" notice outside support hours) and priority
tagging for escalations based on sentiment/intent. Kept intentionally
simple and dependency-free -- these are rules, not ML, by design.
"""

from __future__ import annotations

import datetime as dt

BUSINESS_HOURS = {"start_hour": 8, "end_hour": 18, "days": {0, 1, 2, 3, 4}}  # Mon-Fri, 0=Mon


def is_within_business_hours(now: dt.datetime | None = None) -> bool:
    now = now or dt.datetime.utcnow()
    if now.weekday() not in BUSINESS_HOURS["days"]:
        return False
    return BUSINESS_HOURS["start_hour"] <= now.hour < BUSINESS_HOURS["end_hour"]


def escalation_priority(reason: str, sentiment_label: str) -> str:
    """Map an escalation's reason/sentiment to a priority label used
    by the admin console to sort the queue."""

    if sentiment_label == "angry" or "legal" in reason.lower() or "fraud" in reason.lower():
        return "high"
    if sentiment_label in {"frustrated", "urgent"}:
        return "medium"
    return "normal"
