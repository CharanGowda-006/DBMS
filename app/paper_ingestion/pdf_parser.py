import os
import re
from io import BytesIO

import pymupdf
from pypdf import PdfReader
from pypdf.errors import PdfReadError


DEFAULT_MAX_UPLOAD_MB = 10
MAX_PDF_PAGES = 300
PARSER_VERSION = "smart-import-v2"


class PDFIngestionError(ValueError):
    """A safe, user-displayable PDF validation or extraction failure."""


def max_upload_bytes():
    try:
        limit_mb = int(os.environ.get("RESEARCHNET_MAX_UPLOAD_MB", DEFAULT_MAX_UPLOAD_MB))
    except ValueError as exc:
        raise PDFIngestionError("The PDF upload-size setting is invalid.") from exc
    if limit_mb < 1:
        raise PDFIngestionError("The PDF upload-size setting must be at least 1 MB.")
    return limit_mb * 1024 * 1024


def validate_pdf(filename, content, max_bytes=None):
    if not isinstance(filename, str) or not filename.lower().endswith(".pdf"):
        raise PDFIngestionError("Upload a file with the .pdf extension.")
    if not isinstance(content, bytes) or not content:
        raise PDFIngestionError("The selected PDF is empty.")
    if len(content) > (max_bytes if max_bytes is not None else max_upload_bytes()):
        raise PDFIngestionError("The PDF exceeds the configured upload-size limit.")
    if not content.startswith(b"%PDF-"):
        raise PDFIngestionError("The file contents do not have a valid PDF signature.")

    try:
        reader = PdfReader(BytesIO(content), strict=False)
        if reader.is_encrypted and not reader.decrypt(""):
            raise PDFIngestionError(
                "This PDF is encrypted. Upload an unlocked copy to continue."
            )
        if len(reader.pages) > MAX_PDF_PAGES:
            raise PDFIngestionError(
                f"PDFs with more than {MAX_PDF_PAGES} pages are not supported."
            )
    except PDFIngestionError:
        raise
    except (PdfReadError, OSError, ValueError, TypeError) as exc:
        raise PDFIngestionError(
            "The PDF is damaged or could not be opened. Try exporting it again."
        ) from exc
    return reader


def extract_pdf_text(filename, content, max_bytes=None):
    validate_pdf(filename, content, max_bytes=max_bytes)
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.needs_pass and not document.authenticate(""):
                raise PDFIngestionError(
                    "This PDF is encrypted. Upload an unlocked copy to continue."
                )
            if document.page_count > MAX_PDF_PAGES:
                raise PDFIngestionError(
                    f"PDFs with more than {MAX_PDF_PAGES} pages are not supported."
                )
            extracted_pages = [
                _extract_page_in_reading_order(page) for page in document
            ]
    except PDFIngestionError:
        raise
    except (
        pymupdf.FileDataError,
        pymupdf.EmptyFileError,
        OSError,
        ValueError,
    ) as exc:
        raise PDFIngestionError(
            "Text could not be extracted from this PDF. Try another digital PDF."
        ) from exc
    text = "\n\f\n".join(extracted_pages).strip()
    if len(re.sub(r"\s+", "", text)) < 30:
        raise PDFIngestionError(
            "This PDF contains little extractable text. Scanned documents need OCR, "
            "which is not enabled; upload a text-based PDF instead."
        )
    return text


def _extract_page_in_reading_order(page):
    page_width = page.rect.width
    page_height = page.rect.height
    blocks = [
        {
            "x0": float(block[0]),
            "y0": float(block[1]),
            "x1": float(block[2]),
            "y1": float(block[3]),
            "text": str(block[4]).strip(),
        }
        for block in page.get_text("blocks", sort=False)
        if len(block) >= 5 and int(block[6]) == 0 and str(block[4]).strip()
    ]
    blocks = [
        block for block in blocks
        if not (
            block["y1"] < page_height * 0.04
            or block["y0"] > page_height * 0.94
        )
    ]
    if not blocks:
        return ""

    narrow_blocks = [
        block for block in blocks
        if block["x1"] - block["x0"] <= page_width * 0.62
    ]
    starts = sorted({block["x0"] for block in narrow_blocks})
    gaps = [
        (right - left, left, right)
        for left, right in zip(starts, starts[1:])
        if right - left >= page_width * 0.16
    ]
    gutter = None
    if gaps:
        gap, left, right = max(gaps)
        if gap >= page_width * 0.16:
            gutter = (left + right) / 2

    if gutter is None:
        ordered = sorted(blocks, key=lambda block: (block["y0"], block["x0"]))
    else:
        spanning = sorted(
            (
                block for block in blocks
                if block["x0"] < gutter < block["x1"]
                and block["x1"] - block["x0"] > page_width * 0.5
            ),
            key=lambda block: block["y0"],
        )
        ordered = []
        previous_y = -1.0
        for divider in spanning:
            band = [
                block for block in blocks
                if block not in spanning
                and previous_y <= block["y0"] < divider["y0"]
            ]
            ordered.extend(sorted(
                (
                    block for block in band
                    if (block["x0"] + block["x1"]) / 2 <= gutter
                ),
                key=lambda block: (block["y0"], block["x0"]),
            ))
            ordered.extend(sorted(
                (
                    block for block in band
                    if (block["x0"] + block["x1"]) / 2 > gutter
                ),
                key=lambda block: (block["y0"], block["x0"]),
            ))
            ordered.append(divider)
            previous_y = divider["y1"]
        band = [
            block for block in blocks
            if block not in spanning and block["y0"] >= previous_y
        ]
        ordered.extend(sorted(
            (
                block for block in band
                if (block["x0"] + block["x1"]) / 2 <= gutter
            ),
            key=lambda block: (block["y0"], block["x0"]),
        ))
        ordered.extend(sorted(
            (
                block for block in band
                if (block["x0"] + block["x1"]) / 2 > gutter
            ),
            key=lambda block: (block["y0"], block["x0"]),
        ))

    return "\n".join(block["text"] for block in ordered)


def pdf_metadata(filename, content):
    reader = validate_pdf(filename, content)
    metadata = reader.metadata or {}
    return {
        "title": str(getattr(metadata, "title", "") or metadata.get("/Title", "")).strip(),
        "author": str(getattr(metadata, "author", "") or metadata.get("/Author", "")).strip(),
        "creation_date": str(
            getattr(metadata, "creation_date", "") or metadata.get("/CreationDate", "")
        ).strip(),
    }
