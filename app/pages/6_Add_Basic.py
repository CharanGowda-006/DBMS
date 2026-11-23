import re
import streamlit as st
import sys
from pathlib import Path

# Add app directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db

st.set_page_config(page_title="Register Core Entities", layout="wide")
st.title("Data Management: Core Entities")

st.markdown("""
Register foundational entities into the research collaboration network.
All submissions undergo strict data validation and database constraint enforcement.
""")

tab_res, tab_conf, tab_top, tab_key, tab_data, tab_proj = st.tabs([
    "👤 Researcher", "🏛️ Conference", "🏷️ Topic", "🔑 Keyword", "💾 Dataset", "💡 Project"
])

# 1. RESEARCHER FORM
with tab_res:
    st.subheader("Add New Researcher")
    st.caption("Researcher IDs are assigned by MySQL. They are stable identifiers and may have gaps; they are not row numbers.")
    with st.form("form_researcher", clear_on_submit=True):
        r_name = st.text_input("Researcher Name *").strip()
        r_email = st.text_input("Email Address *").strip()
        r_inst = st.text_input("Institution").strip()
        submit_res = st.form_submit_button("Add Researcher")
        
        if submit_res:
            email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if not r_name:
                st.error("Researcher name is required.")
            elif not r_email:
                st.error("Email address is required.")
            elif not re.match(email_pattern, r_email):
                st.error("Please enter a valid email address (e.g. name@domain.com).")
            else:
                try:
                    researcher_id = db.execute(
                        "INSERT INTO RESEARCHER (r_name, email, institution) VALUES (%s, %s, %s)",
                        (r_name, r_email, r_inst or None)
                    )
                    st.success(f"Researcher '{r_name}' added successfully with ID {researcher_id}.")
                except Exception as e:
                    st.error(db.friendly_error(e))

    st.markdown("#### Existing Researchers")
    st.dataframe(
        db.query("SELECT r_id AS ID, r_name AS Name, email AS Email, institution AS Institution FROM RESEARCHER ORDER BY r_id DESC"),
        use_container_width=True, hide_index=True
    )

# 2. CONFERENCE FORM
with tab_conf:
    st.subheader("Add New Conference")
    with st.form("form_conference", clear_on_submit=True):
        c_name = st.text_input("Conference Name *").strip()
        c_year_input = st.text_input("Conference Year (e.g. 2025) *").strip()
        c_loc = st.text_input("Location (City, Country)").strip()
        submit_conf = st.form_submit_button("Add Conference")

        if submit_conf:
            if not c_name:
                st.error("Conference name is required.")
            elif not c_year_input.isdigit() or int(c_year_input) <= 0:
                st.error("Conference year must be a positive integer.")
            else:
                c_year = int(c_year_input)
                try:
                    db.execute(
                        "INSERT INTO CONFERENCE (c_name, c_year, c_location) VALUES (%s, %s, %s)",
                        (c_name, c_year, c_loc or None)
                    )
                    st.success(f"Conference '{c_name}' ({c_year}) added successfully!")
                except Exception as e:
                    st.error(db.friendly_error(e))

    st.markdown("#### Existing Conferences")
    st.dataframe(
        db.query("SELECT c_id AS ID, c_name AS Name, c_year AS Year, c_location AS Location FROM CONFERENCE ORDER BY c_id DESC"),
        use_container_width=True, hide_index=True
    )

# 3. TOPIC FORM
with tab_top:
    st.subheader("Add New Topic")
    with st.form("form_topic", clear_on_submit=True):
        t_name = st.text_input("Topic Name *").strip()
        submit_top = st.form_submit_button("Add Topic")

        if submit_top:
            if not t_name:
                st.error("Topic name is required.")
            else:
                try:
                    db.execute("INSERT INTO TOPIC (t_name) VALUES (%s)", (t_name,))
                    st.success(f"Topic '{t_name}' registered successfully!")
                except Exception as e:
                    st.error(db.friendly_error(e))

    st.markdown("#### Existing Topics")
    st.dataframe(
        db.query("SELECT t_id AS ID, t_name AS Topic FROM TOPIC ORDER BY t_id DESC"),
        use_container_width=True, hide_index=True
    )

# 4. KEYWORD FORM
with tab_key:
    st.subheader("Add New Keyword")
    with st.form("form_keyword", clear_on_submit=True):
        k_word = st.text_input("Keyword *").strip()
        submit_key = st.form_submit_button("Add Keyword")

        if submit_key:
            if not k_word:
                st.error("Keyword text is required.")
            else:
                try:
                    db.execute("INSERT INTO KEYWORD (keyword) VALUES (%s)", (k_word,))
                    st.success(f"Keyword '{k_word}' registered successfully!")
                except Exception as e:
                    st.error(db.friendly_error(e))

    st.markdown("#### Existing Keywords")
    st.dataframe(
        db.query("SELECT key_id AS ID, keyword AS Keyword FROM KEYWORD ORDER BY key_id DESC"),
        use_container_width=True, hide_index=True
    )

# 5. DATASET FORM
with tab_data:
    st.subheader("Add New Dataset")
    with st.form("form_dataset", clear_on_submit=True):
        d_name = st.text_input("Dataset Name *").strip()
        d_source = st.text_input("Source URL or Repository *").strip()
        submit_data = st.form_submit_button("Add Dataset")

        if submit_data:
            if not d_name or not d_source:
                st.error("Both dataset name and source URL/repository are required.")
            else:
                try:
                    db.execute("INSERT INTO DATASET (name, source) VALUES (%s, %s)", (d_name, d_source))
                    st.success(f"Dataset '{d_name}' registered successfully!")
                except Exception as e:
                    st.error(db.friendly_error(e))

    st.markdown("#### Existing Datasets")
    st.dataframe(
        db.query("SELECT dataset_id AS ID, name AS Name, source AS Source FROM DATASET ORDER BY dataset_id DESC"),
        use_container_width=True, hide_index=True
    )

# 6. PROJECT FORM
with tab_proj:
    st.subheader("Add New Project")
    with st.form("form_project", clear_on_submit=True):
        p_name = st.text_input("Project Name *").strip()
        p_desc = st.text_area("Project Description").strip()
        submit_proj = st.form_submit_button("Add Project")

        if submit_proj:
            if not p_name:
                st.error("Project name is required.")
            else:
                try:
                    db.execute("INSERT INTO PROJECT (name, description) VALUES (%s, %s)", (p_name, p_desc or None))
                    st.success(f"Project '{p_name}' registered successfully!")
                except Exception as e:
                    st.error(db.friendly_error(e))

    st.markdown("#### Existing Projects")
    st.dataframe(
        db.query("SELECT project_id AS ID, name AS Name, description AS Description FROM PROJECT ORDER BY project_id DESC"),
        use_container_width=True, hide_index=True
    )
