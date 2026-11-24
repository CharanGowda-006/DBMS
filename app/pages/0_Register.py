import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db

st.title("Create a student account")
st.caption("Public registration creates student accounts. Teachers and administrators are assigned by an administrator.")

with st.form("register_form", clear_on_submit=True):
    full_name = st.text_input("Full name")
    email = st.text_input("Email", autocomplete="email")
    password = st.text_input("Password (at least 12 characters)", type="password")
    confirm = st.text_input("Confirm password", type="password")
    submitted = st.form_submit_button("Register", type="primary")

if submitted:
    if password != confirm:
        st.error("Passwords do not match.")
    else:
        try:
            auth.register_user(full_name, email, password)
            st.success("Student account created. You can now log in.")
        except auth.AuthenticationError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(db.friendly_error(exc))
