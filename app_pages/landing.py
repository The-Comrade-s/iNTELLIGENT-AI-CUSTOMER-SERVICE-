"""
app_pages/landing.py

Public marketing landing page shown to unauthenticated visitors.
"""

import streamlit as st

from constants import APP_NAME, APP_TAGLINE, SessionKeys


FEATURES = [
    ("AI Powered Support", "Natural-language understanding that resolves customer questions instantly."),
    ("24/7 Availability", "Your assistant never sleeps, so customers get help around the clock."),
    ("Smart Analytics", "Track satisfaction, resolution rate, and trends in real time."),
    ("Knowledge Base", "A searchable library that keeps every answer consistent and accurate."),
    ("Fast Response", "Sub-second retrieval keeps conversations feeling human and immediate."),
    ("Secure Platform", "Role-based access, hashed credentials, and full audit logging."),
]

STATS = [
    ("10,000+", "Customers Served"),
    ("99%", "Customer Satisfaction"),
    ("1 Million+", "Messages Processed"),
    ("24/7", "Availability"),
]

TESTIMONIALS = [
    ("\"Response times dropped from hours to seconds after we rolled this out.\"", "— Operations Lead, Retail"),
    ("\"Our support team finally gets to focus on the conversations that matter.\"", "— Support Manager, Fintech"),
    ("\"Set up in an afternoon, and it already feels like a full team member.\"", "— Founder, SaaS Startup"),
]


def render() -> None:
    """Render the landing page and its call-to-action buttons."""

    st.markdown(
        f"""
        <div class="ics-hero">
            <div class="ics-hero-title">{APP_NAME}</div>
            <div class="ics-hero-subtitle">{APP_TAGLINE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Start Chat", use_container_width=True):
                st.session_state[SessionKeys.AUTH_VIEW] = "login"
                st.session_state["_show_auth"] = True
                st.rerun()
        with c2:
            if st.button("Learn More", use_container_width=True):
                st.session_state["show_learn_more"] = True

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="ics-section-title">Why teams choose us</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, (title, desc) in enumerate(FEATURES):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div class="ics-card">
                    <div style="font-weight:700;font-size:1.05rem;margin:0 0 0.3rem 0;">{title}</div>
                    <div style="color:#6B7280;font-size:0.92rem;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="ics-section-title">Trusted at scale</div>', unsafe_allow_html=True)
    stat_cols = st.columns(4)
    for i, (value, label) in enumerate(STATS):
        with stat_cols[i]:
            st.markdown(
                f"""
                <div class="ics-card" style="text-align:center;">
                    <div class="ics-kpi-value">{value}</div>
                    <div class="ics-kpi-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="ics-section-title">What customers say</div>', unsafe_allow_html=True)
    t_cols = st.columns(3)
    for i, (quote, author) in enumerate(TESTIMONIALS):
        with t_cols[i]:
            st.markdown(
                f"""
                <div class="ics-card">
                    <div style="font-style:italic;color:#374151;">{quote}</div>
                    <div style="margin-top:0.6rem;font-weight:600;font-size:0.85rem;color:#6B7280;">{author}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        f"""
        <div style="text-align:center;padding:2.5rem 0 1rem 0;color:#94A3B8;font-size:0.85rem;border-top:1px solid rgba(148,163,184,0.18);margin-top:2rem;">
            © 2026 {APP_NAME}. Built with Python &amp; Streamlit.
        </div>
        """,
        unsafe_allow_html=True,
    )
