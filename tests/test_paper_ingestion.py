import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pymupdf

from app.paper_ingestion.entity_matcher import exact_duplicate, match_references
from app.paper_ingestion.metadata_extractor import extract_metadata
from app.paper_ingestion.pdf_parser import PDFIngestionError, extract_pdf_text, pdf_metadata
from app.paper_ingestion.reference_parser import parse_references
from app.paper_ingestion.storage import delete_pdf, read_pdf, safe_original_name, store_pdf
from app.paper_ingestion.topic_classifier import classify_topics, suggest_topics


def _pdf_with_text(lines):
    commands = ["BT /F1 12 Tf 72 760 Td"]
    for index, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index:
            commands.append("0 -18 Td")
        commands.append(f"({escaped}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream + b"\nendstream",
    ]
    document = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref_offset = len(document)
    document.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(document)


class PDFParserTests(unittest.TestCase):
    def test_extracts_text_from_valid_pdf(self):
        content = _pdf_with_text(["Research Paper Title", "Abstract", "A useful abstract."])
        text = extract_pdf_text("paper.pdf", content)
        self.assertIn("Research Paper Title", text)
        self.assertIn("A useful abstract.", text)

    def test_handles_pdf_without_document_info(self):
        metadata = pdf_metadata(
            "paper.pdf", _pdf_with_text(["Research Paper Title", "Abstract"])
        )
        self.assertEqual(metadata, {"title": "", "author": "", "creation_date": ""})

    def test_rejects_non_pdf_and_oversized_pdf(self):
        with self.assertRaises(PDFIngestionError):
            extract_pdf_text("paper.pdf", b"not a pdf")
        with self.assertRaises(PDFIngestionError):
            extract_pdf_text("paper.pdf", _pdf_with_text(["Title"]), max_bytes=20)

    def test_extracts_header_metadata_and_author_order(self):
        text = "\n".join([
            "A Study of Research Networks",
            "Alice Smith, Bob Jones",
            "University of Example",
            "alice@example.org",
            "ABSTRACT",
            "We study collaboration graphs and research networks.",
            "Index Terms— collaboration graphs, research networks.",
            "1 Introduction",
            "The paper body.",
            "2024 IEEE Research Conference",
            "DOI: 10.1234/example.2024",
        ])
        metadata = extract_metadata(text)
        self.assertEqual(metadata["title"], "A Study of Research Networks")
        self.assertEqual([author["name"] for author in metadata["authors"]], [
            "Alice Smith", "Bob Jones",
        ])
        self.assertEqual(metadata["authors"][0]["email"], "alice@example.org")
        self.assertIn("collaboration graphs", metadata["abstract"].lower())
        self.assertEqual(metadata["year"], 2024)
        self.assertEqual(metadata["doi"], "10.1234/example.2024")
        self.assertIn("research networks", " ".join(metadata["keywords"]).lower())

    def test_extracts_expected_fields_from_two_page_ieee_style_pdf(self):
        fixture = (
            Path(__file__).parent / "fixtures" / "smart_import_ieee_sample.pdf"
        )
        content = fixture.read_bytes()
        text = extract_pdf_text(fixture.name, content)
        metadata = extract_metadata(text, pdf_metadata(fixture.name, content))
        with pymupdf.open(stream=content, filetype="pdf") as document:
            self.assertEqual(document.page_count, 2)

        self.assertLess(len(content), 10 * 1024 * 1024)
        self.assertEqual(
            metadata["title"],
            "Metadata Extraction and Citation Mapping for Academic Research Networks",
        )
        self.assertTrue(metadata["abstract"].startswith(
            "Academic research platforms often require reliable extraction"
        ))
        self.assertTrue(metadata["abstract"].endswith(
            "human review for academic information systems."
        ))
        self.assertEqual(
            [author["name"] for author in metadata["authors"]],
            ["Ananya Rao", "Vikram Sen", "Meera Iyer"],
        )
        self.assertEqual(
            [author["email"] for author in metadata["authors"]],
            [
                "ananya.rao@example.org",
                "vikram.sen@example.org",
                "meera.iyer@example.org",
            ],
        )
        self.assertEqual(metadata["keywords"], [
            "Document parsing",
            "metadata extraction",
            "relational databases",
            "citation networks",
            "entity resolution",
            "academic information systems",
        ])
        self.assertEqual([item["number"] for item in metadata["references"]], [1, 2, 3, 4])
        self.assertEqual(metadata["references"][0]["title"],
                         "Metadata extraction for scholarly documents")
        self.assertEqual(metadata["references"][3]["title"],
                         "Layout-aware parsing of two-column papers")
        self.assertIsNone(metadata["year"])
        self.assertIsNone(metadata["doi"])
        self.assertEqual(metadata["venue"], "")
        self.assertIn("Synthetic Test Paper", text)
        self.assertNotIn("Synthetic Test Paper", metadata["title"])
        self.assertNotIn("Research Collaboration Journal", text)

        existing_topics = [
            {"t_id": 1, "t_name": "Machine Learning"},
            {"t_id": 2, "t_name": "Deep Learning"},
            {"t_id": 3, "t_name": "Computer Vision"},
            {"t_id": 4, "t_name": "Natural Language Processing"},
            {"t_id": 5, "t_name": "Healthcare AI"},
            {"t_id": 6, "t_name": "Data Science"},
        ]
        self.assertEqual(
            suggest_topics(
                metadata["title"],
                metadata["keywords"],
                existing_topics,
                metadata["abstract"],
            ),
            [],
        )

    def test_abstract_heading_variants_inline_text_and_multiline_authors(self):
        for heading in (
            "Abstract",
            "ABSTRACT",
            "Abstract—",
            "Abstract-",
            "Abstract:",
            "Abstract: Inline abstract text.",
        ):
            with self.subTest(heading=heading):
                metadata = extract_metadata("\n".join([
                    "A Robust Method for Scholarly Metadata",
                    "A. Rao and V. Sen",
                    "Department of Information Systems",
                    "a.rao@example.org; v.sen@example.org",
                    heading,
                    "Complete abstract content begins here.",
                    "Additional abstract sentence.",
                    "Index Terms— metadata extraction, citation networks",
                    "2 Introduction",
                    "The body begins here.",
                ]))
                expected_abstract = (
                    "Inline abstract text. Complete abstract content begins here. "
                    "Additional abstract sentence."
                    if heading.endswith("Inline abstract text.")
                    else "Complete abstract content begins here. "
                    "Additional abstract sentence."
                )
                self.assertEqual(metadata["abstract"], expected_abstract)
                self.assertEqual(
                    [author["name"] for author in metadata["authors"]],
                    ["A. Rao", "V. Sen"],
                )
                self.assertEqual(
                    [author["email"] for author in metadata["authors"]],
                    ["a.rao@example.org", "v.sen@example.org"],
                )
                self.assertEqual(
                    metadata["keywords"], ["metadata extraction", "citation networks"]
                )

    def test_discards_repeated_running_headers_and_page_numbers(self):
        text = (
            "Research Collaboration Journal\n"
            "A Study of Research Networks\n"
            "Ananya Rao, Vikram Sen\n"
            "ABSTRACT\n"
            "A complete abstract for this test document.\n"
            "1 Introduction\n"
            "Body text.\n"
            "\f\n"
            "Research Collaboration Journal\n"
            "2\n"
            "Continuation of the paper body.\n"
        )
        metadata = extract_metadata(text)
        self.assertEqual(metadata["title"], "A Study of Research Networks")
        self.assertNotIn("Research Collaboration Journal", metadata["title"])
        self.assertEqual(
            metadata["abstract"], "A complete abstract for this test document."
        )

    def test_parses_reference_lines(self):
        references = parse_references(
            "Introduction\nText\nReferences\n"
            "[1] A. Author, A Research Paper. 2020. doi:10.1000/test.\n"
            "[2] B. Writer, Another Study. 2019."
        )
        self.assertEqual(len(references), 2)
        self.assertEqual([item["number"] for item in references], [1, 2])
        self.assertEqual(references[0]["doi"], "10.1000/test")
        self.assertEqual(references[1]["year"], 2019)

    def test_parses_multiline_references_across_page_breaks(self):
        references = parse_references(
            "Body text\nREFERENCES\n"
            "[1] A. Author, “A Multi-line Research Paper,” Journal of Examples,\n"
            "    vol. 4, pp. 10-19, 2022.\n"
            "[2] B. Writer, Another Important Study, 2021.\n"
            "\f\n"
            "[3] C. Researcher, A Cross-Page Reference\n"
            "    with a continuation line, 2020.\n"
            "[4] D. Scholar, Final Reference, doi:10.1000/final.\n"
        )
        self.assertEqual([item["number"] for item in references], [1, 2, 3, 4])
        self.assertIn("vol. 4", references[0]["raw"])
        self.assertIn("with a continuation line", references[2]["raw"])
        self.assertEqual(references[0]["year"], 2022)
        self.assertEqual(references[3]["doi"], "10.1000/final")

    def test_topic_suggestions_use_existing_topic_text_only(self):
        topics = [
            {"t_id": 1, "t_name": "Computer Vision"},
            {"t_id": 2, "t_name": "Natural Language Processing"},
            {"t_id": 3, "t_name": "Database Systems"},
        ]
        suggestions = suggest_topics(
            "Computer Vision for image analysis", [], topics
        )
        self.assertEqual([item["t_id"] for item in suggestions], [1])

    def test_topic_classification_uses_normalized_synonyms_without_abstract(self):
        topics = [
            {"t_id": 41, "t_name": "Computer Vision"},
            {"t_id": 42, "t_name": "Data Science"},
        ]
        result = classify_topics(
            "Relational Data Models for Research",
            ["relational databases", "image recognition"],
            topics,
            abstract="",
        )

        self.assertEqual(
            [(item["t_id"], item["t_name"]) for item in result["existing"]],
            [(41, "Computer Vision")],
        )
        self.assertIn(
            "image recognition",
            [phrase["phrase"] for phrase in result["existing"][0]["matched_phrases"]],
        )
        database_topic = next(
            item for item in result["proposed"]
            if item["t_name"] == "Database Management Systems"
        )
        self.assertIn("relational databases", database_topic["reason"])
        self.assertTrue(database_topic["matched_phrases"])

    def test_proposed_topics_are_separate_and_skip_existing_topic_names(self):
        result = classify_topics(
            "Relational databases and citation networks",
            ["entity resolution"],
            [{"t_id": 20, "t_name": "Database Management Systems"}],
            abstract="",
        )
        self.assertEqual(
            [item["t_name"] for item in result["existing"]],
            ["Database Management Systems"],
        )
        proposed_names = [item["t_name"] for item in result["proposed"]]
        self.assertNotIn("Database Management Systems", proposed_names)
        self.assertIn("Citation Networks", proposed_names)
        self.assertIn("Entity Resolution", proposed_names)

    def test_reference_matching_marks_exact_and_ambiguous_candidates(self):
        refs = [
            {"title": "A Research Paper", "year": 2020, "doi": "10.1000/test"},
            {"title": "A Research Paper", "year": 2020, "doi": None},
            {"title": "Completely unrelated", "year": None, "doi": None},
        ]
        papers = [
            {"p_id": 1, "p_title": "A Research Paper", "pub_year": 2020, "doi": "10.1000/test"},
        ]
        matches = match_references(refs, papers)
        self.assertEqual(matches[0]["match_reason"], "DOI")
        self.assertEqual(matches[0]["candidate"]["p_id"], 1)
        self.assertEqual(matches[1]["match_status"], "Possible match")
        self.assertEqual(matches[2]["match_status"], "Unmatched")

    def test_multiple_title_matches_are_not_auto_selected(self):
        result = match_references(
            [{"title": "Shared Title", "year": 2020, "doi": None}],
            [
                {"p_id": 1, "p_title": "Shared Title", "pub_year": 2020, "doi": None},
                {"p_id": 2, "p_title": "Shared Title", "pub_year": 2020, "doi": None},
            ],
        )[0]
        self.assertEqual(result["match_status"], "Ambiguous match")
        self.assertIsNone(result["candidate"])
        self.assertEqual(len(result["candidates"]), 2)

    def test_duplicate_detection_uses_normalized_title_and_year_or_doi(self):
        papers = [{
            "p_id": 4,
            "p_title": "A Research Paper!",
            "pub_year": 2020,
            "doi": "10.1234/abc",
        }]
        self.assertEqual(exact_duplicate("a research paper", 2020, None, papers), papers)
        self.assertEqual(exact_duplicate("Different title", 2021, "10.1234/abc", papers), papers)
        self.assertEqual(exact_duplicate("Different title", 2021, None, papers), [])

    def test_private_upload_storage_uses_generated_key_and_rejects_traversal(self):
        content = _pdf_with_text(["Research Paper Title", "Abstract", "A useful abstract."])
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"RESEARCHNET_UPLOAD_DIR": directory}
        ):
            stored = store_pdf("..\\private\\paper.pdf", content)
            self.assertTrue(stored["storage_key"].endswith(".pdf"))
            self.assertEqual(stored["original_filename"], "paper.pdf")
            self.assertEqual(read_pdf(stored["storage_key"]), content)
            with self.assertRaises(ValueError):
                read_pdf("..\\paper.pdf")
            delete_pdf(stored["storage_key"])
            with self.assertRaises(FileNotFoundError):
                read_pdf(stored["storage_key"])


if __name__ == "__main__":
    unittest.main()
