import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import workflow
from paper_ingestion.ui import render_smart_import


current_user = auth.require_role("TEACHER", "ADMIN")
st.title("Research Paper Submission")
st.caption("Import and review academic papers before submitting them.")

tab_paper, tab_citation = st.tabs(["Submit Paper", "Manage Citations"])

with tab_paper:
    render_smart_import()

with tab_citation:
    st.caption("Teachers may add citations only from their own approved publications.")
    try:
        approved = db.query(
            """SELECT p.p_id, p.p_title, p.pub_year FROM PAPER p
               LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
               WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
               ORDER BY p.p_id"""
        )
        if current_user["role"] == "ADMIN":
            citing = approved
        else:
            citing = db.query(
                """SELECT p.p_id, p.p_title, p.pub_year FROM PAPER p
                   JOIN PAPER_OWNERSHIP o ON o.p_id = p.p_id
                   JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
                   WHERE o.owner_user_id = %s AND w.status = 'APPROVED'
                   ORDER BY p.p_id""",
                (int(current_user["user_id"]),),
            )
        if citing.empty or approved.empty:
            st.info("An eligible citing paper and an approved cited paper are required.")
        else:
            citing_options = {
                f"#{item.p_id}: {item.p_title} ({item.pub_year})": int(item.p_id)
                for item in citing.itertuples()
            }
            cited_options = {
                f"#{item.p_id}: {item.p_title} ({item.pub_year})": int(item.p_id)
                for item in approved.itertuples()
            }
            with st.form("add_citation"):
                source = st.selectbox("Citing paper", list(citing_options))
                target = st.selectbox("Cited paper", list(cited_options))
                add = st.form_submit_button("Add citation", type="primary")
            if add:
                try:
                    workflow.add_citation(citing_options[source], cited_options[target])
                    st.success("Citation relationship added.")
                except Exception as exc:
                    st.error(db.friendly_error(exc))

        with st.expander("Approved citation relationships"):
            citations = db.query(
                """SELECT c.citing_p_id AS `Citing ID`, p1.p_title AS `Citing Paper`,
                          c.cited_p_id AS `Cited ID`, p2.p_title AS `Cited Paper`
                   FROM CITES c
                   JOIN PAPER p1 ON p1.p_id = c.citing_p_id
                   JOIN PAPER p2 ON p2.p_id = c.cited_p_id
                   LEFT JOIN PAPER_WORKFLOW w1 ON w1.p_id = p1.p_id
                   LEFT JOIN PAPER_WORKFLOW w2 ON w2.p_id = p2.p_id
                   WHERE COALESCE(w1.status, 'APPROVED') = 'APPROVED'
                     AND COALESCE(w2.status, 'APPROVED') = 'APPROVED'
                   ORDER BY c.citing_p_id, c.cited_p_id"""
            )
            st.dataframe(citations, width="stretch", hide_index=True)
    except Exception as exc:
        st.error(db.friendly_error(exc))
