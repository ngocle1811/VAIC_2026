"""Validate human-reviewed Ground Truth case structure and approvals."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

APPROVED_MARKER = "HUMAN_REVIEWED_GROUND_TRUTH"
ALLOWED_STATUSES = {"DRAFT", "IN_REVIEW", "APPROVED", "REJECTED"}
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class ValidationSummary:
    planned: int
    approved: int
    pending: int
    errors: tuple[str, ...]


def _read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_source_files(
    manifest: dict[str, object], dataset_root: Path, label: str
) -> list[str]:
    errors: list[str] = []
    source_files = manifest.get("source_files")
    if not isinstance(source_files, list) or not source_files:
        return [f"{label}: approved case requires source_files"]

    for index, source in enumerate(source_files):
        source_label = f"{label}: source_files[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{source_label} must be an object")
            continue
        relative_path = source.get("relative_path")
        expected_hash = source.get("sha256")
        if not isinstance(relative_path, str) or not relative_path:
            errors.append(f"{source_label} requires relative_path")
            continue
        if not isinstance(expected_hash, str) or not SHA256_PATTERN.fullmatch(expected_hash):
            errors.append(f"{source_label} requires a valid SHA-256")
            continue
        resolved = (dataset_root / relative_path).resolve()
        if dataset_root not in resolved.parents:
            errors.append(f"{source_label} escapes dataset root")
            continue
        if not resolved.is_file():
            errors.append(f"{source_label} file not found: {relative_path}")
            continue
        if _sha256(resolved).lower() != expected_hash.lower():
            errors.append(f"{source_label} SHA-256 mismatch")
        if source.get("deidentified") is not True:
            errors.append(f"{source_label} must be explicitly deidentified")
    return errors


def _validate_approved_case(case_path: Path, manifest: dict[str, object]) -> list[str]:
    label = str(case_path)
    errors: list[str] = []
    if manifest.get("approved_for_ground_truth") is not True:
        errors.append(f"{label}: APPROVED case must set approved_for_ground_truth=true")
    if manifest.get("llm_used_as_ground_truth") is not False:
        errors.append(f"{label}: LLM output cannot be Ground Truth")

    review = manifest.get("review")
    if not isinstance(review, dict):
        errors.append(f"{label}: review object is required")
    else:
        extractor = review.get("extractor_id")
        reviewer = review.get("reviewer_id")
        approver = review.get("approver_id")
        if not all(
            isinstance(value, str) and value.strip() for value in (extractor, reviewer, approver)
        ):
            errors.append(f"{label}: extractor, reviewer, and approver IDs are required")
        elif extractor == reviewer:
            errors.append(f"{label}: extractor and reviewer must be different people")
        if review.get("disagreements_resolved") is not True:
            errors.append(f"{label}: disagreements must be resolved")
        for field in ("extracted_at", "reviewed_at", "approved_at"):
            if not review.get(field):
                errors.append(f"{label}: review.{field} is required")

    required = (
        "expected_normalized.json",
        "expected_validation.json",
        "expected_report.docx",
    )
    for name in required:
        path = case_path / name
        if not path.is_file():
            errors.append(f"{label}: missing {name}")

    report_path = case_path / "expected_report.docx"
    if report_path.is_file():
        if not zipfile.is_zipfile(report_path):
            errors.append(f"{label}: expected_report.docx is not a valid DOCX package")
        else:
            with zipfile.ZipFile(report_path) as archive:
                if "word/document.xml" not in archive.namelist():
                    errors.append(f"{label}: expected_report.docx lacks word/document.xml")

    for name in required[:2]:
        path = case_path / name
        if path.is_file():
            try:
                expected = _read_json(path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{label}: invalid {name}: {exc}")
                continue
            if expected.get("ground_truth_marker") != APPROVED_MARKER:
                errors.append(f"{label}: {name} lacks {APPROVED_MARKER}")
            if expected.get("case_id") != manifest.get("case_id"):
                errors.append(f"{label}: {name} case_id mismatch")
    return errors


def validate_ground_truth(root: Path, *, require_approved: bool = False) -> ValidationSummary:
    root = root.resolve()
    dataset_root = root.parent.resolve()
    registry_path = root / "case_registry.csv"
    if not registry_path.is_file():
        return ValidationSummary(0, 0, 0, (f"missing registry: {registry_path}",))

    with registry_path.open(encoding="utf-8", newline="") as stream:
        registry = list(csv.DictReader(stream))

    errors: list[str] = []
    approved = 0
    pending = 0
    for row in registry:
        domain = row.get("domain", "")
        case_id = row.get("case_id", "")
        case_path = root / domain / case_id
        label = f"{domain}/{case_id}"
        if not case_path.is_dir():
            errors.append(f"{label}: case directory missing")
            continue
        manifest_path = case_path / "case_manifest.json"
        if not manifest_path.is_file():
            pending += 1
            if require_approved:
                errors.append(f"{label}: case_manifest.json is required")
            continue
        try:
            manifest = _read_json(manifest_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{label}: invalid manifest: {exc}")
            continue
        status = manifest.get("ground_truth_status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{label}: invalid ground_truth_status {status!r}")
            continue
        if manifest.get("case_id") != case_id or manifest.get("domain") != domain:
            errors.append(f"{label}: manifest identity mismatch")
        if status == "APPROVED":
            approved += 1
            errors.extend(_validate_approved_case(case_path, manifest))
            errors.extend(_validate_source_files(manifest, dataset_root, label))
        else:
            pending += 1
            if manifest.get("approved_for_ground_truth") is True:
                errors.append(f"{label}: non-approved case cannot be marked approved")
            if require_approved:
                errors.append(f"{label}: status is {status}, expected APPROVED")

    return ValidationSummary(len(registry), approved, pending, tuple(errors))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--require-approved", action="store_true")
    args = parser.parse_args()
    summary = validate_ground_truth(args.root, require_approved=args.require_approved)
    print(
        f"planned={summary.planned} approved={summary.approved} "
        f"pending={summary.pending} errors={len(summary.errors)}"
    )
    for error in summary.errors:
        print(f"ERROR: {error}")
    raise SystemExit(1 if summary.errors else 0)


if __name__ == "__main__":
    main()
