import streamlit as st
import sys
from pathlib import Path

# Add app directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db

st.set_page_config(page_title="Overview & Analytics", layout="wide")
st.title("Research Overview & Analytics")

try:
    # 1. Fetch data from views
    df_conf = db.query("SELECT * FROM v_papers_per_conference")
    df_year = db.query("SELECT * FROM v_papers_per_year")
    df_topic = db.query("SELECT * FROM v_papers_per_topic")
    df_team = db.query("SELECT * FROM v_project_team")
    df_datasets = db.query("SELECT * FROM v_project_datasets")

    # Calculate KPI numbers from views
    total_papers = int(df_year["paper_count"].sum()) if not df_year.empty else 0
    total_researchers = int(df_team["r_id"].nunique()) if not df_team.empty else 0
    total_conferences = int(df_conf[df_conf["c_name"] != "No conference"]["c_id"].nunique()) if not df_conf.empty else 0
    total_topics = int(df_topic["t_id"].nunique()) if not df_topic.empty else 0
    total_projects = int(df_team["project_id"].nunique()) if not df_team.empty else 0
    total_datasets = int(df_datasets["dataset_id"].nunique()) if not df_datasets.empty else 0

    # 2. Render KPI Cards
    st.subheader("Key Performance Indicators")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Papers", total_papers)
    col2.metric("Researchers", total_researchers)
    col3.metric("Conferences", total_conferences)
    col4.metric("Topics", total_topics)
    col5.metric("Projects", total_projects)
    col6.metric("Datasets", total_datasets)

    st.markdown("---")

    # 3. Bar Charts
    st.subheader("Publication Distribution & Research Themes")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**Papers Published per Year**")
        if not df_year.empty:
            st.bar_chart(df_year, x="pub_year", y="paper_count", color="#2b5c8f")
        else:
            st.info("No publication year data available.")

    with chart_col2:
        st.markdown("**Papers per Conference**")
        if not df_conf.empty:
            st.bar_chart(df_conf, x="c_name", y="paper_count", color="#008080")
        else:
            st.info("No conference publication data available.")

    st.markdown("**Papers per Research Topic**")
    if not df_topic.empty:
        st.bar_chart(df_topic, x="t_name", y="paper_count", color="#e07a5f")
    else:
        st.info("No topic distribution data available.")

except Exception as e:
    st.error(db.friendly_error(e))
