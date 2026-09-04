#!/usr/bin/env python3
"""Generate bilingual customer questions from complete context packets.

The model selects a variable-size minimal evidence set. Retrieval/OAT/OFAT do
not call this script.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[5]
DEFAULT_PACKETS = ROOT / "experiments/offline-rag-experiments/customer_service_revision/02-question-budget-and-gold/02-context-materialization/runs/selection-v2-multiblock/context-packets.jsonl"
DEFAULT_SLOTS = ROOT / "experiments/offline-rag-experiments/customer_service_revision/02-question-budget-and-gold/01-question-budget-and-distribution/runs/selection-v1/question-slots.csv"
DEFAULT_OUTPUT = ROOT / "experiments/offline-rag-experiments/customer_service_revision/02-question-budget-and-gold/03-question-generation-and-gold/runs/selection-v2-multiblock/00-draft/llm-question-candidates.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def prompt_for(packet: dict[str, Any], slot: dict[str, str]) -> str:
    return f"""Create one natural customer-service question pair from this complete bounded context.

Required metadata:
- question_pair_id: {packet['question_pair_id']}
- product/model: {packet['product_model']}
- question family: {slot.get('question_family', '')}

Rules:
1. Write one customer intent, not two unrelated questions joined with 'also', 'and also', or 'selain itu'.
2. Write a plain English question and a natural Indonesian translation.
3. Select the smallest evidence_block_ids set genuinely needed to answer that one intent. The count is variable: 1, 2, 3, or more. Never pad the set.
4. Evidence IDs must come only from the labelled context below. Do not invent IDs.
5. Return JSON only with keys: question_en, question_id, reference_answer_en, reference_answer_id, evidence_block_ids, evidence_rationale.

Complete context packet:
{packet['context_text']}
"""


def call_model(client: httpx.Client, url: str, api_key: str, model: str, prompt: str, timeout: float) -> dict[str, Any]:
    response = client.post(
        url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are a careful customer-support dataset author. Follow the requested JSON schema exactly."},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise RuntimeError(f"Authoring response has no choices: {payload}")
    content = choices[0].get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError(f"Authoring response has no message content: {payload}")
    value = json.loads(content)
    if not isinstance(value, dict):
        raise RuntimeError("Authoring response is not a JSON object")
    return value


def validate_choice(value: dict[str, Any], packet: dict[str, Any], slot: dict[str, str]) -> dict[str, Any]:
    allowed = {str(block["block_id"]) for block in packet["candidate_blocks"]}
    evidence = value.get("evidence_block_ids")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError(f"{packet['question_pair_id']}: evidence_block_ids must be a non-empty list")
    evidence = [str(item) for item in evidence]
    if len(set(evidence)) != len(evidence):
        raise ValueError(f"{packet['question_pair_id']}: duplicate evidence block ID")
    unknown = sorted(set(evidence) - allowed)
    if unknown:
        raise ValueError(f"{packet['question_pair_id']}: evidence outside packet: {unknown}")
    for field in ("question_en", "question_id", "reference_answer_en", "reference_answer_id", "evidence_rationale"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f"{packet['question_pair_id']}: missing non-empty {field}")
    return {
        "question_pair_id": packet["question_pair_id"],
        "document_id": packet["document_id"],
        "filename": packet["filename"],
        "product_model": packet["product_model"],
        "outline_frame_id": packet["outline_frame_id"],
        "section_path": packet["section_path"],
        "question_family": slot.get("question_family", ""),
        "question_en": value["question_en"].strip(),
        "question_id_text": value["question_id"].strip(),
        "reference_answer_en": value["reference_answer_en"].strip(),
        "reference_answer_id": value["reference_answer_id"].strip(),
        "evidence_block_ids": evidence,
        "evidence_rationale": value["evidence_rationale"].strip(),
        "authoring_source": "external_llm_from_complete_context_text",
        "review_status": "llm_generated_provenance_pending",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packets", type=Path, default=DEFAULT_PACKETS)
    parser.add_argument("--question-slots", type=Path, default=DEFAULT_SLOTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--base-url", default=os.environ.get("LLM_QUESTION_BASE_URL") or os.environ.get("OPENAI_BASE_URL"), help="OpenAI-compatible API base URL")
    parser.add_argument("--api-key", default=os.environ.get("LLM_QUESTION_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    parser.add_argument("--model", default=os.environ.get("LLM_QUESTION_MODEL"))
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()
    if not args.base_url or not args.api_key or not args.model:
        raise SystemExit("Provide --base-url, --api-key, and --model (or LLM_QUESTION_* environment variables)")
    packets = {row["question_pair_id"]: row for row in read_jsonl(args.packets)}
    slots = {row["question_pair_id"]: row for row in read_csv(args.question_slots) if row.get("language", "").casefold() == "en"}
    if len(packets) != 100 or len(slots) != 100:
        raise SystemExit(f"Expected 100 packets and 100 English slots; found {len(packets)} and {len(slots)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    with httpx.Client() as client:
        for index, pair_id in enumerate(sorted(packets, key=lambda value: int(value.split("-")[-1])), 1):
            packet, slot = packets[pair_id], slots[pair_id]
            for attempt in range(args.retries + 1):
                try:
                    value = call_model(client, args.base_url, args.api_key, args.model, prompt_for(packet, slot), args.timeout)
                    results.append(validate_choice(value, packet, slot))
                    print(f"[author] {index}/100 pair={pair_id} evidence={len(results[-1]['evidence_block_ids'])}", flush=True)
                    break
                except (httpx.HTTPError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                    if attempt >= args.retries:
                        raise RuntimeError(f"Authoring failed for {pair_id}: {exc}") from exc
                    time.sleep(2**attempt)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in results:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    counts: dict[str, int] = {}
    for row in results:
        count = str(len(row["evidence_block_ids"]))
        counts[count] = counts.get(count, 0) + 1
    summary = {"question_pair_count": len(results), "evidence_count_distribution": counts, "authoring_source": "external_llm_from_complete_context_text", "model": args.model, "context_field": "context_text", "fixed_evidence_count": False, "external_llm_used": True, "output": str(args.output)}
    args.output.with_name("llm-authoring-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
