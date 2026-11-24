import logging
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auth

logger = logging.getLogger(__name__)
st.set_page_config(
    page_title="Research Collaboration Network",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }
    [data-testid="stMetric"] {
        background: #f8faff; border: 1px solid #dde6f7;
        border-radius: 10px; padding: 14px 18px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem; color: #5a6a85;
        text-transform: uppercase; letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; color: #1a3a6b; }
    h2 { color: #1a3a6b; border-bottom: 2px solid #dde6f7; padding-bottom: 6px; margin-top: 1.4rem; }
    h3 { color: #2b5c8f; margin-top: 1rem; }
    section[data-testid="stSidebar"] { background: #0d2b55; color: white; }
    section[data-testid="stSidebar"] * { color: #d4e3f7 !important; }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { color: white !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    user = auth.get_current_user()
except Exception:
    logger.exception("Could not load the current user session.")
    st.error("The portal could not connect to its database. Check `.env` and apply the database migrations.")
    st.stop()
with st.sidebar:
    st.markdown("## 🔬 ResearchNet")
    st.markdown("**Academic Research Collaboration & Discovery Portal**")
    st.markdown("---")
    if user:
        st.markdown(f"**{user['full_name']}**")
        st.caption(f"Role: {user['role'].title()}")
        if st.button("Log out", use_container_width=True):
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
    account_pages = [st.Page("pages/0_Profile.py", title="My Profile", icon="👤")]
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
    pages["Account"] = account_pages

navigation = st.navigation(pages)
navigation.run()
