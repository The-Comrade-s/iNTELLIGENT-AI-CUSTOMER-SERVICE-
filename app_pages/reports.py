"""
app_pages/reports.py

Report generation and export (CSV / TXT). PDF/Excel export is a
straightforward addition once reportlab/openpyxl are available in
the target environment -- the report *data* is already assembled
here in plain Python so adding a writer is a small, isolated change.
"""

import csv
import io
import json

import streamlit as st

from analytics.metrics import date_range_days, intent_distribution, sentiment_distribution, summary_kpis
from database import Conversation, User, get_db

REPORT_TYPES = ["Conversation Report", "Customer Report", "Intent Report", "Sentiment Report", "System Summary"]


def _conversation_report_rows(days: int) -> list[dict]:
    start, _ = date_range_days(days)
    with get_db() as db:
        conversations = db.query(Conversation).filter(Conversation.created_at >= start).all()
        return [
            {
                "conversation_id": c.id,
                "customer_id": c.user_id,
                "title": c.title,
                "message_count": len(c.messages),
                "created_at": c.created_at.isoformat(),
                "escalated": bool(c.escalation),
            }
            for c in conversations
        ]


def _customer_report_rows() -> list[dict]:
    with get_db() as db:
        users = db.query(User).filter(User.role == "customer").all()
        return [
            {
                "user_id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.profile.full_name if u.profile else "",
                "created_at": u.created_at.isoformat(),
                "last_login": u.last_login_at.isoformat() if u.last_login_at else "",
                "is_active": u.is_active,
            }
            for u in users
        ]


def _rows_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def render() -> None:
    st.markdown('<div class="ics-section-title">Reports</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        report_type = st.selectbox("Report type", REPORT_TYPES)
    with c2:
        days = st.selectbox("Period", [7, 30, 90, 365], index=1, format_func=lambda d: f"Last {d} days")

    if st.button("Generate Report", use_container_width=True):
        st.session_state["_report_generated"] = (report_type, days)

    generated = st.session_state.get("_report_generated")
    if not generated:
        return

    report_type, days = generated
    st.markdown(f'<div class="ics-card"><b>{report_type}</b> — last {days} days</div>', unsafe_allow_html=True)

    if report_type == "Conversation Report":
        rows = _conversation_report_rows(days)
        st.dataframe(rows, use_container_width=True)
        csv_data = _rows_to_csv(rows)
    elif report_type == "Customer Report":
        rows = _customer_report_rows()
        st.dataframe(rows, use_container_width=True)
        csv_data = _rows_to_csv(rows)
    elif report_type == "Intent Report":
        rows = [{"intent": k, "count": v} for k, v in intent_distribution(days).items()]
        st.dataframe(rows, use_container_width=True)
        csv_data = _rows_to_csv(rows)
    elif report_type == "Sentiment Report":
        rows = [{"sentiment": k, "count": v} for k, v in sentiment_distribution(days).items()]
        st.dataframe(rows, use_container_width=True)
        csv_data = _rows_to_csv(rows)
    else:  # System Summary
        summary = summary_kpis(days)
        st.json(summary)
        csv_data = json.dumps(summary, indent=2)

    file_ext = "json" if report_type == "System Summary" else "csv"
    mime = "application/json" if file_ext == "json" else "text/csv"
    st.download_button(
        f"Download {file_ext.upper()}",
        data=csv_data,
        file_name=f"{report_type.lower().replace(' ', '_')}.{file_ext}",
        mime=mime,
        use_container_width=True,
    )
