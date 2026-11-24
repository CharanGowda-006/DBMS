import logging
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth

logger = logging.getLogger(__name__)
st.title("Log in")
st.markdown("Sign in to explore the Research Collaboration Network.")

with st.form("login_form"):
    email = st.text_input("Email", autocomplete="email")
    password = st.text_input("Password", type="password", autocomplete="current-password")
    submitted = st.form_submit_button("Log in", type="primary")

if submitted:
    try:
        if auth.login_user(email, password):
            st.rerun()
        st.error("Invalid email or password.")
    except Exception:
        logger.exception("Authentication backend failure.")
        st.error("Unable to log in. Check that the database is configured and migrations have been applied.")
