import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db

st.set_page_config(
    page_title="Research Collaboration Network",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global typography */
html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }

/* Sidebar nav label */
[data-testid="stSidebarNav"] .st-emotion-cache-pkbazv { font-size: 0.9rem; }

/* KPI metric cards */
[data-testid="stMetric"] {
    background: #f8faff;
    border: 1px solid #dde6f7;
    border-radius: 10px;
    padding: 14px 18px;
}
[data-testid="stMetricLabel"] { font-size: 0.75rem; color: #5a6a85; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; color: #1a3a6b; }

/* Section headers */
h2 { color: #1a3a6b; border-bottom: 2px solid #dde6f7; padding-bottom: 6px; margin-top: 1.4rem; }
h3 { color: #2b5c8f; margin-top: 1rem; }

/* Dataframes */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

/* Buttons */
[data-testid="baseButton-primary"] { background-color: #2b5c8f !important; }

/* Alert boxes */
.stAlert { border-radius: 8px; }

/* Sidebar branding strip */
section[data-testid="stSidebar"] { background: #0d2b55; color: white; }
section[data-testid="stSidebar"] * { color: #d4e3f7 !important; }
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: white !important; }
section[data-testid="stSidebar"] .st-emotion-cache-pkbazv { color: #90b8e0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 ResearchNet")
    st.markdown("**Academic Research Collaboration & Discovery Portal**")
    st.markdown("---")
    st.markdown("""
**Navigation**
- 🏠 Home — this page
- 📊 Overview — KPIs & analytics
- 🔍 Search — unified entity search
- 🧠 Insights — collaboration & similarity
- 🔗 Citations — citation graph traversal
- 📁 Projects — teams & datasets
- ➕ Add Entities — register new data
- 📄 Add Paper — transactional publish
""")
    st.markdown("---")
    st.caption("MySQL 8.0 · Python 3.11 · Streamlit 1.67")

# ── Hero header ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="background: linear-gradient(135deg,#0d2b55,#2b5c8f);
            padding: 2rem 2.5rem; border-radius: 14px; margin-bottom: 1.5rem; color: white;">
    <h1 style="margin:0;color:white;font-size:2rem;">
        Academic Research Collaboration & Discovery Portal
    </h1>
    <p style="margin:0.5rem 0 0;opacity:0.85;font-size:0.98rem;">
        A relational intelligence layer for institutional research networks.
        Powered by MySQL views, recursive CTEs, stored procedures, and Streamlit.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Live table counts ─────────────────────────────────────────────────────────
st.subheader("📋 Live Database Snapshot")

ENTITY_TABLES   = ["RESEARCHER","CONFERENCE","PAPER","TOPIC","KEYWORD","PROJECT","DATASET"]
JUNCTION_TABLES = ["AUTHORS","CITES","HAS_TOPIC","HAS_KEYWORD","WORKS_ON","USES"]
ALL_TABLES = ENTITY_TABLES + JUNCTION_TABLES

try:
    q = " UNION ALL ".join(
        [f"SELECT '{t}' AS table_name, COUNT(*) AS row_count FROM {t}" for t in ALL_TABLES]
    )
    df_counts = db.query(q)

    entities = df_counts[df_counts["table_name"].isin(ENTITY_TABLES)].set_index("table_name")
    junctions = df_counts[df_counts["table_name"].isin(JUNCTION_TABLES)].set_index("table_name")

    # KPI quick glance
    cols = st.columns(len(ENTITY_TABLES))
    icons = ["👤","🏛️","📄","🏷️","🔑","💡","💾"]
    for col, tbl, icon in zip(cols, ENTITY_TABLES, icons):
        cnt = int(entities.loc[tbl, "row_count"]) if tbl in entities.index else 0
        col.metric(f"{icon} {tbl.title()}", cnt)

    st.markdown("#### Junction / Relationship Tables")
    jcol = st.columns(len(JUNCTION_TABLES))
    j_icons = ["✍️","🔗","🏷️","🔑","👥","💾"]
    for col, tbl, icon in zip(jcol, JUNCTION_TABLES, j_icons):
        cnt = int(junctions.loc[tbl, "row_count"]) if tbl in junctions.index else 0
        col.metric(f"{icon} {tbl}", cnt)

    total = int(df_counts["row_count"].sum())
    st.success(f"✅ **{len(df_counts)} tables confirmed** · **{total} total records** in `research_collaboration_db`")

except Exception as e:
    st.error(db.friendly_error(e))

# ── About section ─────────────────────────────────────────────────────────────
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    st.markdown("""
### 🗄️ Database Features
- **13 normalized tables** (InnoDB, FK-enforced)
- **Self-citation prevention** via BEFORE INSERT & UPDATE triggers (SQLSTATE 45000)
- **ON DELETE SET NULL** for Conference → Paper references
- **ON DELETE CASCADE** for Researcher / Paper → junction tables
- **UNIQUE** constraint on `email`, `t_name`, `keyword` with friendly errors
""")
with c2:
    st.markdown("""
### 🧠 Analytical Capabilities
- **Collaboration Discovery** — Jaccard topic overlap across author networks
- **Publication Similarity** — Weighted Jaccard (40 % topics · 60 % keywords)
- **Citation Graph** — Recursive CTE traversal with cycle guard
- **Unified Search** — Cross-entity full-network search via stored procedure
- **Project Analytics** — Shared personnel & dataset usage across projects
""")
