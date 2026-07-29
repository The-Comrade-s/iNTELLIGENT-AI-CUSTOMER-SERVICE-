"""
tests/test_chatbot_integration.py

End-to-end tests through the database: FAQ search, conversation
persistence, and the full chatbot_engine.process_message() pipeline.
"""

from authentication import register_user
from chatbot import chatbot_engine, conversation_manager
from chatbot.faq_engine import seed_default_faqs_if_empty, search


def _make_test_user(username: str) -> int:
    result = register_user(username, f"{username}@example.com", "Str0ngPass!", username.title())
    assert result.success
    return result.user_id


def test_faq_search_finds_seeded_password_faq():
    seed_default_faqs_if_empty()
    matches = search("how do I reset my password", top_n=3)
    assert any("password" in m.question.lower() for m in matches)


def test_conversation_crud_cycle():
    user_id = _make_test_user("conv_test_user")
    convo_id = conversation_manager.create_conversation(user_id)
    conversation_manager.add_message(convo_id, "customer", "Hello there")
    conversation_manager.add_message(convo_id, "ai", "Hi! How can I help?")

    messages = conversation_manager.get_messages(convo_id)
    assert len(messages) == 2
    assert messages[0]["sender"] == "customer"

    conversation_manager.rename_conversation(convo_id, "Renamed chat")
    conversations = conversation_manager.list_conversations(user_id)
    assert any(c["title"] == "Renamed chat" for c in conversations)

    conversation_manager.toggle_pin(convo_id)
    pinned = conversation_manager.list_conversations(user_id)
    assert pinned[0]["is_pinned"] is True


def test_process_message_returns_reply_and_persists():
    seed_default_faqs_if_empty()
    user_id = _make_test_user("engine_test_user")
    convo_id = conversation_manager.create_conversation(user_id)

    result = chatbot_engine.process_message(convo_id, "How do I reset my password?")
    assert result.reply
    assert result.intent in {"password_reset", "unknown"}

    messages = conversation_manager.get_messages(convo_id)
    assert len(messages) == 2  # customer + ai


def test_process_message_escalates_on_angry_sentiment():
    user_id = _make_test_user("angry_test_user")
    convo_id = conversation_manager.create_conversation(user_id)

    result = chatbot_engine.process_message(
        convo_id, "This is absolutely terrible and broken, I am furious and this is ridiculous!!"
    )
    assert result.escalated is True


def test_process_message_handles_empty_input_gracefully():
    user_id = _make_test_user("empty_test_user")
    convo_id = conversation_manager.create_conversation(user_id)
    result = chatbot_engine.process_message(convo_id, "   ")
    assert result.reply
    assert result.escalated is False
