import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import workflow


auth.require_role("ADMIN")
st.title("Publication Review")
st.caption("Review submissions and manage published-paper status.")

try:
    pending = workflow.list_pending_publications()
    st.subheader(f"Review Queue · {len(pending)} pending")
    if pending.empty:
        st.info("There are no publications awaiting review.")
    else:
        choices = {
            int(row.p_id): row
            for row in pending.itertuples()
        }
        selected_id = st.selectbox(
            "Select a pending submission",
            options=list(choices),
            format_func=lambda paper_id: (
                f"#{paper_id} — {choices[paper_id].p_title} · "
                f"{choices[paper_id].owner_name}"
            ),
        )
        paper = choices[selected_id]
        with st.container(border=True):
            st.markdown(f"### {paper.p_title}")
            st.caption(
                f"Paper #{int(paper.p_id)} · Published {paper.pub_year} · "
                f"Submitted {paper.submitted_at}"
            )
            st.write(f"**Submission owner:** {paper.owner_name}")
            st.write(paper.abstract or "No abstract provided.")
            author_col, classification_col = st.columns(2)
            with author_col:
                st.markdown("**Authors**")
                st.write(paper.authors or "None listed")
            with classification_col:
                st.markdown("**Topics**")
                st.write(paper.topics or "None listed")
                st.markdown("**Keywords**")
                st.write(paper.keywords or "None listed")

        approve_col, reject_col = st.columns(2)
        with approve_col:
            with st.form(f"approve_publication_{selected_id}"):
                st.markdown("**Approve submission**")
                confirm_approval = st.checkbox("Confirm approval")
                approve = st.form_submit_button("Approve", type="primary")
            if approve:
                if not confirm_approval:
                    st.error("Confirm the approval before recording the decision.")
                else:
                    try:
                        workflow.review_paper(int(selected_id), "APPROVED")
                        st.success("Publication approved.")
                        st.rerun()
                    except Exception as exc:
                        st.error(db.friendly_error(exc))
        with reject_col:
            with st.form(f"reject_publication_{selected_id}"):
                st.markdown("**Reject submission**")
                remarks = st.text_area("Rejection explanation (required)")
                confirm_rejection = st.checkbox("Confirm rejection")
                reject = st.form_submit_button("Reject")
            if reject:
                if not remarks.strip():
                    st.error("Provide a rejection explanation.")
                elif not confirm_rejection:
                    st.error("Confirm the rejection before recording the decision.")
                else:
                    try:
                        workflow.review_paper(
                            int(selected_id), "REJECTED", remarks.strip()
                        )
                        st.success("Publication rejected and remarks saved.")
                        st.rerun()
                    except Exception as exc:
                        st.error(db.friendly_error(exc))

    with st.expander("Manage publication status and details"):
        all_papers = workflow.admin_list_publications()
        if all_papers.empty:
            st.info("No publications found.")
        else:
            st.dataframe(
                all_papers.rename(columns={
                    "p_id": "Paper ID",
                    "p_title": "Title",
                    "status": "Status",
                }),
                width="stretch",
                hide_index=True,
            )
            archivable = all_papers[all_papers["status"] == "APPROVED"]
            if not archivable.empty:
                archive_choices = {
                    int(row.p_id): row.p_title for row in archivable.itertuples()
                }
                with st.form("archive_publication"):
                    selected_archive = st.selectbox(
                        "Approved publication",
                        options=list(archive_choices),
                        format_func=lambda paper_id: (
                            f"#{paper_id} — {archive_choices[paper_id]}"
                        ),
                    )
                    confirm_archive = st.checkbox("Confirm archive")
                    archive = st.form_submit_button("Archive publication")
                if archive:
                    if not confirm_archive:
                        st.error("Confirm the archive action before continuing.")
                    else:
                        try:
                            workflow.archive_paper(int(selected_archive))
                            st.success("Publication archived and removed from public discovery.")
                            st.rerun()
                        except Exception as exc:
                            st.error(db.friendly_error(exc))

            edit_choices = {
                int(row.p_id): f"#{int(row.p_id)} — {row.p_title} [{row.status}]"
                for row in all_papers.itertuples()
            }
            edit_id = st.selectbox(
                "Publication to edit",
                options=list(edit_choices),
                format_func=lambda paper_id: edit_choices[paper_id],
            )
            paper = workflow.admin_get_publication(edit_id)
            conferences = db.query(
                "SELECT c_id, c_name, c_year FROM CONFERENCE ORDER BY c_name"
            )
            conference_options = {"-- No Conference --": None}
            for conference in conferences.itertuples():
                conference_options[
                    f"{conference.c_name} ({conference.c_year})"
                ] = int(conference.c_id)
            current_conference = next(
                (
                    label for label, conference_id in conference_options.items()
                    if conference_id == paper["c_id"]
                ),
                "-- No Conference --",
            )
            with st.form("admin_edit_publication"):
                title = st.text_input("Publication title", value=paper["p_title"])
                abstract = st.text_area("Abstract", value=paper["abstract"] or "")
                year = st.number_input(
                    "Publication year",
                    min_value=1,
                    max_value=65535,
                    value=int(paper["pub_year"]),
                )
                conference_label = st.selectbox(
                    "Conference",
                    list(conference_options),
                    index=list(conference_options).index(current_conference),
                )
                save_edit = st.form_submit_button("Save publication changes")
            if save_edit:
                try:
                    workflow.admin_update_paper(
                        edit_id,
                        title,
                        abstract,
                        int(year),
                        conference_options[conference_label],
                    )
                    st.success("Publication updated.")
                    st.rerun()
                except Exception as exc:
                    st.error(db.friendly_error(exc))
except Exception as exc:
    st.error(db.friendly_error(exc))
