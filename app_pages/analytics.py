"""
app_pages/analytics.py

Analytics centre: conversation volume, intent distribution, sentiment
distribution, AI resolution rate, and average response time. Uses
Streamlit's built-in chart components (Altair under the hood) so
there's no extra native dependency to install; swapping to Plotly
for more advanced interactivity is a drop-in change per chart.
"""

import pandas as pd
import streamlit as st

from analytics.metrics import (
    average_response_time_ms,
    conversations_per_day,
    intent_distribution,
    sentiment_distribution,
    summary_kpis,
)
from styles import kpi_card


def render() -> None:
    st.markdown('<div class="ics-section-title">Analytics</div>', unsafe_allow_html=True)

    days = st.selectbox("Time range", [7, 14, 30, 90], index=2, format_func=lambda d: f"Last {d} days")

    kpis = summary_kpis(days)
    cols = st.columns(4)
    with cols[0]:
        st.markdown(kpi_card("Total Conversations", str(kpis["total_conversations"])), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(kpi_card("Conversations Today", str(kpis["conversations_today"])), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(kpi_card("AI Resolution Rate", f"{kpis['ai_resolution_rate']}%"), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(kpi_card("Human Escalations", str(kpis["total_escalations"])), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="ics-card">', unsafe_allow_html=True)
        st.markdown("**Conversations per day**")
        daily = conversations_per_day(days)
        df = pd.DataFrame({"date": list(daily.keys()), "conversations": list(daily.values())}).set_index("date")
        st.bar_chart(df, height=260)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="ics-card">', unsafe_allow_html=True)
        st.markdown("**Sentiment distribution**")
        sentiments = sentiment_distribution(days)
        if sentiments:
            df = pd.DataFrame({"sentiment": list(sentiments.keys()), "count": list(sentiments.values())}).set_index("sentiment")
            st.bar_chart(df, height=260)
        else:
            st.caption("No customer messages in this period yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="ics-card">', unsafe_allow_html=True)
    st.markdown("**Intent distribution**")
    intents = intent_distribution(days)
    if intents:
        df = pd.DataFrame({"intent": list(intents.keys()), "count": list(intents.values())}).set_index("intent")
        st.bar_chart(df, height=280)
    else:
        st.caption("No classified intents in this period yet.")
    st.markdown("</div>", unsafe_allow_html=True)

    avg_ms = average_response_time_ms(days)
    st.caption(f"Average AI response time: {avg_ms} ms" if avg_ms else "No response-time data yet.")
