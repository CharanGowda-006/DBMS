import unittest

from app.citation_graph import (
    build_citation_graph,
    graph_paper_ids,
    validate_depth,
)


def paper(paper_id, title=None, year=2024):
    return {
        "p_id": paper_id,
        "p_title": title or f"Paper title {paper_id}",
        "pub_year": year,
    }


class CitationGraphTests(unittest.TestCase):
    def test_forward_paths_keep_citing_to_cited_edge_direction(self):
        traversal = [
            {"depth": 1, "p_id": 2, "path": ",1,2,"},
            {"depth": 2, "p_id": 3, "path": ",1,2,3,"},
        ]
        graph = build_citation_graph(
            1, traversal, [paper(1), paper(2), paper(3)],
            [{"citing_p_id": 1, "cited_p_id": 2}, {"citing_p_id": 2, "cited_p_id": 3}],
            "forward",
        )
        self.assertEqual(
            [(edge["citing_p_id"], edge["cited_p_id"]) for edge in graph["edges"]],
            [(1, 2), (2, 3)],
        )
        self.assertEqual([node["depth"] for node in graph["nodes"]], [0, 1, 2])

    def test_reverse_traversal_does_not_reverse_actual_citation_arrows(self):
        traversal = [
            {"depth": 1, "p_id": 2, "path": ",1,2,"},
            {"depth": 2, "p_id": 3, "path": ",1,2,3,"},
        ]
        graph = build_citation_graph(
            1, traversal, [paper(1), paper(2), paper(3)],
            [{"citing_p_id": 2, "cited_p_id": 1}, {"citing_p_id": 3, "cited_p_id": 2}],
            "reverse",
        )
        self.assertEqual(
            [(edge["citing_p_id"], edge["cited_p_id"]) for edge in graph["edges"]],
            [(2, 1), (3, 2)],
        )
        self.assertGreater(graph["nodes"][0]["x"], graph["nodes"][-1]["x"])

    def test_unique_results_use_minimum_depth_and_report_distinct_paths(self):
        traversal = [
            {"depth": 2, "p_id": 4, "path": ",1,2,4,"},
            {"depth": 2, "p_id": 4, "path": ",1,3,4,"},
            {"depth": 3, "p_id": 4, "path": ",1,2,3,4,"},
            {"depth": 2, "p_id": 4, "path": ",1,2,4,"},
            {"depth": 2, "p_id": 1, "path": ",1,2,1,"},
        ]
        graph = build_citation_graph(
            1, traversal, [paper(1), paper(2), paper(3), paper(4)],
            [
                {"citing_p_id": 1, "cited_p_id": 2},
                {"citing_p_id": 1, "cited_p_id": 3},
                {"citing_p_id": 2, "cited_p_id": 4},
                {"citing_p_id": 3, "cited_p_id": 4},
            ],
            "forward",
        )
        self.assertEqual(graph["reachable_count"], 1)
        self.assertEqual(graph["results"][0]["depth"], 2)
        self.assertEqual(graph["results"][0]["path_count"], 3)
        self.assertEqual(graph["results"][0]["path"], "Paper 1 → Paper 2 → Paper 4")
        self.assertEqual(graph["max_depth"], 2)
        self.assertEqual(graph["direct_connections"], 0)

    def test_only_real_edges_from_traversal_paths_are_included(self):
        graph = build_citation_graph(
            1,
            [
                {"depth": 1, "p_id": 2, "path": ",1,2,"},
                {"depth": 1, "p_id": 3, "path": ",1,3,"},
            ],
            [paper(1), paper(2), paper(3)],
            [
                {"citing_p_id": 1, "cited_p_id": 2},
                {"citing_p_id": 3, "cited_p_id": 1},
                {"citing_p_id": 2, "cited_p_id": 3},
            ],
            "forward",
        )
        self.assertEqual(graph["edges"], [{"citing_p_id": 1, "cited_p_id": 2}])

    def test_paths_through_unapproved_papers_are_excluded(self):
        graph = build_citation_graph(
            1,
            [{"depth": 2, "p_id": 3, "path": ",1,2,3,"}],
            [paper(1), paper(3)],
            [{"citing_p_id": 1, "cited_p_id": 2}, {"citing_p_id": 2, "cited_p_id": 3}],
            "forward",
        )
        self.assertEqual(graph["reachable_count"], 0)
        self.assertEqual([node["id"] for node in graph["nodes"]], [1])
        self.assertEqual(graph["edges"], [])

    def test_isolated_root_and_graph_limit(self):
        isolated = build_citation_graph(1, [], [paper(1)], [], "forward")
        self.assertEqual([node["id"] for node in isolated["nodes"]], [1])
        self.assertEqual(isolated["reachable_count"], 0)
        traversal = [
            {"depth": 1, "p_id": 2, "path": ",1,2,"},
            {"depth": 2, "p_id": 3, "path": ",1,2,3,"},
        ]
        self.assertEqual(graph_paper_ids(1, traversal, graph_limit=2), [1, 2])
        limited = build_citation_graph(
            1, traversal, [paper(1), paper(2), paper(3)], [], "forward", graph_limit=2
        )
        self.assertTrue(limited["graph_truncated"])
        self.assertEqual({node["id"] for node in limited["nodes"]}, {1, 2})

    def test_invalid_direction_and_mismatched_paths_are_rejected(self):
        with self.assertRaises(ValueError):
            build_citation_graph(1, [], [paper(1)], [], "sideways")
        with self.assertRaises(ValueError):
            build_citation_graph(
                1, [{"depth": 1, "p_id": 2, "path": ",9,2,"}],
                [paper(1), paper(2)], [], "forward",
            )

    def test_depth_limit_is_enforced(self):
        self.assertEqual(validate_depth(1), 1)
        self.assertEqual(validate_depth(5), 5)
        for invalid_depth in (0, 6, True, "3"):
            with self.subTest(depth=invalid_depth):
                with self.assertRaises(ValueError):
                    validate_depth(invalid_depth)


if __name__ == "__main__":
    unittest.main()
