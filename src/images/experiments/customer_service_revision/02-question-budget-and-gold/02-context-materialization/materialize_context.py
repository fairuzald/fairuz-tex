#!/usr/bin/env python3
"""Materialize bounded context packets from approved customer outline slots.

The canonical source is the frozen source-frame CSV. For each selected leaf
outline, this script includes the direct text block and carries the parent path
as metadata. No retrieval, embedding, chunker, or second random selection is involved.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

SOFT_TOKEN_LIMIT = 4_000
HARD_TOKEN_LIMIT = 8_000
SELECTION_METHOD = "deterministic_direct_block_materialization"


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def token_estimate(text: str) -> int:
    return max(1, math.ceil(len(text.split()) * 1.30))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outline-frame", type=Path, required=True)
    parser.add_argument("--source-frame", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--question-slots", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    outlines = read_csv(args.outline_frame)
    source_rows = read_csv(args.source_frame)
    slots = read_csv(args.question_slots)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if len(slots) != 200 or len({row.get("question_id") for row in slots}) != 200:
        raise ValueError("question-slots.csv must contain 200 unique question IDs")
    outline_by_id = {row["outline_frame_id"]: row for row in outlines}
    source_by_id = {row["source_frame_id"]: row for row in source_rows}
    if len(outline_by_id) != len(outlines) or len(source_by_id) != len(source_rows):
        raise ValueError("Outline/source frame IDs must be unique")
    if manifest.get("document_count") != 9:
        raise ValueError("Manifest does not describe the 9-document census")

    packet_rows: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    for slot in sorted(slots, key=lambda row: row["question_id"]):
        outline = outline_by_id.get(slot.get("outline_frame_id", ""))
        if outline is None:
            raise ValueError(f"{slot['question_id']} references an unknown outline_frame_id")
        if (
            outline["document_id"] != slot["document_id"]
            or outline["outline_id"] != slot["outline_id"]
        ):
            raise ValueError(f"{slot['question_id']} outline/document provenance mismatch")
        direct_ids = [
            value for value in outline.get("direct_source_frame_ids", "").split(";") if value
        ]
        if not direct_ids or any(value not in source_by_id for value in direct_ids):
            raise ValueError(f"{slot['question_id']} has unresolved direct source IDs")
        if any(
            source_by_id[value]["document_id"] != outline["document_id"] for value in direct_ids
        ):
            raise ValueError(f"{slot['question_id']} crosses document boundaries")

        # Use the selected leaf block as evidence; retain parent headings only as metadata.
        selected_ids = set(direct_ids)
        selected_blocks: list[dict[str, Any]] = []
        for source_id in sorted(
            selected_ids,
            key=lambda value: (int(source_by_id[value].get("block_sequence") or 0), value),
        ):
            source = source_by_id[source_id]
            text = source.get("text", "").strip()
            if not text:
                raise ValueError(f"{slot['question_id']} resolves an empty source block")
            if int(source.get("char_end") or 0) < int(source.get("char_start") or 0):
                raise ValueError(f"{slot['question_id']} has invalid character offsets")
            role = "outline_direct" if source_id in direct_ids else "ancestor_context"
            selected_blocks.append(
                {
                    "source_frame_id": source_id,
                    "block_id": source["block_id"],
                    "block_role": role,
                    "document_id": source["document_id"],
                    "filename": source["filename"],
                    "section_path": source.get("section_path", ""),
                    "page_start": int(source.get("page_start") or 0),
                    "page_end": int(source.get("page_end") or 0),
                    "block_sequence": int(source.get("block_sequence") or 0),
                    "text_block_sequence": int(source.get("text_block_sequence") or 0),
                    "char_start": int(source.get("char_start") or 0),
                    "char_end": int(source.get("char_end") or 0),
                    "text_sha256": source["text_sha256"],
                    "text": text,
                    "token_estimate": int(source.get("token_estimate") or token_estimate(text)),
                }
            )
        context_text = "\n\n".join(
            f"[{block['filename']} | {block['section_path']} | "
            f"halaman {block['page_start']}–{block['page_end']}]\n{block['text']}"
            for block in selected_blocks
        )
        total_tokens = token_estimate(context_text)
        if total_tokens > HARD_TOKEN_LIMIT:
            raise ValueError(
                f"{slot['question_id']} exceeds the {HARD_TOKEN_LIMIT}-token hard limit: "
                f"{total_tokens}"
            )
        packet_status = "ready" if total_tokens <= HARD_TOKEN_LIMIT else "needs_more_context"
        packet_rows.append(
            {
                "question_id": slot["question_id"],
                "outline_frame_id": outline["outline_frame_id"],
                "outline_id": outline["outline_id"],
                "document_id": outline["document_id"],
                "filename": outline["filename"],
                "product_model": outline["product_model"],
                "heading_text": outline["heading_text"],
                "section_path": outline["section_path"],
                "parent_section_path": outline.get("parent_section_path", "[ROOT]"),
                "page_start": int(outline["page_start"]),
                "page_end": int(outline["page_end"]),
                "question_family": slot.get("question_family", ""),
                "language": slot.get("language", ""),
                "selection_method": SELECTION_METHOD,
                "packet_status": packet_status,
                "token_estimate": total_tokens,
                "soft_token_limit": SOFT_TOKEN_LIMIT,
                "hard_token_limit": HARD_TOKEN_LIMIT,
                "source_frame_ids": [block["source_frame_id"] for block in selected_blocks],
                "source_block_ids": [block["block_id"] for block in selected_blocks],
                "context_blocks": selected_blocks,
                "context_text": context_text,
            }
        )
        for block in selected_blocks:
            selection_rows.append(
                {
                    "question_id": slot["question_id"],
                    "outline_frame_id": outline["outline_frame_id"],
                    "outline_id": outline["outline_id"],
                    "heading_text": outline["heading_text"],
                    "section_path": outline["section_path"],
                    **{key: block[key] for key in block if key not in {"text", "token_estimate"}},
                    "selection_method": SELECTION_METHOD,
                    "selection_status": "selected",
                    "rejection_reason": "",
                }
            )

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    selection_fields = list(selection_rows[0])
    write_csv(output / "context-selection.csv", selection_rows, selection_fields)
    write_jsonl(output / "context-packets.jsonl", packet_rows)
    input_hashes = {
        "outline_frame_sha256": sha256_file(args.outline_frame),
        "source_frame_sha256": sha256_file(args.source_frame),
        "manifest_file_sha256": sha256_file(args.manifest),
        "manifest_declared_sha256": manifest.get("manifest_sha256", ""),
        "question_slots_sha256": sha256_file(args.question_slots),
    }
    context_manifest = {
        "process": "02.02-context-materialization",
        "selection_method": SELECTION_METHOD,
        "random_selection_used": False,
        "question_slot_count": len(slots),
        "packet_count": len(packet_rows),
        "packet_ready_count": sum(row["packet_status"] == "ready" for row in packet_rows),
        "packet_needs_more_context_count": sum(
            row["packet_status"] != "ready" for row in packet_rows
        ),
        "source_block_count": len(selection_rows),
        "soft_token_limit": SOFT_TOKEN_LIMIT,
        "hard_token_limit": HARD_TOKEN_LIMIT,
        "input_hashes": input_hashes,
        "outputs": {
            "context_selection": "context-selection.csv",
            "context_packets": "context-packets.jsonl",
        },
    }
    write_json(output / "context-manifest.json", context_manifest)
    print(json.dumps(context_manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
