import unittest

from app.insights import (
    collaboration_figure,
    collaboration_metrics,
    compare_sets,
    filter_collaborations,
    filter_similar_papers,
    similarity_metrics,
)


def collaboration(r1_id, r2_id, names, count, coauthored=0, topics="AI, Vision"):
    return {
        "r1_id": r1_id,
        "r1_name": names[0],
        "r1_institution": f"Institute {r1_id}",
        "r2_id": r2_id,
        "r2_name": names[1],
        "r2_institution": f"Institute {r2_id}",
        "shared_topic_count": count,
        "shared_topics": topics,
        "already_coauthored": coauthored,
    }


def similarity(p1, p2, score, band="Moderate potential overlap", topics=0.5, keywords=0.5):
    return {
        "p1_id": p1,
        "p1_title": f"Paper {p1}",
        "p1_year": 2021 + p1,
        "p2_id": p2,
        "p2_title": f"Paper {p2}",
        "p2_year": 2021 + p2,
        "topic_jaccard": topics,
        "keyword_jaccard": keywords,
        "similarity_score": score,
        "overlap_band": band,
        "shared_topics": "AI",
        "shared_keywords": "model",
    }


class CollaborationInsightsTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            collaboration(1, 2, ("Alice", "Bob"), 3, 1),
            collaboration(1, 3, ("Alice", "Cara"), 2, 0),
            collaboration(2, 3, ("Bob", "Cara"), 5, 0),
            collaboration(1, 3, ("Alice", "Cara"), 2, 0),
        ]

    def test_selected_researcher_matches_either_pair_position_and_ranks_new_first(self):
        rows = filter_collaborations(self.rows, researcher_id=2)
        self.assertEqual([(row["r1_id"], row["r2_id"]) for row in rows], [(2, 3), (1, 2)])
        self.assertEqual(collaboration_metrics(rows), {"total": 2, "new": 1, "existing": 1})

    def test_status_filter_and_duplicate_pair_removal(self):
        rows = filter_collaborations(self.rows, researcher_id=1, status_filter=0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["shared_topic_count"], 2)

    def test_graph_uses_unique_actual_pairs_and_selects_researcher_node(self):
        rows = filter_collaborations(self.rows, researcher_id=1)
        figure, node_count, edge_count, truncated = collaboration_figure(
            rows, selected_researcher_id=1
        )
        self.assertEqual(node_count, 3)
        self.assertEqual(edge_count, 2)
        self.assertFalse(truncated)
        node_trace = figure.data[-1]
        self.assertEqual(set(node_trace.text), {"Alice", "Bob", "Cara"})
        self.assertEqual(node_trace.marker.size[0], 28)
        self.assertEqual({trace.name for trace in figure.data if trace.showlegend}, {
            "Already co-authored",
            "Potential opportunity",
        })


class SimilarityInsightsTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            similarity(1, 2, 0.76, "High potential overlap", 1.0, 0.6),
            similarity(3, 1, 0.50, "Moderate potential overlap", 0.5, 0.5),
            similarity(1, 4, 0.25, "Low potential overlap", 0.25, 0.25),
            similarity(1, 2, 0.76, "High potential overlap", 1.0, 0.6),
            similarity(5, 6, 0.90, "High potential overlap", 1.0, 0.8333),
        ]

    def test_selected_paper_matches_either_pair_position_and_orders_by_score(self):
        results = filter_similar_papers(self.rows, selected_paper_id=1)
        self.assertEqual([row["other_p_id"] for row in results], [2, 3, 4])
        self.assertEqual(results[1]["other_title"], "Paper 3")
        self.assertEqual(results[1]["other_year"], 2024)

    def test_minimum_score_and_overlap_filter_update_consistent_metrics(self):
        results = filter_similar_papers(
            self.rows,
            selected_paper_id=1,
            minimum_score=0.3,
            bands=["High potential overlap", "Moderate potential overlap"],
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(
            similarity_metrics(results),
            {"total": 2, "high": 1, "moderate": 1, "low": 0},
        )

    def test_score_precision_and_pair_deduplication(self):
        results = filter_similar_papers(self.rows, selected_paper_id=1)
        self.assertEqual(len(results), 3)
        self.assertAlmostEqual(results[0]["similarity_score"], 0.76)
        self.assertAlmostEqual(results[0]["topic_jaccard"], 1.0)
        self.assertAlmostEqual(results[0]["keyword_jaccard"], 0.6)

    def test_comparison_set_differences(self):
        self.assertEqual(
            compare_sets(["AI", "Vision"], ["Vision", "Robotics"]),
            {
                "shared": ["Vision"],
                "only_a": ["AI"],
                "only_b": ["Robotics"],
            },
        )


if __name__ == "__main__":
    unittest.main()
