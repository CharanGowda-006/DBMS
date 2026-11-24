import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import workflow
import paper_form

current_user = auth.require_role("TEACHER", "ADMIN")
st.title("Research Paper Submission")

tab_paper, tab_citation = st.tabs(["📄 Submit Paper", "🔗 Manage Citations"])

with tab_paper:
    st.markdown(
        "Teacher submissions enter administrator review. Administrators may create approved publications."
    )
    saved_message = st.session_state.pop("add_paper_success", None)
    if st.session_state.pop("add_paper_clear", False):
        for key in list(st.session_state):
            if key.startswith("add_paper_"):
                del st.session_state[key]
    if saved_message:
        st.success(saved_message)
    try:
        conferences = db.query("SELECT c_id, c_name, c_year FROM CONFERENCE ORDER BY c_name")
        researchers = db.query(
            "SELECT r_id, r_name, email, institution FROM RESEARCHER ORDER BY r_name"
        )
        topics = db.query("SELECT t_id, t_name FROM TOPIC ORDER BY t_name")
        keywords = db.query("SELECT key_id, keyword FROM KEYWORD ORDER BY keyword")

        conference_options = {"-- No Conference / Pre-print --": None}
        for item in conferences.itertuples():
            conference_options[f"{item.c_name} ({item.c_year})"] = int(item.c_id)
        profile_rows = db.query(
            "SELECT researcher_id FROM APP_USER WHERE user_id = %s",
            (int(current_user["user_id"]),),
        )
        profile_researcher_id = (
            int(profile_rows.iloc[0]["researcher_id"])
            if not profile_rows.empty and profile_rows.iloc[0]["researcher_id"] is not None
            else None
        )

        st.subheader("Paper information")
        title = st.text_input("Paper title *", key="add_paper_title")
        abstract = st.text_area("Abstract", key="add_paper_abstract")
        year = st.number_input(
            "Publication year *", min_value=1, max_value=65535,
            value=2025, step=1, key="add_paper_year",
        )
        conference = st.selectbox(
            "Conference", list(conference_options), key="add_paper_conference"
        )
        selections = paper_form.render_dynamic_entity_controls(
            "add_paper",
            researchers.to_dict("records"),
            topics.to_dict("records"),
            keywords.to_dict("records"),
            profile_researcher_id=profile_researcher_id,
        )

        st.subheader("Review submission")
        st.write(f"**Title:** {title.strip() or 'Not entered'}")
        st.write(f"**Authors:** {len(selections['authors'])}")
        st.write(f"**Topics:** {len(selections['topics'])}")
        st.write(f"**Keywords:** {len(selections['keywords'])}")
        if st.button("Submit paper", type="primary", key="add_paper_submit"):
            try:
                paper_id, status = workflow.submit_paper(
                    title,
                    abstract,
                    int(year),
                    conference_options[conference],
                    selections["authors"],
                    selections["topics"],
                    selections["keywords"],
                )
                if status == "PENDING":
                    st.session_state["add_paper_success"] = (
                        "Paper submitted successfully. Awaiting administrator approval."
                    )
                else:
                    st.session_state["add_paper_success"] = (
                        f"Paper #{paper_id} was added as an approved publication."
                    )
                st.session_state["add_paper_clear"] = True
                st.rerun()
            except Exception as exc:
                st.error(db.friendly_error(exc))
        st.caption(
            "New researchers, topics, and keywords remain draft selections until the paper "
            "and all relationships are saved in one transaction."
        )
    except Exception as exc:
        st.error(db.friendly_error(exc))

with tab_citation:
    st.markdown("Teachers may add citations only from their own approved publications.")
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
                add = st.form_submit_button("Add citation")
            if add:
                try:
                    workflow.add_citation(citing_options[source], cited_options[target])
                    st.success("Citation relationship added.")
                except Exception as exc:
                    st.error(db.friendly_error(exc))

        st.subheader("Approved citation relationships")
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
        st.dataframe(citations, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(db.friendly_error(exc))
