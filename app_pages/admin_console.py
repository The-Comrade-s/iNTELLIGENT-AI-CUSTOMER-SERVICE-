"""
app_pages/admin_console.py

Admin-only console with tabs for user management, knowledge-base CMS,
escalation handling, and audit logs. All mutations go through
services/admin_service.py, which also writes the audit-log entries.
"""

import streamlit as st

from constants import ROLE_LABELS, UserRole
from services import admin_service


def _render_user_management(actor_id: int) -> None:
    st.markdown("**Search & filter users**")
    c1, c2, c3 = st.columns(3)
    with c1:
        search = st.text_input("Search by username/email", key="admin_user_search")
    with c2:
        role_filter = st.selectbox("Role", ["All"] + [r.value for r in UserRole], key="admin_user_role_filter")
    with c3:
        status_filter = st.selectbox("Status", ["All", "active", "inactive"], key="admin_user_status_filter")

    users = admin_service.list_users(
        search=search,
        role_filter="" if role_filter == "All" else role_filter,
        status_filter="" if status_filter == "All" else status_filter,
    )

    st.caption(f"{len(users)} user(s) found")

    for user in users:
        with st.expander(f"{'[Active]' if user['is_active'] else '[Inactive]'} {user['username']} — {user['email']} ({ROLE_LABELS.get(UserRole(user['role']), user['role'])})"):
            st.write(f"Full name: {user['full_name'] or '—'}")
            st.write(f"Joined: {user['created_at'].strftime('%Y-%m-%d')}  |  Last login: {user['last_login_at'].strftime('%Y-%m-%d %H:%M') if user['last_login_at'] else 'Never'}")

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                new_role = st.selectbox("Change role", [r.value for r in UserRole], index=[r.value for r in UserRole].index(user["role"]), key=f"role_{user['id']}")
                if new_role != user["role"] and st.button("Apply role", key=f"apply_role_{user['id']}"):
                    admin_service.set_user_role(user["id"], new_role, actor_id)
                    st.rerun()
            with c2:
                if user["is_active"]:
                    if st.button("Deactivate", key=f"deactivate_{user['id']}"):
                        admin_service.set_user_active(user["id"], False, actor_id)
                        st.rerun()
                else:
                    if st.button("Activate", key=f"activate_{user['id']}"):
                        admin_service.set_user_active(user["id"], True, actor_id)
                        st.rerun()
            with c3:
                new_password = st.text_input("Reset password to", type="password", key=f"reset_pw_{user['id']}")
                if st.button("Reset password", key=f"reset_pw_btn_{user['id']}") and new_password:
                    admin_service.admin_reset_password(user["id"], new_password, actor_id)
                    st.success("Password reset.")
            with c4:
                if st.button("Delete user", key=f"delete_user_{user['id']}"):
                    admin_service.delete_user(user["id"], actor_id)
                    st.rerun()


def _render_knowledge_base_cms(actor_id: int) -> None:
    with st.expander("Add new FAQ / article"):
        with st.form("new_faq_form"):
            question = st.text_input("Question")
            answer = st.text_area("Answer", height=100)
            c1, c2, c3 = st.columns(3)
            with c1:
                category = st.text_input("Category", value="General")
            with c2:
                keywords = st.text_input("Keywords (space-separated)")
            with c3:
                status = st.selectbox("Status", ["draft", "published", "archived"])
            submitted = st.form_submit_button("Create")
        if submitted and question and answer:
            admin_service.create_faq(question, answer, category, keywords, status, actor_id)
            st.success("FAQ created.")
            st.rerun()

    status_filter = st.selectbox("Filter by status", ["All", "draft", "published", "archived"], key="faq_status_filter")
    faqs = admin_service.list_faqs("" if status_filter == "All" else status_filter)
    st.caption(f"{len(faqs)} article(s)")

    for faq in faqs:
        with st.expander(f"[{faq['status']}] {faq['question']}  ·  {faq['views']} views"):
            with st.form(f"edit_faq_{faq['id']}"):
                question = st.text_input("Question", value=faq["question"], key=f"q_{faq['id']}")
                answer = st.text_area("Answer", value=faq["answer"], key=f"a_{faq['id']}", height=100)
                c1, c2, c3 = st.columns(3)
                with c1:
                    category = st.text_input("Category", value=faq["category"], key=f"cat_{faq['id']}")
                with c2:
                    keywords = st.text_input("Keywords", value=faq["keywords"] or "", key=f"kw_{faq['id']}")
                with c3:
                    status = st.selectbox("Status", ["draft", "published", "archived"], index=["draft", "published", "archived"].index(faq["status"]), key=f"st_{faq['id']}")
                save = st.form_submit_button("Save changes")
            if save:
                admin_service.update_faq(faq["id"], question, answer, category, keywords, status, actor_id)
                st.success("Saved.")
                st.rerun()
            if st.button("Delete this article", key=f"del_faq_{faq['id']}"):
                admin_service.delete_faq(faq["id"], actor_id)
                st.rerun()


def _render_escalations(actor_id: int) -> None:
    status_filter = st.selectbox("Filter", ["All", "open", "assigned", "resolved"], key="escalation_status_filter")
    escalations = admin_service.list_escalations("" if status_filter == "All" else status_filter)
    st.caption(f"{len(escalations)} escalation(s)")

    agents = [u for u in admin_service.list_users() if u["role"] in {"admin", "support_agent"}]

    for esc in escalations:
        with st.expander(f"#{esc['id']} — {esc['reason']} ({esc['status']})"):
            st.write(f"Conversation #{esc['conversation_id']}  ·  Opened {esc['created_at'].strftime('%Y-%m-%d %H:%M')}")
            if esc["status"] != "resolved":
                agent_options = {f"{a['username']} ({a['role']})": a["id"] for a in agents}
                if agent_options:
                    chosen = st.selectbox("Assign to", list(agent_options.keys()), key=f"assign_{esc['id']}")
                    if st.button("Assign", key=f"assign_btn_{esc['id']}"):
                        admin_service.assign_escalation(esc["id"], agent_options[chosen], actor_id)
                        st.rerun()
                notes = st.text_area("Resolution notes", key=f"notes_{esc['id']}")
                if st.button("Mark resolved", key=f"resolve_{esc['id']}"):
                    admin_service.resolve_escalation(esc["id"], notes, actor_id)
                    st.rerun()
            else:
                st.success(f"Resolved {esc['resolved_at'].strftime('%Y-%m-%d %H:%M') if esc['resolved_at'] else ''}")
                if esc["notes"]:
                    st.caption(esc["notes"])


def _render_audit_logs() -> None:
    actions = ["All"] + admin_service.distinct_audit_actions()
    action_filter = st.selectbox("Filter by action", actions, key="audit_action_filter")
    logs = admin_service.list_audit_logs("" if action_filter == "All" else action_filter)
    st.caption(f"Showing {len(logs)} most recent entries")
    st.dataframe(
        [{"time": l["created_at"].strftime("%Y-%m-%d %H:%M"), "user_id": l["user_id"], "action": l["action"], "description": l["description"]} for l in logs],
        use_container_width=True,
        height=420,
    )


def _render_prompt_templates(actor_id: int) -> None:
    from services import prompt_service

    prompts = prompt_service.list_prompts()
    for prompt in prompts:
        with st.expander(f"{prompt['label']}  ({prompt['key']})"):
            content = st.text_area("Content", value=prompt["content"], key=f"prompt_{prompt['id']}", height=100)
            if st.button("Save", key=f"save_prompt_{prompt['id']}"):
                prompt_service.update_prompt(prompt["id"], content)
                st.success("Prompt updated.")
                st.rerun()
            st.caption(f"Last updated: {prompt['updated_at'].strftime('%Y-%m-%d %H:%M')}")


def _render_customer_profiles() -> None:
    from services import customer_profile_service

    profiles = customer_profile_service.list_all_profiles()
    st.caption(f"{len(profiles)} customer profile(s) with activity")
    st.dataframe(
        [
            {
                "username": p["username"],
                "language": p["preferred_language"],
                "conversations": p["total_conversations"],
                "escalations": p["total_escalations"],
                "top_intent": p["most_frequent_intent"] or "—",
                "avg_sentiment": p["average_sentiment_score"],
                "last_seen": p["last_interaction_at"].strftime("%Y-%m-%d %H:%M") if p["last_interaction_at"] else "—",
            }
            for p in profiles
        ],
        use_container_width=True,
        height=400,
    )


def render(actor_id: int) -> None:
    st.markdown('<div class="ics-section-title">Admin Console</div>', unsafe_allow_html=True)

    tabs = st.tabs(["Users", "Knowledge Base", "Escalations", "Audit Logs", "Prompts", "Customer Profiles"])
    with tabs[0]:
        _render_user_management(actor_id)
    with tabs[1]:
        _render_knowledge_base_cms(actor_id)
    with tabs[2]:
        _render_escalations(actor_id)
    with tabs[3]:
        _render_audit_logs()
    with tabs[4]:
        _render_prompt_templates(actor_id)
    with tabs[5]:
        _render_customer_profiles()
