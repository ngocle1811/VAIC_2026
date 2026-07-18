import json
from pathlib import Path

import pytest

from tests.frameworks.conftest import load_synthetic_pair


@pytest.mark.parametrize("domain", ["population", "complaints", "tasks"])
def test_synthetic_input_and_ground_truth_are_explicitly_paired(domain: str) -> None:
    input_data, ground_truth = load_synthetic_pair(domain)
    assert input_data["data_label"] == "SYNTHETIC_TEST_DATA"
    assert ground_truth["ground_truth_label"] == "NOT_OFFICIAL"
    assert ground_truth["derivation"] == "explicit_fixture_copy"
    assert ground_truth["expected_values"] == input_data["values"]
    serialized = json.dumps((input_data, ground_truth), ensure_ascii=False).casefold()
    assert "cccd" not in serialized and "phone" not in serialized


def test_dataset_manifest_declares_synthetic_policy() -> None:
    path = Path(__file__).parents[3] / "dataset" / "dataset_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["synthetic_policy"]["contains_real_personal_data"] is False
    assert manifest["synthetic_policy"]["llm_generated_ground_truth"] is False
