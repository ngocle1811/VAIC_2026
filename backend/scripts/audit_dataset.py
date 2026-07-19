"""Audit the team dataset without changing, moving, or classifying files as official."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from app.operational_data.extraction import RepositoryOperationalExtractor
from app.operational_data.models import OperationalDomain
from app.operational_data.validation import SyntheticOperationalValidator

SUPPORTED = {".pdf", ".docx", ".xlsx"}


def audit(root: Path) -> dict:
    input_root = root / "01_input_reports"
    files = sorted(path for path in input_root.rglob("*") if path.suffix.lower() in SUPPORTED)
    hashes: dict[str, list[str]] = {}
    records = []
    format_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    validation_counts: Counter[str] = Counter()
    synthetic_name_hits = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        domain = OperationalDomain(path.relative_to(input_root).parts[0])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes.setdefault(digest, []).append(relative)
        report = RepositoryOperationalExtractor().extract(path, domain)
        validation = SyntheticOperationalValidator().validate(report)
        format_counts[path.suffix.lower().lstrip(".")] += 1
        domain_counts[domain.value] += 1
        validation_counts["errors"] += len(validation.errors)
        validation_counts["warnings"] += len(validation.warnings)
        loader = {
            ".pdf": RepositoryOperationalExtractor._pdf,
            ".docx": RepositoryOperationalExtractor._docx,
            ".xlsx": RepositoryOperationalExtractor._xlsx,
        }[path.suffix.lower()]
        _, text, _ = loader(path)
        if re.search(r"Nguyễn\s+Văn\s+A", text, re.I):
            synthetic_name_hits.append(relative)
        records.append(
            {
                "path": relative,
                "sha256": digest,
                "domain": domain.value,
                "format": path.suffix.lower().lstrip("."),
                "classification": report.metadata.classification.value,
                "canonical_value_count": len(report.values),
                "record_count": len(report.records),
                "error_codes": [item.code for item in validation.errors],
                "warning_codes": [item.code for item in validation.warnings],
            }
        )
    duplicate_groups = [paths for paths in hashes.values() if len(paths) > 1]
    required_dirs = [
        "01_input_reports",
        "02_master_data",
        "03_knowledge_base",
        "04_templates",
        "05_rules",
        "06_ground_truth",
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_root": str(root.resolve()),
        "mutation_performed": False,
        "ground_truth_status": "DEFERRED_BY_USER",
        "summary": {
            "required_directories_present": all((root / item).is_dir() for item in required_dirs),
            "operational_file_count": len(files),
            "domain_counts": dict(domain_counts),
            "format_counts": dict(format_counts),
            "duplicate_hash_group_count": len(duplicate_groups),
            "validation_error_count": validation_counts["errors"],
            "validation_warning_count": validation_counts["warnings"],
            "approved_ground_truth_case_count": 0,
            "official_operational_input_count": 0,
        },
        "pii_risk": {
            "real_pii_verified": False,
            "synthetic_person_name_marker": "Nguyễn Văn A",
            "files_with_synthetic_person_name": synthetic_name_hits,
            "action": "keep external transmission disabled and review before production use",
        },
        "duplicate_groups": duplicate_groups,
        "operational_files": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = audit(arguments.dataset_root)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
