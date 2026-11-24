from html import escape
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
from insights import (
    COLLABORATION_FILTERS,
    OVERLAP_BANDS,
    collaboration_figure,
    collaboration_metrics,
    compare_sets,
    filter_collaborations,
    filter_similar_papers,
    similarity_metrics,
)


auth.require_login()

_GRAPH_RESEARCHER_LIMIT = 80
_GRAPH_EDGE_LIMIT = 160
_RECOMMENDATION_LIMIT = 8


@st.cache_data(ttl=30, show_spinner=False)
def _load_researchers():
    return db.query(
        """SELECT DISTINCT r.r_id, r.r_name, r.institution
           FROM RESEARCHER r
           JOIN AUTHORS a ON a.r_id = r.r_id
           JOIN PAPER p ON p.p_id = a.p_id
           LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
           WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
           ORDER BY r.r_name, r.r_id"""
    )


@st.cache_data(ttl=30, show_spinner=False)
def _load_collaborations(researcher_id):
    return db.query(
        """SELECT c.r1_id, c.r1_name, r1.institution AS r1_institution,
                  c.r2_id, c.r2_name, r2.institution AS r2_institution,
                  c.shared_topic_count, c.shared_topics, c.already_coauthored
           FROM v_collaborators c
           JOIN RESEARCHER r1 ON r1.r_id = c.r1_id
           JOIN RESEARCHER r2 ON r2.r_id = c.r2_id
           WHERE (%s IS NULL OR c.r1_id = %s OR c.r2_id = %s)
           ORDER BY c.already_coauthored, c.shared_topic_count DESC,
                    c.r1_name, c.r2_name""",
        (researcher_id, researcher_id, researcher_id),
    ).to_dict("records")


@st.cache_data(ttl=30, show_spinner=False)
def _load_approved_papers():
    return db.query(
        """SELECT p.p_id, p.p_title, p.pub_year
           FROM PAPER p
           LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
           WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
           ORDER BY p.p_title, p.pub_year DESC, p.p_id"""
    )


@st.cache_data(ttl=30, show_spinner=False)
def _similarity_sql(selected_paper_id=None):
    return db.query(
        """SELECT s.p1_id, s.p1_title, p1.pub_year AS p1_year,
                  s.p2_id, s.p2_title, p2.pub_year AS p2_year,
                  s.topic_jaccard, s.keyword_jaccard, s.similarity_score,
                  s.overlap_band, s.shared_topics, s.shared_keywords
           FROM v_paper_similarity s
           JOIN PAPER p1 ON p1.p_id = s.p1_id
           JOIN PAPER p2 ON p2.p_id = s.p2_id
           LEFT JOIN PAPER_WORKFLOW w1 ON w1.p_id = p1.p_id
           LEFT JOIN PAPER_WORKFLOW w2 ON w2.p_id = p2.p_id
           WHERE COALESCE(w1.status, 'APPROVED') = 'APPROVED'
             AND COALESCE(w2.status, 'APPROVED') = 'APPROVED'
             AND (%s IS NULL OR s.p1_id = %s OR s.p2_id = %s)
           ORDER BY s.similarity_score DESC, s.p1_id, s.p2_id""",
        (selected_paper_id, selected_paper_id, selected_paper_id),
    ).to_dict("records")


@st.cache_data(ttl=30, show_spinner=False)
def _paper_comparison(paper_ids):
    paper_ids = list(dict.fromkeys(int(paper_id) for paper_id in paper_ids))
    placeholders = ", ".join(["%s"] * len(paper_ids))
    params = tuple(paper_ids)
    papers = db.query(
        f"""SELECT p.p_id, p.p_title, p.pub_year
            FROM PAPER p
            LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
            WHERE p.p_id IN ({placeholders})
              AND COALESCE(w.status, 'APPROVED') = 'APPROVED'""",
        params,
    ).to_dict("records")
    authors = db.query(
        f"""SELECT a.p_id, a.author_order, r.r_name
            FROM AUTHORS a
            JOIN RESEARCHER r ON r.r_id = a.r_id
            JOIN PAPER p ON p.p_id = a.p_id
            LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
            WHERE a.p_id IN ({placeholders})
              AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
            ORDER BY a.p_id, a.author_order""",
        params,
    ).to_dict("records")
    topics = db.query(
        f"""SELECT ht.p_id, t.t_name
            FROM HAS_TOPIC ht
            JOIN TOPIC t ON t.t_id = ht.t_id
            JOIN PAPER p ON p.p_id = ht.p_id
            LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
            WHERE ht.p_id IN ({placeholders})
              AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
            ORDER BY ht.p_id, t.t_name""",
        params,
    ).to_dict("records")
    keywords = db.query(
        f"""SELECT hk.p_id, k.keyword
            FROM HAS_KEYWORD hk
            JOIN KEYWORD k ON k.key_id = hk.key_id
            JOIN PAPER p ON p.p_id = hk.p_id
            LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
            WHERE hk.p_id IN ({placeholders})
              AND COALESCE(w.status, 'APPROVED') = 'APPROVED'
            ORDER BY hk.p_id, k.keyword""",
        params,
    ).to_dict("records")

    details = {
        int(paper["p_id"]): {
            **paper,
            "authors": [
                row["r_name"] for row in authors
                if int(row["p_id"]) == int(paper["p_id"])
            ],
            "topics": [
                row["t_name"] for row in topics
                if int(row["p_id"]) == int(paper["p_id"])
            ],
            "keywords": [
                row["keyword"] for row in keywords
                if int(row["p_id"]) == int(paper["p_id"])
            ],
        }
        for paper in papers
    }
    return details


def _show_paper_card(row, rank):
    score = row["similarity_score"]
    st.text(f"{rank}. {row['other_title']}")
    year = row.get("other_year")
    st.caption(f"Published {year if year is not None and not pd.isna(year) else 'year unknown'}")
    score_col, band_col = st.columns([1, 2])
    score_col.metric("Similarity", f"{score:.0%}")
    band_col.caption(row["overlap_band"])
    st.progress(min(1.0, max(0.0, score)))
    st.caption(
        f"Topics {row['topic_jaccard']:.0%} · Keywords {row['keyword_jaccard']:.0%}"
    )


def _render_comparison(paper_a, paper_b, similarity):
    if paper_a is None or paper_b is None:
        st.info("Comparison details are unavailable for this publication pair.")
        return
    col_a, col_b = st.columns(2)
    for column, paper, label in (
        (col_a, paper_a, "Paper A"),
        (col_b, paper_b, "Paper B"),
    ):
        with column:
            st.markdown(f"**{label}**")
            st.text(paper["p_title"])
            st.caption(f"Published {paper['pub_year']}")
            st.markdown("Authors")
            st.text(", ".join(paper["authors"]) if paper["authors"] else "None listed")
            st.markdown("Research topics")
            st.text(", ".join(paper["topics"]) if paper["topics"] else "None listed")
            st.markdown("Keywords")
            st.text(", ".join(paper["keywords"]) if paper["keywords"] else "None listed")

    topic_comparison = compare_sets(paper_a["topics"], paper_b["topics"])
    keyword_comparison = compare_sets(paper_a["keywords"], paper_b["keywords"])
    st.markdown("**What overlaps?**")
    left, right = st.columns(2)
    with left:
        st.markdown("Research topics")
        st.text(f"Shared: {', '.join(topic_comparison['shared']) or 'None'}")
        st.text(f"Only Paper A: {', '.join(topic_comparison['only_a']) or 'None'}")
        st.text(f"Only Paper B: {', '.join(topic_comparison['only_b']) or 'None'}")
    with right:
        st.markdown("Keywords")
        st.text(f"Shared: {', '.join(keyword_comparison['shared']) or 'None'}")
        st.text(f"Only Paper A: {', '.join(keyword_comparison['only_a']) or 'None'}")
        st.text(f"Only Paper B: {', '.join(keyword_comparison['only_b']) or 'None'}")

    topic_score = similarity["topic_jaccard"]
    keyword_score = similarity["keyword_jaccard"]
    final_score = similarity["similarity_score"]
    st.markdown("**Why are these papers similar?**")
    st.write(f"Topic Jaccard: {topic_score:.4f}")
    st.write(f"Keyword Jaccard: {keyword_score:.4f}")
    st.code(
        f"0.4 × {topic_score:.4f} + 0.6 × {keyword_score:.4f} "
        f"= {final_score:.4f} ({final_score:.0%})"
    )
    st.caption("Similarity indicates potential topical overlap, not plagiarism or duplicate content.")


st.title("Research Network Insights")
st.caption("Discover shared research interests and related publications.")
tab_collab, tab_sim = st.tabs(["Collaborator Discovery", "Publication Similarity"])

with tab_collab:
    try:
        researchers = _load_researchers()
        researcher_by_id = {
            int(row["r_id"]): row.to_dict()
            for _, row in researchers.iterrows()
        }
        selection_ids = [None, *researcher_by_id]
        with st.container(border=True):
            st.subheader("Find Collaborators For")
            selected_researcher_id = st.selectbox(
                "Researcher",
                options=selection_ids,
                format_func=lambda researcher_id: (
                    "All Researchers" if researcher_id is None else
                    f"{researcher_by_id[researcher_id]['r_name']} — "
                    f"{researcher_by_id[researcher_id].get('institution') or 'Institution not listed'}"
                ),
                key="insights_researcher",
            )
            collaboration_choice = st.radio(
                "Collaboration type",
                options=list(COLLABORATION_FILTERS),
                horizontal=True,
                key="insights_collaboration_filter",
            )

        with st.spinner("Finding researchers with shared research topics..."):
            scoped_rows = _load_collaborations(selected_researcher_id)
        status_filter = COLLABORATION_FILTERS[collaboration_choice]
        collaboration_rows = filter_collaborations(
            scoped_rows, selected_researcher_id, status_filter
        )
        metrics = collaboration_metrics(scoped_rows)
        scope_label = (
            researcher_by_id[selected_researcher_id]["r_name"]
            if selected_researcher_id is not None else "All researchers"
        )
        st.caption(
            f"Metrics for {scope_label}; results below reflect the selected collaboration filter."
        )
        metric_a, metric_b, metric_c = st.columns(3)
        metric_a.metric("Total Pairs", metrics["total"])
        metric_b.metric("New Opportunities", metrics["new"])
        metric_c.metric("Already Co-authored", metrics["existing"])

        if not collaboration_rows:
            st.info("No qualifying collaboration pairs match this selection.")
        else:
            figure, node_count, edge_count, graph_truncated = collaboration_figure(
                collaboration_rows,
                selected_researcher_id,
                _GRAPH_RESEARCHER_LIMIT,
                _GRAPH_EDGE_LIMIT,
            )
            st.markdown("### Collaboration Network")
            st.caption(
                "Connections indicate shared topics across approved publications, "
                "not a guarantee of collaboration suitability."
            )
            st.plotly_chart(
                figure,
                width="stretch",
                config={"scrollZoom": True, "displaylogo": False},
            )
            st.caption(
                "Solid blue: already co-authored · Dashed gray: potential collaboration opportunity"
            )
            if graph_truncated:
                st.warning(
                    f"The network is limited to {node_count} researchers and "
                    f"{edge_count} relationships for readability. All filtered results "
                    "remain available below."
                )

            st.markdown("### Potential Collaborators")
            for rank, row in enumerate(collaboration_rows[:_RECOMMENDATION_LIMIT], 1):
                if selected_researcher_id is None:
                    partner_name = f"{row['r1_name']} & {row['r2_name']}"
                    institution = (
                        f"{row.get('r1_institution') or 'Institution not listed'} · "
                        f"{row.get('r2_institution') or 'Institution not listed'}"
                    )
                elif int(row["r1_id"]) == int(selected_researcher_id):
                    partner_name = row["r2_name"]
                    institution = row.get("r2_institution") or "Institution not listed"
                else:
                    partner_name = row["r1_name"]
                    institution = row.get("r1_institution") or "Institution not listed"
                with st.container(border=True):
                    st.markdown(f"**{escape(str(rank))}. {escape(str(partner_name))}**")
                    st.text(f"Institution: {institution}")
                    st.text(f"Shared topics ({row['shared_topic_count']}): {row['shared_topics']}")
                    status = (
                        "Already co-authored"
                        if int(row["already_coauthored"]) else "New collaboration opportunity"
                    )
                    st.caption(f"Status: {status}")
            if len(collaboration_rows) > _RECOMMENDATION_LIMIT:
                with st.expander(f"Show remaining {len(collaboration_rows) - _RECOMMENDATION_LIMIT} recommendations"):
                    for row in collaboration_rows[_RECOMMENDATION_LIMIT:]:
                        if selected_researcher_id is None:
                            name = f"{row['r1_name']} & {row['r2_name']}"
                        elif int(row["r1_id"]) == int(selected_researcher_id):
                            name = row["r2_name"]
                        else:
                            name = row["r1_name"]
                        st.text(
                            f"{name} · {row['shared_topic_count']} shared topics · "
                            f"{row['shared_topics']} · "
                            f"{'Already co-authored' if int(row['already_coauthored']) else 'New opportunity'}"
                        )

            with st.expander("Advanced Collaboration Results"):
                advanced = pd.DataFrame(collaboration_rows).rename(columns={
                    "r1_name": "Researcher 1",
                    "r2_name": "Researcher 2",
                    "shared_topic_count": "Shared Topic Count",
                    "shared_topics": "Shared Topics",
                    "already_coauthored": "Already Co-authored?",
                })
                advanced["Already Co-authored?"] = advanced["Already Co-authored?"].map(
                    {1: "Yes", 0: "No"}
                )
                st.dataframe(
                    advanced[[
                        "Researcher 1", "Researcher 2", "Shared Topic Count",
                        "Shared Topics", "Already Co-authored?",
                    ]],
                    width="stretch",
                    hide_index=True,
                )
    except Exception as exc:
        st.error(db.friendly_error(exc))

with tab_sim:
    try:
        approved_papers = _load_approved_papers()
        if approved_papers.empty:
            st.info("No approved publications are available for similarity analysis.")
            selected_paper_id = None
            paper_by_id = {}
        else:
            paper_by_id = {
                int(row["p_id"]): row.to_dict()
                for _, row in approved_papers.iterrows()
            }
            st.subheader("Find Similar Papers")
            selected_paper_id = st.selectbox(
                "Select a publication",
                options=[None, *paper_by_id],
                format_func=lambda paper_id: (
                    "Choose a publication" if paper_id is None else
                    f"{paper_by_id[paper_id]['p_title']} "
                    f"({paper_by_id[paper_id]['pub_year']})"
                ),
                key="insights_similarity_paper",
            )

        if selected_paper_id is None:
            scoped_similarity = []
            st.info("Select an approved publication to discover similar papers.")
        else:
            with st.spinner("Comparing approved publications..."):
                scoped_similarity = _similarity_sql(selected_paper_id)

        min_score = st.slider(
            "Minimum similarity",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
            format="%d%%",
            key="insights_min_similarity",
        )
        selected_bands = st.multiselect(
            "Overlap categories",
            options=list(OVERLAP_BANDS),
            default=list(OVERLAP_BANDS),
            key="insights_overlap_bands",
        )
        filtered_similarity = filter_similar_papers(
            scoped_similarity,
            selected_paper_id,
            min_score / 100,
            selected_bands,
        )
        sim_metrics = similarity_metrics(filtered_similarity)
        st.caption("Summary reflects the selected paper and the active filters.")
        sim_a, sim_b, sim_c, sim_d = st.columns(4)
        sim_a.metric("Matching Pairs", sim_metrics["total"])
        sim_b.metric("High", sim_metrics["high"])
        sim_c.metric("Moderate", sim_metrics["moderate"])
        sim_d.metric("Low", sim_metrics["low"])

        if selected_paper_id is not None:
            if not filtered_similarity:
                st.info("No similar papers match the current filters.")
            else:
                st.markdown("### Most Similar Publications")
                ranked_papers = filtered_similarity[:12]
                for start in range(0, len(ranked_papers), 2):
                    cards = st.columns(2)
                    for offset, (column, row) in enumerate(
                        zip(cards, ranked_papers[start:start + 2])
                    ):
                        with column:
                            with st.container(border=True):
                                _show_paper_card(row, start + offset + 1)

                candidate_options = [row["other_p_id"] for row in filtered_similarity]
                similarity_by_other_id = {
                    row["other_p_id"]: row for row in filtered_similarity
                }
                comparison_id = st.selectbox(
                    "Compare selected paper with",
                    options=candidate_options,
                    format_func=lambda paper_id: (
                        f"{similarity_by_other_id[paper_id]['other_title']} "
                        f"({similarity_by_other_id[paper_id]['other_year']})"
                    ),
                    key=f"insights_compare_{selected_paper_id}",
                )
                comparison = similarity_by_other_id[comparison_id]
                comparison_details = _paper_comparison(
                    (selected_paper_id, comparison_id)
                )
                paper_a = comparison_details.get(int(selected_paper_id))
                paper_b = comparison_details.get(int(comparison_id))
                st.markdown("### Paper Comparison")
                _render_comparison(paper_a, paper_b, comparison)

        with st.expander("Advanced Similarity Analysis"):
            load_all_pairs = st.checkbox(
                "Load all approved paper pairs",
                key="insights_load_all_pairs",
            )
            if load_all_pairs:
                all_similarity = filter_similar_papers(
                    _similarity_sql(),
                    minimum_score=min_score / 100,
                    bands=selected_bands,
                )
                if all_similarity:
                    advanced = pd.DataFrame(all_similarity).rename(columns={
                        "p1_id": "Paper 1 ID",
                        "p1_title": "Paper 1",
                        "p2_id": "Paper 2 ID",
                        "p2_title": "Paper 2",
                        "topic_jaccard": "Topic Jaccard",
                        "keyword_jaccard": "Keyword Jaccard",
                        "similarity_score": "Final Weighted Score",
                        "overlap_band": "Overlap Band",
                        "shared_topics": "Shared Topics",
                        "shared_keywords": "Shared Keywords",
                    })
                    advanced["Final Weighted Score"] = advanced["Final Weighted Score"].map(
                        lambda value: f"{value:.4f}"
                    )
                    advanced["Topic Jaccard"] = advanced["Topic Jaccard"].map(
                        lambda value: f"{value:.4f}"
                    )
                    advanced["Keyword Jaccard"] = advanced["Keyword Jaccard"].map(
                        lambda value: f"{value:.4f}"
                    )
                    st.dataframe(
                        advanced[[
                            "Paper 1 ID", "Paper 1", "Paper 2 ID", "Paper 2",
                            "Topic Jaccard", "Keyword Jaccard", "Final Weighted Score",
                            "Overlap Band", "Shared Topics", "Shared Keywords",
                        ]],
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info("No paper pairs match the current advanced filters.")

    except Exception as exc:
        st.error(db.friendly_error(exc))
