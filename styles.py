"""
styles.py

Injects the platform's custom CSS so the app looks like a premium
SaaS product rather than a default Streamlit app: glassmorphism
cards, gradient buttons, hidden Streamlit chrome, and consistent
typography/spacing. Every page calls ``apply_global_styles()`` once.
"""

import streamlit as st

from constants import Colors


def apply_global_styles(dark_mode: bool = False) -> None:
    """Inject the global stylesheet. Call once near the top of every
    page render, before any other st.* calls that produce output."""

    bg = Colors.DARK_BACKGROUND if dark_mode else Colors.BACKGROUND
    card_bg = Colors.CARD_DARK if dark_mode else Colors.CARD_LIGHT
    text_color = "#F1F5F9" if dark_mode else Colors.TEXT

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        /* Hide default Streamlit chrome, but keep the header itself
           visible/interactive since the sidebar expand/collapse arrow
           lives inside it -- hiding the whole header made the sidebar
           impossible to reopen once collapsed. */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        div[data-testid="stDecoration"] {{display: none;}}
        [data-testid="stAppDeployButton"] {{display: none;}}
        header[data-testid="stHeader"] {{
            background: transparent;
            box-shadow: none;
        }}

        /* Belt-and-braces: force the sidebar's own open/close control
           to stay visible and clickable no matter which Streamlit
           version's data-testid naming applies, and no matter what
           other rule above might otherwise catch it. */
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarNavCollapseButton"],
        header[data-testid="stHeader"] button {{
            visibility: visible !important;
            display: flex !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            z-index: 999999 !important;
        }}

        .stApp {{
            background: {bg};
            color: {text_color};
        }}

        /* ---- Glass card ---- */
        .ics-card {{
            background: {card_bg};
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 18px;
            padding: 1.5rem 1.75rem;
            box-shadow: 0 8px 32px rgba(15, 23, 42, 0.08);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            margin-bottom: 1rem;
        }}
        .ics-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(15, 23, 42, 0.14);
        }}

        /* ---- KPI card ---- */
        .ics-kpi-label {{
            font-size: 0.82rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            color: {Colors.TEXT_MUTED};
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }}
        .ics-kpi-value {{
            font-size: 2rem;
            font-weight: 800;
            color: {text_color};
            line-height: 1.1;
        }}
        .ics-kpi-delta-up {{ color: {Colors.SUCCESS}; font-weight: 600; font-size: 0.85rem; }}
        .ics-kpi-delta-down {{ color: {Colors.DANGER}; font-weight: 600; font-size: 0.85rem; }}

        /* ---- Gradient buttons ---- */
        .stButton > button, .stFormSubmitButton > button {{
            background: linear-gradient(135deg, {Colors.PRIMARY} 0%, {Colors.ACCENT} 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.6rem 1.4rem;
            font-weight: 600;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.28);
            transition: transform 0.12s ease, box-shadow 0.12s ease;
        }}
        .stButton > button:hover, .stFormSubmitButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.36);
            color: white;
        }}

        /* ---- Hero section ---- */
        .ics-hero {{
            text-align: center;
            padding: 3.5rem 1rem 2.5rem 1rem;
        }}
        .ics-hero-title {{
            font-size: 2.6rem;
            font-weight: 800;
            background: linear-gradient(135deg, {Colors.PRIMARY}, {Colors.ACCENT});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.75rem;
        }}
        .ics-hero-subtitle {{
            font-size: 1.05rem;
            color: {Colors.TEXT_MUTED};
            max-width: 620px;
            margin: 0 auto 1.75rem auto;
        }}

        /* ---- Badges ---- */
        .ics-badge {{
            display: inline-block;
            padding: 0.2rem 0.7rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.02em;
        }}
        .ics-badge-success {{ background: rgba(34,197,94,0.14); color: {Colors.SUCCESS}; }}
        .ics-badge-warning {{ background: rgba(245,158,11,0.14); color: {Colors.WARNING}; }}
        .ics-badge-danger {{ background: rgba(239,68,68,0.14); color: {Colors.DANGER}; }}
        .ics-badge-info {{ background: rgba(14,165,233,0.14); color: {Colors.INFO}; }}

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {{
            background: {bg};
            border-right: 1px solid rgba(148, 163, 184, 0.15);
        }}

        /* ---- Section heading ---- */
        .ics-section-title {{
            font-size: 1.3rem;
            font-weight: 700;
            margin: 0.25rem 0 1rem 0;
            color: {text_color};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, delta: str = "", delta_positive: bool = True, icon: str = "") -> str:
    """Return HTML for a single glassmorphism KPI card."""

    delta_html = ""
    if delta:
        cls = "ics-kpi-delta-up" if delta_positive else "ics-kpi-delta-down"
        arrow = "▲" if delta_positive else "▼"
        delta_html = f'<div class="{cls}">{arrow} {delta}</div>'

    label_html = f"{icon} {label}" if icon else label

    return f"""
    <div class="ics-card">
        <div class="ics-kpi-label">{label_html}</div>
        <div class="ics-kpi-value">{value}</div>
        {delta_html}
    </div>
    """


def badge(text: str, kind: str = "info") -> str:
    """Return HTML for a small status badge (kind: success/warning/danger/info)."""

    return f'<span class="ics-badge ics-badge-{kind}">{text}</span>'
