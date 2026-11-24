# Smart Paper Import

Smart Paper Import is a local, review-before-submit workflow for text-based academic PDFs. It uses PyMuPDF text-block coordinates to estimate column reading order, with pypdf for PDF validation and document metadata. Parsing is deterministic and does not call an AI or metadata API.

## Setup

Install dependencies from `requirements.txt`, then apply the additive migration to an existing database:

```powershell
mysql -u root -p -e "SOURCE sql/63_paper_ingestion.sql"
```

Do not rerun `schema.sql` or `seed.sql` to enable this feature.

Optional environment settings:

| Variable | Default | Purpose |
|---|---:|---|
| `RESEARCHNET_MAX_UPLOAD_MB` | `10` | Maximum accepted source PDF size |
| `RESEARCHNET_UPLOAD_DIR` | `%LOCALAPPDATA%/ResearchNet/paper_uploads` on Windows | Private storage root; must be outside the application directory |

Uploaded file names are sanitized for display. Files are stored under generated UUID names outside the Streamlit-served application tree. A storage key and SHA-256 digest are associated with the submitted publication. Downloads require administrator access or teacher ownership. The PDF bytes remain in Streamlit session memory while the teacher reviews; no database or filesystem record is created until submission. Cancelling or closing before submission does not persist a paper or upload.

The final paper, authors, topics, keywords, confirmed citations, PDF association, workflow status, and audit events are written through the existing transaction service. Teacher-created papers enter `PENDING`; admin-created papers retain the existing immediate-approval behavior. A failed transaction removes its newly written PDF. Normal approval continues to control public analytics and citation visibility.

## Extraction behavior and limitations

- Accepts PDF extension and `%PDF-` signature, checks size, opens the file, and rejects encrypted files that cannot be opened.
- Uses positioned PyMuPDF text blocks to read two-column pages by column and retain full-width title/abstract blocks in sequence. Repeated edge headers and page numbers are filtered; very low-text files are rejected with an OCR limitation message. OCR is not provided.
- Heuristic title, author, abstract, keyword, year, venue, DOI, and numbered bibliography parsing is a suggestion, not verified metadata. The publication year is read from the first page, not bibliography years or the PDF creation timestamp. Abstract headings may include inline text; wrapped keyword/reference lines are joined.
- The upload and review interface allows corrections. A new researcher needs a real, teacher-provided email because the existing schema requires one. Name-only researcher suggestions are not selected automatically.
- Existing topics can be suggested from normalized research phrases and explainable aliases in the title, abstract, or keywords; title and keywords remain usable when no abstract is extracted. Matches reference existing topic IDs and preselect only those existing topics. Related topics not present in the database are shown separately with an unchecked teacher-approval control and are created only in the final paper-submission transaction. Extracted author keywords remain a separate field and are not represented as topic suggestions.
- References are matched against approved publications by DOI, exact normalized title/year, or a conservative title-similarity suggestion. Citation checkboxes default off; only explicitly confirmed approved-paper matches are written as `CITES` rows.
- Exact duplicate DOI or normalized title/year submissions are blocked. Existing publications are never overwritten.
- Conference venue text remains a review suggestion. Only an explicitly selected existing conference is linked; the parser does not create conference records.
- PDF files are retained for administrator review. There is no automated abandoned-upload cleanup job because files are only written at final submission; operators should include the configured upload directory in their normal access-controlled backup and retention policy.

The parser is a deterministic baseline and does not claim complete support for IEEE or other scholarly layouts. Column boundaries inferred from block coordinates and author/affiliation recognition vary by document, so review is required.

## Evaluation

Automated unit tests use generated, synthetic PDF fixtures for signature/size validation, text extraction, metadata parsing, reference parsing, matching, and storage safety. The two-page [IEEE-style sample PDF](../tests/fixtures/smart_import_ieee_sample.pdf) is synthetic and uses example.org test emails; do not treat them as verified identities. These are parser tests, not a representative scholarly-paper benchmark, and no title/author/keyword accuracy or time-saved percentages are claimed.

To report extraction quality, curate a legally obtained and licensed sample set, manually annotate title, author order, abstract, keywords, year, DOI, venue, and references, and compare parser output with those annotations. Report per-field precision/recall, exact-match accuracy, citation-match precision, and human review time; record the dataset source/license and parser version. No copyrighted sample PDFs are included in this repository.
