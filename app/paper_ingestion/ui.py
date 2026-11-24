import streamlit as st

import db
import workflow
from paper_ingestion.entity_matcher import (
    exact_duplicate,
    match_references,
    researcher_candidates,
)
from paper_ingestion.metadata_extractor import extract_metadata
from paper_ingestion.pdf_parser import (
    DEFAULT_MAX_UPLOAD_MB,
    PDFIngestionError,
    extract_pdf_text,
    max_upload_bytes,
    pdf_metadata,
)
from paper_ingestion.reference_parser import normalize_doi
from paper_ingestion.topic_classifier import classify_topics

_STATE = "smart_import"
_PREFIX = "smart_import_"


def _init_review_state(metadata):
    st.session_state["smart_import_title"] = metadata.get("title", "")
    st.session_state["smart_import_abstract"] = metadata.get("abstract", "")
    st.session_state["smart_import_year"] = metadata.get("year")
    st.session_state["smart_import_doi"] = metadata.get("doi") or ""
    st.session_state["smart_import_venue"] = metadata.get("venue") or ""
    st.session_state["smart_import_authors"] = [
        {
            "name": item.get("name", ""),
            "email": item.get("email", ""),
            "institution": item.get("institution", ""),
            "candidate_ids": [],
        }
        for item in metadata.get("authors", [])
    ]
    st.session_state["smart_import_topic_suggestions"] = metadata.get(
        "topic_suggestions", []
    )
    st.session_state["smart_import_proposed_topic_suggestions"] = metadata.get(
        "proposed_topic_suggestions", []
    )
    st.session_state["smart_import_selected_topics"] = (
        [
            item["t_name"]
            for item in st.session_state["smart_import_topic_suggestions"]
        ]
    )
    st.session_state["smart_import_approved_new_topics"] = []
    st.session_state["smart_import_selected_keywords"] = list(
        metadata.get("keywords", [])
    )
    st.session_state["smart_import_step"] = 1


def _reset_author_state(index):
    authors = st.session_state.get("smart_import_authors", [])
    if 0 <= index < len(authors):
        authors.pop(index)
    author_prefix = f"{_PREFIX}author_"
    for key in list(st.session_state):
        if key.startswith(author_prefix):
            key_index = key[len(author_prefix):].partition("_")[0]
            if key_index.isdigit() and int(key_index) >= index:
                del st.session_state[key]


def _add_author():
    authors = st.session_state.setdefault("smart_import_authors", [])
    authors.append({
        "name": "",
        "email": "",
        "institution": "",
        "candidate_ids": [],
    })


def _load_database_records():
    conferences = db.query(
        "SELECT c_id, c_name, c_year FROM CONFERENCE ORDER BY c_name, c_year"
    ).to_dict("records")
    researchers = db.query(
        "SELECT r_id, r_name, email, institution FROM RESEARCHER ORDER BY r_name"
    ).to_dict("records")
    topics = db.query("SELECT t_id, t_name FROM TOPIC ORDER BY t_name").to_dict("records")
    keywords = db.query(
        "SELECT key_id, keyword FROM KEYWORD ORDER BY keyword"
    ).to_dict("records")
    papers = db.query(
        """SELECT p.p_id, p.p_title, p.pub_year, i.doi
           FROM PAPER p
           LEFT JOIN PAPER_INGESTION i ON i.p_id = p.p_id
           LEFT JOIN PAPER_WORKFLOW w ON w.p_id = p.p_id
           WHERE COALESCE(w.status, 'APPROVED') = 'APPROVED'
           ORDER BY p.p_id"""
    ).to_dict("records")
    return conferences, researchers, topics, keywords, papers


def _entity_values(selected, rows, id_key, value_key):
    by_name = {}
    for row in rows:
        by_name.setdefault(str(row[value_key]).strip().casefold(), int(row[id_key]))
    result = []
    seen = set()
    for value in selected:
        name = str(value).strip()
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        result.append(by_name[name.casefold()] if name.casefold() in by_name else {"new": name})
    return result


def _render_authors(researchers):
    st.markdown("#### Authors (in publication order)")
    authors = st.session_state.get("smart_import_authors", [])
    if not authors:
        st.info("No author names were detected. Add each author and their verified email.")

    labels = {
        int(row["r_id"]): (
            f"#{int(row['r_id'])} {row['r_name']} · {row['email']}"
        )
        for row in researchers
    }
    submitted_authors = []
    for index, initial in enumerate(authors):
        with st.container(border=True):
            st.markdown(f"**Author {index + 1}**")
            include = st.checkbox(
                "Include this author",
                value=True,
                key=f"{_PREFIX}author_{index}_include",
            )
            name_col, email_col = st.columns(2)
            name = name_col.text_input(
                "Author name",
                value=initial.get("name", ""),
                key=f"{_PREFIX}author_{index}_name",
            )
            email = email_col.text_input(
                "Verified email (required for a new researcher)",
                value=initial.get("email", ""),
                key=f"{_PREFIX}author_{index}_email",
            )
            institution = st.text_input(
                "Institution",
                value=initial.get("institution", ""),
                key=f"{_PREFIX}author_{index}_institution",
            )
            suggestion_rows, match_kind = researcher_candidates(
                {"name": name, "email": email}, researchers
            )
            candidate_ids = [int(row["r_id"]) for row in suggestion_rows]
            if candidate_ids:
                reason = "email" if match_kind == "email" else "name only; confirm before reuse"
                st.caption(
                    f"Existing researcher suggestion by {reason}: "
                    + ", ".join(labels[item] for item in candidate_ids)
                )
            options = ["Create new researcher", *candidate_ids]
            selected_index = 0
            if match_kind == "email" and len(candidate_ids) == 1:
                selected_index = 1
            selection = st.selectbox(
                "Resolve researcher",
                options=options,
                index=selected_index,
                format_func=lambda value: (
                    value if isinstance(value, str) else labels[int(value)]
                ),
                key=f"{_PREFIX}author_{index}_match",
            )
            remove_col, _ = st.columns([1, 5])
            remove_col.button(
                "Remove author",
                key=f"{_PREFIX}author_{index}_remove",
                on_click=_reset_author_state,
                args=(index,),
            )
            if include:
                if isinstance(selection, int):
                    submitted_authors.append(selection)
                else:
                    submitted_authors.append({
                        "new": {
                            "name": name,
                            "email": email,
                            "institution": institution,
                        }
                    })
    st.button("Add author", on_click=_add_author, key=f"{_PREFIX}add_author")
    return submitted_authors


def _build_reviewed_metadata(raw, authors, topics, keywords, references):
    return {
        **raw,
        "title": st.session_state.get(f"{_PREFIX}title", "").strip(),
        "abstract": st.session_state.get(f"{_PREFIX}abstract", "").strip(),
        "year": st.session_state.get(f"{_PREFIX}year"),
        "doi": normalize_doi(st.session_state.get(f"{_PREFIX}doi", "")),
        "venue": st.session_state.get(f"{_PREFIX}venue", "").strip(),
        "authors": [
            {
                "name": st.session_state.get(f"{_PREFIX}author_{index}_name", "").strip(),
                "email": st.session_state.get(f"{_PREFIX}author_{index}_email", "").strip(),
                "institution": st.session_state.get(
                    f"{_PREFIX}author_{index}_institution", ""
                ).strip(),
                "researcher_id": (
                    st.session_state.get(f"{_PREFIX}author_{index}_match")
                    if isinstance(
                        st.session_state.get(f"{_PREFIX}author_{index}_match"), int
                    ) else None
                ),
            }
            for index in range(len(st.session_state.get("smart_import_authors", [])))
            if st.session_state.get(f"{_PREFIX}author_{index}_include", True)
        ],
        "topics": [str(item) for item in topics],
        "keywords": [str(item) for item in keywords],
        "references": [
            {
                "raw": item.get("raw"),
                "title": item.get("title"),
                "year": item.get("year"),
                "doi": item.get("doi"),
                "matched_paper_id": (
                    int(item["candidate"]["p_id"])
                    if item.get("candidate") else None
                ),
                "confirmed": bool(
                    st.session_state.get(f"{_PREFIX}reference_{index}", False)
                ),
            }
            for index, item in enumerate(references)
        ],
    }


def render_smart_import():
    st.subheader("Smart Paper Import")
    st.caption(
        "Upload an academic research paper to automatically extract and organize "
        "publication information. Extraction is local; no PDF content is sent to "
        "an external service."
    )

    success = st.session_state.pop("smart_import_success", None)
    if st.session_state.pop("smart_import_reset", False):
        st.session_state.pop(_STATE, None)
        for key in list(st.session_state):
            if key.startswith(_PREFIX):
                del st.session_state[key]
    if success:
        st.success(success)
        st.page_link("pages/8_My_Submissions.py", label="View My Submissions")

    state = st.session_state.get(_STATE)
    uploaded = st.file_uploader(
        "Upload research paper (PDF)",
        type=["pdf"],
        max_upload_size=max(1, max_upload_bytes() // (1024 * 1024)),
        key=f"{_PREFIX}file",
        help=f"Text-based PDF only; maximum {DEFAULT_MAX_UPLOAD_MB} MB.",
    )
    if uploaded is not None:
        st.caption(
            f"File: {uploaded.name} · "
            f"{uploaded.size / (1024 * 1024):.2f} MB"
        )
        if st.button("Extract Information", type="primary", key=f"{_PREFIX}extract"):
            try:
                content = uploaded.getvalue()
                with st.status("Extracting paper information", expanded=True) as status:
                    st.write("Validating PDF and reading document...")
                    text = extract_pdf_text(uploaded.name, content)
                    st.write("Extracting publication metadata and references...")
                    metadata = extract_metadata(text, pdf_metadata(uploaded.name, content))
                    conferences, researchers, topics, keywords, papers = (
                        _load_database_records()
                    )
                    topic_suggestions = classify_topics(
                        metadata.get("title", ""),
                        metadata.get("keywords", []),
                        topics,
                        metadata.get("abstract", ""),
                    )
                    metadata["topic_suggestions"] = topic_suggestions["existing"]
                    metadata["proposed_topic_suggestions"] = (
                        topic_suggestions["proposed"]
                    )
                    metadata["references"] = match_references(
                        metadata.get("references", []), papers
                    )
                    state = {
                        "filename": uploaded.name,
                        "content": content,
                        "metadata": metadata,
                        "step": 1,
                    }
                    st.session_state[_STATE] = state
                    _init_review_state(metadata)
                    status.update(
                        label="Extraction complete — review all detected values",
                        state="complete",
                    )
                st.rerun()
            except PDFIngestionError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(db.friendly_error(exc))

    state = st.session_state.get(_STATE)
    if not state:
        st.info(
            "Upload a text-based academic PDF and select **Extract Information**. "
            f"Scanned PDFs are not supported; the current limit is "
            f"{max_upload_bytes() // (1024 * 1024)} MB."
        )
        return

    metadata = state["metadata"]
    try:
        conferences, researchers, topics, keywords, papers = _load_database_records()
    except Exception as exc:
        st.error(db.friendly_error(exc))
        return

    step = int(st.session_state.get(f"{_PREFIX}step", state.get("step", 1)))
    st.progress(step / 2, text=f"Step {step} of 2 · Review and submit")
    title = st.text_input(
        "Paper title *", max_chars=500, key=f"{_PREFIX}title"
    )
    abstract = st.text_area("Abstract", height=180, key=f"{_PREFIX}abstract")
    title_col, doi_col = st.columns(2)
    year = title_col.number_input(
        "Publication year *",
        min_value=1,
        max_value=65535,
        value=None,
        step=1,
        key=f"{_PREFIX}year",
        placeholder="Enter the verified publication year",
    )
    doi = doi_col.text_input("DOI (optional)", key=f"{_PREFIX}doi")
    if not metadata.get("year"):
        st.caption("Publication year was not reliably detected; enter it from the paper.")
    if metadata.get("venue"):
        st.caption(f"Extracted venue suggestion (not yet verified): {metadata['venue']}")
    st.text_input(
        "Conference / venue (optional; select an existing conference below)",
        key=f"{_PREFIX}venue",
    )

    conference_labels = {
        f"{row['c_name']} ({row['c_year']})": int(row["c_id"])
        for row in conferences
    }
    conference_labels = {"-- No conference / pre-print --": None, **conference_labels}
    conference_match = "-- No conference / pre-print --"
    for row in conferences:
        venue = str(metadata.get("venue") or "").casefold()
        if (
            venue
            and str(row["c_name"]).casefold() in venue
            and (
                not metadata.get("year")
                or int(row["c_year"]) == int(metadata["year"])
            )
        ):
            conference_match = f"{row['c_name']} ({row['c_year']})"
            break
    selected_conference = st.selectbox(
        "Existing conference record",
        list(conference_labels),
        index=list(conference_labels).index(conference_match),
        key=f"{_PREFIX}conference",
        help="Unverified extracted venue text is not added as a new conference.",
    )

    author_entries = _render_authors(researchers)
    topic_names = [str(row["t_name"]) for row in topics]
    keyword_names = [str(row["keyword"]) for row in keywords]
    selected_topics = st.multiselect(
        "Existing research topics — inferred suggestions, separate from extracted author keywords",
        topic_names,
        key=f"{_PREFIX}selected_topics",
        accept_new_options=True,
    )
    suggestions = st.session_state.get("smart_import_topic_suggestions", [])
    if suggestions:
        st.caption(
            "Preselected existing topics based on title, abstract, and keywords: "
            + "; ".join(
                f"{item['t_name']} ({item['reason']})"
                for item in suggestions
            )
        )
    else:
        st.caption(
            "No existing database topic matched the paper's title, abstract, or "
            "keywords. You can choose an existing topic or review new-topic proposals."
        )

    approved_new_topics = []
    proposed_topics = st.session_state.get(
        "smart_import_proposed_topic_suggestions", []
    )
    if proposed_topics:
        st.markdown("#### Proposed new topics")
        st.caption(
            "These are inferred categories, not extracted keywords. Approving one "
            "adds it only if you submit the reviewed paper."
        )
        for index, suggestion in enumerate(proposed_topics):
            if st.checkbox(
                f"Approve new topic: {suggestion['t_name']}",
                value=False,
                key=f"{_PREFIX}approve_new_topic_{index}",
                help=suggestion["reason"],
            ):
                approved_new_topics.append(suggestion["t_name"])
    st.session_state["smart_import_approved_new_topics"] = approved_new_topics

    selected_keywords = st.multiselect(
        "Extracted author keywords — editable source terms, not inferred topics",
        keyword_names,
        key=f"{_PREFIX}selected_keywords",
        accept_new_options=True,
    )

    duplicate_rows = exact_duplicate(
        title, year, doi, papers
    ) if title and year else []
    if duplicate_rows:
        st.error(
            "This looks like an existing publication. Review it in Search instead "
            "of submitting a duplicate: "
            + ", ".join(
                f"#{int(row['p_id'])} {row['p_title']} ({row['pub_year']})"
                for row in duplicate_rows
            )
        )

    st.markdown("#### Extracted references")
    confirmed_citations = []
    references = metadata.get("references", [])
    if not references:
        st.info("No reference list was detected.")
    for index, reference in enumerate(references):
        candidate = reference.get("candidate")
        ambiguous = reference.get("candidates", [])
        if ambiguous:
            choices = {
                int(item["p_id"]): item
                for item in ambiguous
            }
            chosen_id = st.selectbox(
                f"Resolve ambiguous reference {index + 1}",
                options=[None, *choices],
                format_func=lambda value: (
                    "Leave unmatched" if value is None
                    else f"#{value} {choices[value]['p_title']} "
                    f"({choices[value]['pub_year']})"
                ),
                key=f"{_PREFIX}reference_match_{index}",
            )
            candidate = choices.get(chosen_id)
            reference["candidate"] = candidate
        status = reference.get("match_status", "Unmatched")
        if candidate:
            label = (
                f"{status}: #{int(candidate['p_id'])} {candidate['p_title']} "
                f"({candidate['pub_year']}) · {reference.get('match_reason')}"
            )
            confirmed = st.checkbox(
                label,
                key=f"{_PREFIX}reference_{index}",
                help="Only selected, approved papers are added as citation links.",
            )
            if confirmed:
                confirmed_citations.append(int(candidate["p_id"]))
        else:
            raw = reference.get("raw") or "Reference text unavailable."
            st.caption(f"Unmatched — {raw[:500]}")

    all_selected_topics = list(dict.fromkeys(
        [str(topic) for topic in selected_topics] + approved_new_topics
    ))
    reviewed = _build_reviewed_metadata(
        metadata, author_entries, all_selected_topics, selected_keywords, references
    )
    year_value = int(year) if year is not None else None
    final_step = step == 2
    if final_step:
        st.markdown("#### Final review")
        st.write(f"**Title:** {title or 'Missing'}")
        st.write(f"**Year:** {year_value or 'Needs review'}")
        st.write(f"**Conference:** {selected_conference}")
        st.write(f"**Authors in order:** {len(author_entries)}")
        st.write(
            f"**Topics:** "
            f"{', '.join(all_selected_topics) if all_selected_topics else 'None'}"
        )
        st.write(
            f"**Keywords:** "
            f"{', '.join(str(item) for item in selected_keywords) if selected_keywords else 'None'}"
        )
        st.write(f"**Confirmed citation links:** {len(confirmed_citations)}")
        st.write(f"**Unmatched references:** {sum(not item.get('candidate') for item in references)}")
        st.write((abstract[:700] + ("..." if len(abstract) > 700 else "")) or "No abstract.")
        confirmed_review = st.checkbox(
            "I reviewed the extracted values and confirm they are accurate.",
            key=f"{_PREFIX}confirm",
        )
        submit_col, back_col = st.columns(2)
        submit = submit_col.button(
            "Submit Paper for Administrator Approval",
            type="primary",
            disabled=not confirmed_review or bool(duplicate_rows),
            key=f"{_PREFIX}submit",
        )
        if back_col.button("Back to review", key=f"{_PREFIX}back"):
            st.session_state[f"{_PREFIX}step"] = 1
            st.rerun()
        if submit:
            try:
                if not year_value:
                    raise ValueError("Enter the verified publication year before submitting.")
                if not title.strip():
                    raise ValueError("Enter the paper title before submitting.")
                if not author_entries:
                    raise ValueError("Add at least one author before submitting.")
                if not all_selected_topics or not selected_keywords:
                    raise ValueError("Select at least one topic and keyword.")
                reviewed["title"] = title.strip()
                reviewed["abstract"] = abstract.strip()
                reviewed["year"] = year_value
                reviewed["doi"] = normalize_doi(doi)
                reviewed["topics"] = all_selected_topics
                reviewed["keywords"] = [str(item) for item in selected_keywords]
                result, status = workflow.submit_paper(
                    title,
                    abstract,
                    year_value,
                    conference_labels[selected_conference],
                    author_entries,
                    _entity_values(all_selected_topics, topics, "t_id", "t_name"),
                    _entity_values(selected_keywords, keywords, "key_id", "keyword"),
                    ingestion={
                        "filename": state["filename"],
                        "content": state["content"],
                        "metadata": reviewed,
                    },
                    confirmed_citations=confirmed_citations,
                )
                st.session_state["smart_import_success"] = (
                    "Research paper extracted and submitted successfully. "
                    + (
                        "Awaiting administrator approval."
                        if status == "PENDING"
                        else "Added as an approved administrator publication."
                    )
                )
                st.session_state["smart_import_reset"] = True
                st.rerun()
            except Exception as exc:
                st.error(db.friendly_error(exc))
    else:
        continue_button, cancel_button = st.columns(2)
        if continue_button.button("Continue to final review", type="primary"):
            validation_errors = []
            if not title.strip():
                validation_errors.append("Enter a paper title.")
            if year_value is None:
                validation_errors.append("Enter the verified publication year.")
            if not author_entries:
                validation_errors.append("Include at least one author.")
            for entry in author_entries:
                if isinstance(entry, dict):
                    person = entry["new"]
                    if not person["name"].strip():
                        validation_errors.append("Every new author needs a name.")
                    if not person["email"].strip():
                        validation_errors.append(
                            "A verified email is required for every new researcher."
                        )
            if not all_selected_topics:
                validation_errors.append("Select at least one research topic.")
            if not selected_keywords:
                validation_errors.append("Select at least one keyword.")
            if duplicate_rows:
                validation_errors.append("Resolve the potential duplicate before proceeding.")
            if validation_errors:
                for message in dict.fromkeys(validation_errors):
                    st.error(message)
            else:
                st.session_state[f"{_PREFIX}step"] = 2
                st.rerun()
        if cancel_button.button("Cancel and discard draft"):
            st.session_state["smart_import_reset"] = True
            st.rerun()
