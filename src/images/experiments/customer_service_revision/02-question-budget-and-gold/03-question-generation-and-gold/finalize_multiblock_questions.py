#!/usr/bin/env python3
"""Freeze the LLM-authored bilingual question set and variable-size gold evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
RUN = ROOT / "experiments/offline-rag-experiments/customer_service_revision/02-question-budget-and-gold"
DRAFT = RUN / "03-question-generation-and-gold/runs/selection-v2-multiblock/00-draft/llm-question-candidates.jsonl"
PACKETS = RUN / "02-context-materialization/runs/selection-v2-multiblock/context-packets.jsonl"
SOURCE = RUN / "../01-target-corpus-size/01-corpus-eda/question_source_frame.csv"
OUT = RUN / "03-question-generation-and-gold/runs/selection-v2-multiblock"
AUDIT = OUT / "00-draft/database-context-audit.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    drafts = read_jsonl(DRAFT)
    packets = {}
    with PACKETS.open(encoding="utf-8") as handle:
        for line in handle:
            packet = json.loads(line)
            packets[packet["question_pair_id"]] = packet
    source = {row["block_id"]: row for row in read_csv(SOURCE)}
    if len(drafts) != 100 or len(packets) != 100:
        raise SystemExit("Expected exactly 100 LLM draft rows and 100 context packets")

    question_rows: list[dict[str, str]] = []
    candidate_rows: list[dict] = []
    review_rows: list[dict[str, str]] = []
    gold_rows: list[dict] = []
    context_rows: list[dict] = []
    pair_ids: set[str] = set()
    for draft in sorted(drafts, key=lambda row: int(row["question_pair_id"].split("-")[-1])):
        pair_id = draft["question_pair_id"]
        if pair_id in pair_ids:
            raise SystemExit(f"Duplicate pair: {pair_id}")
        pair_ids.add(pair_id)
        packet = packets[pair_id]
        candidate_ids = [str(value) for value in draft.get("evidence_block_ids", [])]
        if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
            raise SystemExit(f"Pair {pair_id} has an empty or duplicate evidence list")
        blocks = {block["block_id"]: block for block in packet["candidate_blocks"]}
        evidence = []
        for index, block_id in enumerate(candidate_ids, 1):
            block = blocks.get(block_id)
            source_row = source.get(block_id)
            if block is None or source_row is None:
                raise SystemExit(f"Pair {pair_id} has a block outside the audited source frame")
            for field in ("source_frame_id", "text_sha256", "document_id", "page_start", "page_end", "char_start", "char_end"):
                if str(block[field]) != str(source_row[field]):
                    raise SystemExit(f"Pair {pair_id} provenance mismatch for {block_id}: {field}")
            evidence.append({
                "evidence_id": f"{pair_id}-E{index}",
                "source_frame_id": block["source_frame_id"],
                "block_id": block_id,
                "document_id": block["document_id"],
                "page_start": int(block["page_start"]),
                "page_end": int(block["page_end"]),
                "char_start": int(block["char_start"]),
                "char_end": int(block["char_end"]),
                "text_sha256": block["text_sha256"],
                "quote": block["text"],
            })
        if any(item["document_id"] != evidence[0]["document_id"] for item in evidence[1:]):
            raise SystemExit(f"Pair {pair_id} crosses documents")
        common = {
            "question_pair_id": pair_id,
            "outline_frame_id": draft["outline_frame_id"],
            "document_id": draft["document_id"],
            "filename": draft["filename"],
            "product_model": draft["product_model"],
            "section_path": draft["section_path"],
            "question_family": draft["question_family"],
            "evidence_block_ids": json.dumps(candidate_ids, ensure_ascii=False),
            "review_status": "codex_selected_provenance_checked",
        }
        en_row = {
            "question_id": pair_id,
            **common,
            "language": "en",
            "question": draft["question_en"],
            "answer": draft["reference_answer_en"],
        }
        id_number = 100 + int(pair_id.split("-")[-1])
        id_row = {
            "question_id": f"Q-{id_number:03d}",
            **common,
            "language": "id",
            "question": draft["question_id_text"],
            "answer": draft["reference_answer_id"],
        }
        question_rows.extend([en_row, id_row])
        candidate_rows.extend([
            {**en_row, "reference_answer": draft["reference_answer_en"], "evidence": evidence, "authoring_source": draft["authoring_source"]},
            {**id_row, "reference_answer": draft["reference_answer_id"], "evidence": evidence, "authoring_source": draft["authoring_source"]},
        ])
        review_rows.extend([
            {"question_id": pair_id, "question_pair_id": pair_id, "language": "en", "evidence_count": str(len(evidence)), "review_status": "codex_selected_provenance_checked", "review_basis": draft["evidence_rationale"]},
            {"question_id": f"Q-{id_number:03d}", "question_pair_id": pair_id, "language": "id", "evidence_count": str(len(evidence)), "review_status": "codex_selected_provenance_checked", "review_basis": "Same variable evidence set as English pair; exact provenance checked."},
        ])
        for question_id, language, question in ((pair_id, "en", draft["question_en"]), (f"Q-{id_number:03d}", "id", draft["question_id_text"])):
            gold_rows.append({
                "question_id": question_id,
                "question_pair_id": pair_id,
                "outline_frame_id": draft["outline_frame_id"],
                "question_family": draft["question_family"],
                "language": language,
                "reference_answer": draft["reference_answer_en"] if language == "en" else draft["reference_answer_id"],
                "gold_evidence": evidence,
                "review_status": "codex_selected_provenance_checked",
            })
            context_rows.append({
                "question_id": question_id,
                "question_pair_id": pair_id,
                "language": language,
                "question": question,
                "question_family": draft["question_family"],
                "outline_frame_id": draft["outline_frame_id"],
                "candidate_block_ids": packet["candidate_block_ids"],
                "context_text": packet["context_text"],
                "evidence_block_ids": candidate_ids,
            })

    question_rows.sort(key=lambda row: row["question_id"])
    candidate_rows.sort(key=lambda row: row["question_id"])
    review_rows.sort(key=lambda row: row["question_id"])
    gold_rows.sort(key=lambda row: row["question_id"])
    context_rows.sort(key=lambda row: row["question_id"])
    frozen = OUT / "03-frozen"
    write_csv(frozen / "question-set.csv", question_rows)
    write_jsonl(frozen / "question-context.jsonl", context_rows)
    write_jsonl(frozen / "gold-evidence.jsonl", gold_rows)
    write_jsonl(OUT / "01-candidates/question-candidates.jsonl", candidate_rows)
    write_csv(OUT / "02-review/question-review.csv", review_rows)
    (frozen / "generation-checkpoints.json").write_text(json.dumps({"question_count": 200, "pair_count": 100, "status": "complete"}, indent=2) + "\n", encoding="utf-8")
    authoring_sources = {str(row.get("authoring_source", "")) for row in drafts}
    external_llm_used = any(source == "external_llm_from_complete_context_text" for source in authoring_sources)
    generation_method = (
        "external_llm_from_complete_context_text"
        if external_llm_used
        else "codex_current_model_from_complete_context_text"
    )
    manifest = {
        "process": "02.03-question-generation-and-gold",
        "generation_method": generation_method,
        "external_api_used": external_llm_used,
        "datasource": "netgear-customer-service",
        "question_count": 200,
        "question_pair_count": 100,
        "language_counts": dict(Counter(row["language"] for row in question_rows)),
        "family_counts": dict(Counter(row["question_family"] for row in question_rows)),
        "evidence_blocks_per_question": {"min": min(len(row["gold_evidence"]) for row in gold_rows), "max": max(len(row["gold_evidence"]) for row in gold_rows), "distribution": dict(Counter(str(len(row["gold_evidence"])) for row in gold_rows))},
        "input_hashes": {
            "draft": sha256(DRAFT),
            "context_packets": sha256(PACKETS),
            "source_frame": sha256(SOURCE),
            "database_context_audit": sha256(AUDIT) if AUDIT.exists() else None,
        },
        "answer_status": (
            "external_llm_reference_answers_frozen"
            if external_llm_used
            else "codex_current_model_reference_answers_frozen"
        ),
        "ready_for_retrieval": True,
        "outputs": {"question_set": "03-frozen/question-set.csv", "gold": "03-frozen/gold-evidence.jsonl", "context": "03-frozen/question-context.jsonl"},
    }
    (frozen / "annotation-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
