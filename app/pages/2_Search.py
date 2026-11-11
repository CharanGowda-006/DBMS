import streamlit as st
import sys
from pathlib import Path

# Add app directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db

st.set_page_config(page_title="Unified Academic Search", layout="wide")
st.title("Unified Academic Search")

st.markdown("""
Search across publications, researchers, conferences, projects, and datasets.
Matches terms in publication titles, research topics, and keywords.
""")

search_term = st.text_input("Enter search keyword, topic, or title", value="Computer Vision", placeholder="e.g. Deep Learning, CNN, Transformers")

if search_term.strip():
    try:
        df_results = db.call_proc("sp_search", (search_term.strip(),))
        
        if df_results.empty:
            st.info(f"No results found matching '{search_term}'. Try another term.")
        else:
            st.success(f"Found {len(df_results)} matching records across the network.")
            
            # Group by result_type with headers
            result_types = ["paper", "researcher", "conference", "project", "dataset"]
            type_icons = {
                "paper": "📄 Papers",
                "researcher": "👤 Researchers",
                "conference": "🏛️ Conferences",
                "project": "💡 Funded Projects",
                "dataset": "💾 Datasets"
            }
            
            for r_type in result_types:
                subset = df_results[df_results["result_type"] == r_type]
                if not subset.empty:
                    st.subheader(type_icons.get(r_type, r_type.title()))
                    display_df = subset[["ref_id", "label", "detail"]].rename(
                        columns={"ref_id": "ID", "label": "Title / Name", "detail": "Match Details"}
                    )
                    st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Paper detail section
            paper_subset = df_results[df_results["result_type"] == "paper"]
            if not paper_subset.empty:
                st.markdown("---")
                st.subheader("Explore Paper Details")
                
                paper_options = {
                    f"#{row['ref_id']}: {row['label']}": int(row['ref_id'])
                    for _, row in paper_subset.iterrows()
                }
                
                selected_label = st.selectbox("Select a paper to view complete metadata:", list(paper_options.keys()))
                selected_p_id = paper_options[selected_label]
                
                if selected_p_id:
                    # Parameterized queries for paper details
                    df_paper = db.query("SELECT p_title, abstract, pub_year, c_id FROM PAPER WHERE p_id = %s", (selected_p_id,))
                    df_authors = db.query(
                        "SELECT a.author_order, r.r_name, r.institution, r.email "
                        "FROM AUTHORS a JOIN RESEARCHER r ON a.r_id = r.r_id "
                        "WHERE a.p_id = %s ORDER BY a.author_order",
                        (selected_p_id,)
                    )
                    df_topics = db.query(
                        "SELECT t.t_name FROM HAS_TOPIC ht JOIN TOPIC t ON ht.t_id = t.t_id "
                        "WHERE ht.p_id = %s ORDER BY t.t_name",
                        (selected_p_id,)
                    )
                    df_keywords = db.query(
                        "SELECT k.keyword FROM HAS_KEYWORD hk JOIN KEYWORD k ON hk.key_id = k.key_id "
                        "WHERE hk.p_id = %s ORDER BY k.keyword",
                        (selected_p_id,)
                    )
                    df_conf = db.query(
                        "SELECT c.c_name, c.c_year, c.c_location "
                        "FROM PAPER p JOIN CONFERENCE c ON p.c_id = c.c_id "
                        "WHERE p.p_id = %s",
                        (selected_p_id,)
                    )

                    with st.container():
                        if not df_paper.empty:
                            p_info = df_paper.iloc[0]
                            st.markdown(f"### {p_info['p_title']} ({p_info['pub_year']})")
                            st.markdown(f"**Abstract**: {p_info['abstract']}")
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown("**Authors (in order):**")
                                if not df_authors.empty:
                                    for _, a_row in df_authors.iterrows():
                                        st.write(f"{a_row['author_order']}. **{a_row['r_name']}** ({a_row['institution']}) - `{a_row['email']}`")
                                else:
                                    st.write("None listed")
                                    
                                st.markdown("**Conference:**")
                                if not df_conf.empty:
                                    c_info = df_conf.iloc[0]
                                    st.write(f"🏛️ {c_info['c_name']} ({c_info['c_year']}) - {c_info['c_location']}")
                                else:
                                    st.write("Not presented at a recorded conference.")

                            with col_b:
                                st.markdown("**Topics:**")
                                if not df_topics.empty:
                                    st.write(", ".join([f"`{t}`" for t in df_topics["t_name"]]))
                                else:
                                    st.write("None")

                                st.markdown("**Keywords:**")
                                if not df_keywords.empty:
                                    st.write(", ".join([f"`{k}`" for k in df_keywords["keyword"]]))
                                else:
                                    st.write("None")
    except Exception as e:
        st.error(db.friendly_error(e))
else:
    st.info("Please enter a term to search across research entities.")
