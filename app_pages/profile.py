"""
app_pages/profile.py

Lets the signed-in user view/edit their profile and change their
password.
"""

import streamlit as st

from authentication import change_password
from constants import ROLE_LABELS, UserRole
from database import Profile, User, get_db


def _load_profile(user_id: int):
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        return {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.strftime("%Y-%m-%d"),
            "last_login": user.last_login_at.strftime("%Y-%m-%d %H:%M") if user.last_login_at else "Never",
            "is_active": user.is_active,
            "full_name": user.profile.full_name if user.profile else "",
            "phone": user.profile.phone if user.profile else "",
            "company": user.profile.company if user.profile else "",
            "job_title": user.profile.job_title if user.profile else "",
            "bio": user.profile.bio if user.profile else "",
        }


def _save_profile(user_id: int, full_name: str, phone: str, company: str, job_title: str, bio: str) -> None:
    with get_db() as db:
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if profile:
            profile.full_name = full_name
            profile.phone = phone
            profile.company = company
            profile.job_title = job_title
            profile.bio = bio


def render(user_id: int) -> None:
    data = _load_profile(user_id)
    if not data:
        st.error("Profile not found.")
        return

    st.markdown('<div class="ics-section-title">My Profile</div>', unsafe_allow_html=True)

    left, right = st.columns([1, 2])
    with left:
        st.markdown(
            f"""
            <div class="ics-card" style="text-align:center;">

                <div style="font-weight:700;font-size:1.1rem;">{data['full_name'] or data['username']}</div>
                <div style="color:#6B7280;font-size:0.85rem;">{ROLE_LABELS.get(UserRole(data['role']), data['role'])}</div>
                <div style="margin-top:0.6rem;font-size:0.8rem;color:#94A3B8;">
                    Member since {data['created_at']}<br>
                    Last login: {data['last_login']}<br>
                    Status: {"Active" if data['is_active'] else "Inactive"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown('<div class="ics-card">', unsafe_allow_html=True)
        with st.form("edit_profile_form"):
            full_name = st.text_input("Full Name", value=data["full_name"])
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Username", value=data["username"], disabled=True)
                phone = st.text_input("Phone", value=data["phone"] or "")
            with c2:
                st.text_input("Email", value=data["email"], disabled=True)
                job_title = st.text_input("Job Title", value=data["job_title"] or "")
            company = st.text_input("Company", value=data["company"] or "")
            bio = st.text_area("Bio", value=data["bio"] or "", height=90)
            saved = st.form_submit_button("Save Changes")

        if saved:
            _save_profile(user_id, full_name, phone, company, job_title, bio)
            st.success("Profile updated successfully.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="ics-section-title">Change Password</div>', unsafe_allow_html=True)
    st.markdown('<div class="ics-card">', unsafe_allow_html=True)
    with st.form("change_password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Update Password")

    if submitted:
        if new_password != confirm_password:
            st.error("New passwords do not match.")
        else:
            result = change_password(user_id, current_password, new_password)
            if result.success:
                st.success(result.message)
            else:
                st.error(result.message)
    st.markdown("</div>", unsafe_allow_html=True)
