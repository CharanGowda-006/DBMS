import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db

if st.session_state.pop("register_clear", False):
    for key in ("register_full_name", "register_email", "register_password", "register_confirm"):
        st.session_state[key] = ""
registration_success = st.session_state.pop("register_success", None)

left, center, right = st.columns([1, 1.15, 1])
with center:
    with st.container(width=480, border=True):
        st.markdown("### 🔬 ResearchNet")
        st.title("Create your account")
        st.caption(
            "New accounts are created with Student access. Teacher permissions are "
            "assigned by an administrator."
        )
        if registration_success:
            st.success(registration_success)
        show_password = st.checkbox("Show passwords", key="register_show_password")
        full_name = st.text_input(
            "Full name", autocomplete="name", key="register_full_name"
        )
        email = st.text_input("Email", autocomplete="email", key="register_email")
        password = st.text_input(
            "Password (at least 12 characters)",
            type="default" if show_password else "password",
            autocomplete="new-password",
            key="register_password",
        )
        confirm = st.text_input(
            "Confirm password",
            type="default" if show_password else "password",
            autocomplete="new-password",
            key="register_confirm",
        )
        submitted = st.button("Register", type="primary", width="stretch")

        if submitted:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    auth.register_user(full_name, email, password)
                    st.session_state["register_success"] = (
                        "Student account created. You can now log in."
                    )
                    st.session_state["register_clear"] = True
                    st.rerun()
                except auth.AuthenticationError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(db.friendly_error(exc))
        st.page_link("pages/0_Login.py", label="Already registered? Log in")
