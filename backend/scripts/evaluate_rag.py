"""Offline metric evaluation for saved retrieval result identifiers."""

import argparse
import json
from pathlib import Path

from app.rag.evaluation.metrics import hit_rate, mean_reciprocal_rank, ndcg, precision, recall


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="JSON list with retrieved and expected IDs")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    rows = json.loads(args.dataset.read_text(encoding="utf-8"))
    metrics = []
    for row in rows:
        retrieved = row["retrieved_ids"]
        expected = set(row["expected_ids"])
        metrics.append(
            {
                "hit_rate": hit_rate(retrieved, expected, args.k),
                "recall": recall(retrieved, expected, args.k),
                "precision": precision(retrieved, expected, args.k),
                "mrr": mean_reciprocal_rank(retrieved, expected),
                "ndcg": ndcg(retrieved, expected, args.k),
            }
        )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
