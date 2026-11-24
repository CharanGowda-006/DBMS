import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import auth
import db


class InsightsPageTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()

    def _query(self, sql, params=None):
        if "FROM RESEARCHER" in sql and "v_collaborators" not in sql:
            return pd.DataFrame([
                {"r_id": 1, "r_name": "Alice", "institution": "Institute A"},
                {"r_id": 2, "r_name": "Bob", "institution": "Institute B"},
            ])
        if "FROM v_collaborators" in sql:
            return pd.DataFrame([{
                "r1_id": 1, "r1_name": "Alice", "r1_institution": "Institute A",
                "r2_id": 2, "r2_name": "Bob", "r2_institution": "Institute B",
                "shared_topic_count": 2, "shared_topics": "AI, Vision",
                "already_coauthored": 0,
            }])
        if "SELECT p.p_id, p.p_title, p.pub_year" in sql:
            return pd.DataFrame([
                {"p_id": 1, "p_title": "Paper One", "pub_year": 2024},
                {"p_id": 2, "p_title": "Paper Two", "pub_year": 2023},
            ])
        if "FROM v_paper_similarity" in sql:
            return pd.DataFrame([{
                "p1_id": 1, "p1_title": "Paper One", "p1_year": 2024,
                "p2_id": 2, "p2_title": "Paper Two", "p2_year": 2023,
                "topic_jaccard": 1.0, "keyword_jaccard": 0.6,
                "similarity_score": 0.76,
                "overlap_band": "High potential overlap",
                "shared_topics": "AI", "shared_keywords": "model",
            }])
        if "WHERE p.p_id IN" in sql:
            if "FROM PAPER p" in sql:
                return pd.DataFrame([
                    {"p_id": 1, "p_title": "Paper One", "pub_year": 2024},
                    {"p_id": 2, "p_title": "Paper Two", "pub_year": 2023},
                ])
            return pd.DataFrame()
        return pd.DataFrame()

    def test_both_discovery_tabs_render(self):
        with patch.object(auth, "require_login"), patch.object(
            db, "query", return_value=pd.DataFrame()
        ):
            app = AppTest.from_file(str(ROOT / "app" / "pages" / "3_Insights.py")).run()

        self.assertFalse(app.exception, [str(error.value) for error in app.exception])
        self.assertEqual([tab.label for tab in app.tabs], [
            "Collaborator Discovery",
            "Publication Similarity",
        ])

    def test_selected_paper_shows_candidate_and_comparison(self):
        with patch.object(auth, "require_login"), patch.object(
            db, "query", side_effect=self._query
        ) as query:
            app = AppTest.from_file(str(ROOT / "app" / "pages" / "3_Insights.py")).run()
            app.selectbox[1].select(1).run()

        self.assertFalse(app.exception, [str(error.value) for error in app.exception])
        self.assertTrue(any("Paper Two" in item.value for item in app.text))
        statements = [call.args[0] for call in query.call_args_list]
        researcher_statement = next(
            statement for statement in statements if "FROM RESEARCHER r" in statement
        )
        self.assertIn("COALESCE(w.status, 'APPROVED') = 'APPROVED'", researcher_statement)
        similarity_call = next(
            call for call in query.call_args_list
            if "FROM v_paper_similarity" in call.args[0]
        )
        similarity_statement = similarity_call.args[0]
        self.assertIn("s.p1_id = %s OR s.p2_id = %s", similarity_statement)
        self.assertIn("COALESCE(w1.status, 'APPROVED') = 'APPROVED'", similarity_statement)
        self.assertIn("COALESCE(w2.status, 'APPROVED') = 'APPROVED'", similarity_statement)
        self.assertEqual(similarity_call.args[1], (1, 1, 1))
        self.assertTrue(any("Compare selected paper with" == item.label for item in app.selectbox))


if __name__ == "__main__":
    unittest.main()
