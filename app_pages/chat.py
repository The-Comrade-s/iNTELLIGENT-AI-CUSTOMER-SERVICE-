"""
app_pages/chat.py

Premium ChatGPT/WhatsApp-style chat interface. Conversation list on
the left, message thread on the right, wired to
chatbot.chatbot_engine.process_message() for real AI replies backed
by the intent/sentiment/FAQ pipeline built in ICS-002.
"""

from __future__ import annotations

import csv
import io

import streamlit as st

from chatbot import chatbot_engine, conversation_manager
from styles import badge
from utils import document_service, voice_service
from utils.translation_service import SUPPORTED_LANGUAGES, translate_phrase

_SENTIMENT_BADGE_KIND = {
    "happy": "success", "satisfied": "success", "neutral": "info",
    "confused": "warning", "frustrated": "warning", "angry": "danger", "urgent": "danger",
}


def _ensure_active_conversation(user_id: int) -> int:
    key = "chat_active_conversation_id"
    if key not in st.session_state or st.session_state[key] is None:
        conversations = conversation_manager.list_conversations(user_id)
        if conversations:
            st.session_state[key] = conversations[0]["id"]
        else:
            st.session_state[key] = conversation_manager.create_conversation(user_id)
    return st.session_state[key]


def _render_sidebar_panel(user_id: int) -> None:
    st.markdown('<div class="ics-card">', unsafe_allow_html=True)
    if st.button("New Chat", use_container_width=True):
        new_id = conversation_manager.create_conversation(user_id)
        st.session_state["chat_active_conversation_id"] = new_id
        st.rerun()

    search_query = st.text_input("Search conversations", value="", label_visibility="collapsed", placeholder="Search conversations...")
    conversations = (
        conversation_manager.search_conversations(user_id, search_query)
        if search_query
        else conversation_manager.list_conversations(user_id)
    )

    st.markdown("<div style='max-height:420px;overflow-y:auto;'>", unsafe_allow_html=True)
    for convo in conversations:
        active = convo["id"] == st.session_state.get("chat_active_conversation_id")
        pin = "[Pinned] " if convo.get("is_pinned") else ""
        fav = "[Favourite] " if convo.get("is_favourite") else ""
        label = f"{'▶ ' if active else ''}{pin}{fav}{convo['title']}"
        if st.button(label, key=f"convo_{convo['id']}", use_container_width=True):
            st.session_state["chat_active_conversation_id"] = convo["id"]
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_conversation_tools(conversation_id: int) -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("Pin/Unpin", use_container_width=True):
            conversation_manager.toggle_pin(conversation_id)
            st.rerun()
    with c2:
        if st.button("Favourite", use_container_width=True):
            conversation_manager.toggle_favourite(conversation_id)
            st.rerun()
    with c3:
        new_title = st.session_state.get(f"rename_{conversation_id}")
    with c4:
        if st.button("Delete", use_container_width=True):
            conversation_manager.delete_conversation(conversation_id)
            st.session_state["chat_active_conversation_id"] = None
            st.rerun()

    with st.expander("Rename conversation"):
        new_title = st.text_input("New title", key=f"rename_input_{conversation_id}")
        if st.button("Save title", key=f"rename_save_{conversation_id}"):
            if new_title.strip():
                conversation_manager.rename_conversation(conversation_id, new_title)
                st.rerun()


def _download_transcript(conversation_id: int, messages: list[dict]) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["timestamp", "sender", "message", "intent", "sentiment"])
    for m in messages:
        writer.writerow([m["created_at"], m["sender"], m["content"], m["intent"] or "", m["sentiment"] or ""])
    st.download_button(
        "Download transcript (CSV)",
        data=buffer.getvalue(),
        file_name=f"conversation_{conversation_id}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def _render_message_bubble(message: dict) -> None:
    is_customer = message["sender"] == "customer"
    align = "flex-end" if is_customer else "flex-start"
    bg = "linear-gradient(135deg,#2563EB,#60A5FA)" if is_customer else "rgba(148,163,184,0.14)"
    color = "white" if is_customer else "inherit"
    avatar = "You" if is_customer else "AI"

    sentiment_html = ""
    if is_customer and message.get("sentiment"):
        kind = _SENTIMENT_BADGE_KIND.get(message["sentiment"], "info")
        sentiment_html = badge(message["sentiment"].title(), kind)

    st.markdown(
        f"""
        <div style="display:flex;justify-content:{align};margin-bottom:0.6rem;">
            <div style="max-width:70%;">
                <div style="font-size:0.75rem;color:#94A3B8;margin-bottom:2px;text-align:{'right' if is_customer else 'left'};">
                    {avatar} · {message['created_at'].strftime('%H:%M')} {sentiment_html}
                </div>
                <div style="background:{bg};color:{color};padding:0.65rem 1rem;border-radius:16px;font-size:0.95rem;white-space:pre-wrap;">
                    {message['content']}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


_QUICK_PROMPTS = [
    "Where is my order?",
    "How do I reset my password?",
    "What's your refund policy?",
    "I want to speak to a human agent",
]


def render(user_id: int) -> None:
    conversation_id = _ensure_active_conversation(user_id)

    left, right = st.columns([1, 2.4])
    with left:
        st.markdown('<div class="ics-section-title">Conversations</div>', unsafe_allow_html=True)
        _render_sidebar_panel(user_id)

    with right:
        st.markdown('<div class="ics-section-title">Live Chat</div>', unsafe_allow_html=True)
        _render_conversation_tools(conversation_id)

        messages = conversation_manager.get_messages(conversation_id)

        chat_container = st.container(height=420)
        with chat_container:
            if not messages:
                st.markdown(
                    '<div class="ics-card" style="text-align:center;">Say hello to start the conversation.</div>',
                    unsafe_allow_html=True,
                )
            for message in messages:
                _render_message_bubble(message)

        quick_prompt_clicked = None
        if not messages:
            st.markdown("**Quick prompts:**")
            qp_cols = st.columns(len(_QUICK_PROMPTS))
            for i, prompt in enumerate(_QUICK_PROMPTS):
                with qp_cols[i]:
                    if st.button(prompt, key=f"qp_{i}", use_container_width=True):
                        quick_prompt_clicked = prompt

        with st.expander("Chat in another language"):
            lang_code = st.selectbox(
                "Preferred language", list(SUPPORTED_LANGUAGES.keys()),
                format_func=lambda c: SUPPORTED_LANGUAGES[c], key=f"lang_{conversation_id}",
            )
            st.caption(
                f"Greeting preview: {translate_phrase('greeting', lang_code)}"
            )
            st.caption("Full free-text translation of every reply needs a translation API/model — this build ships a curated phrase set for common replies (greeting/thanks/goodbye) as a working starting point.")

        user_input = st.chat_input("Type your message...")
        final_input = quick_prompt_clicked or user_input

        if final_input:
            with st.spinner("AI is typing..."):
                result = chatbot_engine.process_message(conversation_id, final_input)
            if result.escalated:
                st.warning("This conversation has been escalated to a human agent.")
            st.rerun()

        with st.expander("Attach a document (PDF, DOCX, TXT, CSV, XLSX, image)"):
            uploaded = st.file_uploader(
                "Upload a file for the AI to summarise", type=["pdf", "docx", "txt", "csv", "xlsx", "png", "jpg", "jpeg"],
                key=f"upload_{conversation_id}",
            )
            if uploaded is not None and st.button("Analyse document", key=f"analyse_{conversation_id}"):
                file_bytes = uploaded.read()
                extraction = document_service.extract_text(uploaded.name, file_bytes)
                if not extraction.success:
                    st.error(extraction.error)
                else:
                    summary = document_service.summarize(extraction.text)
                    key_points = document_service.extract_key_points(extraction.text)
                    note = f"**{uploaded.name}** — summary:\n\n{summary}"
                    if key_points:
                        note += "\n\nKey points:\n" + "\n".join(f"- {p}" for p in key_points)
                    conversation_manager.add_message(conversation_id, "ai", note)
                    st.rerun()

        voice_flags = voice_service.voice_features_available()
        with st.expander("Voice"):
            if not voice_flags["speech_to_text"] and not voice_flags["text_to_speech"]:
                st.caption("Voice input/output isn't installed in this environment (pip install SpeechRecognition pyttsx3).")
            else:
                if voice_flags["speech_to_text"]:
                    audio = st.audio_input("Record a voice message", key=f"audio_{conversation_id}")
                    if audio is not None and st.button("Transcribe & send", key=f"transcribe_{conversation_id}"):
                        transcription = voice_service.transcribe_audio_bytes(audio.read())
                        if transcription.success:
                            with st.spinner("AI is typing..."):
                                chatbot_engine.process_message(conversation_id, transcription.text)
                            st.rerun()
                        else:
                            st.error(transcription.error)
                if not voice_flags["speech_to_text"]:
                    st.caption("Speech-to-text unavailable (pip install SpeechRecognition).")
                if not voice_flags["text_to_speech"]:
                    st.caption("Text-to-speech unavailable (pip install pyttsx3).")

        if messages:
            _download_transcript(conversation_id, messages)
