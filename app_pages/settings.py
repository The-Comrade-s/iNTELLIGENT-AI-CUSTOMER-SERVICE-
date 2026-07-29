"""
app_pages/settings.py

Admin-only settings: branding, AI configuration, chat configuration,
and system information. Backup/restore and environment/secrets
management are extended in ICS-005.
"""

import platform
import sys

import streamlit as st

from config import settings
from services import settings_service


def render() -> None:
    st.markdown('<div class="ics-section-title">Settings</div>', unsafe_allow_html=True)

    tabs = st.tabs(["Branding", "AI Configuration", "Chat Configuration", "AI Model Manager", "System Info"])

    with tabs[0]:
        st.markdown('<div class="ics-card">', unsafe_allow_html=True)
        app_name = st.text_input("Application name", value=settings_service.get_setting("branding.app_name"))
        support_email = st.text_input("Support email", value=settings_service.get_setting("branding.support_email"))
        primary_color = st.color_picker("Primary color", value=settings_service.get_setting("branding.primary_color"))
        if st.button("Save branding settings"):
            settings_service.set_setting("branding.app_name", app_name)
            settings_service.set_setting("branding.support_email", support_email)
            settings_service.set_setting("branding.primary_color", primary_color)
            st.success("Branding settings saved.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        st.markdown('<div class="ics-card">', unsafe_allow_html=True)
        threshold = st.slider(
            "FAQ match confidence threshold",
            min_value=0.0, max_value=1.0,
            value=float(settings_service.get_setting("ai.faq_confidence_threshold") or 0.15),
            step=0.01,
        )
        escalate_angry = st.checkbox(
            "Automatically escalate angry-sentiment conversations",
            value=settings_service.get_setting("ai.escalate_on_angry_sentiment") == "true",
        )
        if st.button("Save AI settings"):
            settings_service.set_setting("ai.faq_confidence_threshold", str(threshold))
            settings_service.set_setting("ai.escalate_on_angry_sentiment", "true" if escalate_angry else "false")
            st.success("AI settings saved.")
        st.caption("Note: the chatbot engine reads these thresholds at the start of each session in this build; a live-reload hook is a natural next step.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:
        st.markdown('<div class="ics-card">', unsafe_allow_html=True)
        max_turns = st.number_input(
            "Conversation memory length (turns)",
            min_value=2, max_value=20,
            value=int(settings_service.get_setting("chat.max_memory_turns") or 6),
        )
        away_message = st.text_area("Away message", value=settings_service.get_setting("chat.away_message"))
        if st.button("Save chat settings"):
            settings_service.set_setting("chat.max_memory_turns", str(max_turns))
            settings_service.set_setting("chat.away_message", away_message)
            st.success("Chat settings saved.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[3]:
        st.markdown('<div class="ics-card">', unsafe_allow_html=True)
        st.write("**Active pipeline:** Rule-based NLP v1 (intent classifier + lexicon sentiment + TF-IDF FAQ search)")
        st.write("**Version:** 1.0.0 (ICS-004)")
        st.write("**Dependencies:** Python standard library only — zero ML runtime required")
        st.write("**Latency:** sub-millisecond per stage on typical hardware (measured live per message on the Analytics page)")
        st.write("**Training data required:** none — intents/sentiment are lexicon-defined, not learned")
        st.info(
            "This architecture is intentionally swappable: chatbot/intent_classifier.py, "
            "chatbot/sentiment_analyzer.py, and chatbot/faq_engine.py each expose a single "
            "function with a stable return type. Pointing them at spaCy, a trained "
            "transformer classifier, or sentence-transformers + FAISS embeddings later is a "
            "contained change with no impact on the rest of the pipeline.",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[4]:
        st.markdown('<div class="ics-card">', unsafe_allow_html=True)
        st.write(f"**Environment:** {settings.environment}")
        st.write(f"**Debug mode:** {settings.debug}")
        st.write(f"**Database URL:** `{settings.database_url}`")
        st.write(f"**Python version:** {sys.version.split()[0]}")
        st.write(f"**Platform:** {platform.platform()}")
        st.markdown("</div>", unsafe_allow_html=True)
