import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
from citation_graph import (
    build_citation_graph,
    citation_figure,
    graph_paper_ids,
    validate_depth,
)


auth.require_login()

_GRAPH_LIMIT = 150
_QUERY_BATCH_SIZE = 500


def _paper_label(paper):
    year = paper.get("pub_year")
    year_label = year if year is not None and not pd.isna(year) else "Year unknown"
    title = str(paper.get("p_title") or "Untitled publication")
    return f"#{int(paper['p_id'])} — {title} ({year_label})"


def _fetch_approved_papers():
    return db.query(
        """SELECT p.p_id, p.p_title, p.pub_year
           FROM PAPER p
           LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
           WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
           ORDER BY p.p_id"""
    )


def _fetch_approved_metadata(paper_ids):
    records = []
    unique_ids = list(dict.fromkeys(int(paper_id) for paper_id in paper_ids))
    for offset in range(0, len(unique_ids), _QUERY_BATCH_SIZE):
        batch = unique_ids[offset:offset + _QUERY_BATCH_SIZE]
        placeholders = ", ".join(["%s"] * len(batch))
        batch_records = db.query(
            f"""SELECT p.p_id, p.p_title, p.abstract, p.pub_year, p.c_id,
                       c.c_name, c.c_year, c.c_location
                FROM PAPER p
                LEFT JOIN CONFERENCE c ON c.c_id = p.c_id
                LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
                WHERE p.p_id IN ({placeholders})
                  AND COALESCE(w.status, 'APPROVED') = 'APPROVED'""",
            tuple(batch),
        ).to_dict("records")
        for record in batch_records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        records.extend(batch_records)
    return records


def _fetch_approved_citation_edges(paper_ids):
    paper_ids = list(dict.fromkeys(int(paper_id) for paper_id in paper_ids))
    if not paper_ids:
        return []
    placeholders = ", ".join(["%s"] * len(paper_ids))
    return db.query(
        f"""SELECT c.citing_p_id, c.cited_p_id
            FROM CITES c
            JOIN PAPER src ON src.p_id = c.citing_p_id
            LEFT JOIN PAPER_WORKFLOW sw ON sw.p_id = src.p_id
            JOIN PAPER target ON target.p_id = c.cited_p_id
            LEFT JOIN PAPER_WORKFLOW tw ON tw.p_id = target.p_id
            WHERE c.citing_p_id IN ({placeholders})
              AND c.cited_p_id IN ({placeholders})
              AND COALESCE(sw.status, 'APPROVED') = 'APPROVED'
              AND COALESCE(tw.status, 'APPROVED') = 'APPROVED'""",
        tuple(paper_ids + paper_ids),
    ).to_dict("records")


def _run_exploration(root_p_id, direction, depth):
    depth = validate_depth(depth)
    root_p_id = int(root_p_id)
    root_rows = _fetch_approved_metadata([root_p_id])
    if not root_rows:
        return None

    traversal = db.call_proc("sp_citations", (root_p_id, direction, int(depth)))
    traversal_rows = traversal.to_dict("records")
    graph_ids = graph_paper_ids(root_p_id, traversal_rows, _GRAPH_LIMIT)
    all_paper_ids = [root_p_id, *(int(row["p_id"]) for row in traversal_rows)]
    papers = _fetch_approved_metadata(all_paper_ids)
    citation_edges = _fetch_approved_citation_edges(graph_ids)
    return build_citation_graph(
        root_p_id,
        traversal_rows,
        papers,
        citation_edges,
        direction,
        _GRAPH_LIMIT,
    )


def _show_paper_details(paper_id):
    details = _fetch_approved_metadata([paper_id])
    if not details:
        st.info("This approved publication is no longer available.")
        return
    paper = details[0]
    st.subheader(f"Paper #{int(paper['p_id'])}")
    st.text(str(paper.get("p_title") or "Untitled publication"))
    st.caption(f"Paper #{int(paper['p_id'])} · Published {paper['pub_year']}")
    abstract = paper.get("abstract")
    st.text(abstract if abstract else "No abstract available.")

    conference_name = paper.get("c_name")
    if conference_name and not pd.isna(conference_name):
        conference_label = str(conference_name)
        if paper.get("c_year") is not None and not pd.isna(paper["c_year"]):
            conference_label += f" ({paper['c_year']})"
        if paper.get("c_location") and not pd.isna(paper["c_location"]):
            conference_label += f" · {paper['c_location']}"
        st.text(f"Conference: {conference_label}")

    authors = db.query(
        """SELECT a.author_order, r.r_name, r.institution
           FROM AUTHORS a
           JOIN RESEARCHER r ON r.r_id = a.r_id
           JOIN PAPER p ON p.p_id = a.p_id
           LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
           WHERE a.p_id = %s
             AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
           ORDER BY a.author_order""",
        (int(paper_id),),
    )
    topics = db.query(
        """SELECT t.t_name
           FROM HAS_TOPIC ht
           JOIN TOPIC t ON t.t_id = ht.t_id
           JOIN PAPER p ON p.p_id = ht.p_id
           LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
           WHERE ht.p_id = %s
             AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
           ORDER BY t.t_name""",
        (int(paper_id),),
    )
    keywords = db.query(
        """SELECT k.keyword
           FROM HAS_KEYWORD hk
           JOIN KEYWORD k ON k.key_id = hk.key_id
           JOIN PAPER p ON p.p_id = hk.p_id
           LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
           WHERE hk.p_id = %s
             AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
           ORDER BY k.keyword""",
        (int(paper_id),),
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**Authors (in publication order)**")
        if authors.empty:
            st.caption("No authors listed.")
        else:
            for _, author in authors.iterrows():
                institution = author.get("institution")
                author_label = f"{int(author['author_order'])}. {author['r_name']}"
                if institution and not pd.isna(institution):
                    author_label += f" — {institution}"
                st.text(author_label)
    with right:
        st.markdown("**Research topics**")
        st.text(", ".join(topics["t_name"].astype(str)) if not topics.empty else "None listed")
        st.markdown("**Keywords**")
        st.text(", ".join(keywords["keyword"].astype(str)) if not keywords.empty else "None listed")


st.title("Citation Network Explorer")
st.caption("Explore how academic publications reference and influence one another.")

try:
    approved_papers = _fetch_approved_papers()
    if approved_papers.empty:
        st.info("No approved publications are available to explore.")
    else:
        paper_by_id = {
            int(row["p_id"]): row.to_dict()
            for _, row in approved_papers.iterrows()
        }
        with st.container(border=True):
            st.subheader("Explore Citations")
            root_p_id = st.selectbox(
                "Select Research Paper",
                options=list(paper_by_id),
                format_func=lambda paper_id: _paper_label(paper_by_id[paper_id]),
                key="citation_root_paper",
            )
            direction = st.radio(
                "Traversal Direction",
                options=("forward", "reverse"),
                format_func=lambda value: (
                    "Forward — References" if value == "forward"
                    else "Reverse — Citations Received"
                ),
                horizontal=True,
                key="citation_direction",
            )
            st.caption(
                "Forward follows references in this paper. Reverse finds papers that cite it."
            )
            depth = st.slider(
                "Maximum Citation Depth",
                min_value=1,
                max_value=5,
                value=3,
                help="Controls how many citation relationships can be followed from the selected paper.",
                key="citation_depth",
            )
            explore = st.button(
                "Explore Citation Network",
                type="primary",
                width="stretch",
            )

        if explore:
            with st.spinner("Tracing approved citation relationships..."):
                graph = _run_exploration(root_p_id, direction, depth)
            if graph is None:
                st.session_state.pop("citation_exploration", None)
                st.warning("The selected approved publication is no longer available.")
            else:
                st.session_state["citation_exploration"] = {
                    "graph": graph,
                    "requested_depth": depth,
                }

        exploration = st.session_state.get("citation_exploration")
        if exploration:
            graph = exploration["graph"]
            visible_ids = set(paper_by_id)
            if graph["root_p_id"] not in visible_ids:
                st.session_state.pop("citation_exploration", None)
                st.info("The selected approved publication is no longer available.")
                exploration = None
            else:
                graph["nodes"] = [
                    node for node in graph["nodes"] if node["id"] in visible_ids
                ]
                graph["results"] = [
                    result for result in graph["results"]
                    if result["p_id"] in visible_ids
                ]
                visible_graph_ids = {node["id"] for node in graph["nodes"]}
                graph["edges"] = [
                    edge for edge in graph["edges"]
                    if edge["citing_p_id"] in visible_graph_ids
                    and edge["cited_p_id"] in visible_graph_ids
                ]
                graph["reachable_count"] = len(graph["results"])
                graph["direct_connections"] = sum(
                    result["depth"] == 1 for result in graph["results"]
                )
                graph["max_depth"] = max(
                    (result["depth"] for result in graph["results"]),
                    default=0,
                )
                graph["graph_truncated"] = (
                    graph["reachable_count"] > len(graph["nodes"]) - 1
                )

        if exploration:
            graph = exploration["graph"]
            st.markdown("### Citation Network")
            st.caption(
                f"Last explored: Paper #{graph['root_p_id']} · "
                f"{graph['direction'].title()} · "
                f"maximum depth {exploration['requested_depth']}"
            )
            if graph["reachable_count"] == 0:
                st.info("No citations found in the selected direction.")
            st.plotly_chart(
                citation_figure(graph),
                width="stretch",
                config={"scrollZoom": True, "displaylogo": False},
            )
            st.caption(
                "Arrows always point from the citing paper to the cited paper. "
                "Only citation edges on returned traversal paths are shown. "
                "Blue marks the selected paper; lighter shades indicate traversal depth."
            )
            if graph["graph_truncated"]:
                st.warning(
                    f"The graph is limited to {_GRAPH_LIMIT} publications for readability. "
                    "Summary and detailed results still cover all reachable publications."
                )

            st.markdown("### Citation Summary")
            metric_a, metric_b, metric_c, metric_d = st.columns(4)
            metric_a.metric("Reachable Publications", graph["reachable_count"])
            metric_b.metric("Citation Relationships", len(graph["edges"]))
            metric_c.metric("Maximum Depth Reached", graph["max_depth"])
            metric_d.metric("Direct Connections", graph["direct_connections"])
            if graph["graph_truncated"]:
                st.caption("Citation relationship count reflects edges shown in the graph.")

            st.markdown("### Detailed Citation Results")
            st.caption(
                "Paths show traversal order from the selected paper; reverse paths are not "
                "the direction of the citation arrows. Each publication uses its shortest "
                "path, and Path Count shows the number of distinct paths returned."
            )
            if graph["results"]:
                results = pd.DataFrame(graph["results"]).rename(columns={
                    "depth": "Depth",
                    "p_id": "Paper ID",
                    "p_title": "Paper Title",
                    "pub_year": "Publication Year",
                    "path": "Canonical Traversal Path",
                    "path_count": "Path Count",
                })
                st.dataframe(results, width="stretch", hide_index=True)
                st.download_button(
                    "Download Citation Results",
                    data=results.to_csv(index=False).encode("utf-8"),
                    file_name=f"citation-results-paper-{graph['root_p_id']}.csv",
                    mime="text/csv",
                )
            else:
                st.caption("No related approved publications were reached.")

            st.markdown("### Publication Details")
            papers_to_inspect = {node["id"]: node for node in graph["nodes"]}
            inspect_id = st.selectbox(
                "Inspect a publication",
                options=list(papers_to_inspect),
                format_func=lambda paper_id: (
                    f"#{paper_id} — {papers_to_inspect[paper_id]['title']}"
                ),
                key=f"citation_inspect_{graph['root_p_id']}_{graph['direction']}",
            )
            _show_paper_details(inspect_id)

except Exception as exc:
    st.error(db.friendly_error(exc))
