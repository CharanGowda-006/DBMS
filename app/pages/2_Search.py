import html
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import ui


auth.require_login()
ui.page_header("Academic Search", "Search approved research publications and related network records.")

with st.form("academic_search", clear_on_submit=False):
    term = st.text_input(
        "Search publications and research network",
        placeholder="Try a title, research topic, keyword, or researcher name",
        key="academic_search_term",
    )
    submitted = st.form_submit_button("Search", type="primary")

if submitted:
    if not term.strip():
        st.session_state["academic_search_results"] = None
        st.session_state["academic_search_term_submitted"] = ""
    else:
        try:
            with st.spinner("Searching the approved research network..."):
                result = db.call_proc("sp_search", (term.strip(),))
            st.session_state["academic_search_results"] = result
            st.session_state["academic_search_term_submitted"] = term.strip()
            st.session_state["academic_search_selected_paper"] = None
        except Exception as exc:
            st.error(db.friendly_error(exc))

if "academic_search_results" not in st.session_state:
    ui.empty_state(
        "Enter a search term to find papers by title, topic, or keyword and discover "
        "related researchers, conferences, projects, and datasets."
    )
else:
    search_results = st.session_state["academic_search_results"]
    search_term = st.session_state.get("academic_search_term_submitted", "")
    if not search_term:
        ui.empty_state("Enter a non-empty search term to begin.")
    elif search_results is None or search_results.empty:
        ui.empty_state(f"No results found for “{search_term}”. Try a broader search.")
    else:
        categories = {
            "paper": "Papers",
            "researcher": "Researchers",
            "conference": "Conferences",
            "project": "Projects",
            "dataset": "Datasets",
        }
        available_types = [
            kind for kind in categories
            if kind in set(search_results["result_type"].astype(str))
        ]
        selected_types = st.multiselect(
            "Result types",
            options=available_types,
            default=available_types,
            format_func=lambda value: categories[value],
        )
        filtered_results = search_results[
            search_results["result_type"].isin(selected_types)
        ]
        st.caption(
            f"{len(filtered_results)} result(s) shown for “{search_term}”."
        )
        if filtered_results.empty:
            ui.empty_state("No results match the selected result types.")
        else:
            for kind, title in categories.items():
                subset = filtered_results[filtered_results["result_type"] == kind]
                if subset.empty:
                    continue
                ui.section_header(f"{title} · {len(subset)}")
                if kind == "paper":
                    paper_options = {
                        int(row.ref_id): row
                        for row in subset.itertuples()
                    }
                    for paper_id, row in paper_options.items():
                        with st.container(border=True):
                            st.markdown(f"**{html.escape(str(row.label))}**")
                            st.caption(f"Paper #{paper_id} · {row.detail}")
                    inspect_id = st.selectbox(
                        "Inspect a paper",
                        options=list(paper_options),
                        format_func=lambda paper_id: (
                            f"#{paper_id} — {paper_options[paper_id].label}"
                        ),
                        key="academic_search_inspect",
                    )
                    with st.expander("Selected publication details", expanded=True):
                        paper = db.query(
                            """SELECT p.p_title, p.abstract, p.pub_year, c.c_name
                               FROM PAPER p
                               LEFT JOIN CONFERENCE c ON c.c_id = p.c_id
                               LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
                               WHERE p.p_id = %s
                                 AND COALESCE(w.status, 'APPROVED') = 'APPROVED'""",
                            (inspect_id,),
                        )
                        if paper.empty:
                            st.info("This approved publication is no longer available.")
                        else:
                            details = paper.iloc[0]
                            st.caption(
                                f"Published {details['pub_year']} · "
                                f"{details['c_name'] or 'No conference listed'}"
                            )
                            st.write(details["abstract"] or "No abstract available.")
                            authors = db.query(
                                """SELECT r.r_name
                                   FROM AUTHORS a
                                   JOIN RESEARCHER r ON r.r_id = a.r_id
                                   JOIN PAPER p ON p.p_id = a.p_id
                                   LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
                                   WHERE a.p_id = %s
                                     AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
                                   ORDER BY a.author_order""",
                                (inspect_id,),
                            )
                            topics = db.query(
                                """SELECT t.t_name
                                   FROM HAS_TOPIC ht JOIN TOPIC t ON t.t_id = ht.t_id
                                   JOIN PAPER p ON p.p_id = ht.p_id
                                   LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
                                   WHERE ht.p_id = %s
                                     AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
                                   ORDER BY t.t_name""",
                                (inspect_id,),
                            )
                            if not authors.empty:
                                st.caption(
                                    "Authors: " + ", ".join(authors["r_name"].astype(str))
                                )
                            if not topics.empty:
                                st.caption(
                                    "Topics: " + ", ".join(topics["t_name"].astype(str))
                                )
                else:
                    display = subset[["ref_id", "label", "detail"]].rename(columns={
                        "ref_id": "ID",
                        "label": "Name",
                        "detail": "Related information",
                    })
                    st.dataframe(
                        display,
                        width="stretch",
                        hide_index=True,
                    )
