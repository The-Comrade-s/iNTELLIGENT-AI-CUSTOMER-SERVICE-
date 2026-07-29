"""
app_pages/dashboard.py

Authenticated landing page: KPI cards computed from real database
counts (not mocked numbers) plus a recent-activity feed. Chat volume
/ AI-accuracy KPIs are wired in from ICS-002 onward once the
conversations table exists; this phase reports what the current
schema actually supports.
"""

import datetime as dt

import streamlit as st

from database import ActivityLog, User, get_db
from styles import kpi_card


def _load_metrics():
    with get_db() as db:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active.is_(True)).count()
        today_start = dt.datetime.combine(dt.date.today(), dt.time.min)
        logins_today = (
            db.query(ActivityLog)
            .filter(ActivityLog.action == "login_success", ActivityLog.created_at >= today_start)
            .count()
        )
        recent_activity = (
            db.query(ActivityLog)
            .order_by(ActivityLog.created_at.desc())
            .limit(8)
            .all()
        )
        recent = [
            {
                "action": a.action,
                "description": a.description or "",
                "when": a.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for a in recent_activity
        ]
    return total_users, active_users, logins_today, recent


def render(full_name: str) -> None:
    st.markdown(f'<div class="ics-section-title">Welcome back, {full_name}</div>', unsafe_allow_html=True)

    total_users, active_users, logins_today, recent = _load_metrics()

    cols = st.columns(4)
    with cols[0]:
        st.markdown(kpi_card("Total Users", str(total_users)), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(kpi_card("Active Users", str(active_users)), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(kpi_card("Logins Today", str(logins_today)), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(kpi_card("System Status", "Online"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="ics-section-title">Recent Activity</div>', unsafe_allow_html=True)

    if not recent:
        st.markdown(
            '<div class="ics-card">No activity recorded yet — actions will appear here as your team uses the platform.</div>',
            unsafe_allow_html=True,
        )
    else:
        for item in recent:
            st.markdown(
                f"""
                <div class="ics-card" style="padding:0.85rem 1.2rem;">
                    <b>{item['action'].replace('_', ' ').title()}</b>
                    <span style="color:#6B7280;"> — {item['description']}</span>
                    <div style="font-size:0.78rem;color:#94A3B8;margin-top:0.2rem;">{item['when']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.info(
        "Chat volume, AI resolution rate, and satisfaction KPIs activate in **ICS-002** "
        "once the conversation engine and its database tables are built.",
    )
