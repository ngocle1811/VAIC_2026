"""Deterministic retrieval metrics for offline evaluation."""

import math


def hit_rate(retrieved: list[str], expected: set[str], k: int) -> float:
    return float(bool(set(retrieved[:k]) & expected)) if expected else 0.0


def recall(retrieved: list[str], expected: set[str], k: int) -> float:
    return len(set(retrieved[:k]) & expected) / len(expected) if expected else 0.0


def precision(retrieved: list[str], expected: set[str], k: int) -> float:
    selected = retrieved[:k]
    return len(set(selected) & expected) / len(selected) if selected else 0.0


def mean_reciprocal_rank(retrieved: list[str], expected: set[str]) -> float:
    return next((1.0 / rank for rank, item in enumerate(retrieved, 1) if item in expected), 0.0)


def ndcg(retrieved: list[str], expected: set[str], k: int) -> float:
    gains = [1.0 if item in expected else 0.0 for item in retrieved[:k]]
    dcg = sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))
    ideal_count = min(len(expected), k)
    ideal = sum(1.0 / math.log2(index + 2) for index in range(ideal_count))
    return dcg / ideal if ideal else 0.0
