import logging
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth

logger = logging.getLogger(__name__)
left, center, right = st.columns([1, 1.15, 1])
with center:
    with st.container(width=480, border=True):
        st.markdown("### 🔬 ResearchNet")
        st.title("Welcome back")
        st.caption("Sign in to explore publications and research collaborations.")
        show_password = st.checkbox("Show password", key="login_show_password")
        email = st.text_input("Email", autocomplete="email", key="login_email")
        password = st.text_input(
            "Password",
            type="default" if show_password else "password",
            autocomplete="current-password",
            key="login_password",
        )
        submitted = st.button("Log in", type="primary", width="stretch")

        if submitted:
            try:
                if auth.login_user(email, password):
                    st.rerun()
                st.error("Invalid email or password.")
            except Exception:
                logger.exception("Authentication backend failure.")
                st.error("Unable to log in. Check the database configuration and migrations.")
        st.page_link("pages/0_Register.py", label="New to ResearchNet? Create an account")
