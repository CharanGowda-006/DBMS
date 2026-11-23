import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db

st.set_page_config(page_title="Unified Search", page_icon="🔍", layout="wide")
st.title("🔍 Unified Academic Search")
st.caption("Searches publication titles, assigned topics, and keywords simultaneously — then surfaces linked authors, conferences, projects, and datasets.")

# ── Search input ──────────────────────────────────────────────────────────────
col_in, col_btn = st.columns([5, 1])
with col_in:
    term = st.text_input("", placeholder="e.g. Deep Learning, CNN, Healthcare, Transformers …",
                         label_visibility="collapsed")
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    search = st.button("Search 🔎", type="primary", use_container_width=True)

if not term.strip():
    st.markdown("""
<div style="background:#f0f6ff;border:1px solid #c5d9f7;border-radius:10px;padding:1.2rem 1.5rem;margin-top:1rem;">
    <strong>💡 Tips</strong><br>
    Try searching for a topic ("Computer Vision"), a methodology ("CNN"), a researcher name ("Alice"), 
    or a conference keyword ("ICML").
</div>
""", unsafe_allow_html=True)
else:
    try:
        df = db.call_proc("sp_search", (term.strip(),))

        if df.empty:
            st.warning(f"No results found for **'{term}'**. Try a broader keyword.")
        else:
            st.success(f"Found **{len(df)} result(s)** matching **'{term}'** across the research network.")

            TYPE_CFG = {
                "paper":      ("📄", "Papers"),
                "researcher": ("👤", "Researchers"),
                "conference": ("🏛️", "Conferences"),
                "project":    ("💡", "Projects"),
                "dataset":    ("💾", "Datasets"),
            }

            # ── Grouped results ────────────────────────────────────────────────
            for rtype, (icon, label) in TYPE_CFG.items():
                subset = df[df["result_type"] == rtype]
                if subset.empty:
                    continue
                st.markdown(f"### {icon} {label} ({len(subset)})")
                disp = subset[["ref_id", "label", "detail"]].rename(
                    columns={"ref_id": "ID", "label": "Name / Title", "detail": "Match Detail"}
                ).reset_index(drop=True)
                st.dataframe(disp, use_container_width=True, hide_index=True)

            # ── Paper inspector ────────────────────────────────────────────────
            paper_rows = df[df["result_type"] == "paper"]
            if not paper_rows.empty:
                st.markdown("---")
                st.subheader("🔬 Inspect Paper Details")
                opts = {f"#{r['ref_id']}: {r['label']}": int(r["ref_id"]) for _, r in paper_rows.iterrows()}
                sel_lbl = st.selectbox("Select a paper to inspect:", list(opts.keys()))
                pid = opts[sel_lbl]

                p     = db.query("SELECT p_title, abstract, pub_year, c_id FROM PAPER WHERE p_id = %s", (pid,))
                auth  = db.query("SELECT a.author_order, r.r_name, r.institution, r.email FROM AUTHORS a JOIN RESEARCHER r ON a.r_id = r.r_id WHERE a.p_id = %s ORDER BY a.author_order", (pid,))
                tops  = db.query("SELECT t.t_name FROM HAS_TOPIC ht JOIN TOPIC t ON ht.t_id = t.t_id WHERE ht.p_id = %s ORDER BY t.t_name", (pid,))
                kws   = db.query("SELECT k.keyword FROM HAS_KEYWORD hk JOIN KEYWORD k ON hk.key_id = k.key_id WHERE hk.p_id = %s ORDER BY k.keyword", (pid,))
                conf  = db.query("SELECT c.c_name, c.c_year, c.c_location FROM PAPER p JOIN CONFERENCE c ON p.c_id = c.c_id WHERE p.p_id = %s", (pid,))

                if not p.empty:
                    info = p.iloc[0]
                    st.markdown(f"""
<div style="background:#f8faff;border:1px solid #dde6f7;border-radius:10px;padding:1.2rem 1.5rem;margin-bottom:1rem;">
    <h4 style="margin:0;color:#1a3a6b;">{info['p_title']}</h4>
    <span style="background:#e0edff;color:#2b5c8f;border-radius:4px;padding:2px 8px;font-size:0.8rem;">
        📅 Published {info['pub_year']}
    </span>
    <p style="margin-top:0.8rem;color:#444;">{info['abstract'] or 'No abstract available.'}</p>
</div>
""", unsafe_allow_html=True)

                    pa, pb = st.columns(2)
                    with pa:
                        st.markdown("**✍️ Authors (in order)**")
                        if not auth.empty:
                            for _, a in auth.iterrows():
                                st.write(f"{a['author_order']}. **{a['r_name']}** — {a['institution']} · `{a['email']}`")
                        st.markdown("**🏛️ Conference**")
                        if not conf.empty:
                            ci = conf.iloc[0]
                            st.info(f"{ci['c_name']} · {ci['c_year']} · {ci['c_location']}")
                        else:
                            st.caption("No conference assigned.")

                    with pb:
                        st.markdown("**🏷️ Topics**")
                        if not tops.empty:
                            st.write(" · ".join([f"`{t}`" for t in tops["t_name"]]))
                        st.markdown("**🔑 Keywords**")
                        if not kws.empty:
                            st.write(" · ".join([f"`{k}`" for k in kws["keyword"]]))

    except Exception as e:
        st.error(db.friendly_error(e))
