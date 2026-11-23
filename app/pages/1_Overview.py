import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db

st.set_page_config(page_title="Overview & Analytics", page_icon="📊", layout="wide")
st.title("📊 Research Overview & Analytics")

try:
    df_year  = db.query("SELECT * FROM v_papers_per_year  ORDER BY pub_year")
    df_conf  = db.query("SELECT * FROM v_papers_per_conference ORDER BY paper_count DESC")
    df_topic = db.query("SELECT * FROM v_papers_per_topic  ORDER BY paper_count DESC")
    df_team  = db.query("SELECT * FROM v_project_team")
    df_ds    = db.query("SELECT * FROM v_project_datasets")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.subheader("Key Metrics")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("📄 Papers",      int(df_year["paper_count"].sum()))
    k2.metric("👤 Researchers", int(df_team["r_id"].nunique()))
    k3.metric("🏛️ Conferences", int(df_conf[df_conf["c_name"] != "No conference"]["c_id"].nunique()))
    k4.metric("🏷️ Topics",      int(df_topic["t_id"].nunique()))
    k5.metric("💡 Projects",    int(df_team["project_id"].nunique()))
    k6.metric("💾 Datasets",    int(df_ds["dataset_id"].nunique()))

    st.markdown("---")

    # ── Charts row 1 ──────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 📅 Papers Published per Year")
        if not df_year.empty:
            df_year["pub_year"] = df_year["pub_year"].astype(str)
            st.bar_chart(df_year.set_index("pub_year")["paper_count"],
                         color="#2b5c8f", use_container_width=True)
        else:
            st.info("No data.")

    with c2:
        st.markdown("#### 🏛️ Papers per Conference")
        if not df_conf.empty:
            df_conf_display = df_conf.copy()
            df_conf_display["c_name"] = df_conf_display["c_name"].apply(
                lambda x: (x[:35] + "…") if len(x) > 35 else x
            )
            st.bar_chart(df_conf_display.set_index("c_name")["paper_count"],
                         color="#008080", use_container_width=True)
        else:
            st.info("No data.")

    # ── Charts row 2 ──────────────────────────────────────────────────────────
    st.markdown("#### 🏷️ Papers per Research Topic")
    if not df_topic.empty:
        st.bar_chart(df_topic.set_index("t_name")["paper_count"],
                     color="#e07a5f", use_container_width=True)
    else:
        st.info("No topic data available.")

    # ── Detailed tables ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Detailed Tables")

    t1, t2, t3 = st.tabs(["Papers by Year & Conference", "Research Topics", "Projects & Datasets"])

    with t1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**By Year**")
            st.dataframe(df_year.rename(columns={"pub_year": "Year", "paper_count": "Papers"}),
                         hide_index=True, use_container_width=True)
        with col_b:
            st.markdown("**By Conference**")
            conf_table = df_conf[["c_name", "paper_count"]].rename(
                columns={"c_name": "Conference", "paper_count": "Papers"})
            st.dataframe(conf_table, hide_index=True, use_container_width=True)

    with t2:
        topic_table = df_topic[["t_name", "paper_count"]].rename(
            columns={"t_name": "Research Topic", "paper_count": "Papers"})
        st.dataframe(topic_table, hide_index=True, use_container_width=True)

    with t3:
        col_c, col_d = st.columns(2)
        with col_c:
            st.markdown("**Project Teams**")
            st.dataframe(df_team[["project_name", "r_name", "institution"]].rename(
                columns={"project_name": "Project", "r_name": "Researcher", "institution": "Institution"}
            ), hide_index=True, use_container_width=True)
        with col_d:
            st.markdown("**Project Datasets**")
            st.dataframe(df_ds[["project_name", "dataset_name", "source"]].rename(
                columns={"project_name": "Project", "dataset_name": "Dataset", "source": "Source / URL"}
            ), hide_index=True, use_container_width=True)

except Exception as e:
    st.error(db.friendly_error(e))
