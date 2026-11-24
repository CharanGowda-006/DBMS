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


class FrontendPageTests(unittest.TestCase):
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

    def test_add_paper_guided_steps_keep_draft_title(self):
        user = {"user_id": 7, "role": "TEACHER"}
        researcher = pd.DataFrame([{
            "r_id": 2, "r_name": "Researcher Two",
            "email": "researcher@example.org", "institution": "Institute",
        }])
        topic = pd.DataFrame([{"t_id": 3, "t_name": "Research Topic"}])
        keyword = pd.DataFrame([{"key_id": 4, "keyword": "Keyword"}])

        def query(sql, params=None):
            if "SELECT c_id, c_name, c_year" in sql:
                return pd.DataFrame(columns=["c_id", "c_name", "c_year"])
            if "SELECT r_id, r_name, email, institution" in sql:
                return researcher
            if "SELECT t_id, t_name" in sql:
                return topic
            if "SELECT key_id, keyword" in sql:
                return keyword
            if "SELECT researcher_id FROM APP_USER" in sql:
                return pd.DataFrame([{"researcher_id": None}])
            if "PAPER_OWNERSHIP" in sql:
                return pd.DataFrame(columns=["p_id", "p_title", "pub_year"])
            if "SELECT p.p_id, p.p_title, p.pub_year" in sql:
                return pd.DataFrame(columns=["p_id", "p_title", "pub_year"])
            if "FROM CITES c" in sql:
                return pd.DataFrame(columns=["Citing ID", "Citing Paper", "Cited ID", "Cited Paper"])
            raise AssertionError(f"Unexpected paper page query: {sql}")

        with patch.object(auth, "require_role", return_value=user), patch.object(
            db, "query", side_effect=query
        ):
            app = AppTest.from_file(str(ROOT / "app" / "pages" / "7_Add_Paper.py")).run()
            app.text_input[0].set_value("Draft title")
            continue_button = next(button for button in app.button if button.label == "Continue")
            continue_button.click().run()

        self.assertFalse(app.exception, [str(error.value) for error in app.exception])
        self.assertTrue(any("Authors" in item.value for item in app.subheader))
        self.assertEqual(app.session_state["add_paper_draft_title"], "Draft title")
        self.assertEqual(app.session_state["add_paper_step"], 1)


if __name__ == "__main__":
    unittest.main()
