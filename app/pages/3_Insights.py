import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db

st.set_page_config(page_title="Research Insights", page_icon="🧠", layout="wide")
st.title("🧠 Research Network Insights")

tab_collab, tab_sim = st.tabs(["🤝 Potential Collaborators", "📑 Publication Similarity"])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — Collaboration Discovery
# ══════════════════════════════════════════════════════════════════
with tab_collab:
    st.markdown("""
Identifies researcher pairs who share **≥ 2 distinct research topics** across their published works.
Flags whether a pair has already co-authored papers, or represents a **new cross-institutional opportunity**.
""")

    try:
        df = db.query("SELECT * FROM v_collaborators")
        if df.empty:
            st.info("No researcher pairs with at least 2 shared topics found.")
        else:
            new_pairs   = int((df["already_coauthored"] == 0).sum())
            known_pairs = int((df["already_coauthored"] == 1).sum())
            k1, k2, k3 = st.columns(3)
            k1.metric("🔍 Total Pairs",          len(df))
            k2.metric("🆕 New Opportunities",   new_pairs)
            k3.metric("✅ Already Co-authored",  known_pairs)

            st.markdown("---")

            # Filter toggle
            show_filter = st.radio(
                "Show", ["All Pairs", "New Opportunities Only", "Already Co-authored Only"],
                horizontal=True
            )
            if show_filter == "New Opportunities Only":
                df = df[df["already_coauthored"] == 0]
            elif show_filter == "Already Co-authored Only":
                df = df[df["already_coauthored"] == 1]

            # Build display table
            disp = df.copy()
            disp["Researcher Pair"]       = disp["r1_name"] + " & " + disp["r2_name"]
            disp["Shared Topics"]         = disp["shared_topics"]
            disp["# Shared Topics"]       = disp["shared_topic_count"]
            disp["Already Co-authored?"]  = disp["already_coauthored"].map({1: "✅ Yes", 0: "🆕 No"})
            st.dataframe(
                disp[["Researcher Pair", "# Shared Topics", "Shared Topics", "Already Co-authored?"]],
                use_container_width=True, hide_index=True
            )

    except Exception as e:
        st.error(db.friendly_error(e))

# ══════════════════════════════════════════════════════════════════
# TAB 2 — Publication Similarity
# ══════════════════════════════════════════════════════════════════
with tab_sim:
    st.markdown("""
Computes a **weighted Jaccard similarity** between every pair of publications:

$$\\text{Score} = 0.4 \\times J_{\\text{topic}} + 0.6 \\times J_{\\text{keyword}}$$

> ⚠️ Scores reflect **potential topical overlap**, not plagiarism.
""")

    try:
        df_sim = db.query("SELECT * FROM v_paper_similarity")
        if df_sim.empty:
            st.info("No similarity data available.")
        else:
            # Ensure numeric
            for col in ["similarity_score", "topic_jaccard", "keyword_jaccard"]:
                df_sim[col] = df_sim[col].astype(float)

            # Controls row
            sc1, sc2 = st.columns([3, 2])
            with sc1:
                min_score = st.slider(
                    "Minimum similarity score", 0.0, 1.0, 0.2, 0.05,
                    help="Weighted Jaccard: 0 = no overlap, 1 = identical topic+keyword sets"
                )
            with sc2:
                band_filter = st.multiselect(
                    "Overlap band filter",
                    ["High potential overlap", "Moderate potential overlap", "Low potential overlap"],
                    default=["High potential overlap", "Moderate potential overlap", "Low potential overlap"]
                )

            filtered = df_sim[
                (df_sim["similarity_score"] >= min_score) &
                (df_sim["overlap_band"].isin(band_filter))
            ]

            # KPIs
            hi   = int((filtered["overlap_band"] == "High potential overlap").sum())
            med  = int((filtered["overlap_band"] == "Moderate potential overlap").sum())
            low  = int((filtered["overlap_band"] == "Low potential overlap").sum())
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Pairs Shown",  len(filtered))
            m2.metric("🔴 High",      hi)
            m3.metric("🟡 Moderate",  med)
            m4.metric("🟢 Low",       low)

            if filtered.empty:
                st.info("No pairs match the current filter.")
            else:
                # Summary table
                BAND_COLOR = {
                    "High potential overlap":     "🔴",
                    "Moderate potential overlap": "🟡",
                    "Low potential overlap":      "🟢",
                }
                disp = filtered.copy()
                disp["Band"] = disp["overlap_band"].map(BAND_COLOR) + " " + disp["overlap_band"]
                disp["Score"] = disp["similarity_score"].apply(lambda x: f"{x:.4f}")
                disp["Topic J"] = disp["topic_jaccard"].apply(lambda x: f"{x:.4f}")
                disp["Keyword J"] = disp["keyword_jaccard"].apply(lambda x: f"{x:.4f}")

                st.dataframe(
                    disp[["p1_id","p1_title","p2_id","p2_title","Score","Topic J","Keyword J","Band"]].rename(
                        columns={"p1_id":"P1 ID","p1_title":"Paper 1","p2_id":"P2 ID","p2_title":"Paper 2"}
                    ),
                    use_container_width=True, hide_index=True
                )

                # Expandable per-pair detail
                with st.expander("🔍 View Shared Topics & Keywords for Each Pair"):
                    for _, row in filtered.iterrows():
                        score = float(row["similarity_score"])
                        band  = row["overlap_band"]
                        color = "#ffd7d7" if "High" in band else "#fff5cc" if "Moderate" in band else "#e8f9e8"
                        st.markdown(f"""
<div style="background:{color};border-radius:8px;padding:0.8rem 1.2rem;margin-bottom:0.8rem;">
    <strong>Paper #{int(row['p1_id'])}</strong>: {row['p1_title']}<br>
    <strong>Paper #{int(row['p2_id'])}</strong>: {row['p2_title']}<br>
    <span style="font-size:0.85rem;">Score: <strong>{score:.4f}</strong> · {band}</span>
</div>
""", unsafe_allow_html=True)
                        tc, kc = st.columns(2)
                        with tc:
                            st.markdown(f"**🏷️ Shared Topics** (J = {float(row['topic_jaccard']):.4f})")
                            st.info(row["shared_topics"] or "None")
                        with kc:
                            st.markdown(f"**🔑 Shared Keywords** (J = {float(row['keyword_jaccard']):.4f})")
                            st.info(row["shared_keywords"] or "None")

    except Exception as e:
        st.error(db.friendly_error(e))
