"""
chatbot/faq_engine.py

Searchable FAQ / knowledge-base engine. Implements TF-IDF + cosine
similarity by hand (stdlib `math`/`collections` only) so semantic-ish
search works with zero extra dependencies. If sentence-transformers +
FAISS are installed, `semantic_search()` is the single function to
swap for an embedding-based nearest-neighbour lookup -- the return
type (list[FAQMatch]) stays identical.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from chatbot.text_processing import preprocess
from database import FAQ, get_db


@dataclass
class FAQMatch:
    faq_id: int
    question: str
    answer: str
    category: str
    score: float


def _term_freq(tokens: list[str]) -> Counter:
    return Counter(tokens)


def _cosine_similarity(vec_a: Counter, vec_b: Counter) -> float:
    shared = set(vec_a) & set(vec_b)
    numerator = sum(vec_a[t] * vec_b[t] for t in shared)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return numerator / (mag_a * mag_b)


def _document_frequency(corpus_tokens: list[list[str]]) -> Counter:
    df: Counter = Counter()
    for tokens in corpus_tokens:
        for term in set(tokens):
            df[term] += 1
    return df


def _tfidf_vector(tokens: list[str], df: Counter, n_docs: int) -> Counter:
    tf = _term_freq(tokens)
    vec: Counter = Counter()
    for term, freq in tf.items():
        idf = math.log((n_docs + 1) / (df.get(term, 0) + 1)) + 1
        vec[term] = freq * idf
    return vec


def search(query: str, top_n: int = 3, min_score: float = 0.08) -> list[FAQMatch]:
    """Return the best-matching published FAQ entries for ``query``,
    ranked by TF-IDF cosine similarity."""

    query_tokens = preprocess(query)
    if not query_tokens:
        return []

    with get_db() as db:
        faqs = db.query(FAQ).filter(FAQ.status == "published").all()
        if not faqs:
            return []

        docs = []
        for faq in faqs:
            text = f"{faq.question} {faq.keywords or ''} {faq.answer}"
            docs.append((faq, preprocess(text)))

        corpus_tokens = [tokens for _, tokens in docs]
        df = _document_frequency(corpus_tokens + [query_tokens])
        n_docs = len(corpus_tokens) + 1

        query_vec = _tfidf_vector(query_tokens, df, n_docs)

        scored: list[FAQMatch] = []
        for faq, tokens in docs:
            doc_vec = _tfidf_vector(tokens, df, n_docs)
            score = _cosine_similarity(query_vec, doc_vec)
            if score >= min_score:
                scored.append(
                    FAQMatch(
                        faq_id=faq.id,
                        question=faq.question,
                        answer=faq.answer,
                        category=faq.category,
                        score=round(score, 3),
                    )
                )

        scored.sort(key=lambda m: m.score, reverse=True)

        # Bump view counters for the top match only (mirrors a real
        # "this answer was surfaced" analytics signal).
        if scored:
            top = db.query(FAQ).filter(FAQ.id == scored[0].faq_id).first()
            if top:
                top.views += 1

        return scored[:top_n]


def seed_default_faqs_if_empty() -> None:
    """Populate a handful of starter FAQs on first run so the chatbot
    and admin CMS have real data to demonstrate against."""

    starters = [
        ("What are your business hours?", "We're available 24/7 through this chatbot. Our human support team is online Monday to Friday, 8am - 6pm.", "General", "hours open time"),
        ("How do I reset my password?", "Go to the login page and select 'Forgot password?', then follow the emailed instructions to set a new password.", "Account", "password reset forgot login"),
        ("How can I track my order?", "Open 'Order Status' in the chat and share your order number, or check the Orders section of your account.", "Orders", "track order shipment delivery"),
        ("What is your refund policy?", "Refunds are processed within 5-7 business days once a return is approved. Contact support with your order number to start one.", "Payments", "refund return money back"),
        ("How do I contact a human agent?", "Type 'talk to an agent' at any point in the chat, or ask a question our AI can't resolve -- it will escalate automatically.", "Support", "contact agent human escalate"),
    ]

    with get_db() as db:
        if db.query(FAQ).count() > 0:
            return
        for question, answer, category, keywords in starters:
            db.add(FAQ(question=question, answer=answer, category=category, keywords=keywords, status="published"))
