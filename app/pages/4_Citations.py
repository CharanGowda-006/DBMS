import streamlit as st
import sys
from pathlib import Path

# Add app directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db

st.set_page_config(page_title="Citation Network Explorer", layout="wide")
st.title("Citation Network Explorer")

st.markdown("""
Recursively traverses the citation graph starting from any publication.
- **Forward Traversal**: Discovers literature cited by the selected paper (outgoing references).
- **Reverse Traversal**: Discovers publications citing the selected paper (impact & incoming citations).
- **Cycle-Guarded**: Safely navigates mutual citations without infinite recursion.
""")

try:
    df_papers = db.query("SELECT p_id, p_title, pub_year FROM PAPER ORDER BY p_id")
    if df_papers.empty:
        st.info("No papers available in the database.")
    else:
        paper_map = {
            f"#{row['p_id']}: {row['p_title']} ({row['pub_year']})": int(row['p_id'])
            for _, row in df_papers.iterrows()
        }

        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            selected_label = st.selectbox("Select Root Paper:", list(paper_map.keys()))
            start_p_id = paper_map[selected_label]
        with col2:
            direction = st.radio(
                "Traversal Direction:",
                options=["forward", "reverse"],
                format_func=lambda x: "Forward (Papers cited by this paper)" if x == "forward" else "Reverse (Papers citing this paper)"
            )
        with col3:
            depth = st.slider("Maximum Depth Level:", min_value=1, max_value=6, value=3)

        if st.button("Explore Citation Graph", type="primary"):
            df_citations = db.call_proc("sp_citations", (start_p_id, direction, depth))

            if df_citations.empty:
                st.info(f"No citations found in {direction} direction from Paper #{start_p_id} within depth {depth}.")
            else:
                st.success(f"Discovered {len(df_citations)} citation path(s) within depth {depth}.")

                # Format depth with dash indentation per depth level
                display_df = df_citations.copy()
                display_df["Hierarchical View"] = display_df.apply(
                    lambda r: ("-" * int(r["depth"])) + " " + str(r["p_title"]), axis=1
                )
                
                output_table = display_df[[
                    "depth", "Hierarchical View", "p_id", "path"
                ]].rename(columns={
                    "depth": "Depth Level",
                    "p_id": "Target Paper ID",
                    "path": "Traversal Path"
                })

                st.dataframe(output_table, use_container_width=True, hide_index=True)

                # Summary metric
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric("Unique Papers Reached", display_df["p_id"].nunique())
                with col_m2:
                    st.metric("Max Traversal Depth Reached", int(display_df["depth"].max()))

except Exception as e:
    st.error(db.friendly_error(e))
