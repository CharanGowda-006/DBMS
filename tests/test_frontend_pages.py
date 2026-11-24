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
import ui
from paper_ingestion import ui as ingestion_ui
from tests.test_paper_ingestion import _pdf_with_text


class FrontendPageTests(unittest.TestCase):
    def test_removing_author_clears_state_for_shifted_authors(self):
        state = {
            "smart_import_authors": [
                {"name": name} for name in ("Alice", "Bob", "Carol", "Dana")
            ],
            "smart_import_author_1_name": "Bob",
            "smart_import_author_2_name": "Carol",
            "smart_import_author_3_name": "Dana",
            "smart_import_title": "Keep unrelated state",
        }

        with patch.object(ingestion_ui.st, "session_state", state):
            ingestion_ui._reset_author_state(1)

        self.assertEqual(
            [author["name"] for author in state["smart_import_authors"]],
            ["Alice", "Carol", "Dana"],
        )
        self.assertNotIn("smart_import_author_2_name", state)
        self.assertEqual(state["smart_import_title"], "Keep unrelated state")

    def test_shared_styles_do_not_override_streamlit_icon_fonts(self):
        with patch.object(ui.st, "markdown") as markdown:
            ui.install_styles()

        styles = markdown.call_args.args[0]
        self.assertIn('html, body {', styles)
        self.assertNotIn('[class*="st-"]', styles)
        self.assertNotIn("material-symbols-rounded", styles)
        self.assertNotIn("font-size: 0", styles)

    def test_login_password_visibility_preserves_input(self):
        email = "Person@Example.Org "
        password = "CaseSensitive Test 42 "
        with patch.object(auth, "login_user", return_value=False) as login, patch.object(
            st, "page_link"
        ):
            app = AppTest.from_file(str(ROOT / "app" / "pages" / "0_Login.py")).run()
            app.text_input[0].set_value(email)
            app.text_input[1].set_value(password)
            app.checkbox[0].check().run()

            self.assertTrue(app.text_input[0].value == email, "Email changed on checkbox rerun.")
            self.assertTrue(app.text_input[1].value == password, "Password changed on checkbox rerun.")
            app.button[0].click().run()

        self.assertFalse(app.exception, [str(error.value) for error in app.exception])
        self.assertEqual(login.call_count, 1, "Login service should be called once.")
        self.assertTrue(
            login.call_args.args == (email, password),
            "Login form changed credentials before calling the auth service.",
        )

    def test_registration_password_visibility_preserves_inputs(self):
        with patch.object(auth, "register_user") as register, patch.object(
            st, "page_link"
        ):
            app = AppTest.from_file(str(ROOT / "app" / "pages" / "0_Register.py")).run()
            app.text_input[0].set_value("Researcher Name")
            app.text_input[1].set_value("person@example.org")
            app.text_input[2].set_value("a sufficiently long password")
            app.text_input[3].set_value("a sufficiently long password")
            app.checkbox[0].check().run()

            self.assertEqual(app.text_input[0].value, "Researcher Name")
            self.assertEqual(app.text_input[2].value, "a sufficiently long password")
            app.button[0].click().run()

        self.assertFalse(app.exception, [str(error.value) for error in app.exception])
        register.assert_called_once_with(
            "Researcher Name",
            "person@example.org",
            "a sufficiently long password",
        )

    def test_dashboard_uses_live_metrics_and_recent_publications(self):
        user = {"full_name": "Student One", "role": "STUDENT"}

        def query(sql, params=None):
            if "UNION ALL SELECT 'RESEARCHERS'" in sql:
                return pd.DataFrame([
                    {"metric": "APPROVED_PUBLICATIONS", "value": 8},
                    {"metric": "RESEARCHERS", "value": 6},
                    {"metric": "PROJECTS", "value": 3},
                    {"metric": "CONFERENCES", "value": 2},
                ])
            if "GROUP_CONCAT(r.r_name" in sql:
                return pd.DataFrame([{
                    "p_id": 1,
                    "p_title": "Approved Paper",
                    "pub_year": 2024,
                    "authors": "Researcher One",
                    "topics": "Computer Vision",
                }])
            if "UNION ALL" in sql and "table_name" in sql:
                return pd.DataFrame([
                    {"table_name": "PAPER", "row_count": 8},
                    {"table_name": "AUTHORS", "row_count": 10},
                ])
            raise AssertionError(f"Unexpected dashboard query: {sql}")

        with patch.object(auth, "require_login", return_value=user), patch.object(
            db, "query", side_effect=query
        ), patch.object(st, "page_link") as page_link:
            app = AppTest.from_file(str(ROOT / "app" / "pages" / "0_Dashboard.py")).run()

        self.assertFalse(app.exception, [str(error.value) for error in app.exception])
        self.assertTrue(any("Welcome back, Student One" in item.value for item in app.title))
        self.assertTrue(any("Approved Paper" in item.value for item in app.markdown))
        self.assertEqual([call.kwargs["label"] for call in page_link.call_args_list], [
            "Explore Publications", "Find Collaborators",
            "Explore Citations", "Browse Projects",
        ])

    def test_add_paper_starts_with_smart_pdf_import_not_blank_manual_form(self):
        user = {"user_id": 7, "role": "TEACHER"}

        def query(sql, params=None):
            if "FROM PAPER p" in sql and "PAPER_WORKFLOW" in sql:
                return pd.DataFrame(columns=["p_id", "p_title", "pub_year"])
            if "PAPER_OWNERSHIP" in sql:
                return pd.DataFrame(columns=["p_id", "p_title", "pub_year"])
            if "FROM CITES c" in sql:
                return pd.DataFrame(columns=[
                    "Citing ID", "Citing Paper", "Cited ID", "Cited Paper",
                ])
            raise AssertionError(f"Unexpected citation-tab query: {sql}")

        with patch.object(auth, "require_role", return_value=user), patch.object(
            db, "query", side_effect=query
        ):
            app = AppTest.from_file(str(ROOT / "app" / "pages" / "7_Add_Paper.py")).run()

        self.assertFalse(app.exception, [str(error.value) for error in app.exception])
        self.assertTrue(any("Smart Paper Import" in item.value for item in app.subheader))
        self.assertTrue(any("Upload research paper (PDF)" in item.label for item in app.file_uploader))
        self.assertFalse(any("Paper title *" in item.label for item in app.text_input))

    def test_smart_import_extracts_and_preserves_editable_values(self):
        user = {"user_id": 7, "role": "TEACHER"}
        pdf = _pdf_with_text([
            "A Study of Research Networks",
            "Alice Smith, Bob Jones",
            "alice@example.org",
            "ABSTRACT",
            "We study computer vision and research networks.",
            "Index Terms: research networks, computer vision, relational databases.",
            "1 Introduction",
            "The paper body.",
            "2024 IEEE Research Conference",
        ])

        def query(sql, params=None):
            if "FROM PAPER p" in sql and "PAPER_WORKFLOW" in sql:
                return pd.DataFrame(columns=["p_id", "p_title", "pub_year"])
            if "PAPER_OWNERSHIP" in sql:
                return pd.DataFrame(columns=["p_id", "p_title", "pub_year"])
            if "FROM CITES c" in sql:
                return pd.DataFrame(columns=[
                    "Citing ID", "Citing Paper", "Cited ID", "Cited Paper",
                ])
            raise AssertionError(f"Unexpected citation-tab query: {sql}")

        db_records = (
            [],
            [{
                "r_id": 2, "r_name": "Alice Smith", "email": "alice@example.org",
                "institution": "Example University",
            }],
            [{"t_id": 3, "t_name": "Computer Vision"}],
            [{"key_id": 4, "keyword": "research networks"}],
            [],
        )
        with patch.object(auth, "require_role", return_value=user), patch.object(
            db, "query", side_effect=query
        ), patch.object(
            ingestion_ui, "_load_database_records", return_value=db_records
        ):
            app = AppTest.from_file(str(ROOT / "app" / "pages" / "7_Add_Paper.py")).run()
            app.file_uploader[0].set_value(
                ("research.pdf", pdf, "application/pdf")
            ).run()
            next(
                button for button in app.button if button.label == "Extract Information"
            ).click().run()

            research_topics = next(
                item for item in app.multiselect if "Existing research topics" in item.label
            )
            self.assertEqual(research_topics.value, ["Computer Vision"])
            self.assertTrue(any(
                "Preselected existing topics" in item.value
                for item in app.caption
            ))
            database_topic_approval = next(
                item for item in app.checkbox
                if item.label == "Approve new topic: Database Management Systems"
            )
            self.assertFalse(database_topic_approval.value)
            database_topic_approval.check().run()
            self.assertEqual(
                app.session_state["smart_import_approved_new_topics"],
                ["Database Management Systems"],
            )

            title = next(item for item in app.text_input if item.label == "Paper title *")
            self.assertEqual(title.value, "A Study of Research Networks")
            title.set_value("Corrected Research Networks Paper")
            author_emails = [
                item for item in app.text_input
                if item.label == "Verified email (required for a new researcher)"
            ]
            author_emails[1].set_value("bob@example.org")
            next(
                button for button in app.button
                if button.label == "Continue to final review"
            ).click().run()

        self.assertFalse(app.exception, [str(error.value) for error in app.exception])
        self.assertTrue(
            any("Final review" in item.value for item in app.markdown),
            [item.value for item in app.error],
        )
        self.assertEqual(
            app.session_state["smart_import_title"],
            "Corrected Research Networks Paper",
        )


if __name__ == "__main__":
    unittest.main()
