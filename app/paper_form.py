import re

import streamlit as st


_EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _key(prefix, name):
    return f"{prefix}_{name}"


def _entries(prefix, kind):
    key = _key(prefix, kind)
    if key not in st.session_state:
        st.session_state[key] = []
    return key, st.session_state[key]


def _append_once(entries, value):
    if value not in entries:
        entries.append(value)
        return True
    return False


def _notice(prefix, level, message):
    st.session_state[_key(prefix, "notice")] = (level, message)


def _add_selected(prefix, kind):
    entries_key, entries = _entries(prefix, kind)
    picker_name = {
        "authors": "researcher_picker",
        "topics": "topic_picker",
        "keywords": "keyword_picker",
    }[kind]
    picker_key = _key(prefix, picker_name)
    selected = st.session_state.get(picker_key, [])
    added = sum(_append_once(entries, int(item)) for item in selected)
    st.session_state[picker_key] = []
    _notice(prefix, "success", f"Added {added} selection(s)." if added else "Those selections are already listed.")


def _add_researcher(prefix, email_to_id):
    entries_key, entries = _entries(prefix, "authors")
    name_key = _key(prefix, "new_researcher_name")
    email_key = _key(prefix, "new_researcher_email")
    institution_key = _key(prefix, "new_researcher_institution")
    name = st.session_state.get(name_key, "").strip()
    email = st.session_state.get(email_key, "").strip().lower()
    institution = st.session_state.get(institution_key, "").strip()
    if not name or len(name) > 150:
        _notice(prefix, "error", "Researcher name must contain 1 to 150 characters.")
        return
    if len(email) > 245 or not _EMAIL_PATTERN.fullmatch(email):
        _notice(prefix, "error", "Enter a valid researcher email address.")
        return
    if len(institution) > 255:
        _notice(prefix, "error", "Institution must contain at most 255 characters.")
        return

    existing_id = email_to_id.get(email)
    if existing_id is not None:
        added = _append_once(entries, existing_id)
        message = "Matched the existing researcher; their details were not changed."
    else:
        match = next(
            (
                item for item in entries
                if isinstance(item, dict)
                and isinstance(item.get("new"), dict)
                and item["new"]["email"] == email
            ),
            None,
        )
        added = match is None
        if added:
            entries.append({
                "new": {"name": name, "email": email, "institution": institution}
            })
        message = "Researcher added to this draft." if added else "That researcher is already listed."

    for key in (name_key, email_key, institution_key):
        st.session_state[key] = ""
    _notice(prefix, "success", message)


def _add_named(prefix, kind, existing_name_to_id):
    entries_key, entries = _entries(prefix, kind)
    name_key = _key(prefix, "new_topic_name" if kind == "topics" else "new_keyword_name")
    name = st.session_state.get(name_key, "").strip()
    if not name or len(name) > 150:
        _notice(prefix, "error", f"Name must contain 1 to 150 characters.")
        return
    normalized = name.lower()
    existing_id = existing_name_to_id.get(normalized)
    if existing_id is not None:
        added = _append_once(entries, existing_id)
        message = "Matched the existing value." if added else "That value is already listed."
    else:
        match = next(
            (
                item for item in entries
                if isinstance(item, dict)
                and isinstance(item.get("new"), str)
                and item["new"].lower() == normalized
            ),
            None,
        )
        added = match is None
        if added:
            entries.append({"new": name})
        message = f"Added to this draft: {name}" if added else "That value is already listed."
    st.session_state[name_key] = ""
    _notice(prefix, "success", message)


def _add_profile_first(prefix, researcher_id):
    entries_key, entries = _entries(prefix, "authors")
    if researcher_id not in entries:
        entries.insert(0, researcher_id)
        _notice(prefix, "success", "Your linked researcher profile was added as the first author.")


def _move(prefix, kind, index, offset):
    _, entries = _entries(prefix, kind)
    destination = index + offset
    if 0 <= destination < len(entries):
        entries[index], entries[destination] = entries[destination], entries[index]


def _remove(prefix, kind, index):
    _, entries = _entries(prefix, kind)
    if 0 <= index < len(entries):
        entries.pop(index)


def _render_ordered_list(prefix, kind, labels, title):
    entries_key, entries = _entries(prefix, kind)
    st.markdown(f"**{title}**")
    if not entries:
        st.caption("Nothing selected yet.")
        return
    for index, item in enumerate(entries):
        if isinstance(item, dict) and isinstance(item.get("new"), dict):
            researcher = item["new"]
            label = f"{researcher['name']} — {researcher['email']} (new)"
        elif isinstance(item, dict) and isinstance(item.get("new"), str):
            label = f"{item['new']} (new)"
        else:
            label = labels.get(int(item), f"Unknown record #{item}")
        name, up, down, remove = st.columns([8, 1, 1, 1])
        name.write(f"{index + 1}. {label}")
        up.button(
            "↑", key=_key(prefix, f"{kind}_{index}_up"),
            disabled=index == 0,
            on_click=_move, args=(prefix, kind, index, -1),
        )
        down.button(
            "↓", key=_key(prefix, f"{kind}_{index}_down"),
            disabled=index == len(entries) - 1,
            on_click=_move, args=(prefix, kind, index, 1),
        )
        remove.button(
            "✕", key=_key(prefix, f"{kind}_{index}_remove"),
            on_click=_remove, args=(prefix, kind, index),
        )


def render_dynamic_entity_controls(
    prefix, researchers, topics, keywords, profile_researcher_id=None, initial=None,
    sections=("authors", "topics", "keywords"),
):
    initial = initial or {}
    for kind in ("authors", "topics", "keywords"):
        key = _key(prefix, kind)
        if key not in st.session_state:
            st.session_state[key] = list(initial.get(kind, []))

    researcher_labels = {
        int(item["r_id"]): (
            f"{item['r_name']} ({item.get('institution') or 'Institution not listed'}) "
            f"— #{int(item['r_id'])}"
        )
        for item in researchers
    }
    email_to_id = {}
    for item in researchers:
        email_to_id.setdefault(str(item["email"]).strip().lower(), int(item["r_id"]))
    topic_labels = {int(item["t_id"]): item["t_name"] for item in topics}
    topic_name_to_id = {}
    for item in topics:
        topic_name_to_id.setdefault(str(item["t_name"]).strip().lower(), int(item["t_id"]))
    keyword_labels = {int(item["key_id"]): item["keyword"] for item in keywords}
    keyword_name_to_id = {}
    for item in keywords:
        keyword_name_to_id.setdefault(str(item["keyword"]).strip().lower(), int(item["key_id"]))

    if "authors" in sections:
        st.subheader("Authors in order")
        if profile_researcher_id in researcher_labels:
            _, selected_authors = _entries(prefix, "authors")
            if profile_researcher_id not in selected_authors:
                st.button(
                    "Add my researcher profile as first author",
                    key=_key(prefix, "add_profile_first"),
                    on_click=_add_profile_first,
                    args=(prefix, int(profile_researcher_id)),
                )
        st.multiselect(
            "Select existing researchers",
            options=list(researcher_labels),
            format_func=lambda researcher_id: researcher_labels[researcher_id],
            key=_key(prefix, "researcher_picker"),
        )
        st.button(
            "Add selected researchers",
            key=_key(prefix, "add_researchers"),
            on_click=_add_selected,
            args=(prefix, "authors"),
        )
        with st.expander("+ Add New Researcher"):
            st.text_input("Researcher full name *", key=_key(prefix, "new_researcher_name"))
            st.text_input("Email address *", key=_key(prefix, "new_researcher_email"))
            st.text_input("Institution (optional)", key=_key(prefix, "new_researcher_institution"))
            st.button(
                "Add to Authors",
                key=_key(prefix, "add_new_researcher"),
                on_click=_add_researcher,
                args=(prefix, email_to_id),
            )
        _render_ordered_list(prefix, "authors", researcher_labels, "Ordered authors")

    if "topics" in sections:
        st.subheader("Research topics")
        st.multiselect(
            "Select existing topics",
            options=list(topic_labels),
            format_func=lambda topic_id: topic_labels[topic_id],
            key=_key(prefix, "topic_picker"),
        )
        st.button(
            "Add selected topics", key=_key(prefix, "add_topics"),
            on_click=_add_selected, args=(prefix, "topics"),
        )
        with st.expander("+ Add New Research Topic"):
            st.text_input("Research topic name *", key=_key(prefix, "new_topic_name"))
            st.button(
                "Add to Topics", key=_key(prefix, "add_new_topic"),
                on_click=_add_named, args=(prefix, "topics", topic_name_to_id),
            )
        _render_ordered_list(prefix, "topics", topic_labels, "Selected research topics")

    if "keywords" in sections:
        st.subheader("Keywords")
        st.multiselect(
            "Select existing keywords",
            options=list(keyword_labels),
            format_func=lambda keyword_id: keyword_labels[keyword_id],
            key=_key(prefix, "keyword_picker"),
        )
        st.button(
            "Add selected keywords", key=_key(prefix, "add_keywords"),
            on_click=_add_selected, args=(prefix, "keywords"),
        )
        with st.expander("+ Add New Keyword"):
            st.text_input("Keyword *", key=_key(prefix, "new_keyword_name"))
            st.button(
                "Add to Keywords", key=_key(prefix, "add_new_keyword"),
                on_click=_add_named, args=(prefix, "keywords", keyword_name_to_id),
            )
        _render_ordered_list(prefix, "keywords", keyword_labels, "Selected keywords")

    notice = st.session_state.pop(_key(prefix, "notice"), None)
    if notice:
        level, message = notice
        getattr(st, level)(message)

    return {
        "authors": list(st.session_state[_key(prefix, "authors")]),
        "topics": list(st.session_state[_key(prefix, "topics")]),
        "keywords": list(st.session_state[_key(prefix, "keywords")]),
    }
