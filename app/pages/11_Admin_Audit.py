import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import workflow


def _redact_audit_values(value):
    if not value:
        return "Not recorded"
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return str(value)
    sensitive_keys = ("password", "token", "secret")

    def redact(item):
        if isinstance(item, dict):
            return {
                key: (
                    "[redacted]"
                    if any(part in str(key).lower() for part in sensitive_keys)
                    else redact(child)
                )
                for key, child in item.items()
            }
        if isinstance(item, list):
            return [redact(child) for child in item]
        return item

    return json.dumps(redact(parsed), ensure_ascii=False, indent=2)


auth.require_role("ADMIN")
st.title("Audit Logs")
st.caption("Review account, publication, project, and administrative activity.")

try:
    with st.form("audit_filters"):
        filter_col_a, filter_col_b = st.columns(2)
        with filter_col_a:
            action = st.text_input("Action")
            actor_id = st.number_input("Actor user ID (0 for any)", min_value=0, step=1)
        with filter_col_b:
            start_date = st.date_input("From date")
            end_date = st.date_input("Through date")
        submitted = st.form_submit_button("Apply filters", type="primary")
    logs = workflow.list_audit_logs(
        action.strip() or None,
        int(actor_id) or None,
        start_date if submitted else None,
        end_date if submitted else None,
    )
    if logs.empty:
        st.info("No audit events match the selected filters.")
    else:
        st.caption(f"{len(logs)} event(s) shown · maximum 500 most recent records")
        columns = [
            "audit_id", "created_at", "actor_name", "action", "entity_type", "entity_id"
        ]
        st.dataframe(
            logs[columns].rename(columns={
                "audit_id": "Event ID",
                "created_at": "Timestamp",
                "actor_name": "Actor",
                "action": "Action",
                "entity_type": "Entity",
                "entity_id": "Entity ID",
            }),
            width="stretch",
            hide_index=True,
        )
        choices = {
            f"#{int(row.audit_id)} · {row.action} · {row.created_at}": int(row.audit_id)
            for row in logs.itertuples()
        }
        selected_id = st.selectbox("Inspect an event", list(choices.values()),
                                   format_func=lambda audit_id: next(
                                       label for label, value in choices.items()
                                       if value == audit_id
                                   ))
        selected = logs[logs["audit_id"].astype(int) == selected_id].iloc[0]
        with st.expander("Change details"):
            st.text(f"Actor: {selected.get('actor_name') or 'Unknown'}")
            st.text(f"Action: {selected['action']}")
            st.text(f"Entity: {selected['entity_type']} #{selected['entity_id']}")
            st.markdown("**Previous values**")
            st.code(_redact_audit_values(selected.get("old_values")), language="json")
            st.markdown("**New values**")
            st.code(_redact_audit_values(selected.get("new_values")), language="json")
except Exception as exc:
    st.error(db.friendly_error(exc))
