import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth

user = auth.require_login()
st.title("My Profile")
st.caption("Account information and access level.")
with st.container(border=True):
    st.subheader(user["full_name"])
    name_col, email_col, role_col = st.columns(3)
    name_col.metric("Full Name", user["full_name"])
    email_col.metric("Email", user["email"])
    role_col.metric("Role", user["role"].title())
    st.caption("Contact an administrator if your account role needs to be changed.")
