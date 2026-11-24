import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import auth
import db


class CitationPageTests(unittest.TestCase):
    def setUp(self):
        self.approved = pd.DataFrame([
            {"p_id": 1, "p_title": "Root paper", "pub_year": 2024},
            {"p_id": 2, "p_title": "Cited paper", "pub_year": 2023},
        ])
        self.metadata = pd.DataFrame([
            {
                "p_id": 1, "p_title": "Root paper", "abstract": "Root abstract",
                "pub_year": 2024, "c_id": None, "c_name": None,
                "c_year": None, "c_location": None,
            },
            {
                "p_id": 2, "p_title": "Cited paper", "abstract": "Cited abstract",
                "pub_year": 2023, "c_id": None, "c_name": None,
                "c_year": None, "c_location": None,
            },
        ])

    def _query(self, sql, params=None):
        if "SELECT p.p_id, p.p_title, p.pub_year" in sql:
            return self.approved
        if "SELECT p.p_id, p.p_title, p.abstract" in sql:
            return self.metadata
        if "FROM CITES c" in sql:
            return pd.DataFrame([{"citing_p_id": 1, "cited_p_id": 2}])
        return pd.DataFrame()

    def test_controls_load_only_approved_papers(self):
        with patch.object(auth, "require_login"), patch.object(
            db, "query", return_value=self.approved
        ) as query:
            app = AppTest.from_file(str(ROOT / "app" / "pages" / "4_Citations.py")).run()

        self.assertFalse(app.exception)
        options = list(app.selectbox[0].options)
        self.assertEqual(len(options), 2)
        self.assertTrue(any("Root paper" in option for option in options))
        self.assertTrue(any("Cited paper" in option for option in options))
        statement = query.call_args.args[0]
        self.assertIn("COALESCE(w.status, 'APPROVED') = 'APPROVED'", statement)

    def test_exploration_renders_directed_graph_and_approved_details(self):
        traversal = pd.DataFrame([
            {"depth": 1, "p_id": 2, "p_title": "Cited paper", "path": ",1,2,"},
        ])
        with patch.object(auth, "require_login"), patch.object(
            db, "query", side_effect=self._query
        ) as query, patch.object(db, "call_proc", return_value=traversal) as call_proc:
            app = AppTest.from_file(str(ROOT / "app" / "pages" / "4_Citations.py")).run()
            app.button[0].click().run()

        self.assertFalse(app.exception, [str(error.value) for error in app.exception])
        call_proc.assert_called_once_with("sp_citations", (1, "forward", 3))
        statements = [call.args[0] for call in query.call_args_list]
        self.assertTrue(any("FROM CITES c" in statement for statement in statements))
        for statement in statements:
            if any(table in statement for table in (
                "FROM PAPER", "FROM CITES", "FROM AUTHORS",
                "FROM HAS_TOPIC", "FROM HAS_KEYWORD",
            )):
                self.assertIn("COALESCE(", statement)
        headings = [element.value for element in app.markdown]
        for heading in (
            "### Citation Network",
            "### Citation Summary",
            "### Detailed Citation Results",
            "### Publication Details",
        ):
            self.assertIn(heading, headings)

    def test_empty_traversal_shows_root_graph_and_empty_state(self):
        with patch.object(auth, "require_login"), patch.object(
            db, "query", side_effect=self._query
        ), patch.object(db, "call_proc", return_value=pd.DataFrame()):
            app = AppTest.from_file(str(ROOT / "app" / "pages" / "4_Citations.py")).run()
            app.button[0].click().run()

        self.assertFalse(app.exception, [str(error.value) for error in app.exception])
        self.assertTrue(any("No citations found" in item.value for item in app.info))
        self.assertIn("### Citation Network", [element.value for element in app.markdown])


if __name__ == "__main__":
    unittest.main()
