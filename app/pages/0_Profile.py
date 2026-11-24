import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth

user = auth.require_login()
st.title("My Profile")
st.write(f"**Name:** {user['full_name']}")
st.write(f"**Email:** {user['email']}")
st.write(f"**Role:** {user['role'].title()}")
