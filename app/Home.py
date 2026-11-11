import streamlit as st
import db

st.set_page_config(page_title="Research Collaboration Network", layout="wide")

st.title("Academic Research Collaboration & Discovery Portal")

st.markdown("""
This system provides an institutional platform to track, analyze, and explore scholarly research connections. 
Built on a relational database architecture, it enables automated collaboration discovery across shared research domains, 
bipartite Jaccard topic and keyword similarity scoring, multi-hop citation graph traversal with cycle prevention, and cross-entity 
unified searching across publications, researchers, conferences, funded projects, and research datasets.
""")

st.subheader("Database Overview: Table Row Counts")

table_names = [
    "RESEARCHER", "CONFERENCE", "PAPER", "TOPIC", "KEYWORD", "PROJECT", "DATASET",
    "AUTHORS", "CITES", "HAS_TOPIC", "HAS_KEYWORD", "WORKS_ON", "USES"
]

queries = " UNION ALL ".join([f"SELECT '{t}' AS table_name, COUNT(*) AS row_count FROM {t}" for t in table_names])

try:
    df_counts = db.query(queries)
    if not df_counts.empty:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(df_counts, use_container_width=True, hide_index=True)
        with col2:
            st.metric("Total Tables", len(df_counts))
            st.metric("Total Records", int(df_counts["row_count"].sum()))
    else:
        st.info("No tables or records found in the database.")
except Exception as e:
    st.error(db.friendly_error(e))
