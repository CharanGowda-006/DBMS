import streamlit as st
import sys
from pathlib import Path

# Add app directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db

st.set_page_config(page_title="Collaboration & Similarity Insights", layout="wide")
st.title("Research Network Insights")

tab_collab, tab_sim = st.tabs(["🤝 Potential Collaborators", "📑 Publication Similarity"])

# TAB 1: Collaboration Discovery
with tab_collab:
    st.subheader("Potential Research Collaborators")
    st.markdown("""
    Discovers researcher pairs who share at least 2 distinct research topics across their published work.
    Highlights whether they have already co-authored papers together or represent new cross-institutional collaboration opportunities.
    """)
    try:
        df_collab = db.query("SELECT * FROM v_collaborators")
        if df_collab.empty:
            st.info("No researcher pairs with at least 2 shared topics found.")
        else:
            col_kpi1, col_kpi2 = st.columns(2)
            with col_kpi1:
                st.metric("Total Identified Pairs", len(df_collab))
            with col_kpi2:
                new_pairs = len(df_collab[df_collab["already_coauthored"] == 0])
                st.metric("New Potential Collaborations (Never Co-authored)", new_pairs)
            
            # Format display dataframe
            display_collab = df_collab.copy()
            display_collab["Pair"] = display_collab["r1_name"] + " & " + display_collab["r2_name"]
            display_collab["Co-authored Before?"] = display_collab["already_coauthored"].apply(
                lambda x: "✅ Yes" if x == 1 else "🆕 No (Opportunity)"
            )
            display_collab = display_collab[[
                "Pair", "shared_topic_count", "shared_topics", "Co-authored Before?"
            ]].rename(columns={
                "shared_topic_count": "Shared Topics Count",
                "shared_topics": "Shared Topic List"
            })
            
            st.dataframe(display_collab, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(db.friendly_error(e))

# TAB 2: Publication Similarity
with tab_sim:
    st.subheader("Paper Similarity & Overlap Analysis")
    st.caption("Based on topic/keyword overlap. A signal of potential similarity, not a plagiarism verdict.")
    
    try:
        df_sim = db.query("SELECT * FROM v_paper_similarity")
        if df_sim.empty:
            st.info("No publication similarity data available.")
        else:
            min_score = st.slider(
                "Filter by Minimum Similarity Score",
                min_value=0.0,
                max_value=1.0,
                value=0.3,
                step=0.05,
                help="Similarity score is computed as 0.4 * Topic Jaccard + 0.6 * Keyword Jaccard."
            )
            
            filtered_df = df_sim[df_sim["similarity_score"] >= min_score]
            st.write(f"Showing **{len(filtered_df)}** paper pair(s) with similarity score >= {min_score:.2f}")

            # Display table
            summary_table = filtered_df[[
                "p1_id", "p1_title", "p2_id", "p2_title",
                "similarity_score", "overlap_band", "topic_jaccard", "keyword_jaccard"
            ]].rename(columns={
                "p1_id": "P1 ID",
                "p1_title": "Paper 1 Title",
                "p2_id": "P2 ID",
                "p2_title": "Paper 2 Title",
                "similarity_score": "Score",
                "overlap_band": "Overlap Band",
                "topic_jaccard": "Topic Jaccard",
                "keyword_jaccard": "Keyword Jaccard"
            })
            st.dataframe(summary_table, use_container_width=True, hide_index=True)

            # Expander for inspecting shared topics & keywords
            with st.expander("🔍 View Shared Topics & Keywords for Filtered Pairs"):
                for _, row in filtered_df.iterrows():
                    st.markdown(f"#### #{row['p1_id']} vs #{row['p2_id']} (Score: {row['similarity_score']:.4f} - *{row['overlap_band']}*)")
                    st.write(f"**P1**: {row['p1_title']}")
                    st.write(f"**P2**: {row['p2_title']}")
                    col_t, col_k = st.columns(2)
                    with col_t:
                        st.markdown(f"**Shared Topics ({row['topic_jaccard']:.2f} Jaccard):**")
                        st.info(row['shared_topics'] if row['shared_topics'] else "None")
                    with col_k:
                        st.markdown(f"**Shared Keywords ({row['keyword_jaccard']:.2f} Jaccard):**")
                        st.info(row['shared_keywords'] if row['shared_keywords'] else "None")
                    st.markdown("---")
    except Exception as e:
        st.error(db.friendly_error(e))
