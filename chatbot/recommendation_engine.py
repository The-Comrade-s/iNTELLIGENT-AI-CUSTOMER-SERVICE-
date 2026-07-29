"""
chatbot/recommendation_engine.py

Recommends related FAQ articles / questions based on the customer's
current message and intent. ICS-004 extends this with customer
history and purchase-context signals; the function signature here is
designed to accept those as optional keyword args later without
breaking callers.
"""

from __future__ import annotations

from dataclasses import dataclass

from chatbot.faq_engine import search as faq_search


@dataclass
class Recommendation:
    title: str
    reason: str
    faq_id: int | None = None


def recommend_related(message: str, primary_faq_id: int | None = None, limit: int = 3) -> list[Recommendation]:
    """Suggest related knowledge-base articles for the current
    message, excluding whichever FAQ was already used as the primary
    answer."""

    matches = faq_search(message, top_n=limit + 1)
    recommendations = []
    for match in matches:
        if match.faq_id == primary_faq_id:
            continue
        recommendations.append(
            Recommendation(
                title=match.question,
                reason=f"Related to your question (match score {match.score:.2f})",
                faq_id=match.faq_id,
            )
        )
        if len(recommendations) >= limit:
            break
    return recommendations
