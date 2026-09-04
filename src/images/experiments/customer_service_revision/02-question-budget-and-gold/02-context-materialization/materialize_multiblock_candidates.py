#!/usr/bin/env python3
"""Build complete bounded parent-subtree context candidates for LLM authoring.

This stage is deliberately retrieval-free.  It starts from the frozen English
anchor slots, resolves the nearest ancestor heading, and writes one language-neutral
candidate packet per intent.  The same packet is later reused for the English and
Indonesian question pair. The LLM chooses gold evidence from the complete packet;
this script does not choose a fixed evidence count.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

SOFT_TOKEN_LIMIT = 4000
HARD_TOKEN_LIMIT = 8000
EXPECTED_INTENTS = 100


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_context_text(blocks: list[dict[str, Any]]) -> str:
    """Render the complete bounded packet as one labelled authoring string."""

    sections: list[str] = []
    for index, block in enumerate(blocks, 1):
        sections.append(
            "\n".join(
                [
                    f"[CONTEXT BLOCK {index}]",
                    f"block_id: {block['block_id']}",
                    f"section_path: {block['section_path']}",
                    f"page: {block['page_start']}-{block['page_end']}",
                    f"block_role: {block['block_role']}",
                    "text:",
                    block["text"],
                    f"[END CONTEXT BLOCK {index}]",
                ]
            )
        )
    return "\n\n".join(sections)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parent_ids(row: dict[str, str]) -> list[str]:
    return [value for value in row.get("parent_heading_ids", "").split(";") if value]


def token_count(row: dict[str, str]) -> int:
    return int(row.get("token_estimate") or 0)


def choose_parent(
    anchor: dict[str, str],
    source_rows: list[dict[str, str]],
    hard_limit: int,
) -> tuple[str, list[dict[str, str]], str]:
    """Choose the nearest useful ancestor, excluding the immediate leaf heading."""

    ids = parent_ids(anchor)
    by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source_rows:
        if row.get("document_id") != anchor.get("document_id"):
            continue
        for value in parent_ids(row):
            by_id[value].append(row)

    for parent_id in reversed(ids[:-1]):
        descendants = sorted(
            {row["source_frame_id"]: row for row in by_id.get(parent_id, [])}.values(),
            key=lambda row: (int(row.get("block_sequence") or 0), row["block_id"]),
        )
        if not descendants:
            continue
        if sum(token_count(row) for row in descendants) <= hard_limit:
            return parent_id, descendants, "nearest_ancestor_subtree"

        # The ancestor is meaningful but too large.  Keep a deterministic window
        # around the anchor and expand by sequence until the hard budget is met.
        anchor_index = next(
            (index for index, row in enumerate(descendants) if row["block_id"] == anchor["block_id"]),
            0,
        )
        selected = [descendants[anchor_index]]
        left = anchor_index - 1
        right = anchor_index + 1
        while left >= 0 or right < len(descendants):
            choices: list[tuple[int, int, dict[str, str]]] = []
            if left >= 0:
                choices.append((abs(left - anchor_index), left, descendants[left]))
            if right < len(descendants):
                choices.append((abs(right - anchor_index), right, descendants[right]))
            _, index, candidate = min(choices, key=lambda item: (item[0], item[1]))
            if sum(token_count(row) for row in selected) + token_count(candidate) > hard_limit:
                if index < anchor_index:
                    left = -1
                else:
                    right = len(descendants)
                continue
            selected.append(candidate)
            if index < anchor_index:
                left -= 1
            else:
                right += 1
        selected.sort(key=lambda row: (int(row.get("block_sequence") or 0), row["block_id"]))
        if selected:
            return parent_id, selected, "nearest_ancestor_bounded_window"

    # Defensive fallback for a malformed or unusually shallow hierarchy.
    ordered = sorted(
        source_rows,
        key=lambda row: (int(row.get("block_sequence") or 0), row["block_id"]),
    )
    anchor_index = next(
        (index for index, row in enumerate(ordered) if row["block_id"] == anchor["block_id"]),
        0,
    )
    selected = [ordered[anchor_index]]
    if len(ordered) == 1:
        return "fallback_anchor_only", selected, "same_document_anchor_only"
    for distance in range(1, len(ordered)):
        for index in (anchor_index - distance, anchor_index + distance):
            if index < 0 or index >= len(ordered):
                continue
            candidate = ordered[index]
            if sum(token_count(row) for row in selected) + token_count(candidate) > hard_limit:
                continue
            selected.append(candidate)
            if selected:
                selected.sort(key=lambda row: (int(row.get("block_sequence") or 0), row["block_id"]))
                return "fallback_contiguous_window", selected, "same_document_contiguous_window"
    raise ValueError(f"Could not build a context for {anchor['source_frame_id']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outline-frame", type=Path, required=True)
    parser.add_argument("--source-frame", type=Path, required=True)
    parser.add_argument("--question-slots", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--soft-token-limit", type=int, default=SOFT_TOKEN_LIMIT)
    parser.add_argument("--hard-token-limit", type=int, default=HARD_TOKEN_LIMIT)
    args = parser.parse_args()

    outlines = {row["outline_frame_id"]: row for row in read_csv(args.outline_frame)}
    source_rows = read_csv(args.source_frame)
    source_by_id = {row["source_frame_id"]: row for row in source_rows}
    slots = [row for row in read_csv(args.question_slots) if row.get("language", "").casefold() == "en"]
    if len(slots) != EXPECTED_INTENTS:
        raise ValueError(f"Expected {EXPECTED_INTENTS} English anchors, found {len(slots)}")
    if len({row.get("question_pair_id") for row in slots}) != EXPECTED_INTENTS:
        raise ValueError("English anchor slots must have unique question_pair_id values")

    source_by_document: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source_rows:
        if row.get("text", "").strip():
            source_by_document[row["document_id"]].append(row)

    packets: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    for slot in sorted(slots, key=lambda row: row["question_id"]):
        outline = outlines.get(slot.get("outline_frame_id", ""))
        if outline is None:
            raise ValueError(f"Unknown outline for {slot['question_id']}")
        direct_ids = [value for value in slot.get("direct_source_frame_ids", "").split(";") if value]
        if len(direct_ids) != 1 or direct_ids[0] not in source_by_id:
            raise ValueError(f"{slot['question_id']} must have one resolvable anchor block")
        anchor = source_by_id[direct_ids[0]]
        parent_id, candidates, method = choose_parent(
            anchor,
            source_by_document[anchor["document_id"]],
            args.hard_token_limit,
        )
        total_tokens = sum(token_count(row) for row in candidates)
        if total_tokens > args.hard_token_limit:
            raise ValueError(f"{slot['question_id']} exceeds hard token limit: {total_tokens}")
        packet_blocks: list[dict[str, Any]] = []
        for row in candidates:
            role = "anchor" if row["block_id"] == anchor["block_id"] else "parent_subtree_child"
            block = {
                "block_id": row["block_id"],
                "source_frame_id": row["source_frame_id"],
                "document_id": row["document_id"],
                "filename": row["filename"],
                "product_model": row["product_model"],
                "block_type": row.get("block_type", ""),
                "block_role": role,
                "section_path": row.get("section_path", ""),
                "parent_heading_ids": parent_ids(row),
                "page_start": int(row.get("page_start") or 0),
                "page_end": int(row.get("page_end") or 0),
                "block_sequence": int(row.get("block_sequence") or 0),
                "char_start": int(row.get("char_start") or 0),
                "char_end": int(row.get("char_end") or 0),
                "token_estimate": token_count(row),
                "text_sha256": row.get("text_sha256", ""),
                "text": row.get("text", "").strip(),
            }
            packet_blocks.append(block)
            selection_rows.append(
                {
                    "question_pair_id": slot["question_pair_id"],
                    "anchor_question_id": slot["question_id"],
                    "outline_frame_id": slot["outline_frame_id"],
                    "document_id": row["document_id"],
                    "filename": row["filename"],
                    "product_model": row["product_model"],
                    "parent_heading_id": parent_id,
                    "block_id": row["block_id"],
                    "source_frame_id": row["source_frame_id"],
                    "block_role": role,
                    "section_path": row.get("section_path", ""),
                    "page_start": row.get("page_start", ""),
                    "page_end": row.get("page_end", ""),
                    "block_sequence": row.get("block_sequence", ""),
                    "token_estimate": row.get("token_estimate", ""),
                    "selection_method": method,
                    "selection_status": "candidate",
                    "selection_reason": "anchor_or_parent_subtree_child",
                }
            )
        context_text = build_context_text(packet_blocks)
        packets.append(
            {
                "question_pair_id": slot["question_pair_id"],
                "anchor_question_id": slot["question_id"],
                "outline_frame_id": slot["outline_frame_id"],
                "document_id": slot["document_id"],
                "filename": slot["filename"],
                "product_model": slot["product_model"],
                "section_path": slot["section_path"],
                "parent_heading_id": parent_id,
                "candidate_block_count": len(packet_blocks),
                "candidate_token_estimate": total_tokens,
                "soft_token_limit": args.soft_token_limit,
                "hard_token_limit": args.hard_token_limit,
                "selection_method": method,
                "candidate_block_ids": [block["block_id"] for block in packet_blocks],
                "candidate_blocks": packet_blocks,
                "context_text": context_text,
                "context_text_sha256": hashlib.sha256(context_text.encode("utf-8")).hexdigest(),
                "packet_status": "ready" if total_tokens <= args.soft_token_limit else "ready_over_soft_limit",
            }
        )

    output = args.output_dir
    write_csv(output / "context-selection.csv", selection_rows)
    write_jsonl(output / "context-packets.jsonl", packets)
    manifest = {
        "process": "02.02-context-materialization-multiblock-candidates",
        "question_pair_count": len(packets),
        "language_slot_count": len(packets) * 2,
        "candidate_block_count": len(selection_rows),
        "candidate_packet_count": len(packets),
        "candidate_block_minimum": 1,
        "gold_block_count": "variable; selected by authoring model from context_text",
        "context_text_field": "context_text",
        "soft_token_limit": args.soft_token_limit,
        "hard_token_limit": args.hard_token_limit,
        "random_selection_used": False,
        "retrieval_used": False,
        "inputs": {
            "outline_frame": args.outline_frame.as_posix(),
            "source_frame": args.source_frame.as_posix(),
            "question_slots": args.question_slots.as_posix(),
            "outline_frame_sha256": sha256_file(args.outline_frame),
            "source_frame_sha256": sha256_file(args.source_frame),
            "question_slots_sha256": sha256_file(args.question_slots),
        },
        "outputs": {
            "context_selection": "context-selection.csv",
            "context_packets": "context-packets.jsonl",
        },
    }
    (output / "context-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
