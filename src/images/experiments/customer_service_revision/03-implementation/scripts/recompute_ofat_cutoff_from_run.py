#!/usr/bin/env python3
"""Recompute OFAT cutoff metrics from completed retrieval traces offline."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import statistics
from pathlib import Path
from typing import Any


CUTOFFS = tuple(range(5, 61, 5))
CHUNKER_CONDITIONS = (
    "baseline-generic-hybrid",
    "chunker-generic-recursive",
    "chunker-generic-sliding-window",
)
INDEXER_CONDITIONS = (
    "baseline-generic-hybrid",
    "indexer-generic-sparse",
    "indexer-generic-dense",
)


def load_analyzer() -> Any:
    path = Path(__file__).with_name("analyze_multiblock_retrieval.py")
    spec = importlib.util.spec_from_file_location("customer_multiblock_analyzer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profile-set", choices=("chunker", "indexer"), required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise SystemExit(f"Output directory already exists: {args.output_dir}")

    manifest = json.loads((args.run_dir / "run-manifest.json").read_text(encoding="utf-8"))
    profiles = {
        str(item["condition_id"]): str(item["profile_id"])
        for item in manifest.get("conditions", [])
        if item.get("condition_id") and item.get("profile_id")
    }
    conditions = CHUNKER_CONDITIONS if args.profile_set == "chunker" else INDEXER_CONDITIONS
    analyzer = load_analyzer()
    rows: list[dict[str, Any]] = []
    for condition in conditions:
        source = args.run_dir / condition / "per-question-results.jsonl"
        if not source.exists():
            raise FileNotFoundError(source)
        with source.open(encoding="utf-8") as handle:
            condition_rows = [json.loads(line) for line in handle if line.strip()]
        if len(condition_rows) != 200:
            raise ValueError(f"{condition} has {len(condition_rows)} rows; expected 200")
        for raw in condition_rows:
            item: dict[str, Any] = {
                "condition_id": condition,
                "profile_id": profiles.get(condition, ""),
                "question_id": raw.get("question_id", ""),
                "question_pair_id": raw.get("question_pair_id", ""),
                "language": raw.get("language", ""),
                "question_family": raw.get("question_family", ""),
                "retrieved_count": int(raw.get("retrieved_count") or 0),
                "retrieval_empty": bool(raw.get("retrieval_empty", False)),
                "elapsed_ms": float(raw.get("elapsed_ms") or 0.0),
            }
            for cutoff in CUTOFFS:
                scored = analyzer.score(raw, cutoff)
                item[f"evidence_recall@{cutoff}"] = scored["gold_block_recall"]
                item[f"evidence_precision@{cutoff}"] = scored["chunk_precision"]
                item[f"ndcg@{cutoff}"] = scored["chunk_ndcg"]
            rows.append(item)

    args.output_dir.mkdir(parents=True)
    with (args.output_dir / "per-question-cutoff-results.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    aggregates: list[dict[str, Any]] = []
    for condition in conditions:
        condition_rows = [row for row in rows if row["condition_id"] == condition]
        for cutoff in CUTOFFS:
            aggregates.append(
                {
                    "condition_id": condition,
                    "profile_id": profiles.get(condition, ""),
                    "cutoff_k": cutoff,
                    "question_count": len(condition_rows),
                    "empty_retrieval_count": sum(bool(row["retrieval_empty"]) for row in condition_rows),
                    "evidence_recall": statistics.fmean(row[f"evidence_recall@{cutoff}"] for row in condition_rows),
                    "evidence_precision": statistics.fmean(row[f"evidence_precision@{cutoff}"] for row in condition_rows),
                    "ndcg": statistics.fmean(row[f"ndcg@{cutoff}"] for row in condition_rows),
                    "median_latency_ms": statistics.median(row["elapsed_ms"] for row in condition_rows),
                }
            )
    write_csv(args.output_dir / "cutoff-metrics.csv", aggregates)
    (args.output_dir / "analysis-manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "analysis": "customer-service-ofat-cutoff-recomputed-from-multiblock-traces",
                "profile_set": args.profile_set,
                "source_run": str(args.run_dir),
                "question_count": 200,
                "question_sha256": manifest.get("question_sha256", ""),
                "gold_sha256": manifest.get("gold_sha256", ""),
                "cutoffs": list(CUTOFFS),
                "conditions": profiles,
                "metric_definitions": {
                    "evidence_recall": "complete gold-block coverage",
                    "evidence_precision": "hit chunks divided by returned chunks",
                    "ndcg": "binary chunk relevance ranked directly",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output_dir": str(args.output_dir), "profile_set": args.profile_set, "rows": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
