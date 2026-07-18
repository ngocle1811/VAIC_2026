"""File-signature checks for user-controlled operational uploads."""

from pathlib import Path
from zipfile import BadZipFile, ZipFile


class UnsafeUploadError(ValueError):
    pass


def validate_operational_file(path: Path, max_bytes: int) -> None:
    if path.stat().st_size > max_bytes:
        raise UnsafeUploadError("uploaded file exceeds configured size limit")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if not path.read_bytes()[:5] == b"%PDF-":
            raise UnsafeUploadError("PDF signature does not match extension")
        return
    if suffix not in {".docx", ".xlsx"}:
        raise UnsafeUploadError("only PDF, DOCX, and XLSX operational files are allowed")
    try:
        with ZipFile(path) as archive:
            names = set(archive.namelist())
    except BadZipFile as exc:
        raise UnsafeUploadError("Office file is not a valid ZIP package") from exc
    required = "word/document.xml" if suffix == ".docx" else "xl/workbook.xml"
    if required not in names or "[Content_Types].xml" not in names:
        raise UnsafeUploadError("Office package content does not match extension")
    if any(
        name.casefold().endswith(("vbaProject.bin".casefold(), ".exe", ".dll")) for name in names
    ):
        raise UnsafeUploadError("active or executable content is not allowed")
