#!/usr/bin/env python3
"""Audit question/evidence relevance and provenance for the frozen customer set."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKETS = DEFAULT_ROOT / "02-context-materialization/runs/selection-v2-multiblock/context-packets.jsonl"
DEFAULT_FROZEN = DEFAULT_ROOT / "03-question-generation-and-gold/runs/selection-v2-multiblock/03-frozen"
DEFAULT_SOURCE = DEFAULT_ROOT.parent / "01-target-corpus-size/01-corpus-eda/question_source_frame.csv"

STOPWORDS = set(
    "the a an and or to of in on for from with is are was were be been this that what how why can do does should i my me it its as at by after before when where which then use using your you their they them has have had will would could may might must into over under only all each one two three four five not no yes also than more less very about if so own"
    .split()
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def content_tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value).lower()
    return {token for token in re.findall(r"[a-z0-9]{3,}", normalized) if token not in STOPWORDS}


def parse_ids(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError("evidence_block_ids must be a JSON list of strings")
    return parsed


def audit(packets: dict[str, dict[str, Any]], source: dict[str, dict[str, str]], rows: list[dict[str, str]], gold: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    by_pair_language = {(row["question_pair_id"], row["language"]): row for row in rows}
    reports: list[dict[str, Any]] = []
    for pair_id in sorted({row["question_pair_id"] for row in rows}, key=lambda value: int(value.split("-")[-1])):
        en = by_pair_language.get((pair_id, "en"))
        id_row = by_pair_language.get((pair_id, "id"))
        packet = packets.get(pair_id)
        issues: list[str] = []
        if en is None or id_row is None:
            issues.append("missing bilingual row")
        if packet is None:
            issues.append("missing context packet")
            reports.append({"question_pair_id": pair_id, "status": "fail", "issues": issues})
            continue
        try:
            selected_ids = parse_ids(en["evidence_block_ids"])
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            reports.append({"question_pair_id": pair_id, "status": "fail", "issues": [f"invalid evidence IDs: {exc}"]})
            continue
        id_selected = parse_ids(id_row["evidence_block_ids"]) if id_row else []
        candidate_by_id = {block["block_id"]: block for block in packet["candidate_blocks"]}
        candidate_ids = set(candidate_by_id)
        if len(selected_ids) != len(set(selected_ids)):
            issues.append("duplicate selected evidence ID")
        if set(selected_ids) - candidate_ids:
            issues.append("selected ID is outside the packet")
        if selected_ids != id_selected:
            issues.append("English/Indonesian evidence IDs differ")
        if any(candidate_by_id[block_id]["document_id"] != en["document_id"] for block_id in selected_ids if block_id in candidate_by_id):
            issues.append("selected evidence crosses documents")
        context_hash = hashlib.sha256(packet["context_text"].encode("utf-8")).hexdigest()
        if context_hash != packet["context_text_sha256"]:
            issues.append("context hash mismatch")

        answer_tokens = content_tokens(en.get("answer", ""))
        question_tokens = content_tokens(en.get("question", ""))
        selected_text = " ".join(candidate_by_id[block_id]["text"] for block_id in selected_ids if block_id in candidate_by_id)
        selected_tokens = content_tokens(selected_text)
        answer_coverage = len(answer_tokens & selected_tokens) / max(1, len(answer_tokens))
        question_coverage = len(question_tokens & selected_tokens) / max(1, len(question_tokens))
        block_checks: list[dict[str, Any]] = []
        for index, block_id in enumerate(selected_ids, start=1):
            block = candidate_by_id.get(block_id)
            block_issues: list[str] = []
            overlap = sorted((answer_tokens | question_tokens) & content_tokens(block["text"])) if block else []
            gold_row = gold.get((pair_id, en["language"]))
            evidence = next((item for item in (gold_row or {}).get("gold_evidence", []) if item["block_id"] == block_id), None)
            if block is None:
                block_issues.append("block not in packet")
            elif not overlap:
                block_issues.append("no question/answer content-token overlap")
            if evidence is None:
                block_issues.append("missing gold evidence row")
            else:
                quote = evidence["quote"]
                if quote not in block["text"]:
                    block_issues.append("gold quote is not in selected block")
                start, end = evidence["char_start"], evidence["char_end"]
                source_row = source.get(block_id)
                if source_row is None:
                    block_issues.append("selected block is missing from source frame")
                else:
                    if quote != source_row["text"]:
                        block_issues.append("gold quote differs from source-frame block text")
                    if str(start) != source_row["char_start"] or str(end) != source_row["char_end"]:
                        block_issues.append("gold offsets differ from source-frame offsets")
                if hashlib.sha256(block["text"].encode("utf-8")).hexdigest() != evidence["text_sha256"]:
                    block_issues.append("gold text hash mismatch")
            if block_issues:
                issues.extend(f"{block_id[:8]}: {issue}" for issue in block_issues)
            block_checks.append({"evidence_index": index, "block_id": block_id, "content_overlap": overlap, "issues": block_issues})
        status = "pass" if not issues and answer_coverage >= 0.35 and all(not check["issues"] for check in block_checks) else "review"
        reports.append(
            {
                "question_pair_id": pair_id,
                "status": status,
                "language_parity": selected_ids == id_selected,
                "evidence_count": len(selected_ids),
                "answer_content_coverage": round(answer_coverage, 4),
                "question_content_coverage": round(question_coverage, 4),
                "selected_block_ids": selected_ids,
                "selected_sections": [candidate_by_id[block_id]["section_path"] for block_id in selected_ids if block_id in candidate_by_id],
                "block_checks": block_checks,
                "issues": issues,
            }
        )
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packets", type=Path, default=DEFAULT_PACKETS)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--frozen", type=Path, default=DEFAULT_FROZEN)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.frozen / "question-evidence-relevance-audit.json"
    packets = {row["question_pair_id"]: row for row in read_jsonl(args.packets)}
    with args.source.open(encoding="utf-8-sig", newline="") as handle:
        source = {row["block_id"]: row for row in csv.DictReader(handle)}
    rows = list(csv.DictReader((args.frozen / "question-set.csv").open(encoding="utf-8-sig")))
    gold = {(row["question_pair_id"], row["language"]): row for row in read_jsonl(args.frozen / "gold-evidence.jsonl")}
    reports = audit(packets, source, rows, gold)
    summary = {
        "process": "02.03-question-generation-and-gold.relevance-audit",
        "datasource": "netgear-customer-service",
        "question_pair_count": len(reports),
        "language_row_count": len(rows),
        "status_counts": dict(Counter(row["status"] for row in reports)),
        "evidence_count_distribution": dict(Counter(str(row["evidence_count"]) for row in reports)),
        "min_answer_content_coverage": min(row.get("answer_content_coverage", 0) for row in reports),
        "mean_answer_content_coverage": round(sum(row.get("answer_content_coverage", 0) for row in reports) / max(1, len(reports)), 4),
        "method": "deterministic provenance, source-frame offsets, quote, hash, bilingual-parity, and content-token relevance checks; source context is English",
        "reports": reports,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = [
        "# Question/evidence relevance audit",
        "",
        "This audit checks the frozen Customer Service set against the complete context packet for each pair.",
        "It verifies candidate membership, same-document provenance, bilingual ID parity, source-frame offsets, context hashes, block hashes, and a conservative content-token relevance proxy.",
        "The token proxy is a deterministic guardrail, not a substitute for the Codex full-context review.",
        "",
        f"- Pairs: {summary['question_pair_count']}; language rows: {summary['language_row_count']}",
        f"- Status: `{summary['status_counts']}`",
        f"- Evidence distribution: `{summary['evidence_count_distribution']}`",
        f"- Answer content coverage: min `{summary['min_answer_content_coverage']}`, mean `{summary['mean_answer_content_coverage']}`",
        "- Result: every selected block must contribute question/answer terms and every gold quote must resolve exactly.",
        "",
        "| Pair | Status | Evidence | Answer coverage | Selected blocks |",
        "|---|---|---:|---:|---|",
    ]
    for row in reports:
        prefixes = ", ".join(f"`{block_id[:8]}`" for block_id in row.get("selected_block_ids", []))
        md.append(f"| `{row['question_pair_id']}` | {row['status']} | {row.get('evidence_count', 0)} | {row.get('answer_content_coverage', 0):.2f} | {prefixes} |")
    md.append("")
    md.append("A `review` status means the deterministic guardrail found a possible mismatch; it must be inspected before retrieval.")
    (output.with_suffix(".md")).write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "reports"}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["status_counts"].get("review", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
