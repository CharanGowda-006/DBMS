import math


COLLABORATION_FILTERS = {
    "All Collaborations": None,
    "New Opportunities": 0,
    "Existing Co-authors": 1,
}

OVERLAP_BANDS = (
    "High potential overlap",
    "Moderate potential overlap",
    "Low potential overlap",
)


def _as_int(value):
    return int(value)


def _unique_collaborations(rows):
    unique = {}
    ordered = sorted(rows, key=lambda row: (
        -int(row["already_coauthored"]),
        -int(row["shared_topic_count"]),
        str(row["r1_name"]).casefold(),
        str(row["r2_name"]).casefold(),
        int(row["r1_id"]),
        int(row["r2_id"]),
    ))
    for source in ordered:
        row = dict(source)
        key = tuple(sorted((_as_int(row["r1_id"]), _as_int(row["r2_id"]))))
        unique.setdefault(key, row)
    return list(unique.values())


def filter_collaborations(rows, researcher_id=None, status_filter=None):
    filtered = []
    for row in _unique_collaborations(rows):
        r1_id = _as_int(row["r1_id"])
        r2_id = _as_int(row["r2_id"])
        if researcher_id is not None and int(researcher_id) not in (r1_id, r2_id):
            continue
        if status_filter is not None and int(row["already_coauthored"]) != status_filter:
            continue
        filtered.append(dict(row))
    filtered.sort(key=lambda row: (
        int(row["already_coauthored"]),
        -int(row["shared_topic_count"]),
        str(row["r1_name"]).casefold(),
        str(row["r2_name"]).casefold(),
        int(row["r1_id"]),
        int(row["r2_id"]),
    ))
    return filtered


def collaboration_metrics(rows):
    new_count = sum(int(row["already_coauthored"]) == 0 for row in rows)
    existing_count = sum(int(row["already_coauthored"]) == 1 for row in rows)
    return {
        "total": len(rows),
        "new": new_count,
        "existing": existing_count,
    }


def filter_similar_papers(rows, selected_paper_id=None, minimum_score=0, bands=None):
    allowed_bands = set(OVERLAP_BANDS if bands is None else bands)
    selected_id = int(selected_paper_id) if selected_paper_id is not None else None
    unique = {}
    for source in rows:
        row = dict(source)
        p1_id = int(row["p1_id"])
        p2_id = int(row["p2_id"])
        if selected_id is not None and selected_id not in (p1_id, p2_id):
            continue
        if selected_id == p1_id:
            other_id, other_title = p2_id, row["p2_title"]
            other_year = row.get("p2_year")
        elif selected_id == p2_id:
            other_id, other_title = p1_id, row["p1_title"]
            other_year = row.get("p1_year")
        else:
            other_id, other_title, other_year = None, None, None
        row.update({
            "similarity_score": float(row["similarity_score"]),
            "topic_jaccard": float(row["topic_jaccard"]),
            "keyword_jaccard": float(row["keyword_jaccard"]),
            "other_p_id": other_id,
            "other_title": other_title,
            "other_year": other_year,
        })
        if row["similarity_score"] < float(minimum_score):
            continue
        if row["overlap_band"] not in allowed_bands:
            continue
        key = (min(p1_id, p2_id), max(p1_id, p2_id))
        existing = unique.get(key)
        if existing is None or row["similarity_score"] > existing["similarity_score"]:
            unique[key] = row
    result = list(unique.values())
    result.sort(key=lambda row: (
        -row["similarity_score"],
        str(row.get("other_title") or row["p1_title"]).casefold(),
        int(row["other_p_id"] or row["p1_id"]),
    ))
    return result


def similarity_metrics(rows):
    counts = {band: 0 for band in OVERLAP_BANDS}
    for row in rows:
        band = row["overlap_band"]
        if band in counts:
            counts[band] += 1
    return {
        "total": len(rows),
        "high": counts["High potential overlap"],
        "moderate": counts["Moderate potential overlap"],
        "low": counts["Low potential overlap"],
    }


def compare_sets(values_a, values_b):
    set_a = set(values_a)
    set_b = set(values_b)
    return {
        "shared": sorted(set_a & set_b, key=str.casefold),
        "only_a": sorted(set_a - set_b, key=str.casefold),
        "only_b": sorted(set_b - set_a, key=str.casefold),
    }


def collaboration_figure(rows, selected_researcher_id=None, node_limit=80, edge_limit=160):
    import plotly.graph_objects as go

    unique_rows = _unique_collaborations(rows)
    graph_truncated = len(unique_rows) > edge_limit
    ordered_rows = unique_rows[:edge_limit]
    researchers = {}
    for row in ordered_rows:
        for side in ("r1", "r2"):
            researcher_id = int(row[f"{side}_id"])
            researchers.setdefault(researcher_id, {
                "id": researcher_id,
                "name": str(row[f"{side}_name"]),
                "institution": str(row.get(f"{side}_institution") or "Institution not listed"),
            })

    if selected_researcher_id is not None:
        selected_id = int(selected_researcher_id)
        researchers = {
            researcher_id: researcher
            for researcher_id, researcher in researchers.items()
            if researcher_id == selected_id or any(
                selected_id in (int(row["r1_id"]), int(row["r2_id"]))
                and researcher_id in (int(row["r1_id"]), int(row["r2_id"]))
                for row in ordered_rows
            )
        }
    if len(researchers) > node_limit:
        graph_truncated = True
        priority_ids = sorted(researchers)
        if selected_researcher_id is not None:
            selected_id = int(selected_researcher_id)
            priority_ids = [selected_id, *(
                researcher_id for researcher_id in priority_ids
                if researcher_id != selected_id
            )]
        keep_ids = set(priority_ids[:node_limit])
        researchers = {key: value for key, value in researchers.items() if key in keep_ids}
        ordered_rows = [
            row for row in ordered_rows
            if int(row["r1_id"]) in researchers and int(row["r2_id"]) in researchers
        ]

    researcher_ids = sorted(researchers)
    positions = {}
    if selected_researcher_id is not None and int(selected_researcher_id) in researchers:
        selected_id = int(selected_researcher_id)
        peers = [researcher_id for researcher_id in researcher_ids if researcher_id != selected_id]
        positions[selected_id] = (0.0, 0.0)
        for index, researcher_id in enumerate(peers):
            angle = 2 * math.pi * index / max(1, len(peers))
            positions[researcher_id] = (math.cos(angle), math.sin(angle))
    else:
        for index, researcher_id in enumerate(researcher_ids):
            angle = 2 * math.pi * index / max(1, len(researcher_ids))
            positions[researcher_id] = (math.cos(angle), math.sin(angle))

    figure = go.Figure()
    for existing, label, color, dash in (
        (True, "Already co-authored", "#2563EB", "solid"),
        (False, "Potential opportunity", "#64748B", "dash"),
    ):
        subset = [row for row in ordered_rows if bool(int(row["already_coauthored"])) == existing]
        if not subset:
            continue
        line_x = []
        line_y = []
        hover_x = []
        hover_y = []
        hover_data = []
        for row in subset:
            first = int(row["r1_id"])
            second = int(row["r2_id"])
            if first not in positions or second not in positions:
                continue
            x1, y1 = positions[first]
            x2, y2 = positions[second]
            line_x.extend((x1, x2, None))
            line_y.extend((y1, y2, None))
            hover_x.append((x1 + x2) / 2)
            hover_y.append((y1 + y2) / 2)
            hover_data.append([
                row["r1_name"], row["r2_name"], int(row["shared_topic_count"]),
                str(row.get("shared_topics") or "Not listed"), label,
            ])
        figure.add_trace(go.Scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            line={"color": color, "width": 2, "dash": dash},
            name=label,
            showlegend=True,
            hoverinfo="skip",
        ))
        if hover_data:
            figure.add_trace(go.Scatter(
                x=hover_x,
                y=hover_y,
                mode="markers",
                marker={"size": 12, "color": "rgba(0,0,0,0.01)"},
                customdata=hover_data,
                hovertemplate=(
                    "%{customdata[0]} ↔ %{customdata[1]}"
                    "<br>Shared topics: %{customdata[2]} (%{customdata[3]})"
                    "<br>Status: %{customdata[4]}<extra></extra>"
                ),
                showlegend=False,
            ))

    if researchers:
        root_id = int(selected_researcher_id) if selected_researcher_id is not None else None
        figure.add_trace(go.Scatter(
            x=[positions[researcher_id][0] for researcher_id in researcher_ids],
            y=[positions[researcher_id][1] for researcher_id in researcher_ids],
            mode="markers+text",
            text=[researchers[researcher_id]["name"] for researcher_id in researcher_ids],
            textposition="bottom center",
            textfont={"size": 10},
            customdata=[
                [researchers[researcher_id]["name"], researchers[researcher_id]["institution"]]
                for researcher_id in researcher_ids
            ],
            hovertemplate="%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
            marker={
                "size": [28 if researcher_id == root_id else 20 for researcher_id in researcher_ids],
                "color": ["#2563EB" if researcher_id == root_id else "#93C5FD"
                          for researcher_id in researcher_ids],
                "line": {"width": 1.5, "color": "#1D4ED8"},
            },
            name="Researchers",
            showlegend=False,
        ))

    figure.update_layout(
        height=520,
        margin={"l": 20, "r": 20, "t": 28, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        dragmode="pan",
        hovermode="closest",
        xaxis={"visible": False, "showgrid": False, "zeroline": False},
        yaxis={"visible": False, "showgrid": False, "zeroline": False},
        legend={"orientation": "h", "y": 1.02, "x": 0},
    )
    return figure, len(researchers), len(ordered_rows), graph_truncated
