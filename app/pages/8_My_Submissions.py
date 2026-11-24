import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import workflow
import paper_form

current_user = auth.require_role("TEACHER", "ADMIN")
st.title("My Submissions")

try:
    submissions = workflow.list_my_submissions()
    if submissions.empty:
        st.info("You have not submitted any papers yet.")
    else:
        display = submissions[["p_id", "p_title", "submitted_at", "status"]].rename(
            columns={
                "p_id": "Paper ID",
                "p_title": "Title",
                "submitted_at": "Submitted",
                "status": "Status",
            }
        )
        st.dataframe(display, use_container_width=True, hide_index=True)

        labels = {
            f"#{int(row.p_id)} — {row.p_title} [{row.status}]": int(row.p_id)
            for row in submissions.itertuples()
        }
        selected = st.selectbox("Select a submission", list(labels))
        row = submissions[submissions["p_id"] == labels[selected]].iloc[0]
        if row.get("rejection_remarks"):
            st.warning(f"Administrator remarks: {row['rejection_remarks']}")

        if row["status"] in ("PENDING", "REJECTED") and current_user["role"] == "TEACHER":
            paper = db.query(
                """SELECT p_title, abstract, pub_year, c_id
                   FROM PAPER WHERE p_id = %s""",
                (int(row["p_id"]),),
            ).iloc[0]
            conferences = db.query("SELECT c_id, c_name, c_year FROM CONFERENCE ORDER BY c_name")
            options = {"-- No Conference --": None}
            for conference in conferences.itertuples():
                options[f"{conference.c_name} ({conference.c_year})"] = int(conference.c_id)
            selected_label = next(
                (label for label, conference_id in options.items()
                 if conference_id == paper["c_id"]),
                "-- No Conference --",
            )
            researchers = db.query(
                "SELECT r_id, r_name, email, institution FROM RESEARCHER ORDER BY r_name"
            )
            topics = db.query("SELECT t_id, t_name FROM TOPIC ORDER BY t_name")
            keywords = db.query("SELECT key_id, keyword FROM KEYWORD ORDER BY keyword")
            current_authors = db.query(
                "SELECT r_id FROM AUTHORS WHERE p_id = %s ORDER BY author_order",
                (int(row["p_id"]),),
            )["r_id"].tolist()
            current_topics = db.query(
                "SELECT t_id FROM HAS_TOPIC WHERE p_id = %s",
                (int(row["p_id"]),),
            )["t_id"].tolist()
            current_keywords = db.query(
                "SELECT key_id FROM HAS_KEYWORD WHERE p_id = %s",
                (int(row["p_id"]),),
            )["key_id"].tolist()
            profile_rows = db.query(
                "SELECT researcher_id FROM APP_USER WHERE user_id = %s",
                (int(current_user["user_id"]),),
            )
            profile_researcher_id = (
                int(profile_rows.iloc[0]["researcher_id"])
                if not profile_rows.empty and profile_rows.iloc[0]["researcher_id"] is not None
                else None
            )
            st.subheader("Edit eligible submission")
            edit_prefix = f"edit_paper_{int(row['p_id'])}"
            title = st.text_input(
                "Title", value=paper["p_title"], key=f"{edit_prefix}_title"
            )
            abstract = st.text_area(
                "Abstract", value=paper["abstract"] or "", key=f"{edit_prefix}_abstract"
            )
            year = st.number_input(
                "Publication year", min_value=1, max_value=65535,
                value=int(paper["pub_year"]), key=f"{edit_prefix}_year",
            )
            conference_label = st.selectbox(
                "Conference", list(options), index=list(options).index(selected_label),
                key=f"{edit_prefix}_conference",
            )
            selections = paper_form.render_dynamic_entity_controls(
                edit_prefix,
                researchers.to_dict("records"),
                topics.to_dict("records"),
                keywords.to_dict("records"),
                profile_researcher_id=profile_researcher_id,
                initial={
                    "authors": [int(item) for item in current_authors],
                    "topics": [int(item) for item in current_topics],
                    "keywords": [int(item) for item in current_keywords],
                },
            )
            save = st.button("Save changes", key=f"{edit_prefix}_save")
            resubmit = (
                st.button("Resubmit for approval", key=f"{edit_prefix}_resubmit")
                if row["status"] == "REJECTED"
                else False
            )
            if save or resubmit:
                try:
                    workflow.edit_my_submission(
                        int(row["p_id"]), title, abstract, int(year), options[conference_label],
                        selections["authors"], selections["topics"], selections["keywords"],
                        resubmit=bool(resubmit),
                    )
                    st.success("Submission updated." if save else "Paper resubmitted for approval.")
                    st.rerun()
                except Exception as exc:
                    st.error(db.friendly_error(exc))
except Exception as exc:
    st.error(db.friendly_error(exc))
