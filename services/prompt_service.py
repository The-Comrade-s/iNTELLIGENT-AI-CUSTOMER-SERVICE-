"""
services/prompt_service.py

Stores and serves editable prompt templates (system, escalation,
knowledge, translation, summarisation). The current rule-based engine
doesn't call an LLM, so these templates aren't consumed by the
pipeline yet -- they exist so ICS-004's "prompt management" surface
is real and functional, and so a future LLM-backed response_generator
has a ready-made place to read prompts from without a schema change.
"""

from __future__ import annotations

import datetime as dt

from database import PromptTemplate, get_db

DEFAULT_PROMPTS = {
    "system": ("System Prompt", "You are a helpful, professional customer service assistant. Be concise, empathetic, and accurate."),
    "escalation": ("Escalation Prompt", "Summarize this conversation for a human agent, highlighting the customer's issue, sentiment, and any attempted resolutions."),
    "knowledge": ("Knowledge Prompt", "Answer the customer's question using only the provided knowledge base article. If it doesn't fully answer, say so."),
    "translation": ("Translation Prompt", "Translate the assistant's reply into the customer's preferred language while preserving tone and meaning."),
    "summarisation": ("Summarisation Prompt", "Summarize this conversation in 2-3 sentences, focusing on the customer's goal and outcome."),
}


def seed_default_prompts_if_empty() -> None:
    with get_db() as db:
        if db.query(PromptTemplate).count() > 0:
            return
        for key, (label, content) in DEFAULT_PROMPTS.items():
            db.add(PromptTemplate(key=key, label=label, content=content))


def list_prompts() -> list[dict]:
    with get_db() as db:
        prompts = db.query(PromptTemplate).order_by(PromptTemplate.label).all()
        return [{"id": p.id, "key": p.key, "label": p.label, "content": p.content, "updated_at": p.updated_at} for p in prompts]


def update_prompt(prompt_id: int, content: str) -> None:
    with get_db() as db:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if prompt:
            prompt.content = content
            prompt.updated_at = dt.datetime.utcnow()
