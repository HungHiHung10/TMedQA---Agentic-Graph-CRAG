import os
from pathlib import Path
from typing import List

from modules.settings import FILES, USER_SOURCES_DIR
from modules.ingestion.loaders import load_document_text
from modules.ingestion.splitters import SOURCE_NAMES, split_sections

SUPPORTED_USER_SOURCE_EXTS = {".docx", ".txt", ".md"}
DELETED_USER_SOURCES_FILE = USER_SOURCES_DIR / ".deleted_sources.txt"


def deleted_sources() -> set[str]:
    if not DELETED_USER_SOURCES_FILE.exists():
        return set()
    try:
        return {
            line.strip()
            for line in DELETED_USER_SOURCES_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip()
        }
    except Exception:
        return set()


def mark_deleted(filename: str) -> None:
    USER_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    deleted = deleted_sources()
    deleted.add(Path(filename).name)
    DELETED_USER_SOURCES_FILE.write_text("\n".join(sorted(deleted)) + "\n", encoding="utf-8")


def restore_source(filename: str) -> None:
    deleted = deleted_sources()
    safe_name = Path(filename).name
    if safe_name in deleted:
        deleted.remove(safe_name)
        DELETED_USER_SOURCES_FILE.write_text("\n".join(sorted(deleted)) + "\n", encoding="utf-8")


def safe_filename(path: str) -> str:
    name = Path(path).name or "source"
    clean = "".join(ch if ch.isalnum() or ch in "._ -" else "_" for ch in name).strip(" ._")
    return clean or "source"


def uploaded_names() -> List[str]:
    USER_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    names = []
    deleted = deleted_sources()
    for path_obj in sorted(USER_SOURCES_DIR.iterdir(), key=lambda item: item.name.lower()):
        if not path_obj.is_file() or path_obj.name.startswith("~$") or path_obj.name == "test-user-source.txt":
            continue
        if path_obj.name in deleted:
            continue
        if path_obj.suffix.lower() in SUPPORTED_USER_SOURCE_EXTS:
            names.append(path_obj.name)
    return names


def split_uploads():
    USER_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    chunks = []
    deleted = deleted_sources()
    for path_obj in sorted(USER_SOURCES_DIR.iterdir(), key=lambda item: item.name.lower()):
        if not path_obj.is_file() or path_obj.name.startswith("~$") or path_obj.name == "test-user-source.txt" or path_obj.name in deleted:
            continue

        ext = path_obj.suffix.lower()
        if ext not in SUPPORTED_USER_SOURCE_EXTS:
            print(f"[WARNING] Skip unsupported uploaded source: {path_obj.name}")
            continue

        try:
            print(f"[PROCESS] Processing uploaded source: {path_obj.name}")
            raw_text = load_document_text(str(path_obj))
            source_id = f"user:{path_obj.name}"
            source_chunks = split_sections(
                text=raw_text,
                source_id=source_id,
                title=path_obj.name,
                splitter="user_upload",
            )
            print(f"[INFO] {source_id}: {len(source_chunks)} chunks")
            chunks.extend(source_chunks)
        except Exception as exc:
            print(f"[WARNING] Could not process uploaded source {path_obj.name}: {exc}")

    return chunks


def list_sources():
    rows = []
    for file_key, path in FILES.items():
        if file_key in {"eval_json", "predictions"}:
            continue
        exists = os.path.exists(path)
        rows.append({
            "kind": "Built-in",
            "name": SOURCE_NAMES.get(file_key, file_key),
            "path": str(path),
            "status": "Available" if exists else "Missing",
        })

    USER_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    deleted = deleted_sources()
    for path_obj in sorted(USER_SOURCES_DIR.iterdir(), key=lambda item: item.name.lower()):
        if not path_obj.is_file() or path_obj.name.startswith("~$") or path_obj.name == "test-user-source.txt" or path_obj.name in deleted:
            continue
        status = "Available" if path_obj.suffix.lower() in SUPPORTED_USER_SOURCE_EXTS else "Unsupported"
        rows.append({
            "kind": "Uploaded",
            "name": path_obj.name,
            "path": str(path_obj),
            "status": status,
        })
    return rows


# Backward-compatible names for UI and older notebooks.
list_deleted_uploaded_sources = deleted_sources
deleted_user_source_names = deleted_sources
_deleted_user_source_names = deleted_sources
mark_uploaded_source_deleted = mark_deleted
mark_user_source_deleted = mark_deleted
restore_uploaded_source = restore_source
unmark_user_source_deleted = restore_source
sanitize_uploaded_filename = safe_filename
safe_upload_name = safe_filename
_safe_filename = safe_filename
list_uploaded_source_names = uploaded_names
uploaded_source_names = uploaded_names
split_uploaded_sources = split_uploads
split_user_sources = split_uploads
list_available_sources = list_sources
list_source_inventory = list_sources