# Evaluation Plan

Current offline retrieval metrics are Hit Rate@K, Recall@K, Precision@K, MRR, and nDCG@K.
Synthetic fixtures verify deterministic mechanics but cannot measure real-domain quality.

Future reviewed datasets must measure:

- extraction and normalization accuracy for all three domains;
- deterministic KPI and rule correctness;
- retrieval relevance and citation accuracy;
- numeric faithfulness of report drafts;
- tool selection, latency, hallucination rate, and human edit rate.

Ground truth must be human-reviewed or copied from explicit approved fixture values. LLM output
must never be promoted to ground truth automatically.

The operational workflow, review roles, case lifecycle, templates, and minimum scenario registry
are maintained in `ubnd_report_dataset/06_ground_truth/README.md`. Scaffold directories are not
approved Ground Truth and must not contribute to quality metrics.
