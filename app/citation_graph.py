from html import escape


_DEPTH_COLORS = ("#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE", "#E0F2FE")


def validate_depth(depth):
    if isinstance(depth, bool) or not isinstance(depth, int) or not 1 <= depth <= 5:
        raise ValueError("Maximum citation depth must be between 1 and 5.")
    return depth


def _paper_id(value):
    return int(value)


def _path_ids(value):
    if not isinstance(value, str):
        raise ValueError("Citation traversal returned an invalid path.")
    try:
        paper_ids = tuple(int(part) for part in value.strip(",").split(",") if part)
    except ValueError as exc:
        raise ValueError("Citation traversal returned an invalid path.") from exc
    if len(paper_ids) < 2:
        raise ValueError("Citation traversal returned an incomplete path.")
    return paper_ids


def graph_paper_ids(root_p_id, traversal_rows, graph_limit=150):
    root_p_id = _paper_id(root_p_id)
    shortest_depth = {}
    for row in traversal_rows:
        paper_id = _paper_id(row["p_id"])
        if paper_id == root_p_id:
            continue
        depth = int(row["depth"])
        if depth < 1:
            continue
        shortest_depth[paper_id] = min(depth, shortest_depth.get(paper_id, depth))
    related = sorted(shortest_depth, key=lambda paper_id: (shortest_depth[paper_id], paper_id))
    return [root_p_id, *related[:max(0, graph_limit - 1)]]


def build_citation_graph(
    root_p_id,
    traversal_rows,
    paper_rows,
    citation_rows,
    direction,
    graph_limit=150,
):
    root_p_id = _paper_id(root_p_id)
    direction = str(direction).lower()
    if direction not in {"forward", "reverse"}:
        raise ValueError("Citation direction must be forward or reverse.")

    papers = {_paper_id(row["p_id"]): row for row in paper_rows}
    if root_p_id not in papers:
        raise ValueError("The selected approved publication is unavailable.")

    paths_by_paper = {}
    depths = {}
    for row in traversal_rows:
        paper_id = _paper_id(row["p_id"])
        if paper_id == root_p_id:
            continue
        path = _path_ids(row["path"])
        if path[0] != root_p_id or path[-1] != paper_id:
            raise ValueError("Citation traversal returned a mismatched path.")
        if any(path_id not in papers for path_id in path):
            continue
        depth = int(row["depth"])
        if depth < 1:
            continue
        depths[paper_id] = min(depth, depths.get(paper_id, depth))
        paths_by_paper.setdefault(paper_id, set()).add(path)

    results = []
    for paper_id, paths in paths_by_paper.items():
        canonical_path = min(paths, key=lambda path: (len(path), path))
        paper = papers[paper_id]
        results.append({
            "depth": depths[paper_id],
            "p_id": paper_id,
            "p_title": paper.get("p_title") or "",
            "pub_year": paper.get("pub_year"),
            "path": " → ".join(f"Paper {path_id}" for path_id in canonical_path),
            "path_count": len(paths),
        })
    results.sort(key=lambda result: (result["depth"], result["p_id"]))

    selected_ids = set(graph_paper_ids(root_p_id, traversal_rows, graph_limit))
    selected_ids.intersection_update(papers)
    selected_ids.intersection_update({result["p_id"] for result in results})
    selected_ids.add(root_p_id)
    node_depths = {root_p_id: 0}
    node_depths.update({
        result["p_id"]: result["depth"]
        for result in results
        if result["p_id"] in selected_ids
    })

    traversed_edges = set()
    for row in traversal_rows:
        paper_id = _paper_id(row["p_id"])
        if paper_id == root_p_id or paper_id not in selected_ids:
            continue
        path = _path_ids(row["path"])
        for first, second in zip(path, path[1:]):
            if first not in selected_ids or second not in selected_ids:
                continue
            if direction == "forward":
                traversed_edges.add((first, second))
            else:
                traversed_edges.add((second, first))

    actual_edges = {
        (_paper_id(row["citing_p_id"]), _paper_id(row["cited_p_id"]))
        for row in citation_rows
    }
    edges = sorted(traversed_edges.intersection(actual_edges))

    node_ids = sorted(selected_ids, key=lambda paper_id: (node_depths.get(paper_id, 0), paper_id))
    layer_indices = {}
    nodes = []
    for paper_id in node_ids:
        layer = node_depths.get(paper_id, 0)
        layer_index = layer_indices.get(layer, 0)
        layer_indices[layer] = layer_index + 1
        layer_size = sum(1 for value in node_depths.values() if value == layer)
        paper = papers[paper_id]
        title = str(paper.get("p_title") or "")
        short_title = title if len(title) <= 28 else title[:25].rstrip() + "..."
        year = paper.get("pub_year")
        x_depth = -layer if direction == "reverse" else layer
        nodes.append({
            "id": paper_id,
            "title": title,
            "year": year,
            "depth": layer,
            "label": (
                f"#{paper_id} · {escape(short_title)}\n"
                f"{year if year is not None else 'Year unknown'}"
            ),
            "x": x_depth,
            "y": layer_index - (layer_size - 1) / 2,
            "is_root": paper_id == root_p_id,
        })

    reachable_count = len(results)
    return {
        "root_p_id": root_p_id,
        "direction": direction,
        "nodes": nodes,
        "edges": [{"citing_p_id": source, "cited_p_id": target} for source, target in edges],
        "results": results,
        "reachable_count": reachable_count,
        "direct_connections": sum(result["depth"] == 1 for result in results),
        "max_depth": max((result["depth"] for result in results), default=0),
        "graph_truncated": reachable_count > len(selected_ids) - 1,
    }


def citation_figure(graph):
    import plotly.graph_objects as go

    positions = {node["id"]: (node["x"], node["y"]) for node in graph["nodes"]}
    figure = go.Figure()
    for edge in graph["edges"]:
        source = positions.get(edge["citing_p_id"])
        target = positions.get(edge["cited_p_id"])
        if source is None or target is None:
            continue
        figure.add_trace(go.Scatter(
            x=[source[0], target[0]],
            y=[source[1], target[1]],
            mode="lines",
            line={"color": "#94A3B8", "width": 1.5},
            hoverinfo="skip",
            showlegend=False,
        ))
        figure.add_annotation(
            x=target[0],
            y=target[1],
            ax=source[0],
            ay=source[1],
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            arrowhead=3,
            arrowsize=1,
            arrowwidth=1.5,
            arrowcolor="#64748B",
            standoff=18,
            startstandoff=18,
            showarrow=True,
        )

    for depth in sorted({node["depth"] for node in graph["nodes"]}):
        group = [node for node in graph["nodes"] if node["depth"] == depth]
        is_root = depth == 0
        figure.add_trace(go.Scatter(
            x=[node["x"] for node in group],
            y=[node["y"] for node in group],
            mode="markers+text",
            name="Selected paper" if is_root else f"Depth {depth}",
            text=[node["label"] for node in group],
            textposition="bottom center",
            textfont={"size": 10, "color": "#1E293B"},
            customdata=[
                [node["id"], escape(node["title"]), node["year"] or "Unknown"]
                for node in group
            ],
            hovertemplate=(
                "Paper #%{customdata[0]}<br>%{customdata[1]}"
                "<br>Year: %{customdata[2]}<extra></extra>"
            ),
            marker={
                "size": 34 if is_root else 25,
                "color": "#2563EB" if is_root else _DEPTH_COLORS[(depth - 1) % len(_DEPTH_COLORS)],
                "line": {"width": 2 if is_root else 1, "color": "#1D4ED8" if is_root else "#3B82F6"},
            },
        ))

    height = min(900, max(480, 340 + len(graph["nodes"]) * 5))
    figure.update_layout(
        height=height,
        margin={"l": 24, "r": 24, "t": 28, "b": 50},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#1E293B"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        xaxis={
            "visible": False,
            "showgrid": False,
            "zeroline": False,
            "title": "Traversal depth",
        },
        yaxis={"visible": False, "showgrid": False, "zeroline": False},
        hovermode="closest",
        dragmode="pan",
        showlegend=True,
    )
    return figure
