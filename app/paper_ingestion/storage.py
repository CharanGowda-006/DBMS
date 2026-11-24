import hashlib
import os
import re
import uuid
from pathlib import Path, PureWindowsPath

from .pdf_parser import validate_pdf


_STORAGE_KEY = re.compile(r"^[0-9a-f]{32}\.pdf$")
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._ -]+")


def upload_root():
    configured = os.environ.get("RESEARCHNET_UPLOAD_DIR")
    if configured:
        root = Path(configured).expanduser().resolve()
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        root = (base / "ResearchNet" / "paper_uploads").resolve()
    application_root = Path(__file__).resolve().parents[2]
    if root == application_root or application_root in root.parents:
        raise ValueError("PDF storage must be outside the application directory.")
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_original_name(filename):
    base = PureWindowsPath(str(filename or "")).name
    base = Path(base).name
    cleaned = _SAFE_FILENAME.sub("_", base).strip(" .")
    if not cleaned.lower().endswith(".pdf"):
        raise ValueError("Upload a PDF file.")
    return cleaned[:255] or "research-paper.pdf"


def store_pdf(filename, content):
    validate_pdf(filename, content)
    storage_key = f"{uuid.uuid4().hex}.pdf"
    root = upload_root()
    destination = (root / storage_key).resolve()
    if destination.parent != root:
        raise ValueError("The PDF storage key is invalid.")
    with destination.open("xb") as output:
        output.write(content)
    return {
        "storage_key": storage_key,
        "original_filename": safe_original_name(filename),
        "sha256": hashlib.sha256(content).hexdigest(),
        "file_size": len(content),
    }


def read_pdf(storage_key):
    if not isinstance(storage_key, str) or not _STORAGE_KEY.fullmatch(storage_key):
        raise ValueError("The stored PDF reference is invalid.")
    root = upload_root()
    path = (root / storage_key).resolve()
    if path.parent != root:
        raise ValueError("The stored PDF reference is invalid.")
    return path.read_bytes()


def delete_pdf(storage_key):
    if not isinstance(storage_key, str) or not _STORAGE_KEY.fullmatch(storage_key):
        return
    root = upload_root()
    path = (root / storage_key).resolve()
    if path.parent == root:
        path.unlink(missing_ok=True)
