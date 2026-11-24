import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import ui


auth.require_login()
ui.page_header("Research Overview", "Explore publication trends, research topics, and project resources.")

try:
    df_year = db.query("SELECT * FROM v_papers_per_year ORDER BY pub_year")
    df_conf = db.query("SELECT * FROM v_papers_per_conference ORDER BY paper_count DESC, c_name")
    df_topic = db.query("SELECT * FROM v_papers_per_topic ORDER BY paper_count DESC, t_name")
    df_team = db.query("SELECT * FROM v_project_team ORDER BY project_name, r_name")
    df_datasets = db.query("SELECT * FROM v_project_datasets ORDER BY project_name, dataset_name")

    metrics = st.columns(3)
    metrics[0].metric(
        "Research Topics",
        int(df_topic["t_id"].nunique()) if not df_topic.empty else 0,
    )
    metrics[1].metric(
        "Project Teams",
        int(df_team["project_id"].nunique()) if not df_team.empty else 0,
    )
    metrics[2].metric(
        "Linked Datasets",
        int(df_datasets["dataset_id"].nunique()) if not df_datasets.empty else 0,
    )

    left, right = st.columns(2)
    with left:
        ui.section_header("Publications by Year")
        if df_year.empty:
            ui.empty_state("No publication-year data is available.")
        else:
            chart_data = df_year.copy()
            chart_data["pub_year"] = chart_data["pub_year"].astype(str)
            fig = px.bar(
                chart_data,
                x="pub_year",
                y="paper_count",
                text="paper_count",
                labels={"pub_year": "Publication year", "paper_count": "Papers"},
                color_discrete_sequence=["#4F83FF"],
            )
            fig.update_traces(
                hovertemplate="%{x}<br>Approved publications: %{y}<extra></extra>",
                textposition="outside",
            )
            fig.update_layout(
                height=320,
                margin={"l": 8, "r": 8, "t": 12, "b": 8},
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                yaxis={"title": None, "showgrid": True, "gridcolor": "rgba(128,128,128,.15)"},
                xaxis={"title": None, "showgrid": False},
            )
            st.plotly_chart(fig, width="stretch", config={"displaylogo": False})

    with right:
        ui.section_header("Publications by Conference")
        if df_conf.empty:
            ui.empty_state("No conference publication data is available.")
        else:
            chart_data = df_conf.copy()
            chart_data["conference_label"] = chart_data["c_name"].astype(str).map(
                lambda name: name if len(name) <= 28 else name[:25].rstrip() + "..."
            )
            fig = px.bar(
                chart_data,
                x="paper_count",
                y="conference_label",
                orientation="h",
                text="paper_count",
                custom_data=["c_name"],
                labels={"conference_label": "Conference", "paper_count": "Papers"},
                color_discrete_sequence=["#4F83FF"],
            )
            fig.update_traces(
                hovertemplate="%{customdata[0]}<br>Approved publications: %{x}<extra></extra>",
                textposition="outside",
            )
            fig.update_layout(
                height=max(280, min(520, 90 + len(chart_data) * 38)),
                margin={"l": 8, "r": 34, "t": 12, "b": 8},
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis={"title": None, "showgrid": True, "gridcolor": "rgba(128,128,128,.15)"},
                yaxis={"title": None, "showgrid": False, "categoryorder": "total ascending"},
            )
            st.plotly_chart(fig, width="stretch", config={"displaylogo": False})

    ui.section_header("Publications by Research Topic")
    if df_topic.empty:
        ui.empty_state("No research-topic data is available.")
    else:
        topic_data = df_topic.sort_values(
            ["paper_count", "t_name"], ascending=[True, False]
        )
        fig = px.bar(
            topic_data,
            x="paper_count",
            y="t_name",
            orientation="h",
            text="paper_count",
            labels={"t_name": "Research topic", "paper_count": "Papers"},
            color_discrete_sequence=["#4F83FF"],
        )
        fig.update_traces(
            hovertemplate="%{y}<br>Approved publications: %{x}<extra></extra>",
            textposition="outside",
        )
        fig.update_layout(
            height=max(260, min(620, 80 + len(topic_data) * 34)),
            margin={"l": 8, "r": 34, "t": 10, "b": 8},
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis={"title": None, "showgrid": True, "gridcolor": "rgba(128,128,128,.15)"},
            yaxis={"title": None, "showgrid": False},
        )
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})

    with st.expander("Detailed Research Analytics"):
        year_tab, topic_tab, resources_tab = st.tabs([
            "Papers by Year & Conference",
            "Research Topics",
            "Projects & Datasets",
        ])
        with year_tab:
            year_col, conf_col = st.columns(2)
            with year_col:
                st.markdown("**By year**")
                st.dataframe(
                    df_year.rename(columns={
                        "pub_year": "Year",
                        "paper_count": "Approved Papers",
                    }),
                    width="stretch",
                    hide_index=True,
                )
            with conf_col:
                st.markdown("**By conference**")
                st.dataframe(
                    df_conf[["c_name", "paper_count"]].rename(columns={
                        "c_name": "Conference",
                        "paper_count": "Approved Papers",
                    }),
                    width="stretch",
                    hide_index=True,
                )
        with topic_tab:
            st.dataframe(
                df_topic[["t_name", "paper_count"]].rename(columns={
                    "t_name": "Research Topic",
                    "paper_count": "Approved Papers",
                }),
                width="stretch",
                hide_index=True,
            )
        with resources_tab:
            team_col, dataset_col = st.columns(2)
            with team_col:
                st.markdown("**Project Teams**")
                team_columns = [
                    column for column in ("project_name", "r_name", "institution")
                    if column in df_team.columns
                ]
                st.dataframe(
                    df_team[team_columns].rename(columns={
                        "project_name": "Project",
                        "r_name": "Researcher",
                        "institution": "Institution",
                    }),
                    width="stretch",
                    hide_index=True,
                )
            with dataset_col:
                st.markdown("**Project Datasets**")
                dataset_columns = [
                    column for column in ("project_name", "dataset_name", "source")
                    if column in df_datasets.columns
                ]
                st.dataframe(
                    df_datasets[dataset_columns].rename(columns={
                        "project_name": "Project",
                        "dataset_name": "Dataset",
                        "source": "Source / URL",
                    }),
                    width="stretch",
                    hide_index=True,
                )
except Exception as exc:
    st.error(db.friendly_error(exc))
