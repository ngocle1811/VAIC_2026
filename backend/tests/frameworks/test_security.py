from app.security.content_guard import ExternalTransmissionGuard


def test_external_guard_masks_sensitive_shapes_without_logging_values() -> None:
    text = "Contact 0901234567; identifier 123456789012; API key=synthetic-secret"
    result = ExternalTransmissionGuard().inspect(text)
    assert result.allowed
    assert "0901234567" not in result.redacted_text
    assert "123456789012" not in result.redacted_text
    assert "synthetic-secret" not in result.redacted_text
    assert "restoration_map" not in result.model_dump()
    assert "0901234567" not in repr(result)


def test_external_guard_blocks_restricted_document_instead_of_redacting_label() -> None:
    result = ExternalTransmissionGuard().inspect("MẬT\nSYNTHETIC_TEST_DATA")
    assert not result.allowed
    assert result.redacted_text == ""
    assert result.reasons == ["restricted_or_classified_content"]
