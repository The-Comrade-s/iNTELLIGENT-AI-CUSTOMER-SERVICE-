"""
services/settings_service.py

Get/set helpers for the AppSetting key-value store, plus the set of
default settings the platform ships with. Grouped by section so the
Settings page can render tabs without hard-coding key names twice.
"""

from __future__ import annotations

import datetime as dt

from database import AppSetting, get_db

DEFAULTS: dict[str, str] = {
    "branding.app_name": "Intelligent Customer Service Chatbot Platform",
    "branding.support_email": "support@example.com",
    "branding.primary_color": "#2563EB",
    "ai.faq_confidence_threshold": "0.15",
    "ai.escalate_on_angry_sentiment": "true",
    "chat.max_memory_turns": "6",
    "chat.away_message": "We're offline right now, but I'm still here to help with common questions!",
}


def get_setting(key: str) -> str:
    with get_db() as db:
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row:
            return row.value
        return DEFAULTS.get(key, "")


def get_all_settings() -> dict[str, str]:
    with get_db() as db:
        rows = {r.key: r.value for r in db.query(AppSetting).all()}
    merged = dict(DEFAULTS)
    merged.update(rows)
    return merged


def set_setting(key: str, value: str) -> None:
    with get_db() as db:
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row:
            row.value = value
            row.updated_at = dt.datetime.utcnow()
        else:
            db.add(AppSetting(key=key, value=value))
