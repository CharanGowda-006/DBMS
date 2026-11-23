import streamlit as st
import sys
from pathlib import Path

# Add app directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db

st.set_page_config(page_title="Register Linked Entities & Papers", layout="wide")
st.title("Data Management: Linked Entities & Citations")

tab_paper, tab_cite, tab_works, tab_uses = st.tabs([
    "📄 Register Paper (Transactional)",
    "🔗 Add Citation",
    "👥 Assign Researcher to Project",
    "💾 Link Dataset to Project"
])

# ==============================================================================
# TAB 1: REGISTER PAPER IN ONE ATOMIC TRANSACTION
# ==============================================================================
with tab_paper:
    st.subheader("Register Publication with Authors, Topics & Keywords")
    st.markdown("""
    Inserts paper, author hierarchy, research topics, and keywords in **one atomic database transaction**.
    If any constraint fails, the entire transaction rolls back immediately.
    """)

    try:
        df_confs = db.query("SELECT c_id, c_name, c_year FROM CONFERENCE ORDER BY c_name")
        df_res = db.query("SELECT r_id, r_name, institution FROM RESEARCHER ORDER BY r_name")
        df_top = db.query("SELECT t_id, t_name FROM TOPIC ORDER BY t_name")
        df_key = db.query("SELECT key_id, keyword FROM KEYWORD ORDER BY keyword")

        conf_options = {"-- No Conference / Pre-print --": None}
        for _, r in df_confs.iterrows():
            conf_options[f"{r['c_name']} ({r['c_year']})"] = int(r["c_id"])

        res_options = {f"{r['r_name']} ({r['institution']})": int(r["r_id"]) for _, r in df_res.iterrows()}
        top_options = {r["t_name"]: int(r["t_id"]) for _, r in df_top.iterrows()}
        key_options = {r["keyword"]: int(r["key_id"]) for _, r in df_key.iterrows()}

        with st.form("form_add_paper"):
            p_title = st.text_input("Paper Title *").strip()
            p_abstract = st.text_area("Abstract").strip()
            p_year_input = st.text_input("Publication Year (e.g. 2025) *").strip()
            selected_conf_name = st.selectbox("Conference Presented (Optional):", list(conf_options.keys()))
            selected_c_id = conf_options[selected_conf_name]

            st.markdown("---")
            st.markdown("##### Authors & Ordering (1..n without gaps)")
            selected_authors = st.multiselect(
                "Select Authors in Exact Order (First selected will be Author #1): *",
                options=list(res_options.keys()),
                help="The order in which you pick researchers determines their author_order (1, 2, ...)."
            )

            st.markdown("##### Research Classification")
            col_t, col_k = st.columns(2)
            with col_t:
                selected_topics = st.multiselect("Select Topics: *", options=list(top_options.keys()))
            with col_k:
                selected_keywords = st.multiselect("Select Keywords: *", options=list(key_options.keys()))

            submit_paper = st.form_submit_button("Submit Publication (Atomic Transaction)", type="primary")

            if submit_paper:
                if not p_title:
                    st.error("Paper title is required.")
                elif not p_year_input.isdigit() or int(p_year_input) <= 0:
                    st.error("Publication year must be a positive integer.")
                elif not selected_authors:
                    st.error("At least one author must be selected.")
                elif not selected_topics:
                    st.error("At least one topic must be selected.")
                elif not selected_keywords:
                    st.error("At least one keyword must be selected.")
                else:
                    pub_year = int(p_year_input)
                    conn = db.get_connection()
                    conn.autocommit = False
                    cur = conn.cursor()
                    try:
                        # 1. Insert Paper
                        cur.execute(
                            "INSERT INTO PAPER (p_title, abstract, pub_year, c_id) VALUES (%s, %s, %s, %s)",
                            (p_title, p_abstract or None, pub_year, selected_c_id)
                        )
                        new_p_id = cur.lastrowid

                        # 2. Insert Authors in 1..n order
                        for idx, author_name in enumerate(selected_authors, start=1):
                            r_id = res_options[author_name]
                            cur.execute(
                                "INSERT INTO AUTHORS (r_id, p_id, author_order) VALUES (%s, %s, %s)",
                                (r_id, new_p_id, idx)
                            )

                        # 3. Insert Topics
                        for top_name in selected_topics:
                            t_id = top_options[top_name]
                            cur.execute(
                                "INSERT INTO HAS_TOPIC (p_id, t_id) VALUES (%s, %s)",
                                (new_p_id, t_id)
                            )

                        # 4. Insert Keywords
                        for key_name in selected_keywords:
                            k_id = key_options[key_name]
                            cur.execute(
                                "INSERT INTO HAS_KEYWORD (p_id, key_id) VALUES (%s, %s)",
                                (new_p_id, k_id)
                            )

                        # All succeeded: Commit
                        conn.commit()
                        st.success(f"Paper #{new_p_id} '{p_title}' and all associations registered atomically!")
                    except Exception as exc:
                        conn.rollback()
                        st.error(f"Transaction failed and was rolled back cleanly: {db.friendly_error(exc)}")
                    finally:
                        conn.close()

    except Exception as e:
        st.error(db.friendly_error(e))

# ==============================================================================
# TAB 2: ADD CITATION LINK
# ==============================================================================
with tab_cite:
    st.subheader("Establish Citation Link Between Papers")
    try:
        df_papers_all = db.query("SELECT p_id, p_title, pub_year FROM PAPER ORDER BY p_id")
        if len(df_papers_all) < 2:
            st.info("At least two papers are required to establish citation links.")
        else:
            paper_choices = {
                f"#{r['p_id']}: {r['p_title']} ({r['pub_year']})": int(r["p_id"])
                for _, r in df_papers_all.iterrows()
            }
            
            with st.form("form_add_citation"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    citing_label = st.selectbox("Citing Paper (The paper citing another):", list(paper_choices.keys()), key="citing_sel")
                with col_c2:
                    cited_label = st.selectbox("Cited Paper (The referenced paper):", list(paper_choices.keys()), key="cited_sel")
                
                citing_id = paper_choices[citing_label]
                cited_id = paper_choices[cited_label]

                submit_cite = st.form_submit_button("Add Citation Link")

                if submit_cite:
                    if citing_id == cited_id:
                        st.error("A paper cannot cite itself (Self-citation blocked).")
                    else:
                        try:
                            db.execute(
                                "INSERT INTO CITES (citing_p_id, cited_p_id) VALUES (%s, %s)",
                                (citing_id, cited_id)
                            )
                            st.success(f"Citation registered: Paper #{citing_id} cites Paper #{cited_id}!")
                        except Exception as e:
                            st.error(db.friendly_error(e))

            st.markdown("#### Existing Citation Relationships")
            df_existing_cites = db.query("""
                SELECT 
                    c.citing_p_id AS `Citing ID`, p1.p_title AS `Citing Paper`,
                    c.cited_p_id AS `Cited ID`, p2.p_title AS `Cited Paper`
                FROM CITES c
                JOIN PAPER p1 ON c.citing_p_id = p1.p_id
                JOIN PAPER p2 ON c.cited_p_id = p2.p_id
                ORDER BY c.citing_p_id, c.cited_p_id
            """)
            st.dataframe(df_existing_cites, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(db.friendly_error(e))

# ==============================================================================
# TAB 3: ASSIGN RESEARCHER TO PROJECT (WORKS_ON)
# ==============================================================================
with tab_works:
    st.subheader("Assign Researcher to Project (WORKS_ON)")
    try:
        df_r = db.query("SELECT r_id, r_name, institution FROM RESEARCHER ORDER BY r_name")
        df_p = db.query("SELECT project_id, name FROM PROJECT ORDER BY name")

        r_map = {f"{r['r_name']} ({r['institution']})": int(r["r_id"]) for _, r in df_r.iterrows()}
        p_map = {f"Project #{p['project_id']}: {p['name']}": int(p["project_id"]) for _, p in df_p.iterrows()}

        with st.form("form_works_on"):
            sel_r = st.selectbox("Select Researcher:", list(r_map.keys()))
            sel_p = st.selectbox("Select Project:", list(p_map.keys()))
            submit_works = st.form_submit_button("Assign Researcher to Project")

            if submit_works:
                try:
                    db.execute(
                        "INSERT INTO WORKS_ON (r_id, project_id) VALUES (%s, %s)",
                        (r_map[sel_r], p_map[sel_p])
                    )
                    st.success(f"Assigned {sel_r.split(' (')[0]} to project successfully!")
                except Exception as e:
                    st.error(db.friendly_error(e))

        st.markdown("#### Current Project Assignments")
        st.dataframe(
            db.query("SELECT project_name AS Project, r_name AS Researcher, institution AS Institution FROM v_project_team"),
            use_container_width=True, hide_index=True
        )
    except Exception as e:
        st.error(db.friendly_error(e))

# ==============================================================================
# TAB 4: LINK DATASET TO PROJECT (USES)
# ==============================================================================
with tab_uses:
    st.subheader("Link Research Dataset to Project (USES)")
    try:
        df_proj = db.query("SELECT project_id, name FROM PROJECT ORDER BY name")
        df_ds = db.query("SELECT dataset_id, name FROM DATASET ORDER BY name")

        pr_map = {f"Project #{p['project_id']}: {p['name']}": int(p["project_id"]) for _, p in df_proj.iterrows()}
        ds_map = {f"Dataset #{d['dataset_id']}: {d['name']}": int(d["dataset_id"]) for _, d in df_ds.iterrows()}

        with st.form("form_uses"):
            sel_proj = st.selectbox("Select Project:", list(pr_map.keys()), key="uses_p")
            sel_ds = st.selectbox("Select Dataset:", list(ds_map.keys()), key="uses_d")
            submit_uses = st.form_submit_button("Link Dataset to Project")

            if submit_uses:
                try:
                    db.execute(
                        "INSERT INTO USES (project_id, dataset_id) VALUES (%s, %s)",
                        (pr_map[sel_proj], ds_map[sel_ds])
                    )
                    st.success("Dataset linked to project successfully!")
                except Exception as e:
                    st.error(db.friendly_error(e))

        st.markdown("#### Current Project Datasets")
        st.dataframe(
            db.query("SELECT project_name AS Project, dataset_name AS Dataset, source AS Source FROM v_project_datasets"),
            use_container_width=True, hide_index=True
        )
    except Exception as e:
        st.error(db.friendly_error(e))

