import streamlit as st
import sys
from pathlib import Path

# Add app directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db

st.set_page_config(page_title="Projects & Datasets", layout="wide")
st.title("Research Projects & Data Assets")

tab_project_detail, tab_shared_proj = st.tabs(["📁 Project Details & Assets", "🔗 Cross-Project Resource Sharing"])

# TAB 1: Project Team & Datasets
with tab_project_detail:
    st.subheader("Project Teams & Datasets")
    try:
        df_projects = db.query("SELECT project_id, name, description FROM PROJECT ORDER BY project_id")
        if df_projects.empty:
            st.info("No projects found in the database.")
        else:
            proj_dict = {
                f"Project #{row['project_id']}: {row['name']}": int(row['project_id'])
                for _, row in df_projects.iterrows()
            }
            selected_label = st.selectbox("Select Project:", list(proj_dict.keys()))
            selected_proj_id = proj_dict[selected_label]

            # Project Description
            proj_info = df_projects[df_projects["project_id"] == selected_proj_id].iloc[0]
            st.markdown(f"**Description**: {proj_info['description']}")

            st.markdown("---")
            col_team, col_data = st.columns(2)

            with col_team:
                st.markdown("#### 👥 Research Team Members")
                df_team = db.query(
                    "SELECT r_name, institution FROM v_project_team WHERE project_id = %s",
                    (selected_proj_id,)
                )
                if not df_team.empty:
                    st.dataframe(
                        df_team.rename(columns={"r_name": "Researcher", "institution": "Institution"}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No researchers assigned to this project.")

            with col_data:
                st.markdown("#### 💾 Associated Datasets")
                df_datasets = db.query(
                    "SELECT dataset_name, source FROM v_project_datasets WHERE project_id = %s",
                    (selected_proj_id,)
                )
                if not df_datasets.empty:
                    st.dataframe(
                        df_datasets.rename(columns={"dataset_name": "Dataset", "source": "Source / URL"}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No datasets linked to this project.")

    except Exception as e:
        st.error(db.friendly_error(e))

# TAB 2: Shared Resources
with tab_shared_proj:
    st.subheader("Shared Personnel & Data Assets Across Projects")
    st.markdown("""
    Displays project pairs that collaborate through shared investigators or reuse common scientific datasets.
    """)
    try:
        df_shared = db.query("SELECT * FROM v_projects_shared")
        if df_shared.empty:
            st.info("No resource sharing detected between project pairs.")
        else:
            display_shared = df_shared.copy()
            display_shared["Project Pair"] = display_shared["p1_name"] + "  ↔  " + display_shared["p2_name"]
            display_table = display_shared[[
                "Project Pair", "shared_researcher_count", "shared_dataset_count"
            ]].rename(columns={
                "shared_researcher_count": "Shared Researchers",
                "shared_dataset_count": "Shared Datasets"
            })
            st.dataframe(display_table, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(db.friendly_error(e))
