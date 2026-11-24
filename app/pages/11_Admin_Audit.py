import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import workflow

auth.require_role("ADMIN")
st.title("Audit Logs")

try:
    with st.form("audit_filters"):
        action = st.text_input("Action (optional)")
        actor_id = st.number_input("Actor user ID (0 for any)", min_value=0, step=1)
        start_date = st.date_input("From date")
        end_date = st.date_input("Through date")
        submitted = st.form_submit_button("Apply filters")
    logs = workflow.list_audit_logs(
        action.strip() or None,
        int(actor_id) or None,
        start_date if submitted else None,
        end_date if submitted else None,
    )
    st.dataframe(logs, use_container_width=True, hide_index=True)
except Exception as exc:
    st.error(db.friendly_error(exc))
