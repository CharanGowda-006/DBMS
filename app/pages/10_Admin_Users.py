import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import workflow

auth.require_role("ADMIN")
st.title("User Management")

try:
    users = workflow.list_users()
    st.dataframe(
        users[["user_id", "full_name", "email", "role", "is_active", "created_at"]],
        use_container_width=True,
        hide_index=True,
    )
    if not users.empty:
        choices = {
            f"#{int(row.user_id)} — {row.full_name} ({row.email})": row
            for row in users.itertuples()
        }
        selected = st.selectbox("Select account", list(choices))
        account = choices[selected]
        with st.form("update_user"):
            role = st.selectbox(
                "Role", ["STUDENT", "TEACHER", "ADMIN"],
                index=["STUDENT", "TEACHER", "ADMIN"].index(account.role),
            )
            active = st.checkbox("Account active", value=bool(account.is_active))
            submitted = st.form_submit_button("Save account")
        if submitted:
            try:
                workflow.admin_update_user(int(account.user_id), role, active)
                st.success("Account updated.")
                st.rerun()
            except Exception as exc:
                st.error(db.friendly_error(exc))
except Exception as exc:
    st.error(db.friendly_error(exc))
