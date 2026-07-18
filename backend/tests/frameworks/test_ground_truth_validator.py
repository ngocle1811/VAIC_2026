import hashlib
import json
from pathlib import Path

from docx import Document

from scripts.validate_ground_truth import APPROVED_MARKER, validate_ground_truth


def _write_registry(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "case_registry.csv").write_text(
        "domain,case_id,scenario,purpose,status\n"
        "tasks,case_01_normal,normal,test,AWAITING_OFFICIAL_INPUT\n",
        encoding="utf-8",
    )
    case = root / "tasks" / "case_01_normal"
    case.mkdir(parents=True)
    return case


def test_scaffold_is_pending_but_structurally_valid(tmp_path: Path) -> None:
    root = tmp_path / "06_ground_truth"
    _write_registry(root)
    summary = validate_ground_truth(root)
    assert summary.planned == 1
    assert summary.pending == 1
    assert summary.errors == ()


def test_require_approved_rejects_scaffold(tmp_path: Path) -> None:
    root = tmp_path / "06_ground_truth"
    _write_registry(root)
    summary = validate_ground_truth(root, require_approved=True)
    assert summary.errors


def test_approved_case_requires_independent_review_and_matching_sources(tmp_path: Path) -> None:
    dataset_root = tmp_path / "dataset"
    root = dataset_root / "06_ground_truth"
    case = _write_registry(root)
    source = dataset_root / "01_input_reports" / "tasks" / "source.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"marker":"SYNTHETIC_TEST_DATA"}', encoding="utf-8")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = {
        "case_id": "case_01_normal",
        "domain": "tasks",
        "ground_truth_status": "APPROVED",
        "approved_for_ground_truth": True,
        "llm_used_as_ground_truth": False,
        "source_files": [
            {
                "relative_path": "01_input_reports/tasks/source.json",
                "sha256": source_hash,
                "deidentified": True,
            }
        ],
        "review": {
            "extractor_id": "reviewer_a",
            "reviewer_id": "reviewer_b",
            "approver_id": "reviewer_c",
            "extracted_at": "2099-01-01T00:00:00Z",
            "reviewed_at": "2099-01-02T00:00:00Z",
            "approved_at": "2099-01-03T00:00:00Z",
            "disagreements_resolved": True,
        },
    }
    (case / "case_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name in ("expected_normalized.json", "expected_validation.json"):
        (case / name).write_text(
            json.dumps(
                {
                    "ground_truth_marker": APPROVED_MARKER,
                    "case_id": "case_01_normal",
                }
            ),
            encoding="utf-8",
        )
    report = Document()
    report.add_paragraph("SYNTHETIC_TEST_DATA — NOT_OFFICIAL")
    report.save(case / "expected_report.docx")

    summary = validate_ground_truth(root, require_approved=True)
    assert summary.approved == 1
    assert summary.errors == ()

    manifest["review"]["reviewer_id"] = "reviewer_a"
    (case / "case_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    invalid = validate_ground_truth(root, require_approved=True)
    assert any("must be different" in error for error in invalid.errors)
