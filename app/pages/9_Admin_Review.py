import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import workflow

auth.require_role("ADMIN")
st.title("Publication Review")

try:
    pending = workflow.list_pending_publications()
    if pending.empty:
        st.info("There are no publications awaiting review.")
    else:
        for paper in pending.itertuples():
            with st.expander(f"#{paper.p_id}: {paper.p_title}"):
                st.write(f"**Owner:** {paper.owner_name}")
                st.write(f"**Submitted:** {paper.submitted_at}")
                st.write(f"**Abstract:** {paper.abstract or 'No abstract provided.'}")
                st.write(f"**Authors:** {paper.authors or 'None'}")
                st.write(f"**Topics:** {paper.topics or 'None'}")
                st.write(f"**Keywords:** {paper.keywords or 'None'}")
                with st.form(f"review_{paper.p_id}"):
                    remarks = st.text_area("Rejection explanation (required to reject)")
                    approve = st.form_submit_button("Approve", type="primary")
                    reject = st.form_submit_button("Reject")
                if approve or reject:
                    try:
                        workflow.review_paper(
                            int(paper.p_id), "APPROVED" if approve else "REJECTED", remarks
                        )
                        st.success("Decision recorded.")
                        st.rerun()
                    except Exception as exc:
                        st.error(db.friendly_error(exc))

    st.subheader("Manage publication status")
    all_papers = workflow.admin_list_publications()
    if all_papers.empty:
        st.info("No publications found.")
    else:
        st.dataframe(all_papers, use_container_width=True, hide_index=True)
        archivable = all_papers[all_papers["status"] == "APPROVED"]
        if not archivable.empty:
            choices = {
                f"#{int(row.p_id)} — {row.p_title}": int(row.p_id)
                for row in archivable.itertuples()
            }
            with st.form("archive_publication"):
                selected = st.selectbox("Approved publication", list(choices))
                archive = st.form_submit_button("Archive publication")
            if archive:
                try:
                    workflow.archive_paper(choices[selected])
                    st.success("Publication archived and removed from public discovery.")
                    st.rerun()
                except Exception as exc:
                    st.error(db.friendly_error(exc))

        edit_choices = {
            f"#{int(row.p_id)} — {row.p_title} [{row.status}]": int(row.p_id)
            for row in all_papers.itertuples()
        }
        selected_edit = st.selectbox("Publication to edit", list(edit_choices))
        edit_id = edit_choices[selected_edit]
        paper = workflow.admin_get_publication(edit_id)
        conferences = db.query("SELECT c_id, c_name, c_year FROM CONFERENCE ORDER BY c_name")
        conference_options = {"-- No Conference --": None}
        for conference in conferences.itertuples():
            conference_options[f"{conference.c_name} ({conference.c_year})"] = int(conference.c_id)
        current_conference = next(
            (label for label, conference_id in conference_options.items()
             if conference_id == paper["c_id"]),
            "-- No Conference --",
        )
        with st.form("admin_edit_publication"):
            title = st.text_input("Publication title", value=paper["p_title"])
            abstract = st.text_area("Abstract", value=paper["abstract"] or "")
            year = st.number_input(
                "Publication year", min_value=1, max_value=65535,
                value=int(paper["pub_year"]),
            )
            conference_label = st.selectbox(
                "Conference", list(conference_options),
                index=list(conference_options).index(current_conference),
            )
            save_edit = st.form_submit_button("Save publication changes")
        if save_edit:
            try:
                workflow.admin_update_paper(
                    edit_id, title, abstract, int(year), conference_options[conference_label]
                )
                st.success("Publication updated.")
                st.rerun()
            except Exception as exc:
                st.error(db.friendly_error(exc))
except Exception as exc:
    st.error(db.friendly_error(exc))
