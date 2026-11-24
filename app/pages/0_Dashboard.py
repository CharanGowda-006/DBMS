import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import ui


user = auth.require_login()
role = user["role"]

welcome_subtitles = {
    "STUDENT": "Discover research, explore publications, and find academic collaborations.",
    "TEACHER": "Manage your research submissions and discover collaboration opportunities.",
    "ADMIN": "Manage publications, researchers, and research activity.",
}
ui.page_header(f"Welcome back, {user['full_name']}", welcome_subtitles.get(role))

try:
    counts = db.query(
        """SELECT 'APPROVED_PUBLICATIONS' AS metric, COUNT(*) AS value
             FROM PAPER p LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
             WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
           UNION ALL SELECT 'RESEARCHERS', COUNT(*) FROM RESEARCHER
           UNION ALL SELECT 'PROJECTS', COUNT(*) FROM PROJECT
           UNION ALL SELECT 'CONFERENCES', COUNT(*) FROM CONFERENCE"""
    )
    metric_values = {
        row["metric"]: int(row["value"])
        for _, row in counts.iterrows()
    }
    columns = st.columns(4)
    for column, metric, label in zip(
        columns,
        ("APPROVED_PUBLICATIONS", "RESEARCHERS", "PROJECTS", "CONFERENCES"),
        ("Approved Publications", "Researchers", "Research Projects", "Conferences"),
    ):
        column.metric(label, metric_values.get(metric, 0))

    st.subheader("Quick Actions")
    actions = {
        "STUDENT": [
            ("Explore Publications", "pages/2_Search.py"),
            ("Find Collaborators", "pages/3_Insights.py"),
            ("Explore Citations", "pages/4_Citations.py"),
            ("Browse Projects", "pages/5_Projects.py"),
        ],
        "TEACHER": [
            ("Submit Paper", "pages/7_Add_Paper.py"),
            ("My Submissions", "pages/8_My_Submissions.py"),
            ("Manage Projects", "pages/5_Projects.py"),
            ("Find Collaborators", "pages/3_Insights.py"),
        ],
        "ADMIN": [
            ("Review Pending Papers", "pages/9_Admin_Review.py"),
            ("Manage Users", "pages/10_Admin_Users.py"),
            ("Manage Entities", "pages/6_Add_Basic.py"),
            ("View Audit Logs", "pages/11_Admin_Audit.py"),
        ],
    }
    action_cols = st.columns(4)
    for column, (label, page_path) in zip(action_cols, actions.get(role, [])):
        with column:
            st.page_link(page_path, label=label, width="stretch")

    st.subheader("Recent Publications")
    recent = db.query(
        """SELECT p.p_id, p.p_title, p.pub_year,
                  (SELECT GROUP_CONCAT(r.r_name ORDER BY a.author_order SEPARATOR ', ')
                   FROM AUTHORS a JOIN RESEARCHER r ON r.r_id = a.r_id
                   WHERE a.p_id = p.p_id) AS authors,
                  (SELECT GROUP_CONCAT(t.t_name ORDER BY t.t_name SEPARATOR ', ')
                   FROM HAS_TOPIC ht JOIN TOPIC t ON t.t_id = ht.t_id
                   WHERE ht.p_id = p.p_id) AS topics
           FROM PAPER p
           LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
           WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
           ORDER BY p.p_id DESC
           LIMIT 6"""
    )
    if recent.empty:
        ui.empty_state("No approved publications are available yet.")
    else:
        for paper in recent.itertuples():
            with st.container(border=True):
                st.markdown(f"**{paper.p_title}**")
                st.caption(
                    f"Published {paper.pub_year} · "
                    f"{paper.authors or 'Authors not listed'}"
                )
                if paper.topics:
                    st.caption(f"Research topics: {paper.topics}")

    with st.expander("About ResearchNet and Database Snapshot"):
        st.markdown(
            "ResearchNet uses a MySQL relational database, parameterized stored "
            "procedures and views, recursive CTEs, transactions, and integrity triggers. "
            "Publication similarity uses the existing weighted Jaccard calculation."
        )
        st.markdown("#### Live database snapshot")
        entity_tables = [
            "RESEARCHER", "CONFERENCE", "PAPER", "TOPIC", "KEYWORD", "PROJECT", "DATASET"
        ]
        junction_tables = ["AUTHORS", "CITES", "HAS_TOPIC", "HAS_KEYWORD", "WORKS_ON", "USES"]
        all_tables = entity_tables + junction_tables
        snapshot_query = " UNION ALL ".join(
            [
                "SELECT 'PAPER' AS table_name, COUNT(*) AS row_count FROM PAPER p "
                "LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id "
                "WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'"
                if table == "PAPER"
                else f"SELECT '{table}' AS table_name, COUNT(*) AS row_count FROM {table}"
                for table in all_tables
            ]
        )
        snapshot = db.query(snapshot_query)
        st.dataframe(
            snapshot.rename(columns={
                "table_name": "Database table",
                "row_count": "Records",
            }),
            width="stretch",
            hide_index=True,
        )
except Exception as exc:
    st.error(db.friendly_error(exc))
