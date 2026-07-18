"""Conservative PII masking and restricted-content blocking."""

import re

from pydantic import BaseModel, Field

_CLASSIFIED = re.compile(r"(?im)^\s*(?:TUYỆT\s+MẬT|TỐI\s+MẬT|MẬT)\s*$")
_PHONE = re.compile(r"(?<!\d)(?:\+84|0)(?:\d[ .-]?){8,10}(?!\d)")
_IDENTIFIER = re.compile(r"(?<!\d)\d{12}(?!\d)")
_API_KEY = re.compile(r"(?i)(?:api[_ -]?key|authorization)\s*[:=]\s*\S+")
_WINDOWS_PATH = re.compile(r"(?i)\b[A-Z]:\\[^\r\n]+")


class TransmissionDecision(BaseModel):
    allowed: bool
    redacted_text: str
    reasons: list[str] = Field(default_factory=list)
    restoration_map: dict[str, str] = Field(default_factory=dict, exclude=True, repr=False)


class ExternalTransmissionGuard:
    def inspect(self, text: str, *, restricted: bool = False) -> TransmissionDecision:
        if restricted or _CLASSIFIED.search(text):
            return TransmissionDecision(
                allowed=False,
                redacted_text="",
                reasons=["restricted_or_classified_content"],
            )
        redacted = text
        restoration: dict[str, str] = {}
        reasons = []
        for label, pattern in (
            ("PHONE", _PHONE),
            ("IDENTIFIER", _IDENTIFIER),
            ("SECRET", _API_KEY),
            ("LOCAL_PATH", _WINDOWS_PATH),
        ):
            matches = list(pattern.finditer(redacted))
            for match in reversed(matches):
                token = f"[{label}_{len(restoration) + 1}]"
                restoration[token] = match.group(0)
                redacted = redacted[: match.start()] + token + redacted[match.end() :]
            if matches:
                reasons.append(f"masked_{label.lower()}")
        return TransmissionDecision(
            allowed=True,
            redacted_text=redacted,
            reasons=reasons,
            restoration_map=restoration,
        )
