"""
app_pages/knowledge_base.py

Customer-facing FAQ browser/search. The admin CMS for creating and
editing articles arrives in ICS-003; this page is the read-only,
searchable front end backed by the same chatbot.faq_engine used
inside the chat pipeline.
"""

import streamlit as st

from chatbot.faq_engine import search as faq_search
from database import FAQ, get_db


def _load_all_published() -> list[dict]:
    with get_db() as db:
        faqs = db.query(FAQ).filter(FAQ.status == "published").order_by(FAQ.category, FAQ.question).all()
        return [{"id": f.id, "question": f.question, "answer": f.answer, "category": f.category, "views": f.views} for f in faqs]


def render() -> None:
    st.markdown('<div class="ics-section-title">Knowledge Base</div>', unsafe_allow_html=True)

    query = st.text_input("Search the knowledge base", placeholder="e.g. how do I reset my password?")

    if query:
        matches = faq_search(query, top_n=8, min_score=0.02)
        if not matches:
            st.info("No matching articles found — try rephrasing, or ask the AI assistant in Chat.")
        for match in matches:
            with st.expander(f"{match.question}  ·  {match.category}"):
                st.write(match.answer)
        return

    all_faqs = _load_all_published()
    if not all_faqs:
        st.markdown(
            '<div class="ics-card">The knowledge base is empty — articles will appear here once added.</div>',
            unsafe_allow_html=True,
        )
        return

    categories = sorted({f["category"] for f in all_faqs})
    tabs = st.tabs(categories)
    for tab, category in zip(tabs, categories):
        with tab:
            for faq in [f for f in all_faqs if f["category"] == category]:
                with st.expander(faq["question"]):
                    st.write(faq["answer"])
                    st.caption(f"{faq['views']} views")
