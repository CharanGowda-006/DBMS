import logging
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auth
import ui

logger = logging.getLogger(__name__)
st.set_page_config(
    page_title="ResearchNet",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.install_styles()

try:
    user = auth.get_current_user()
except Exception:
    logger.exception("Could not load the current user session.")
    st.error("The portal could not connect to its database. Check `.env` and apply the database migrations.")
    st.stop()
with st.sidebar:
    st.markdown("### 🔬 ResearchNet")
    if user:
        st.caption(f"{user['full_name']} · {user['role'].title()}")
        if st.button("Log out", width="stretch"):
            auth.logout_user()
            st.rerun()

pages = {}
if user is None:
    pages["Account"] = [
        st.Page("pages/0_Login.py", title="Login", icon="🔐", default=True),
        st.Page("pages/0_Register.py", title="Register", icon="📝"),
    ]
else:
    pages["Research"] = [
        st.Page("pages/0_Dashboard.py", title="Dashboard", icon="🏠", url_path="dashboard", default=True),
        st.Page("pages/1_Overview.py", title="Overview", icon="📊"),
        st.Page("pages/2_Search.py", title="Search", icon="🔍"),
        st.Page("pages/3_Insights.py", title="Insights", icon="🧠"),
        st.Page("pages/4_Citations.py", title="Citations", icon="🔗"),
        st.Page("pages/5_Projects.py", title="Projects", icon="📁"),
    ]
    if user["role"] in ("TEACHER", "ADMIN"):
        pages["Research"].extend([
            st.Page("pages/7_Add_Paper.py", title="Add Paper", icon="📄"),
            st.Page("pages/8_My_Submissions.py", title="My Submissions", icon="📨"),
        ])
    if user["role"] == "ADMIN":
        pages["Administration"] = [
            st.Page("pages/6_Add_Basic.py", title="Add Entities", icon="➕"),
            st.Page("pages/9_Admin_Review.py", title="Publication Review", icon="✅"),
            st.Page("pages/10_Admin_Users.py", title="User Management", icon="🛡️"),
            st.Page("pages/11_Admin_Audit.py", title="Audit Logs", icon="📋"),
        ]
    pages["Account"] = [
        st.Page("pages/0_Profile.py", title="My Profile", icon="👤")
    ]

navigation = st.navigation(pages)
navigation.run()
