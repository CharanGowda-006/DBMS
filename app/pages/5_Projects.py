import sys
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auth
import db
import workflow


current_user = auth.require_login()
can_manage = current_user["role"] in ("TEACHER", "ADMIN")

st.title("Research Projects & Data Assets")
tab_labels = ["Explore Projects"]
if can_manage:
    tab_labels.append("Manage Projects")
tab_labels.append("Cross-Project Collaboration")
tabs = st.tabs(tab_labels)
explore_tab = tabs[0]
manage_tab = tabs[1] if can_manage else None
collaboration_tab = tabs[-1]


def _show_notice():
    notice = st.session_state.pop("projects_notice", None)
    if notice:
        level, message = notice
        getattr(st, level)(message)


def _safe_http_url(value):
    if not value:
        return None
    try:
        parsed = urlsplit(str(value).strip())
        if (
            parsed.scheme.lower() in ("http", "https")
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
        ):
            return str(value).strip()
    except ValueError:
        return None
    return None


def _optional_text(value):
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _project_selector(projects, key, label):
    identifiers = [int(value) for value in projects["project_id"].tolist()]
    selected_id = st.session_state.get(key)
    index = identifiers.index(selected_id) if selected_id in identifiers else 0
    return st.selectbox(
        label,
        identifiers,
        index=index,
        key=key,
        format_func=lambda project_id: (
            f"Project #{project_id}: "
            f"{projects.loc[projects['project_id'] == project_id, 'name'].iloc[0]}"
        ),
    )


_show_notice()


with explore_tab:
    st.subheader("Explore Projects")
    try:
        projects = workflow.list_projects()
        search = st.text_input("Search Projects", key="project_explore_search")
        if projects.empty:
            st.info("No projects found in the database.")
        else:
            matching = projects[
                projects["name"].astype(str).str.contains(
                    search.strip(), case=False, na=False, regex=False
                )
            ] if search.strip() else projects
            st.caption(
                f"Showing {len(matching)} of {len(projects)} research projects."
            )
            if matching.empty:
                st.info("No matching research projects found.")
            else:
                selected_id = _project_selector(
                    matching, "explore_project_id", "Select a project"
                )
                project = workflow.get_project(selected_id)
                with st.container(border=True):
                    st.markdown(f"### {project['name']}")
                    st.caption(f"Project ID: {int(project['project_id'])}")
                    description = _optional_text(project.get("description"))
                    st.write(description or "No project description provided.")
                    owner_name = _optional_text(project.get("owner_name"))
                    st.caption(
                        f"Coordinator: {owner_name}"
                        if owner_name else "Coordinator: Not assigned"
                    )

                metric_team, metric_datasets = st.columns(2)
                metric_team.metric("Researchers", int(project["researcher_count"]))
                metric_datasets.metric("Datasets", int(project["dataset_count"]))

                team, dataset_list = st.columns(2)
                with team:
                    st.markdown("#### Research Team Members")
                    researchers = workflow.list_project_team(selected_id)
                    if researchers.empty:
                        st.info("No researchers have been assigned to this project yet.")
                    else:
                        st.dataframe(
                            researchers[["r_name", "institution"]].rename(
                                columns={"r_name": "Researcher", "institution": "Institution"}
                            ),
                            use_container_width=True,
                            hide_index=True,
                        )

                with dataset_list:
                    st.markdown("#### Associated Datasets")
                    datasets = workflow.list_project_datasets(selected_id)
                    if datasets.empty:
                        st.info("No datasets have been linked to this project yet.")
                    else:
                        display = datasets[["dataset_name", "source"]].rename(
                            columns={
                                "dataset_name": "Dataset",
                                "source": "Source / URL",
                            }
                        )
                        display["Open source"] = datasets["source"].map(_safe_http_url)
                        st.dataframe(
                            display,
                            column_config={
                                "Open source": st.column_config.LinkColumn(
                                    "Open source", display_text="Open"
                                )
                            },
                            use_container_width=True,
                            hide_index=True,
                        )
    except Exception as exc:
        st.error(db.friendly_error(exc))


if can_manage:
    with manage_tab:
        st.subheader("Manage Projects")
        create_section, manage_section = st.columns([1, 2])

        with create_section:
            with st.container(border=True):
                st.markdown("### Create New Project")
                with st.form("create_project", clear_on_submit=True):
                    project_name = st.text_input("Project name *")
                    project_description = st.text_area("Project description")
                    create = st.form_submit_button("Create Project", type="primary")
                if create:
                    try:
                        project_id = workflow.create_project(
                            project_name, project_description
                        )
                        st.session_state["project_manage_selected"] = int(project_id)
                        st.session_state["projects_notice"] = (
                            "success", f"Project created with ID {project_id}."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(db.friendly_error(exc))

        with manage_section:
            st.markdown("### Manage Existing Project")
            try:
                manageable = workflow.list_manageable_projects()
                if manageable.empty:
                    st.info("Create a project to manage its details, team, and datasets.")
                else:
                    selected_id = _project_selector(
                        manageable,
                        "project_manage_selected",
                        "Select a project to manage",
                    )
                    details_tab, team_tab, datasets_tab = st.tabs(
                        ["Project Details", "Team Members", "Datasets"]
                    )
                    project = manageable[
                        manageable["project_id"] == selected_id
                    ].iloc[0]

                    with details_tab:
                        with st.form("update_project_details"):
                            updated_name = st.text_input(
                                "Project name *",
                                value=project["name"],
                                key=f"manage_project_name_{selected_id}",
                            )
                            updated_description = st.text_area(
                                "Project description",
                                value=_optional_text(project["description"]),
                                key=f"manage_project_description_{selected_id}",
                            )
                            save_details = st.form_submit_button("Save Project Details")
                        if save_details:
                            try:
                                workflow.update_project(
                                    selected_id, updated_name, updated_description
                                )
                                st.session_state["projects_notice"] = (
                                    "success", "Project details saved."
                                )
                                st.rerun()
                            except Exception as exc:
                                st.error(db.friendly_error(exc))

                    with team_tab:
                        st.markdown("#### Assigned Researchers")
                        assigned = workflow.list_project_team(selected_id)
                        if assigned.empty:
                            st.info("No researchers have been assigned to this project yet.")
                        for researcher in assigned.itertuples():
                            row, confirm_col, remove_col = st.columns([5, 2, 1])
                            row.write(
                                f"**{researcher.r_name}** · "
                                f"{_optional_text(researcher.institution) or 'Institution not listed'}"
                            )
                            confirmed = confirm_col.checkbox(
                                "Confirm removal",
                                key=f"confirm_researcher_remove_{selected_id}_{researcher.r_id}",
                            )
                            if remove_col.button(
                                "Remove",
                                key=f"remove_researcher_{selected_id}_{researcher.r_id}",
                                disabled=not confirmed,
                            ):
                                try:
                                    workflow.remove_researcher_from_project(
                                        selected_id, int(researcher.r_id)
                                    )
                                    st.session_state["projects_notice"] = (
                                        "success", "Researcher removed from this project."
                                    )
                                    st.rerun()
                                except Exception as exc:
                                    st.error(db.friendly_error(exc))

                        all_researchers = db.query(
                            """SELECT r_id, r_name, institution
                               FROM RESEARCHER ORDER BY r_name, r_id"""
                        )
                        assigned_ids = (
                            set(assigned["r_id"].astype(int).tolist())
                            if not assigned.empty else set()
                        )
                        available = (
                            all_researchers[
                                ~all_researchers["r_id"].astype(int).isin(assigned_ids)
                            ]
                            if not all_researchers.empty else all_researchers
                        )
                        st.markdown("#### Add Existing Researcher")
                        if available.empty:
                            st.info(
                                "All existing researchers are already assigned."
                                if not all_researchers.empty
                                else "No researchers are available yet."
                            )
                        else:
                            researcher_options = {
                                int(researcher.r_id): (
                                    f"{researcher.r_name} "
                                    f"({_optional_text(researcher.institution) or 'Institution not listed'})"
                                )
                                for researcher in available.itertuples()
                            }
                            with st.form("add_existing_researcher"):
                                researcher_id = st.selectbox(
                                    "Researcher",
                                    list(researcher_options),
                                    format_func=lambda item: researcher_options[item],
                                )
                                add_existing = st.form_submit_button(
                                    "Add Researcher to Project"
                                )
                            if add_existing:
                                try:
                                    workflow.assign_researcher(selected_id, researcher_id)
                                    st.session_state["projects_notice"] = (
                                        "success", "Researcher assigned to the project."
                                    )
                                    st.rerun()
                                except Exception as exc:
                                    st.error(db.friendly_error(exc))

                        with st.expander("+ Register New Researcher"):
                            with st.form(
                                f"register_project_researcher_{selected_id}",
                                clear_on_submit=True,
                            ):
                                new_researcher_name = st.text_input(
                                    "Full name *", key=f"new_researcher_name_{selected_id}"
                                )
                                new_researcher_email = st.text_input(
                                    "Email *", key=f"new_researcher_email_{selected_id}"
                                )
                                new_researcher_institution = st.text_input(
                                    "Institution (optional)",
                                    key=f"new_researcher_institution_{selected_id}",
                                )
                                add_new_researcher = st.form_submit_button(
                                    "Register and Assign Researcher"
                                )
                            if add_new_researcher:
                                try:
                                    workflow.add_researcher_to_project(
                                        selected_id,
                                        new_researcher_name,
                                        new_researcher_email,
                                        new_researcher_institution,
                                    )
                                    st.session_state["projects_notice"] = (
                                        "success", "Researcher registered and assigned."
                                    )
                                    st.rerun()
                                except Exception as exc:
                                    st.error(db.friendly_error(exc))

                    with datasets_tab:
                        st.markdown("#### Linked Datasets")
                        linked = workflow.list_project_datasets(selected_id)
                        if linked.empty:
                            st.info("No datasets have been linked to this project yet.")
                        for dataset in linked.itertuples():
                            row, confirm_col, unlink_col = st.columns([5, 2, 1])
                            row.write(
                                f"**{dataset.dataset_name}** · {dataset.source}"
                            )
                            confirmed = confirm_col.checkbox(
                                "Confirm unlink",
                                key=f"confirm_dataset_unlink_{selected_id}_{dataset.dataset_id}",
                            )
                            if unlink_col.button(
                                "Unlink",
                                key=f"unlink_dataset_{selected_id}_{dataset.dataset_id}",
                                disabled=not confirmed,
                            ):
                                try:
                                    workflow.unlink_dataset_from_project(
                                        selected_id, int(dataset.dataset_id)
                                    )
                                    st.session_state["projects_notice"] = (
                                        "success", "Dataset unlinked from this project."
                                    )
                                    st.rerun()
                                except Exception as exc:
                                    st.error(db.friendly_error(exc))

                        all_datasets = db.query(
                            "SELECT dataset_id, name, source FROM DATASET ORDER BY name, dataset_id"
                        )
                        linked_ids = (
                            set(linked["dataset_id"].astype(int).tolist())
                            if not linked.empty else set()
                        )
                        available_datasets = (
                            all_datasets[
                                ~all_datasets["dataset_id"].astype(int).isin(linked_ids)
                            ]
                            if not all_datasets.empty else all_datasets
                        )
                        st.markdown("#### Link Existing Dataset")
                        if available_datasets.empty:
                            st.info(
                                "All existing datasets are already linked."
                                if not all_datasets.empty
                                else "No datasets are available yet."
                            )
                        else:
                            dataset_options = {
                                int(dataset.dataset_id): (
                                    f"{dataset.name} — {dataset.source}"
                                )
                                for dataset in available_datasets.itertuples()
                            }
                            with st.form("link_existing_dataset"):
                                dataset_id = st.selectbox(
                                    "Dataset",
                                    list(dataset_options),
                                    format_func=lambda item: dataset_options[item],
                                )
                                link_existing = st.form_submit_button("Link Dataset")
                            if link_existing:
                                try:
                                    workflow.link_dataset(selected_id, dataset_id)
                                    st.session_state["projects_notice"] = (
                                        "success", "Dataset linked to the project."
                                    )
                                    st.rerun()
                                except Exception as exc:
                                    st.error(db.friendly_error(exc))

                        with st.expander("+ Register New Dataset"):
                            with st.form(
                                f"register_project_dataset_{selected_id}",
                                clear_on_submit=True,
                            ):
                                dataset_name = st.text_input(
                                    "Dataset name *", key=f"new_dataset_name_{selected_id}"
                                )
                                dataset_source = st.text_input(
                                    "Dataset source / URL *",
                                    key=f"new_dataset_source_{selected_id}",
                                )
                                register_dataset = st.form_submit_button(
                                    "Register and Link Dataset"
                                )
                            if register_dataset:
                                try:
                                    _, created = workflow.add_dataset_to_project(
                                        selected_id, dataset_name, dataset_source
                                    )
                                    st.session_state["projects_notice"] = (
                                        "success",
                                        "Dataset registered and linked."
                                        if created else
                                        "A matching dataset was reused and linked.",
                                    )
                                    st.rerun()
                                except Exception as exc:
                                    st.error(db.friendly_error(exc))
            except Exception as exc:
                st.error(db.friendly_error(exc))


with collaboration_tab:
    st.subheader("Cross-Project Collaboration")
    st.write(
        "Discover research projects that collaborate through shared researchers "
        "or reuse common scientific datasets."
    )
    try:
        shared = workflow.list_shared_project_pairs()
        if shared.empty:
            st.info("No shared researchers or datasets were found between projects.")
        else:
            pair_count, researcher_pairs, dataset_pairs = st.columns(3)
            pair_count.metric("Project pairs with shared resources", len(shared))
            researcher_pairs.metric(
                "Pairs sharing researchers",
                int((shared["shared_researcher_count"] > 0).sum()),
            )
            dataset_pairs.metric(
                "Pairs sharing datasets",
                int((shared["shared_dataset_count"] > 0).sum()),
            )

            display = shared[[
                "p1_name", "p2_name", "shared_researcher_count", "shared_dataset_count"
            ]].rename(columns={
                "p1_name": "Project 1",
                "p2_name": "Project 2",
                "shared_researcher_count": "Shared Researchers",
                "shared_dataset_count": "Shared Datasets",
            })
            st.dataframe(display, use_container_width=True, hide_index=True)

            pair_ids = [
                (int(pair.p1_id), int(pair.p2_id))
                for pair in shared.itertuples()
            ]
            pair_labels = {
                (int(pair.p1_id), int(pair.p2_id)): (
                    f"{pair.p1_name} ↔ {pair.p2_name}"
                )
                for pair in shared.itertuples()
            }
            selected_pair = st.selectbox(
                "Explore a project pair",
                pair_ids,
                format_func=lambda pair: pair_labels[pair],
                key="collaboration_project_pair",
            )
            project1_id, project2_id = selected_pair
            researcher_details = workflow.list_shared_researchers(
                project1_id, project2_id
            )
            dataset_details = workflow.list_shared_datasets(project1_id, project2_id)
            details_left, details_right = st.columns(2)
            with details_left:
                st.markdown("#### Shared Researchers")
                if researcher_details.empty:
                    st.info("No researchers are shared between these projects.")
                else:
                    st.dataframe(
                        researcher_details[["r_name", "institution"]].rename(
                            columns={
                                "r_name": "Researcher",
                                "institution": "Institution",
                            }
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
            with details_right:
                st.markdown("#### Shared Datasets")
                if dataset_details.empty:
                    st.info("No datasets are shared between these projects.")
                else:
                    dataset_display = dataset_details[
                        ["dataset_name", "source"]
                    ].rename(columns={
                        "dataset_name": "Dataset",
                        "source": "Source / URL",
                    })
                    dataset_display["Open source"] = dataset_details["source"].map(
                        _safe_http_url
                    )
                    st.dataframe(
                        dataset_display,
                        column_config={
                            "Open source": st.column_config.LinkColumn(
                                "Open source", display_text="Open"
                            )
                        },
                        use_container_width=True,
                        hide_index=True,
                    )
    except Exception as exc:
        st.error(db.friendly_error(exc))
