import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import workflow

auth.require_role("ADMIN")
st.title("User Management")
st.caption("Find accounts, review access, and update roles or account status.")

try:
    users = workflow.list_users()
    if users.empty:
        st.info("No user accounts were found.")
    else:
        search = st.text_input("Search accounts", placeholder="Name or email")
        role_filter = st.selectbox(
            "Role", ["All roles", "STUDENT", "TEACHER", "ADMIN"]
        )
        status_filter = st.selectbox(
            "Account status", ["All accounts", "Active", "Inactive"]
        )
        filtered = users
        if search.strip():
            matches = (
                filtered["full_name"].astype(str).str.contains(search.strip(), case=False, na=False)
                | filtered["email"].astype(str).str.contains(search.strip(), case=False, na=False)
            )
            filtered = filtered[matches]
        if role_filter != "All roles":
            filtered = filtered[filtered["role"] == role_filter]
        if status_filter != "All accounts":
            active_value = status_filter == "Active"
            filtered = filtered[filtered["is_active"].astype(bool) == active_value]

        st.caption(f"{len(filtered)} of {len(users)} account(s)")
        st.dataframe(
            filtered[["user_id", "full_name", "email", "role", "is_active", "created_at"]].rename(
                columns={
                    "user_id": "User ID",
                    "full_name": "Name",
                    "email": "Email",
                    "role": "Role",
                    "is_active": "Active",
                    "created_at": "Created",
                }
            ),
            width="stretch",
            hide_index=True,
        )
        if not filtered.empty:
            choices = {
                f"#{int(row.user_id)} — {row.full_name} ({row.email})": row
                for row in filtered.itertuples()
            }
            selected = st.selectbox("Select account to edit", list(choices))
            account = choices[selected]
            st.subheader("Account Access")
            with st.form("update_user"):
                role = st.selectbox(
                    "Role",
                    ["STUDENT", "TEACHER", "ADMIN"],
                    index=["STUDENT", "TEACHER", "ADMIN"].index(account.role),
                )
                active = st.checkbox("Account active", value=bool(account.is_active))
                changed = role != account.role or active != bool(account.is_active)
                confirm = st.checkbox(
                    "Confirm this account access change",
                    disabled=not changed,
                )
                submitted = st.form_submit_button(
                    "Save account changes", type="primary"
                )
            if submitted:
                if changed and not confirm:
                    st.error("Confirm the role or account-status change before saving.")
                else:
                    try:
                        workflow.admin_update_user(int(account.user_id), role, active)
                        st.success("Account updated.")
                        st.rerun()
                    except Exception as exc:
                        st.error(db.friendly_error(exc))
except Exception as exc:
    st.error(db.friendly_error(exc))
