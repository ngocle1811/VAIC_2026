"""Deterministic lightweight token estimation without model dependencies."""


def estimate_tokens(text: str) -> int:
    """Conservatively approximate tokens as four Unicode characters each."""
    return max(1, (len(text) + 3) // 4) if text else 0
