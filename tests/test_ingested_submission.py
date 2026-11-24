import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import workflow


class IngestionCursor:
    def __init__(self, fail_on=None, existing_papers=None, existing_doi=None):
        self.fail_on = fail_on
        self.existing_papers = existing_papers or []
        self.existing_doi = existing_doi
        self.statements = []
        self.lastrowid = 701

    def execute(self, statement, params=None):
        self.statements.append((statement, params))
        if self.fail_on and self.fail_on in statement:
            raise RuntimeError("simulated ingestion persistence failure")
        if statement.startswith("INSERT INTO PAPER "):
            self.lastrowid = 701

    def fetchall(self):
        if "FROM PAPER p" in self.statements[-1][0]:
            return self.existing_papers
        return []

    def fetchone(self):
        if "FROM PAPER_INGESTION" in self.statements[-1][0]:
            return self.existing_doi
        if "FROM PAPER p LEFT JOIN PAPER_WORKFLOW" in self.statements[-1][0]:
            return {"p_id": 11}
        return None


class DownloadCursor:
    def __init__(self, result):
        self.result = result
        self.statement = None
        self.params = None

    def execute(self, statement, params=None):
        self.statement = statement
        self.params = params

    def fetchone(self):
        return self.result


class IngestedSubmissionTests(unittest.TestCase):
    def _transaction_runner(self, cursor):
        state = {"committed": False, "rolled_back": False}

        def run(operation):
            try:
                result = operation(cursor)
                state["committed"] = True
                return result
            except Exception:
                state["rolled_back"] = True
                raise

        return run, state

    def _ingestion(self):
        return {
            "filename": "paper.pdf",
            "content": b"%PDF-1.4 test fixture",
            "metadata": {
                "title": "Ingested Paper",
                "doi": "https://doi.org/10.1234/ingested",
                "references": [],
            },
        }

    def test_ingested_paper_saves_private_metadata_and_confirmed_citation_atomically(self):
        cursor = IngestionCursor()
        transaction, transaction_state = self._transaction_runner(cursor)
        stored = {
            "storage_key": "a" * 32 + ".pdf",
            "original_filename": "paper.pdf",
            "sha256": "b" * 64,
            "file_size": 22,
        }
        with patch.object(workflow.db, "transaction", side_effect=transaction), patch.object(
            workflow.auth,
            "require_actor",
            return_value={"user_id": 9, "role": "TEACHER"},
        ), patch.object(workflow, "validate_pdf"), patch.object(
            workflow.paper_storage, "store_pdf", return_value=stored
        ) as store_pdf:
            result = workflow.submit_paper(
                "Ingested Paper", "Abstract", 2024, None, [1], [2], [3],
                ingestion=self._ingestion(),
                confirmed_citations=[11],
            )

        self.assertEqual(result, (701, "PENDING"))
        self.assertTrue(transaction_state["committed"])
        self.assertFalse(transaction_state["rolled_back"])
        store_pdf.assert_called_once_with("paper.pdf", b"%PDF-1.4 test fixture")
        ingestion_insert = next(
            params for sql, params in cursor.statements
            if "INSERT INTO PAPER_INGESTION" in sql
        )
        self.assertEqual(ingestion_insert[0], 701)
        self.assertEqual(ingestion_insert[1], "10.1234/ingested")
        self.assertTrue(any(
            sql.startswith("INSERT INTO CITES")
            and params == (701, 11)
            for sql, params in cursor.statements
        ))
        self.assertTrue(any(
            "INSERT INTO PAPER_WORKFLOW" in sql and params[1] == "PENDING"
            for sql, params in cursor.statements
        ))

    def test_failed_ingestion_persistence_rolls_back_and_removes_file(self):
        cursor = IngestionCursor(fail_on="INSERT INTO PAPER_INGESTION")
        transaction, transaction_state = self._transaction_runner(cursor)
        stored = {
            "storage_key": "a" * 32 + ".pdf",
            "original_filename": "paper.pdf",
            "sha256": "b" * 64,
            "file_size": 22,
        }
        with patch.object(workflow.db, "transaction", side_effect=transaction), patch.object(
            workflow.auth,
            "require_actor",
            return_value={"user_id": 9, "role": "TEACHER"},
        ), patch.object(workflow, "validate_pdf"), patch.object(
            workflow.paper_storage, "store_pdf", return_value=stored
        ), patch.object(workflow.paper_storage, "delete_pdf") as delete_pdf:
            with self.assertRaisesRegex(RuntimeError, "simulated"):
                workflow.submit_paper(
                    "Ingested Paper", "Abstract", 2024, None, [1], [2], [3],
                    ingestion=self._ingestion(),
                )

        self.assertTrue(transaction_state["rolled_back"])
        self.assertFalse(transaction_state["committed"])
        delete_pdf.assert_called_once_with(stored["storage_key"])

    def test_existing_doi_is_rejected_before_file_storage(self):
        cursor = IngestionCursor(existing_doi={"p_id": 22})
        transaction, transaction_state = self._transaction_runner(cursor)
        with patch.object(workflow.db, "transaction", side_effect=transaction), patch.object(
            workflow.auth,
            "require_actor",
            return_value={"user_id": 9, "role": "TEACHER"},
        ), patch.object(workflow, "validate_pdf"), patch.object(
            workflow.paper_storage, "store_pdf"
        ) as store_pdf:
            with self.assertRaisesRegex(ValueError, "publication #22"):
                workflow.submit_paper(
                    "Different title", "Abstract", 2024, None, [1], [2], [3],
                    ingestion=self._ingestion(),
                )

        self.assertTrue(transaction_state["rolled_back"])
        store_pdf.assert_not_called()

    def test_pdf_download_checks_teacher_ownership_before_reading_file(self):
        cursor = DownloadCursor({
            "storage_key": "a" * 32 + ".pdf",
            "original_filename": "paper.pdf",
        })
        transaction, _ = self._transaction_runner(cursor)
        with patch.object(workflow.db, "transaction", side_effect=transaction), patch.object(
            workflow.auth,
            "require_actor",
            return_value={"user_id": 9, "role": "TEACHER"},
        ), patch.object(
            workflow.paper_storage, "read_pdf", return_value=b"private pdf"
        ) as read_pdf:
            result = workflow.download_submission_pdf(701)

        self.assertIn("o.owner_user_id = %s", cursor.statement)
        self.assertEqual(cursor.params, (701, "TEACHER", 9))
        read_pdf.assert_called_once_with("a" * 32 + ".pdf")
        self.assertEqual(result, (b"private pdf", "paper.pdf"))

    def test_pdf_download_rejects_non_editor_before_reading_file(self):
        cursor = DownloadCursor(None)
        transaction, _ = self._transaction_runner(cursor)
        with patch.object(workflow.db, "transaction", side_effect=transaction), patch.object(
            workflow.auth,
            "require_actor",
            side_effect=PermissionError("Not authorized."),
        ) as require_actor, patch.object(
            workflow.paper_storage, "read_pdf"
        ) as read_pdf:
            with self.assertRaises(PermissionError):
                workflow.download_submission_pdf(701)

        require_actor.assert_called_once_with(cursor, {"TEACHER", "ADMIN"})
        read_pdf.assert_not_called()


if __name__ == "__main__":
    unittest.main()
