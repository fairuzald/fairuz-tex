#!/usr/bin/env python3
"""Select reproducible customer-service outline intents for bilingual question slots.

The script samples only from the frozen leaf-outline frame.  Text blocks are not
sampled here; they remain a lookup source for context materialization.  Family
and language are deliberately left open for manual review after the random pick.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

TARGET_SEMANTIC_QUESTIONS = 100
LANGUAGES = ("en", "id")
TARGET_QUESTIONS = TARGET_SEMANTIC_QUESTIONS * len(LANGUAGES)
FLOOR_PER_DOCUMENT = 8
POOL_MULTIPLIER = 2
DEFAULT_SEED = 20260831
PAGE_BINS = ("P1", "P2", "P3", "P4", "P5")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV is empty: {path}")
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_bool(value: str, field: str) -> bool:
    if value.casefold() not in {"true", "false"}:
        raise ValueError(f"{field} must be true/false, got {value!r}")
    return value.casefold() == "true"


def largest_remainder(total: int, weights: dict[str, int], *, minimum: int = 0) -> dict[str, int]:
    """Allocate an integer total using transparent largest-remainder rounding."""

    if not weights or total < sum(minimum for _ in weights):
        raise ValueError("Allocation target is smaller than the requested minimum")
    allocation = {key: minimum for key in weights}
    remaining = total - sum(allocation.values())
    weight_total = sum(max(0, value) for value in weights.values())
    if remaining and weight_total == 0:
        raise ValueError("Cannot allocate remainder with zero total weight")
    raw = {
        key: (remaining * max(0, value) / weight_total if weight_total else 0.0)
        for key, value in weights.items()
    }
    floors = {key: math.floor(value) for key, value in raw.items()}
    for key, value in floors.items():
        allocation[key] += value
    leftover = remaining - sum(floors.values())
    order = sorted(weights, key=lambda key: (-raw[key] + floors[key], key))
    for key in order[:leftover]:
        allocation[key] += 1
    return allocation


def bounded_allocate(
    total: int,
    weights: dict[str, int],
    capacities: dict[str, int],
    *,
    minimum: int = 0,
) -> dict[str, int]:
    """Largest-remainder allocation with explicit per-bin capacity checks."""

    allocation = largest_remainder(total, weights, minimum=minimum)
    if any(allocation[key] > capacities[key] for key in allocation):
        allocation = {key: minimum for key in weights}
        remaining = total - sum(allocation.values())
        while remaining:
            candidates = [key for key in weights if allocation[key] < capacities[key]]
            if not candidates:
                raise ValueError("Cannot satisfy allocation under candidate capacities")
            chosen = max(
                candidates,
                key=lambda key: (
                    weights[key] / max(1, capacities[key]),
                    capacities[key] - allocation[key],
                    key,
                ),
            )
            allocation[chosen] += 1
            remaining -= 1
    return allocation


def select_from_stratum(
    rows: list[dict[str, str]], count: int, *, seed: int, stage: str
) -> list[dict[str, str]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            row.get("filename", ""),
            int(row.get("page_start") or 0),
            row.get("section_path", ""),
            row.get("outline_id", ""),
        ),
    )
    seed_text = f"{seed}|{stage}|{rows[0]['document_id']}|{rows[0].get('page_bin', '')}"
    digest = hashlib.sha256(seed_text.encode()).hexdigest()
    random.Random(int(digest[:16], 16)).shuffle(ordered)
    return ordered[:count]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outline-frame", type=Path, required=True)
    parser.add_argument("--source-frame", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    outlines = read_csv(args.outline_frame)
    source_rows = read_csv(args.source_frame)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if len(outlines) != 1240:
        raise ValueError(f"Expected 1,240 outline candidates, received {len(outlines)}")
    if any(
        not as_bool(row.get("question_outline_allowed", ""), "question_outline_allowed")
        for row in outlines
    ):
        raise ValueError("Outline frame contains a non-eligible row")
    if len({row["outline_id"] for row in outlines}) != len(outlines):
        raise ValueError("outline_id must be unique")
    source_by_id = {row["source_frame_id"]: row for row in source_rows}
    for outline in outlines:
        ids = [value for value in outline.get("direct_source_frame_ids", "").split(";") if value]
        if not ids or any(value not in source_by_id for value in ids):
            raise ValueError(f"Outline {outline['outline_id']} has an unresolved source frame")
    if manifest.get("document_count") != 9 or len(manifest.get("documents", [])) != 9:
        raise ValueError("Manifest does not describe the expected 9-document census")

    by_document: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in outlines:
        by_document[row["document_id"]].append(row)
    if len(by_document) != 9:
        raise ValueError(f"Expected 9 documents, received {len(by_document)}")
    page_counts = {
        document_id: max(int(rows[0].get("page_end") or 0), 1)
        for document_id, rows in by_document.items()
    }
    # Use the frozen corpus page count from the manifest's document inventory when available.
    inventory_path = args.manifest.parent / "document_inventory.csv"
    if inventory_path.exists():
        for row in read_csv(inventory_path):
            if row.get("document_id") in page_counts:
                page_counts[row["document_id"]] = int(
                    row.get("page_count") or page_counts[row["document_id"]]
                )
    document_alloc = largest_remainder(
        TARGET_SEMANTIC_QUESTIONS, page_counts, minimum=FLOOR_PER_DOCUMENT
    )

    by_stratum: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in outlines:
        by_stratum[(row["document_id"], row.get("page_bin", ""))].append(row)
    final_bin_alloc: dict[tuple[str, str], int] = {}
    pool_bin_alloc: dict[tuple[str, str], int] = {}
    for document_id in sorted(by_document):
        bins = {page_bin: by_stratum[(document_id, page_bin)] for page_bin in PAGE_BINS}
        empty = [page_bin for page_bin, rows in bins.items() if not rows]
        if empty:
            raise ValueError(f"{document_id} has empty page-bin candidates: {empty}")
        capacities = {page_bin: len(rows) for page_bin, rows in bins.items()}
        weights = dict(capacities)
        final = bounded_allocate(document_alloc[document_id], weights, capacities, minimum=1)
        pool_target = min(POOL_MULTIPLIER * document_alloc[document_id], sum(capacities.values()))
        pool = bounded_allocate(pool_target, capacities, capacities, minimum=0)
        for page_bin in PAGE_BINS:
            key = (document_id, page_bin)
            final_bin_alloc[key] = final[page_bin]
            pool_bin_alloc[key] = max(final[page_bin], pool[page_bin])
    # Top up pool to exactly 2x target while keeping final as a subset.
    desired_pool = min(POOL_MULTIPLIER * TARGET_SEMANTIC_QUESTIONS, len(outlines))
    while sum(pool_bin_alloc.values()) < desired_pool:
        candidates = [key for key in final_bin_alloc if pool_bin_alloc[key] < len(by_stratum[key])]
        if not candidates:
            raise ValueError("Cannot create the requested 2x candidate pool")
        chosen = max(
            candidates,
            key=lambda key: (len(by_stratum[key]) - pool_bin_alloc[key], key[0], key[1]),
        )
        pool_bin_alloc[chosen] += 1

    pool_rows: list[dict[str, Any]] = []
    semantic_rows: list[dict[str, Any]] = []
    for key in sorted(final_bin_alloc):
        candidates = by_stratum[key]
        pool_selected = select_from_stratum(
            candidates, pool_bin_alloc[key], seed=args.seed, stage="pool"
        )
        final_selected = select_from_stratum(
            pool_selected, final_bin_alloc[key], seed=args.seed + 1, stage="final"
        )
        final_ids = {row["outline_id"] for row in final_selected}
        for rank, row in enumerate(pool_selected, 1):
            pool_rows.append(
                {
                    **row,
                    "stratum_id": f"{row['document_id']}::{row.get('page_bin', '')}",
                    "candidate_rank_in_stratum": rank,
                    "selected_for_question": row["outline_id"] in final_ids,
                    "selection_seed": args.seed,
                    "selection_stage": "outline_random_pick",
                    "review_status": "pending_manual_review",
                }
            )
        for row in final_selected:
            semantic_rows.append(
                {
                    "question_id": "",
                    "outline_frame_id": row["outline_frame_id"],
                    "outline_id": row["outline_id"],
                    "document_id": row["document_id"],
                    "filename": row["filename"],
                    "product_model": row["product_model"],
                    "heading_text": row["heading_text"],
                    "section_path": row["section_path"],
                    "page_start": row["page_start"],
                    "page_end": row["page_end"],
                    "page_bin": row["page_bin"],
                    "direct_source_frame_ids": row["direct_source_frame_ids"],
                    "question_family": "",
                    "language": "",
                    "selection_seed": args.seed,
                    "slot_status": "open",
                    "review_status": "pending_manual_family_review",
                }
            )
    # Sort before assigning IDs so reruns remain deterministic.
    semantic_rows.sort(
        key=lambda row: (
            row["filename"],
            int(row["page_start"]),
            row["section_path"],
            row["outline_id"],
        )
    )
    final_rows: list[dict[str, Any]] = []
    for index, row in enumerate(semantic_rows, 1):
        pair_id = f"Q-{index:03d}"
        for language, question_number in (("en", index), ("id", index + TARGET_SEMANTIC_QUESTIONS)):
            final_rows.append(
                {
                    **row,
                    "question_id": f"Q-{question_number:03d}",
                    "question_pair_id": pair_id,
                    "language": language,
                }
            )
    pool_rows.sort(
        key=lambda row: (
            row["filename"],
            int(row["page_start"]),
            row["section_path"],
            row["outline_id"],
        )
    )
    if (
        len(semantic_rows) != TARGET_SEMANTIC_QUESTIONS
        or len(final_rows) != TARGET_QUESTIONS
        or len(pool_rows) != desired_pool
    ):
        raise AssertionError("Selection count mismatch")

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    pool_fields = list(outlines[0]) + [
        "stratum_id", "candidate_rank_in_stratum", "selected_for_question", "selection_seed",
        "selection_stage", "review_status",
    ]
    slot_fields = list(final_rows[0])
    write_csv(output / "candidate-pool.csv", pool_rows, pool_fields)
    write_csv(output / "question-slots.csv", final_rows, slot_fields)
    report = {
        "process": "02.01-question-budget-and-distribution",
        "seed": args.seed,
        "sampling_unit": "eligible_leaf_outline",
        "sampling_method": "seeded_random_pick_with_document_page_bin_coverage",
        "heuristic_labels_used_for_sampling": False,
        "outline_frame_sha256": sha256_file(args.outline_frame),
        "source_frame_sha256": sha256_file(args.source_frame),
        "manifest_file_sha256": sha256_file(args.manifest),
        "manifest_declared_sha256": manifest.get("manifest_sha256", ""),
        "outline_population": len(outlines),
        "candidate_pool_count": len(pool_rows),
        "semantic_outline_slot_count": len(semantic_rows),
        "question_slot_count": len(final_rows),
        "language_allocations": {language: TARGET_SEMANTIC_QUESTIONS for language in LANGUAGES},
        "question_id_scheme": (
            "Q-001..Q-100 English; Q-101..Q-200 Indonesian; "
            "question_pair_id links translations"
        ),
        "document_allocations": {
            document_id: {
                "page_count": page_counts[document_id],
                "outline_population": len(by_document[document_id]),
                "question_slots": document_alloc[document_id],
                "page_bin_slots": {
                    page_bin: final_bin_alloc[(document_id, page_bin)] for page_bin in PAGE_BINS
                },
                "page_bin_pool": {
                    page_bin: pool_bin_alloc[(document_id, page_bin)] for page_bin in PAGE_BINS
                },
            }
            for document_id in sorted(by_document)
        },
        "family_review": "pending_manual_review",
        "outputs": {
            "candidate_pool": "candidate-pool.csv",
            "question_slots": "question-slots.csv",
        },
    }
    (output / "allocation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
