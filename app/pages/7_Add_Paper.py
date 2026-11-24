import sys
from pathlib import Path
from datetime import date

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import workflow
import paper_form


current_user = auth.require_role("TEACHER", "ADMIN")
st.title("Research Paper Submission")
st.caption("Create a paper draft, review its metadata, then submit it in one transaction.")

tab_paper, tab_citation = st.tabs(["Submit Paper", "Manage Citations"])

with tab_paper:
    saved_message = st.session_state.pop("add_paper_success", None)
    if st.session_state.pop("add_paper_clear", False):
        for key in list(st.session_state):
            if key.startswith("add_paper_"):
                del st.session_state[key]
    if saved_message:
        st.success(saved_message)
        st.page_link("pages/8_My_Submissions.py", label="View My Submissions")

    st.caption(
        "Teacher submissions are reviewed by an administrator. Administrator-created "
        "publications are approved immediately."
    )
    try:
        conferences = db.query("SELECT c_id, c_name, c_year FROM CONFERENCE ORDER BY c_name")
        researchers = db.query(
            "SELECT r_id, r_name, email, institution FROM RESEARCHER ORDER BY r_name"
        )
        topics = db.query("SELECT t_id, t_name FROM TOPIC ORDER BY t_name")
        keywords = db.query("SELECT key_id, keyword FROM KEYWORD ORDER BY keyword")
        profile_rows = db.query(
            "SELECT researcher_id FROM APP_USER WHERE user_id = %s",
            (int(current_user["user_id"]),),
        )
        profile_researcher_id = (
            int(profile_rows.iloc[0]["researcher_id"])
            if not profile_rows.empty and profile_rows.iloc[0]["researcher_id"] is not None
            else None
        )

        conference_options = {"-- No Conference / Pre-print --": None}
        for item in conferences.itertuples():
            conference_options[f"{item.c_name} ({item.c_year})"] = int(item.c_id)

        steps = ("Paper Details", "Authors", "Classification", "Review & Submit")
        step = int(st.session_state.setdefault("add_paper_step", 0))
        st.progress((step + 1) / len(steps), text=f"Step {step + 1} of {len(steps)} · {steps[step]}")

        if step == 0:
            st.subheader("Paper Details")
            for field, default in (
                ("title", ""),
                ("abstract", ""),
                ("year", date.today().year),
                ("conference", "-- No Conference / Pre-print --"),
            ):
                widget_key = f"add_paper_{field}"
                draft_key = f"add_paper_draft_{field}"
                if widget_key not in st.session_state:
                    st.session_state[widget_key] = st.session_state.get(draft_key, default)
            st.text_input("Paper title *", key="add_paper_title")
            st.text_area("Abstract", key="add_paper_abstract")
            st.number_input(
                "Publication year *",
                min_value=1,
                max_value=65535,
                step=1,
                key="add_paper_year",
            )
            st.selectbox(
                "Conference",
                list(conference_options),
                key="add_paper_conference",
            )
        elif step == 1:
            st.subheader("Authors")
            selections = paper_form.render_dynamic_entity_controls(
                "add_paper",
                researchers.to_dict("records"),
                topics.to_dict("records"),
                keywords.to_dict("records"),
                profile_researcher_id=profile_researcher_id,
                sections=("authors",),
            )
        elif step == 2:
            st.subheader("Research Classification")
            selections = paper_form.render_dynamic_entity_controls(
                "add_paper",
                researchers.to_dict("records"),
                topics.to_dict("records"),
                keywords.to_dict("records"),
                profile_researcher_id=profile_researcher_id,
                sections=("topics", "keywords"),
            )
        else:
            st.subheader("Review & Submit")
            selections = {
                kind: list(st.session_state.get(f"add_paper_{kind}", []))
                for kind in ("authors", "topics", "keywords")
            }
            labels_by_kind = {
                "authors": {
                    int(item["r_id"]): f"{item['r_name']} — {item['email']}"
                    for item in researchers.to_dict("records")
                },
                "topics": {
                    int(item["t_id"]): item["t_name"]
                    for item in topics.to_dict("records")
                },
                "keywords": {
                    int(item["key_id"]): item["keyword"]
                    for item in keywords.to_dict("records")
                },
            }
            st.markdown("#### Paper Details")
            st.write(
                f"**Title:** "
                f"{st.session_state.get('add_paper_draft_title', '').strip() or 'Not entered'}"
            )
            st.write(
                f"**Publication year:** "
                f"{st.session_state.get('add_paper_draft_year', date.today().year)}"
            )
            st.write(
                f"**Conference:** "
                f"{st.session_state.get('add_paper_draft_conference', '-- No Conference / Pre-print --')}"
            )
            abstract = st.session_state.get("add_paper_draft_abstract", "").strip()
            st.write(abstract or "No abstract provided.")
            st.markdown("#### Authors and Classification")
            for kind, label in (
                ("authors", "Authors"),
                ("topics", "Research topics"),
                ("keywords", "Keywords"),
            ):
                values = []
                for item in selections[kind]:
                    if isinstance(item, dict) and isinstance(item.get("new"), dict):
                        researcher = item["new"]
                        values.append(
                            f"{researcher['name']} — {researcher['email']} (new)"
                        )
                    elif isinstance(item, dict) and isinstance(item.get("new"), str):
                        values.append(f"{item['new']} (new)")
                    else:
                        values.append(labels_by_kind[kind].get(int(item), f"Unknown #{item}"))
                st.markdown(f"**{label}**")
                st.write(", ".join(values) if values else "None selected")
                if not selections[kind]:
                    st.warning(f"Select at least one {label.lower()} before submitting.")
            st.caption(
                "New researchers, topics, and keywords are draft-only and are saved "
                "atomically with the paper."
            )

        back_col, spacer, next_col = st.columns([1, 4, 1])
        with back_col:
            if step > 0 and st.button("Back", key=f"add_paper_back_{step}"):
                st.session_state["add_paper_step"] = step - 1
                st.rerun()
        with next_col:
            if step < len(steps) - 1:
                if st.button("Continue", type="primary", key=f"add_paper_continue_{step}"):
                    if step == 0 and not st.session_state.get("add_paper_title", "").strip():
                        st.error("Enter a paper title before continuing.")
                    elif step == 1 and not st.session_state.get("add_paper_authors"):
                        st.error("Select or add at least one author before continuing.")
                    elif step == 2 and (
                        not st.session_state.get("add_paper_topics")
                        or not st.session_state.get("add_paper_keywords")
                    ):
                        st.error("Select at least one topic and keyword before continuing.")
                    else:
                        if step == 0:
                            for field in ("title", "abstract", "year", "conference"):
                                st.session_state[f"add_paper_draft_{field}"] = (
                                    st.session_state.get(f"add_paper_{field}")
                                )
                        st.session_state["add_paper_step"] = step + 1
                        st.rerun()
            elif st.button("Submit Paper", type="primary", key="add_paper_submit"):
                title = st.session_state.get("add_paper_draft_title", "")
                abstract = st.session_state.get("add_paper_draft_abstract", "")
                year = int(
                    st.session_state.get("add_paper_draft_year", date.today().year)
                )
                conference_label = st.session_state.get(
                    "add_paper_draft_conference", "-- No Conference / Pre-print --"
                )
                try:
                    paper_id, status = workflow.submit_paper(
                        title,
                        abstract,
                        year,
                        conference_options[conference_label],
                        selections["authors"],
                        selections["topics"],
                        selections["keywords"],
                    )
                    st.session_state["add_paper_success"] = (
                        "Paper submitted successfully. Awaiting administrator approval."
                        if status == "PENDING"
                        else f"Paper #{paper_id} was added as an approved publication."
                    )
                    st.session_state["add_paper_clear"] = True
                    st.rerun()
                except Exception as exc:
                    st.error(db.friendly_error(exc))
    except Exception as exc:
        st.error(db.friendly_error(exc))

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
