import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import mysql.connector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import auth
import db
import workflow
import paper_form


class FakeCursor:
    def __init__(self, fail_on=None, workflow_status="PENDING", owned_record=None):
        self.fail_on = fail_on
        self.workflow_status = workflow_status
        self.owned_record = owned_record
        self.statements = []
        self.lastrowid = 41
        self.rowcount = 1
        self._result = None

    def execute(self, statement, params=None):
        self.statements.append((statement, params))
        if self.fail_on and self.fail_on in statement:
            raise RuntimeError("simulated database failure")
        if (
            "SELECT status FROM PAPER_WORKFLOW" in statement
            or "SELECT w.status FROM PAPER_OWNERSHIP" in statement
        ):
            self._result = (
                {"status": self.workflow_status}
                if self.workflow_status is not None else None
            )
        elif "FROM PAPER_OWNERSHIP o JOIN PAPER p" in statement:
            self._result = self.owned_record
        elif "SELECT p_id FROM PAPER WHERE" in statement:
            self._result = {"p_id": 41}
        elif "SELECT project_id FROM PROJECT WHERE project_id" in statement:
            self._result = {"project_id": 22}
        elif "SELECT 1 FROM PROJECT_OWNERSHIP" in statement:
            self._result = None
        else:
            self._result = None

    def fetchone(self):
        result = self._result
        self._result = None
        return result

    def fetchall(self):
        return []


class EntityCursor(FakeCursor):
    def __init__(self, fail_on=None, workflow_status="PENDING", owned_record=None, entities=None):
        super().__init__(fail_on, workflow_status, owned_record)
        self.entities = entities or {"RESEARCHER": [], "TOPIC": [], "KEYWORD": []}
        self.next_ids = {"RESEARCHER": 101, "TOPIC": 201, "KEYWORD": 301}

    def execute(self, statement, params=None):
        super().execute(statement, params)
        upper = statement.upper()
        if "LOWER(TRIM(EMAIL))" in upper:
            email = params[0]
            row = next(
                (item for item in self.entities["RESEARCHER"]
                 if item["email"].strip().lower() == email),
                None,
            )
            self._result = {"r_id": row["r_id"]} if row else None
        elif "LOWER(TRIM(T_NAME))" in upper:
            name = params[0]
            row = next(
                (item for item in self.entities["TOPIC"]
                 if item["t_name"].strip().lower() == name),
                None,
            )
            self._result = {"t_id": row["t_id"]} if row else None
        elif "LOWER(TRIM(KEYWORD))" in upper:
            name = params[0]
            row = next(
                (item for item in self.entities["KEYWORD"]
                 if item["keyword"].strip().lower() == name),
                None,
            )
            self._result = {"key_id": row["key_id"]} if row else None
        elif upper.startswith("INSERT INTO RESEARCHER"):
            self.lastrowid = self.next_ids["RESEARCHER"]
            self.next_ids["RESEARCHER"] += 1
            self.entities["RESEARCHER"].append({
                "r_id": self.lastrowid, "r_name": params[0],
                "email": params[1], "institution": params[2],
            })
        elif upper.startswith("INSERT INTO TOPIC"):
            self.lastrowid = self.next_ids["TOPIC"]
            self.next_ids["TOPIC"] += 1
            self.entities["TOPIC"].append({"t_id": self.lastrowid, "t_name": params[0]})
        elif upper.startswith("INSERT INTO KEYWORD"):
            self.lastrowid = self.next_ids["KEYWORD"]
            self.next_ids["KEYWORD"] += 1
            self.entities["KEYWORD"].append({"key_id": self.lastrowid, "keyword": params[0]})
        elif upper.startswith("INSERT INTO PAPER "):
            self.lastrowid = 41


class ConcurrentDuplicateCursor(EntityCursor):
    def __init__(self):
        super().__init__()
        self.raced = False

    def execute(self, statement, params=None):
        if statement.upper().startswith("INSERT INTO RESEARCHER") and not self.raced:
            super().execute(statement, params)
            self.raced = True
            raise mysql.connector.IntegrityError(msg="duplicate", errno=1062)
        super().execute(statement, params)


class ProjectCursor(FakeCursor):
    def __init__(
        self, fail_on=None, owned=True, project_name=None,
        existing_researcher=None, existing_researcher_email=None,
        existing_dataset=None, existing_dataset_match=None, assigned=False, linked=False,
    ):
        super().__init__(fail_on)
        self.owned = owned
        self.project_name = project_name
        self.existing_researcher = existing_researcher
        self.existing_researcher_email = existing_researcher_email
        self.existing_dataset = existing_dataset
        self.existing_dataset_match = existing_dataset_match
        self.assigned = assigned
        self.linked = linked
        self.project_row = {"name": "Project", "description": "Description"}
        self.lastrowid = 88

    def execute(self, statement, params=None):
        super().execute(statement, params)
        upper = " ".join(statement.upper().split())
        if "SELECT PROJECT_ID FROM PROJECT WHERE LOWER(TRIM(NAME))" in upper:
            self._result = (
                {"project_id": 99}
                if self.project_name and self.project_name == params[0]
                else None
            )
        elif "SELECT PROJECT_ID FROM PROJECT WHERE PROJECT_ID" in upper:
            self._result = {"project_id": params[0]}
        elif "FROM PROJECT_OWNERSHIP" in upper:
            self._result = {"project_id": params[0]} if self.owned else None
        elif "SELECT NAME, DESCRIPTION FROM PROJECT WHERE PROJECT_ID" in upper:
            self._result = self.project_row
        elif "SELECT R_ID FROM RESEARCHER WHERE R_ID" in upper:
            self._result = {"r_id": params[0]}
        elif "SELECT R_ID FROM RESEARCHER" in upper and "LOWER(TRIM(EMAIL))" in upper:
            self._result = (
                {"r_id": self.existing_researcher_email}
                if self.existing_researcher_email is not None else None
            )
        elif "SELECT 1 FROM WORKS_ON" in upper:
            self._result = {"one": 1} if self.assigned else None
        elif "SELECT DATASET_ID FROM DATASET WHERE DATASET_ID" in upper:
            self._result = {"dataset_id": params[0]}
        elif "SELECT 1 FROM USES" in upper:
            self._result = {"one": 1} if self.linked else None
        elif "SELECT DATASET_ID FROM DATASET" in upper and "LOWER(TRIM(NAME))" in upper:
            self._result = (
                {"dataset_id": self.existing_dataset_match}
                if self.existing_dataset_match is not None else None
            )


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def start_transaction(self):
        pass

    def cursor(self, dictionary=False):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class AuthenticationTests(unittest.TestCase):
    def test_password_hash_is_argon2id_and_not_plaintext(self):
        password = "correct horse battery staple"
        hashed = auth._password_hasher.hash(password)
        self.assertNotEqual(hashed, password)
        self.assertTrue(hashed.startswith("$argon2id$"))
        self.assertTrue(auth._password_hasher.verify(hashed, password))

    def test_login_returns_safe_user_for_valid_password(self):
        account = {
            "user_id": 7,
            "full_name": "Researcher",
            "email": "researcher@example.org",
            "password_hash": auth._password_hasher.hash("correct horse battery staple"),
            "role": "STUDENT",
            "is_active": True,
        }
        with patch.object(auth.db, "query", return_value=pd.DataFrame([account])):
            user = auth.authenticate_user("Researcher@example.org", "correct horse battery staple")
        self.assertEqual(user["role"], "STUDENT")
        self.assertNotIn("password_hash", user)

    def test_invalid_password_and_deactivated_account_fail_generically(self):
        account = {
            "user_id": 7,
            "full_name": "Researcher",
            "email": "researcher@example.org",
            "password_hash": auth._password_hasher.hash("correct horse battery staple"),
            "role": "STUDENT",
            "is_active": True,
        }
        with patch.object(auth.db, "query", return_value=pd.DataFrame([account])):
            self.assertIsNone(auth.authenticate_user(account["email"], "wrong password"))
        account["is_active"] = False
        with patch.object(auth.db, "query", return_value=pd.DataFrame([account])):
            self.assertIsNone(
                auth.authenticate_user(account["email"], "correct horse battery staple")
            )

    def test_duplicate_email_registration_is_rejected_by_database(self):
        error = RuntimeError("duplicate email")
        with patch.object(auth.db, "transaction", side_effect=error):
            with self.assertRaises(RuntimeError):
                auth.register_user("Student", "student@example.org", "a long enough password")

    def test_public_registration_hashes_password_and_sets_student_role(self):
        cursor = FakeCursor()
        with patch.object(auth.db, "transaction", side_effect=lambda operation: operation(cursor)):
            self.assertEqual(
                auth.register_user("Student", "STUDENT@example.org", "a long enough password"),
                41,
            )
        insert, values = cursor.statements[0]
        self.assertIn("'STUDENT'", insert)
        self.assertEqual(values[1], "student@example.org")
        self.assertNotEqual(values[2], "a long enough password")
        self.assertTrue(values[2].startswith("$argon2id$"))
        self.assertEqual(cursor.statements[1][1][1], "USER_REGISTERED")

    def test_expired_session_is_cleared(self):
        state = {"auth_user_id": 7, "auth_started_at": 1}
        with patch.object(auth.db, "query") as query:
            self.assertIsNone(auth.get_current_user(state))
        self.assertEqual(state, {})
        query.assert_not_called()

    def test_login_and_logout_update_only_server_session_identifiers(self):
        state = {}
        user = {
            "user_id": 12,
            "full_name": "Student",
            "email": "student@example.org",
            "role": "STUDENT",
        }
        with patch.object(auth, "authenticate_user", return_value=user):
            self.assertTrue(auth.login_user(user["email"], "secret", state))
        self.assertEqual(state["auth_user_id"], 12)
        self.assertNotIn("role", state)
        auth.logout_user(state)
        self.assertEqual(state, {})

    def test_logout_blocks_direct_protected_actor_lookup(self):
        with patch.object(auth, "st", SimpleNamespace(session_state={})):
            with self.assertRaises(auth.AuthorizationError):
                auth.require_actor(FakeCursor(), {"ADMIN"})


class WorkflowTests(unittest.TestCase):
    def run_transaction(self, cursor, operation):
        connection = FakeConnection(cursor)
        with patch.object(db, "get_connection", return_value=connection):
            with self._capture_connection(connection):
                result = operation()
        return result, connection, cursor

    class _capture_connection:
        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            return self.connection

        def __exit__(self, exc_type, exc_value, traceback):
            self.connection.close()

    def test_teacher_submission_is_pending_and_atomic(self):
        cursor = FakeCursor()
        with patch.object(
            auth, "require_actor",
            return_value={"user_id": 9, "role": "TEACHER"},
        ):
            result, connection, cursor = self.run_transaction(
                cursor,
                lambda: workflow.submit_paper(
                    "Title", "Abstract", 2025, None, [1], [2], [3]
                ),
            )
        self.assertEqual(result, (41, "PENDING"))
        self.assertTrue(connection.committed)
        self.assertFalse(connection.rolled_back)
        workflow_insert = next(
            values for statement, values in cursor.statements
            if "INSERT INTO PAPER_WORKFLOW" in statement
        )
        self.assertEqual(workflow_insert[1], "PENDING")
        self.assertTrue(any("INSERT INTO PAPER_OWNERSHIP" in sql for sql, _ in cursor.statements))
        self.assertTrue(any("INSERT INTO AUDIT_LOG" in sql for sql, _ in cursor.statements))

    def test_submit_resolves_mixed_existing_and_new_entities_in_author_order(self):
        cursor = EntityCursor()
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            result, connection, _ = self.run_transaction(
                cursor,
                lambda: workflow.submit_paper(
                    "Title", "Abstract", 2025, None,
                    [
                        7,
                        7,
                        {"new": {"name": "New Researcher One", "email": "ONE@example.org"}},
                        {"new": {"name": "New Researcher Two", "email": "two@example.org"}},
                    ],
                    [12, {"new": "Federated Learning"}, {"new": "FEDERATED LEARNING"}],
                    [4, {"new": "Differential Privacy"}, {"new": "DIFFERENTIAL PRIVACY"}],
                ),
            )
        self.assertEqual(result, (41, "PENDING"))
        self.assertTrue(connection.committed)
        author_rows = [
            params for statement, params in cursor.statements if "INSERT INTO AUTHORS" in statement
        ]
        self.assertEqual(author_rows, [(7, 41, 1), (101, 41, 2), (102, 41, 3)])
        topic_rows = [
            params for statement, params in cursor.statements if "INSERT INTO HAS_TOPIC" in statement
        ]
        keyword_rows = [
            params for statement, params in cursor.statements
            if "INSERT INTO HAS_KEYWORD" in statement
        ]
        self.assertEqual(topic_rows, [(41, 12), (41, 201)])
        self.assertEqual(keyword_rows, [(41, 4), (41, 301)])
        self.assertEqual(len(cursor.entities["TOPIC"]), 1)
        self.assertEqual(len(cursor.entities["KEYWORD"]), 1)
        self.assertEqual(
            sum("INSERT INTO AUDIT_LOG" in sql for sql, _ in cursor.statements), 5
        )

    def test_admin_dynamic_submission_remains_approved(self):
        cursor = EntityCursor()
        with patch.object(
            auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}
        ):
            result, _, _ = self.run_transaction(
                cursor,
                lambda: workflow.submit_paper(
                    "Admin paper", "", 2025, None,
                    [{"new": {"name": "Author", "email": "author@example.org"}}],
                    [{"new": "New topic"}], [{"new": "New keyword"}],
                ),
            )
        self.assertEqual(result, (41, "APPROVED"))

    def test_existing_researcher_email_is_reused_without_overwriting(self):
        existing = {
            "r_id": 23, "r_name": "Stored Name", "email": "known@example.org",
            "institution": "Stored Institution",
        }
        cursor = EntityCursor(entities={
            "RESEARCHER": [existing], "TOPIC": [], "KEYWORD": [],
        })
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            self.run_transaction(
                cursor,
                lambda: workflow.submit_paper(
                    "Title", "", 2025, None,
                    [{"new": {
                        "name": "Different Name", "email": " KNOWN@example.org ",
                        "institution": "Different Institution",
                    }}],
                    [2], [3],
                ),
            )
        self.assertFalse(any("INSERT INTO RESEARCHER" in sql for sql, _ in cursor.statements))
        author = next(params for sql, params in cursor.statements if "INSERT INTO AUTHORS" in sql)
        self.assertEqual(author, (23, 41, 1))
        self.assertEqual(cursor.entities["RESEARCHER"], [existing])

    def test_concurrent_researcher_email_conflict_reuses_winning_insert(self):
        cursor = ConcurrentDuplicateCursor()
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            _, connection, cursor = self.run_transaction(
                cursor,
                lambda: workflow.submit_paper(
                    "Title", "", 2025, None,
                    [{"new": {"name": "Concurrent Author", "email": "race@example.org"}}],
                    [2], [3],
                ),
            )
        self.assertTrue(connection.committed)
        self.assertEqual(len(cursor.entities["RESEARCHER"]), 1)
        researcher_id = cursor.entities["RESEARCHER"][0]["r_id"]
        author = next(params for sql, params in cursor.statements if "INSERT INTO AUTHORS" in sql)
        self.assertEqual(author[0], researcher_id)

    def test_dynamic_entry_validation_rejects_empty_and_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "valid researcher email"):
            workflow._resolve_researcher(
                EntityCursor(), {"new": {"name": "Name", "email": "bad"}}, 9
            )
        with self.assertRaisesRegex(ValueError, "Topic must contain"):
            workflow._resolve_named_entity(
                EntityCursor(), {"new": "  "}, 9, "topic", "t_name", 150
            )
        with self.assertRaisesRegex(ValueError, "Keyword must contain"):
            workflow._resolve_named_entity(
                EntityCursor(), {"new": ""}, 9, "keyword", "keyword", 150
            )

    def test_new_entities_roll_back_when_paper_insert_fails(self):
        cursor = EntityCursor(fail_on="INSERT INTO PAPER ")
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            connection = FakeConnection(cursor)
            with patch.object(db, "get_connection", return_value=connection):
                with self.assertRaises(RuntimeError):
                    workflow.submit_paper(
                        "Title", "", 2025, None,
                        [{"new": {"name": "New Author", "email": "new@example.org"}}],
                        [{"new": "New Topic"}], [{"new": "New Keyword"}],
                    )
        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)
        self.assertTrue(cursor.entities["RESEARCHER"])
        self.assertTrue(cursor.entities["TOPIC"])
        self.assertTrue(cursor.entities["KEYWORD"])

    def test_new_entities_roll_back_when_relationship_insert_fails(self):
        cursor = EntityCursor(fail_on="INSERT INTO HAS_KEYWORD")
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            connection = FakeConnection(cursor)
            with patch.object(db, "get_connection", return_value=connection):
                with self.assertRaises(RuntimeError):
                    workflow.submit_paper(
                        "Title", "", 2025, None,
                        [{"new": {"name": "New Author", "email": "new@example.org"}}],
                        [{"new": "New Topic"}], [{"new": "New Keyword"}],
                    )
        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)

    def test_student_cannot_create_supporting_entities_during_submission(self):
        cursor = EntityCursor()
        with patch.object(
            auth, "require_actor", side_effect=auth.AuthorizationError("not allowed")
        ):
            with self.assertRaises(auth.AuthorizationError):
                self.run_transaction(
                    cursor,
                    lambda: workflow.submit_paper(
                        "Title", "", 2025, None,
                        [{"new": {"name": "New Author", "email": "new@example.org"}}],
                        [{"new": "New Topic"}], [{"new": "New Keyword"}],
                    ),
                )
        self.assertFalse(any(
            "INSERT INTO RESEARCHER" in sql or "INSERT INTO TOPIC" in sql
            or "INSERT INTO KEYWORD" in sql
            for sql, _ in cursor.statements
        ))

    def test_student_cannot_submit_through_service(self):
        cursor = FakeCursor()
        with patch.object(
            auth, "require_actor",
            side_effect=auth.AuthorizationError("not allowed"),
        ):
            with self.assertRaises(auth.AuthorizationError):
                self.run_transaction(
                    cursor,
                    lambda: workflow.submit_paper(
                        "Title", "Abstract", 2025, None, [1], [2], [3]
                    ),
                )
        self.assertFalse(any("INSERT INTO PAPER " in sql for sql, _ in cursor.statements))

    def test_teacher_cannot_approve_publications(self):
        cursor = FakeCursor()
        with patch.object(
            auth, "require_actor",
            side_effect=auth.AuthorizationError("not allowed"),
        ):
            with self.assertRaises(auth.AuthorizationError):
                self.run_transaction(
                    cursor, lambda: workflow.review_paper(22, "APPROVED")
                )
        self.assertFalse(any("UPDATE PAPER_WORKFLOW" in sql for sql, _ in cursor.statements))

    def test_student_cannot_change_roles_through_service(self):
        cursor = FakeCursor()
        with patch.object(
            auth, "require_actor_id_for_read",
            side_effect=auth.AuthorizationError("not allowed"),
        ):
            with self.assertRaises(auth.AuthorizationError):
                self.run_transaction(
                    cursor, lambda: workflow.admin_update_user(5, "ADMIN", True)
                )
        self.assertFalse(any("UPDATE APP_USER" in sql for sql, _ in cursor.statements))

    def test_teacher_cannot_manage_another_teachers_project(self):
        cursor = FakeCursor(owned_record=None)
        with patch.object(auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}):
            with self.assertRaises(auth.AuthorizationError):
                self.run_transaction(
                    cursor, lambda: workflow.assign_researcher(22, 3)
                )
        self.assertFalse(any("INSERT INTO WORKS_ON" in sql for sql, _ in cursor.statements))

    def test_association_failure_rolls_back_paper_submission(self):
        cursor = FakeCursor(fail_on="INSERT INTO HAS_TOPIC")
        connection = FakeConnection(cursor)
        with patch.object(auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}):
            with patch.object(db, "get_connection", return_value=connection):
                with self.assertRaises(RuntimeError):
                    workflow.submit_paper("Title", "Abstract", 2025, None, [1], [2], [3])
        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)
        self.assertTrue(connection.closed)

    def test_teacher_cannot_edit_another_teachers_submission(self):
        cursor = FakeCursor(owned_record=None)
        with patch.object(auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}):
            with self.assertRaises(auth.AuthorizationError):
                self.run_transaction(
                    cursor,
                    lambda: workflow.edit_my_submission(22, "Title", "", 2025, None),
                )
        self.assertFalse(any(sql.startswith("UPDATE PAPER SET") for sql, _ in cursor.statements))

    def test_edit_can_add_dynamic_entities_and_resubmit_atomically(self):
        cursor = EntityCursor(
            workflow_status="REJECTED",
            owned_record={
                "status": "REJECTED", "p_title": "Old title", "abstract": "",
                "pub_year": 2024, "c_id": None,
            },
        )
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            _, connection, cursor = self.run_transaction(
                cursor,
                lambda: workflow.edit_my_submission(
                    41, "Updated", "", 2025, None,
                    [{"new": {"name": "New Author", "email": "new@example.org"}}],
                    [{"new": "New Topic"}], [{"new": "New Keyword"}],
                    resubmit=True,
                ),
            )
        self.assertTrue(connection.committed)
        self.assertTrue(any("INSERT INTO RESEARCHER" in sql for sql, _ in cursor.statements))
        self.assertTrue(any("INSERT INTO TOPIC" in sql for sql, _ in cursor.statements))
        self.assertTrue(any("INSERT INTO KEYWORD" in sql for sql, _ in cursor.statements))
        self.assertTrue(any(
            "UPDATE PAPER_WORKFLOW SET status = 'PENDING'" in sql
            for sql, _ in cursor.statements
        ))
        self.assertTrue(any(
            values[1] == "PAPER_RESUBMITTED"
            for sql, values in cursor.statements if "INSERT INTO AUDIT_LOG" in sql
        ))

    def test_only_pending_papers_can_be_reviewed(self):
        cursor = FakeCursor(workflow_status="APPROVED")
        with patch.object(auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}):
            with self.assertRaises(ValueError):
                self.run_transaction(
                    cursor, lambda: workflow.review_paper(22, "REJECTED", "Reason")
                )
        self.assertFalse(any("INSERT INTO PUBLICATION_REVIEW" in sql for sql, _ in cursor.statements))

    def test_rejection_requires_remarks(self):
        with self.assertRaises(ValueError):
            workflow.review_paper(22, "REJECTED", "")

    def test_approval_writes_review_and_audit_in_transaction(self):
        cursor = FakeCursor(workflow_status="PENDING")
        with patch.object(auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}):
            _, connection, cursor = self.run_transaction(
                cursor, lambda: workflow.review_paper(22, "APPROVED")
            )
        self.assertTrue(connection.committed)
        self.assertTrue(any("INSERT INTO PUBLICATION_REVIEW" in sql for sql, _ in cursor.statements))
        self.assertTrue(any("INSERT INTO AUDIT_LOG" in sql for sql, _ in cursor.statements))

    def test_admin_can_reject_with_remarks(self):
        cursor = FakeCursor(workflow_status="PENDING")
        with patch.object(auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}):
            _, connection, cursor = self.run_transaction(
                cursor, lambda: workflow.review_paper(22, "REJECTED", "Please clarify the method.")
            )
        self.assertTrue(connection.committed)
        review = next(
            values for statement, values in cursor.statements
            if "INSERT INTO PUBLICATION_REVIEW" in statement
        )
        self.assertEqual(review[2], "REJECTED")
        self.assertEqual(review[3], "Please clarify the method.")

    def test_rejected_paper_can_be_resubmitted(self):
        cursor = FakeCursor(workflow_status="REJECTED")
        with patch.object(auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}):
            _, connection, cursor = self.run_transaction(
                cursor, lambda: workflow.resubmit_paper(22)
            )
        self.assertTrue(connection.committed)
        update = next(sql for sql, _ in cursor.statements if "UPDATE PAPER_WORKFLOW" in sql)
        self.assertIn("status = 'PENDING'", update)

    def test_legacy_approved_paper_can_be_archived(self):
        cursor = FakeCursor(workflow_status=None)
        with patch.object(auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}):
            _, connection, cursor = self.run_transaction(
                cursor, lambda: workflow.archive_paper(22)
            )
        self.assertTrue(connection.committed)
        self.assertTrue(any(
            "INSERT INTO PAPER_WORKFLOW" in sql and "ARCHIVED" in sql
            for sql, _ in cursor.statements
        ))


class PaperFormDraftTests(unittest.TestCase):
    def test_existing_researcher_selection_is_added_without_database_write(self):
        state = {"draft_researcher_picker": [1, 2], "draft_authors": []}
        with patch.object(paper_form, "st", SimpleNamespace(session_state=state)):
            paper_form._add_selected("draft", "authors")
        self.assertEqual(state["draft_authors"], [1, 2])
        self.assertEqual(state["draft_researcher_picker"], [])

    def test_multiple_new_researchers_remain_ordered_draft_entries(self):
        state = {
            "draft_new_researcher_name": " First Author ",
            "draft_new_researcher_email": "FIRST@example.org ",
            "draft_new_researcher_institution": "University",
            "draft_authors": [],
        }
        with patch.object(paper_form, "st", SimpleNamespace(session_state=state)):
            paper_form._add_researcher("draft", {})
            state["draft_new_researcher_name"] = "Second Author"
            state["draft_new_researcher_email"] = "second@example.org"
            state["draft_new_researcher_institution"] = "Research Institute"
            paper_form._add_researcher("draft", {})
        self.assertEqual(
            state["draft_authors"],
            [
                {"new": {
                    "name": "First Author", "email": "first@example.org",
                    "institution": "University",
                }},
                {"new": {
                    "name": "Second Author", "email": "second@example.org",
                    "institution": "Research Institute",
                }},
            ],
        )

    def test_new_researcher_matching_existing_email_reuses_id(self):
        state = {
            "draft_new_researcher_name": "Different Name",
            "draft_new_researcher_email": "known@example.org",
            "draft_new_researcher_institution": "Other Institution",
            "draft_authors": [],
        }
        with patch.object(paper_form, "st", SimpleNamespace(session_state=state)):
            paper_form._add_researcher("draft", {"known@example.org": 8})
        self.assertEqual(state["draft_authors"], [8])

    def test_topics_and_keywords_reuse_case_insensitive_existing_values(self):
        state = {
            "draft_new_topic_name": "  DATA SCIENCE ",
            "draft_new_keyword_name": " privacy ",
            "draft_topics": [],
            "draft_keywords": [],
        }
        with patch.object(paper_form, "st", SimpleNamespace(session_state=state)):
            paper_form._add_named("draft", "topics", {"data science": 2})
            paper_form._add_named("draft", "keywords", {"privacy": 3})
        self.assertEqual(state["draft_topics"], [2])
        self.assertEqual(state["draft_keywords"], [3])

    def test_authors_can_be_reordered_and_removed(self):
        state = {"draft_authors": [1, 2, 3]}
        with patch.object(paper_form, "st", SimpleNamespace(session_state=state)):
            paper_form._move("draft", "authors", 2, -1)
            self.assertEqual(state["draft_authors"], [1, 3, 2])
            paper_form._remove("draft", "authors", 0)
        self.assertEqual(state["draft_authors"], [3, 2])


class ProjectWorkflowTests(unittest.TestCase):
    def run_transaction(self, cursor, operation):
        connection = FakeConnection(cursor)
        with patch.object(db, "get_connection", return_value=connection):
            result = operation()
        return result, connection, cursor

    def test_create_project_assigns_owner_and_audits_creation(self):
        cursor = ProjectCursor()
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            project_id, connection, cursor = self.run_transaction(
                cursor, lambda: workflow.create_project("  Project Alpha  ", " Description ")
            )
        self.assertEqual(project_id, 88)
        self.assertTrue(connection.committed)
        self.assertTrue(any("INSERT INTO PROJECT_OWNERSHIP" in sql for sql, _ in cursor.statements))
        audit = next(params for sql, params in cursor.statements if "INSERT INTO AUDIT_LOG" in sql)
        self.assertEqual(audit[1:4], ("PROJECT_CREATED", "PROJECT", 88))

    def test_duplicate_project_name_is_rejected(self):
        cursor = ProjectCursor(project_name="project alpha")
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            with self.assertRaisesRegex(ValueError, "already exists"):
                self.run_transaction(
                    cursor, lambda: workflow.create_project(" Project Alpha ", "")
                )
        self.assertFalse(any("INSERT INTO PROJECT " in sql for sql, _ in cursor.statements))

    def test_teacher_cannot_edit_unowned_or_legacy_project(self):
        cursor = ProjectCursor(owned=False)
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            with self.assertRaises(auth.AuthorizationError):
                self.run_transaction(
                    cursor, lambda: workflow.update_project(22, "Changed", "Description")
                )
        self.assertFalse(any("UPDATE PROJECT SET" in sql for sql, _ in cursor.statements))

    def test_admin_can_manage_legacy_project_without_ownership_row(self):
        cursor = ProjectCursor(owned=False)
        with patch.object(
            auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}
        ):
            _, connection, cursor = self.run_transaction(
                cursor, lambda: workflow.update_project(22, "Project", "Updated description")
            )
        self.assertTrue(connection.committed)
        self.assertTrue(any("UPDATE PROJECT SET" in sql for sql, _ in cursor.statements))
        self.assertFalse(any("FROM PROJECT_OWNERSHIP" in sql for sql, _ in cursor.statements))

    def test_update_project_skips_unchanged_values_and_audit(self):
        cursor = ProjectCursor()
        cursor.project_row = {"name": "Project", "description": "Description"}
        with patch.object(
            auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}
        ):
            _, connection, cursor = self.run_transaction(
                cursor, lambda: workflow.update_project(22, "Project", "Description")
            )
        self.assertTrue(connection.committed)
        self.assertFalse(any("UPDATE PROJECT SET" in sql for sql, _ in cursor.statements))
        self.assertFalse(any("INSERT INTO AUDIT_LOG" in sql for sql, _ in cursor.statements))

    def test_new_researcher_and_assignment_are_atomic_and_audited(self):
        cursor = ProjectCursor()
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            researcher_id, connection, cursor = self.run_transaction(
                cursor,
                lambda: workflow.add_researcher_to_project(
                    22, "New Researcher", "NEW@example.org", "Institute"
                ),
            )
        self.assertEqual(researcher_id, 88)
        self.assertTrue(connection.committed)
        self.assertTrue(any("INSERT INTO RESEARCHER" in sql for sql, _ in cursor.statements))
        self.assertTrue(any("INSERT INTO WORKS_ON" in sql for sql, _ in cursor.statements))
        actions = [
            params[1] for sql, params in cursor.statements if "INSERT INTO AUDIT_LOG" in sql
        ]
        self.assertEqual(actions, ["RESEARCHER_CREATED", "PROJECT_RESEARCHER_ADDED"])

    def test_new_researcher_is_rolled_back_if_project_assignment_fails(self):
        cursor = ProjectCursor(fail_on="INSERT INTO WORKS_ON")
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            connection = FakeConnection(cursor)
            with patch.object(db, "get_connection", return_value=connection):
                with self.assertRaises(RuntimeError):
                    workflow.add_researcher_to_project(
                        22, "New Researcher", "NEW@example.org"
                    )
        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)

    def test_existing_researcher_is_reused_and_duplicate_assignment_rejected(self):
        cursor = ProjectCursor(existing_researcher_email=17, assigned=True)
        with patch.object(
            auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}
        ):
            with self.assertRaisesRegex(ValueError, "already assigned"):
                self.run_transaction(
                    cursor,
                    lambda: workflow.add_researcher_to_project(
                        22, "Other Name", "RESEARCHER@example.org"
                    ),
                )
        self.assertFalse(any("INSERT INTO RESEARCHER" in sql for sql, _ in cursor.statements))
        self.assertFalse(any("INSERT INTO WORKS_ON" in sql for sql, _ in cursor.statements))

    def test_removing_researcher_deletes_only_relationship(self):
        cursor = ProjectCursor()
        with patch.object(
            auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}
        ):
            _, connection, cursor = self.run_transaction(
                cursor, lambda: workflow.remove_researcher_from_project(22, 17)
            )
        self.assertTrue(connection.committed)
        self.assertTrue(any("DELETE FROM WORKS_ON" in sql for sql, _ in cursor.statements))
        self.assertFalse(any("DELETE FROM RESEARCHER" in sql for sql, _ in cursor.statements))
        audit = next(params for sql, params in cursor.statements if "INSERT INTO AUDIT_LOG" in sql)
        self.assertEqual(audit[1], "PROJECT_RESEARCHER_REMOVED")

    def test_add_existing_and_new_dataset_then_unlink_without_deleting_dataset(self):
        existing_cursor = ProjectCursor()
        with patch.object(
            auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}
        ):
            self.run_transaction(
                existing_cursor, lambda: workflow.link_dataset(22, 31)
            )
        self.assertTrue(any("INSERT INTO USES" in sql for sql, _ in existing_cursor.statements))

        new_cursor = ProjectCursor()
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            _, connection, new_cursor = self.run_transaction(
                new_cursor,
                lambda: workflow.add_dataset_to_project(
                    22, " New Dataset ", " https://example.org/data "
                ),
            )
        self.assertTrue(connection.committed)
        self.assertTrue(any("INSERT INTO DATASET" in sql for sql, _ in new_cursor.statements))
        self.assertTrue(any("INSERT INTO USES" in sql for sql, _ in new_cursor.statements))

        unlink_cursor = ProjectCursor()
        with patch.object(
            auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}
        ):
            self.run_transaction(
                unlink_cursor, lambda: workflow.unlink_dataset_from_project(22, 31)
            )
        self.assertTrue(any("DELETE FROM USES" in sql for sql, _ in unlink_cursor.statements))
        self.assertFalse(any("DELETE FROM DATASET" in sql for sql, _ in unlink_cursor.statements))

    def test_existing_matching_dataset_is_reused_and_duplicate_links_are_rejected(self):
        cursor = ProjectCursor(existing_dataset_match=44)
        with patch.object(
            auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}
        ):
            result, _, cursor = self.run_transaction(
                cursor,
                lambda: workflow.add_dataset_to_project(
                    22, " Existing Dataset ", " HTTPS://example.org/data "
                ),
            )
        self.assertEqual(result, (44, False))
        self.assertFalse(any("INSERT INTO DATASET" in sql for sql, _ in cursor.statements))
        self.assertTrue(any("INSERT INTO USES" in sql for sql, _ in cursor.statements))

        duplicate_cursor = ProjectCursor(linked=True)
        with patch.object(
            auth, "require_actor", return_value={"user_id": 1, "role": "ADMIN"}
        ):
            with self.assertRaisesRegex(ValueError, "already linked"):
                self.run_transaction(
                    duplicate_cursor, lambda: workflow.link_dataset(22, 44)
                )
        self.assertFalse(any("INSERT INTO USES" in sql for sql, _ in duplicate_cursor.statements))

    def test_dataset_link_failure_rolls_back_new_dataset(self):
        cursor = ProjectCursor(fail_on="INSERT INTO USES")
        with patch.object(
            auth, "require_actor", return_value={"user_id": 9, "role": "TEACHER"}
        ):
            connection = FakeConnection(cursor)
            with patch.object(db, "get_connection", return_value=connection):
                with self.assertRaises(RuntimeError):
                    workflow.add_dataset_to_project(22, "Dataset", "repository")
        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)

    def test_student_cannot_write_project_resources_through_service(self):
        for operation in (
            lambda: workflow.create_project("Project", ""),
            lambda: workflow.update_project(22, "Project", ""),
            lambda: workflow.assign_researcher(22, 3),
            lambda: workflow.add_researcher_to_project(
                22, "Researcher", "r@example.org"
            ),
            lambda: workflow.remove_researcher_from_project(22, 3),
            lambda: workflow.link_dataset(22, 4),
            lambda: workflow.add_dataset_to_project(22, "Dataset", "Source"),
            lambda: workflow.unlink_dataset_from_project(22, 4),
        ):
            with self.subTest(operation=operation):
                with patch.object(
                    auth, "require_actor",
                    side_effect=auth.AuthorizationError("not allowed"),
                ), patch.object(
                    db, "transaction", side_effect=lambda callback: callback(FakeCursor())
                ):
                    with self.assertRaises(auth.AuthorizationError):
                        operation()

    def test_shared_resource_detail_queries_are_parameterized(self):
        with patch.object(db, "query", return_value=pd.DataFrame()) as query:
            workflow.list_shared_researchers(4, 9)
            self.assertIn("%s", query.call_args.args[0])
            self.assertEqual(query.call_args.args[1], (4, 9))
            workflow.list_shared_datasets(4, 9)
            self.assertIn("%s", query.call_args.args[0])
            self.assertEqual(query.call_args.args[1], (4, 9))


class VisibilityMigrationTests(unittest.TestCase):
    def test_public_discovery_objects_filter_unapproved_papers(self):
        sql = (ROOT / "sql" / "61_visibility_views.sql").read_text(encoding="utf-8")
        for name in (
            "v_collaborators",
            "v_paper_topic_sim",
            "v_paper_keyword_sim",
            "v_paper_similarity",
            "v_papers_per_conference",
            "v_papers_per_year",
            "v_papers_per_topic",
            "sp_search",
            "sp_citations",
        ):
            self.assertIn(name, sql)
        self.assertGreaterEqual(sql.count("COALESCE(w.status, 'APPROVED')"), 6)
        self.assertIn("COALESCE(sw.status, 'APPROVED')", sql)
        self.assertIn("COALESCE(tw.status, 'APPROVED')", sql)

    def test_researcher_normalized_email_migration_adds_unique_index(self):
        sql = (ROOT / "sql" / "62_researcher_email_unique.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("CREATE UNIQUE INDEX uq_researcher_normalized_email", sql)
        self.assertIn("LOWER(TRIM(email))", sql)
        self.assertIn("HAVING COUNT(*) > 1", sql)


if __name__ == "__main__":
    unittest.main()
