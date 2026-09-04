#!/usr/bin/env python3
"""Run the Customer Service Revision E2E matrix through the real API.

The runner deliberately stops at retrieval evidence.  It can create and sync
profiles for a new matrix, or reuse existing indexed profiles via
``--profile-map`` without dispatching documents again.  No question generation,
answer LLM, intent classifier, reranker, knowledge graph, or local/fake replay
is used.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean, median
from threading import Lock
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_DATASOURCE = "077b19c1-b65c-4447-8394-d96a91d07337"
DEFAULT_QUESTIONS = ROOT / (
    "experiments/offline-rag-experiments/customer_service_revision/"
    "02-question-budget-and-gold/03-question-generation-and-gold/runs/selection-v2-multiblock/"
    "03-frozen/question-set.csv"
)
DEFAULT_GOLD = DEFAULT_QUESTIONS.with_name("gold-evidence.jsonl")
DEFAULT_RUN_ROOT = ROOT / (
    "experiments/offline-rag-experiments/customer_service_revision/"
    "03-implementation/runs"
)

MODELS = {
    "qwen3": "Qwen/Qwen3-Embedding-0.6B",
    "bge-m3": "BAAI/bge-m3",
    "jina-v5-small": "jinaai/jina-embeddings-v5-text-small-retrieval",
}
MODEL_REVISIONS = {
    "qwen3": "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
    "bge-m3": "5617a9f61b028005a4858fdac845db406aefb181",
    "jina-v5-small": "6856e76bb72982e58de0620458a4e8b3614da340",
}
CUTOFFS = tuple(range(5, 61, 5))
METRIC_MODES = ("multiblock", "single-block")

CONDITIONS = [
    {"id": "oat-qwen3", "stage": "oat", "model": "qwen3", "chunker": "structure", "indexer": "dense"},
    {"id": "oat-bge-m3", "stage": "oat", "model": "bge-m3", "chunker": "structure", "indexer": "dense"},
    {"id": "oat-jina-v5-small-retrieval", "stage": "oat", "model": "jina-v5-small", "chunker": "structure", "indexer": "dense", "research": True},
    {"id": "baseline-generic-hybrid", "stage": "ofat", "model": "bge-m3", "chunker": "structure", "indexer": "hybrid", "model_from": "oat-bge-m3"},
    {"id": "chunker-generic-recursive", "stage": "ofat", "model": "bge-m3", "chunker": "recursive", "indexer": "hybrid"},
    {"id": "chunker-generic-sliding-window", "stage": "ofat", "model": "bge-m3", "chunker": "sliding", "indexer": "hybrid"},
    {"id": "indexer-generic-sparse", "stage": "ofat", "model": "bge-m3", "chunker": "structure", "indexer": "sparse"},
    {"id": "indexer-generic-dense", "stage": "ofat", "model": "bge-m3", "chunker": "structure", "indexer": "dense"},
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_value(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return default


def load_questions(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 200:
        raise ValueError(f"Expected exactly 200 frozen customer questions, found {len(rows)}")
    required = {"question_id", "question_pair_id", "language", "question", "evidence_block_ids", "document_id", "question_family"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Question CSV is missing columns: {sorted(missing)}")
    if len({row["question_id"] for row in rows}) != 200:
        raise ValueError("question_id must be unique")
    if sum(row["language"] == "en" for row in rows) != 100 or sum(row["language"] == "id" for row in rows) != 100:
        raise ValueError("Frozen customer set must contain 100 en and 100 id rows")
    return sorted(rows, key=lambda row: row["question_id"])


def load_gold(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict) or not isinstance(row.get("question_id"), str):
                raise ValueError(f"Invalid gold row at {path}:{line_number}")
            result[row["question_id"]] = row
    if len(result) != 200:
        raise ValueError(f"Expected 200 gold rows, found {len(result)}")
    return result


def load_profile_map(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value:
        raise ValueError(f"Profile map must be a non-empty JSON object: {path}")
    result = {str(key): str(profile_id) for key, profile_id in value.items()}
    if any(not key or not profile_id for key, profile_id in result.items()):
        raise ValueError(f"Profile map contains an empty condition or profile ID: {path}")
    return result


def login(client: httpx.Client, email: str, password: str) -> None:
    csrf = client.cookies.get("omni_csrf_token")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": csrf} if csrf else {},
    )
    response.raise_for_status()
    if not response.json().get("success"):
        raise RuntimeError(f"Login failed: {response.text}")


def api_data(response: httpx.Response, path: str) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"API {path} failed: {response.text}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"API {path} returned no object data")
    return data


def validate_reusable_profile(detail: dict[str, Any], *, profile_id: str, datasource_id: str) -> None:
    profile = detail.get("profile") if isinstance(detail.get("profile"), dict) else detail
    if str(profile.get("datasource_id")) != datasource_id:
        raise ValueError(f"Profile {profile_id} belongs to datasource {profile.get('datasource_id')}, not {datasource_id}")
    nodes = detail.get("nodes") if isinstance(detail.get("nodes"), list) else []
    orchestrators = [node for node in nodes if isinstance(node, dict) and node.get("component_type") == "retrieval_orchestrator"]
    if len(orchestrators) != 1:
        raise ValueError(f"Profile {profile_id} must have exactly one retrieval orchestrator")
    config = orchestrators[0].get("config") if isinstance(orchestrators[0].get("config"), dict) else {}
    candidate_limit = int(config.get("candidate_limit", 0) or 0)
    if candidate_limit < max(CUTOFFS):
        raise ValueError(f"Profile {profile_id} exposes candidate_limit={candidate_limit}; need at least {max(CUTOFFS)} for this sweep")


def post(client: httpx.Client, path: str, body: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
    csrf = client.cookies.get("omni_csrf_token")
    response = client.post(path, json=body, params=params, headers={"X-CSRF-Token": csrf} if csrf else {})
    return api_data(response, path)


def profile_body(condition: dict[str, Any], datasource_id: str, profile_name: str) -> dict[str, Any]:
    model = MODELS[condition["model"]]
    if condition["chunker"] == "structure":
        chunker = "generic-structure-aware"
        chunker_config = {"target_level": "text_block", "include_parent_context": True, "size_unit": "character", "max_size": 512}
    elif condition["chunker"] == "recursive":
        chunker = "generic-recursive"
        chunker_config = {"size_unit": "character", "max_size": 512, "overlap": 51, "separators": ["\n\n", "\n", ". ", "; ", ", ", " "]}
    else:
        chunker = "generic-sliding-window"
        chunker_config = {"size_unit": "character", "window_size": 512, "overlap": 51}

    indexer = {"dense": "dense-semantic", "hybrid": "hybrid-semantic-keyword", "sparse": "sparse-keyword"}[condition["indexer"]]
    orchestrator = {"dense": "dense-semantic-orchestrator", "hybrid": "hybrid-semantic-keyword-orchestrator", "sparse": "sparse-keyword-orchestrator"}[condition["indexer"]]
    nodes = [
        {"node_id": "parser-1", "component_type": "parser", "plugin_name": "generic-outline", "plugin_version": "1.0.0", "config": {"outline": {"header_margin_ratio": 0.075, "footer_margin_ratio": 0.9, "anchor_search_window_points": 150, "line_merge_tolerance_points": 4, "text_decoration": True, "excluded_section_titles": ["contents", "table of contents"]}}},
        {"node_id": "chunker-1", "component_type": "chunker", "plugin_name": chunker, "plugin_version": "1.0.0", "config": chunker_config},
    ]
    indexer_config: dict[str, Any] = {}
    if condition["indexer"] != "sparse":
        indexer_config["embedding"] = {"provider": "local", "model": model, "revision": MODEL_REVISIONS[condition["model"]], "local_backend": "sentence-transformers" if condition["model"] == "bge-m3" else "transformers", "batch_size": 16, "device": "cpu"}
    if condition["indexer"] in {"sparse", "hybrid"}:
        indexer_config.update({"sparse_fields": ["lexical_text^4", "content^1.5"], "sparse_match_type": "best_fields"})
    nodes.extend([
        {"node_id": "indexer-1", "component_type": "indexer", "plugin_name": indexer, "plugin_version": "1.0.0", "config": indexer_config},
        {"node_id": "retrieval-orchestrator-1", "component_type": "retrieval_orchestrator", "plugin_name": orchestrator, "plugin_version": "1.0.0", "config": ({"top_k": 60, "candidate_limit": 60, "use_reranker": False, "parent_hydration_enabled": False, "kg_mode": "none"} if condition["indexer"] != "hybrid" else {"dense_top_k": 60, "sparse_top_k": 60, "candidate_limit": 60, "rrf_k": 60, "use_reranker": False, "parent_hydration_enabled": False, "kg_mode": "none"})},
    ])
    return {
        "name": profile_name,
        "description": f"Customer Service Revision E2E; condition={condition['id']}; deterministic retrieval only; no LLM generation, intent, reranker, or KG.",
        "version": "1.0.0",
        "datasource_id": datasource_id,
        "nodes": nodes,
        "xai": {"intent": {"method": "noop"}, "retrieval": {"method": "noop"}, "reranking": {"method": "noop"}, "generation": {"method": "noop"}},
        "domain": {"name": "customer-service", "language": "multi", "intent_provider": "passthrough", "query_resolution_provider": "passthrough", "intent_dispatch": "orchestrator", "ingestion_mode": "full", "component_mode": "full", "show_source_documents": True, "temperature": 0.0},
    }


def list_docs(client: httpx.Client, profile_id: str, reauth: Any | None = None) -> list[dict[str, Any]]:
    for attempt in range(5):
        try:
            response = client.get(f"/api/v1/profiles/{profile_id}/documents", params={"limit": 100, "page": 1})
            if response.status_code == 401 and reauth is not None:
                reauth()
                response = client.get(f"/api/v1/profiles/{profile_id}/documents", params={"limit": 100, "page": 1})
            break
        except httpx.ReadTimeout:
            if attempt == 4:
                raise
            time.sleep(2)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success") or not isinstance(payload.get("data"), list):
        raise RuntimeError(f"API profile documents failed: {response.text}")
    return [row for row in payload["data"] if isinstance(row, dict)]


def poll_documents(client: httpx.Client, profile_id: str, expected: int, timeout: float, interval: float, log_path: Path, reauth: Any | None = None) -> dict[str, Any]:
    started = time.monotonic()
    last: list[dict[str, Any]] = []
    with log_path.open("w", encoding="utf-8") as log:
        while True:
            last = list_docs(client, profile_id, reauth=reauth)
            statuses = [str(row.get("latest_status", "unknown")).lower() for row in last]
            counts = {status: statuses.count(status) for status in sorted(set(statuses))}
            snapshot = {"at": datetime.now(UTC).isoformat(), "document_count": len(last), "statuses": counts}
            log.write(json.dumps(snapshot, ensure_ascii=False) + "\n"); log.flush()
            print(f"[poll] profile={profile_id} documents={len(last)}/{expected} statuses={counts}", flush=True)
            if len(last) == expected and all(status == "succeeded" for status in statuses):
                return {"document_count": len(last), "statuses": counts, "elapsed_seconds": round(time.monotonic() - started, 3)}
            if any(status in {"failed", "cancelled"} for status in statuses):
                raise RuntimeError(f"Profile {profile_id} has failed/cancelled documents: {counts}")
            if time.monotonic() - started > timeout:
                raise TimeoutError(f"Profile {profile_id} did not finish in {timeout}s: {counts}")
            time.sleep(interval)


def parse_sse(block: str) -> tuple[str | None, dict[str, Any] | None]:
    event = None; data: list[str] = []
    for line in block.splitlines():
        if line.startswith("event:"): event = line.partition(":")[2].strip()
        elif line.startswith("data:"): data.append(line.partition(":")[2].lstrip())
    if not data: return event, None
    value = json.loads("\n".join(data))
    # Accept event names from either SSE metadata or the JSON type field.
    if event is None and isinstance(value, dict):
        payload_type = value.get("type")
        if isinstance(payload_type, str):
            event = payload_type
    return event, value if isinstance(value, dict) else None


def chat(client: httpx.Client, profile_id: str, question: str, timeout: float, reauth: Any | None = None) -> dict[str, Any]:
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.post(
                "/api/v1/chat/stream",
                json={
                    "message": question,
                    "profile_id": profile_id,
                    "detail": False,
                    "source": "typed",
                },
                headers={
                    "X-CSRF-Token": client.cookies.get("omni_csrf_token", ""),
                },
                timeout=timeout,
            )
            if response.status_code == 401 and reauth is not None:
                reauth()
                response = client.post(
                    "/api/v1/chat/stream",
                    json={
                        "message": question,
                        "profile_id": profile_id,
                        "detail": False,
                        "source": "typed",
                    },
                    headers={
                        "X-CSRF-Token": client.cookies.get("omni_csrf_token", ""),
                    },
                    timeout=timeout,
                )
            response.raise_for_status()
            done = None
            events: list[str] = []
            buffer: list[str] = []
            for line in response.text.splitlines():
                if line == "":
                    if buffer:
                        event, payload = parse_sse("\n".join(buffer))
                        buffer = []
                        if event:
                            events.append(event)
                        if event == "done":
                            done = payload
                        if event == "error":
                            raise RuntimeError(f"Chat error: {payload}")
                else:
                    buffer.append(line)
            if buffer:
                event, payload = parse_sse("\n".join(buffer))
                if event:
                    events.append(event)
                if event == "done":
                    done = payload
            if done is None:
                raise RuntimeError(f"Chat stream ended without done; events={events}")
            done["_events"] = events
            return done
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            if attempt >= max_attempts:
                raise
            delay = min(2**attempt, 8)
            print(
                f"[chat-retry] attempt={attempt}/{max_attempts - 1} "
                f"delay={delay}s reason={type(exc).__name__}",
                flush=True,
            )
            time.sleep(delay)
    raise RuntimeError("Chat request retry loop exited unexpectedly")


def candidate_block_id_list(candidate: dict[str, Any]) -> list[str]:
    raw = candidate.get("source_block_ids", [])
    if isinstance(raw, str): raw = [raw]
    return [str(value) for value in raw] if isinstance(raw, list) else []


def candidate_block_ids(candidate: dict[str, Any]) -> set[str]:
    return set(candidate_block_id_list(candidate))


def chunk_is_hit(candidate: dict[str, Any], gold: set[str]) -> bool:
    return bool(candidate_block_ids(candidate) & gold)


def chunk_ndcg(candidates: list[Any], gold: set[str], k: int) -> float:
    import math

    pool_gains = [
        int(chunk_is_hit(candidate, gold))
        for candidate in candidates
        if isinstance(candidate, dict)
    ]
    actual = pool_gains[:k]
    ideal = sorted(pool_gains, reverse=True)[:k]

    def dcg(values: list[int]) -> float:
        return sum(gain / math.log2(index + 2) for index, gain in enumerate(values))

    ideal_dcg = dcg(ideal)
    return dcg(actual) / ideal_dcg if ideal_dcg else 0.0


def score_row(
    question: dict[str, str],
    done: dict[str, Any],
    elapsed_ms: float,
    *,
    gold_row: dict[str, Any] | None = None,
    metric_mode: str = "multiblock",
) -> dict[str, Any]:
    message = done.get("message") if isinstance(done.get("message"), dict) else {}
    metadata = message.get("metadata") if isinstance(message, dict) else {}
    rag = metadata.get("rag") if isinstance(metadata, dict) and isinstance(metadata.get("rag"), dict) else {}
    candidates = rag.get("retrieval_candidates")
    # Treat missing or empty candidates as a valid zero-recall result, not a failed run.
    if not isinstance(candidates, list):
        candidates = []
    gold_items = gold_row.get("gold_evidence", []) if isinstance(gold_row, dict) else []
    gold = {
        str(item.get("block_id"))
        for item in gold_items
        if isinstance(item, dict) and item.get("block_id")
    }
    if not gold:
        gold = set(json_value(question.get("evidence_block_ids"), []))
    row: dict[str, Any] = {"question_id": question["question_id"], "question_pair_id": question["question_pair_id"], "language": question["language"], "question_family": question["question_family"], "product_model": question.get("product_model", ""), "retrieved_count": len(candidates), "retrieval_empty": not candidates, "elapsed_ms": round(elapsed_ms, 3), "answer_generation_provider": "deterministic", "intent_provider": "passthrough", "use_reranker": False, "kg_mode": "none"}
    for k in CUTOFFS:
        prefix = [item for item in candidates[:k] if isinstance(item, dict)]
        found = set().union(*(candidate_block_ids(item) for item in prefix))
        hit_chunks = sum(chunk_is_hit(item, gold) for item in prefix)
        if metric_mode == "single-block":
            row[f"chunk_precision@{k}"] = hit_chunks / k
            row[f"chunk_success@{k}"] = bool(hit_chunks)
            row[f"gold_block_recall@{k}"] = len(found & gold) / len(gold) if gold else 0.0
            row[f"chunk_ndcg@{k}"] = chunk_ndcg(candidates, gold, k)
        else:
            row[f"evidence_recall@{k}"] = len(found & gold) / len(gold) if gold else 0.0
            row[f"evidence_precision@{k}"] = hit_chunks / len(prefix) if prefix else 0.0
    if metric_mode != "single-block":
        row["ndcg@10"] = chunk_ndcg(candidates, gold, 10)
    # Preserve the full evaluation window for later cutoff analysis.
    row["retrieval_candidates"] = candidates[:60]
    row["gold_evidence_block_ids"] = sorted(gold)
    return row


def run_condition(args: argparse.Namespace, condition: dict[str, Any], questions: list[dict[str, str]], gold: dict[str, dict[str, Any]], run_dir: Path, email: str, password: str, existing_profile_id: str | None = None) -> dict[str, Any]:
    condition_dir = run_dir / condition["id"]; condition_dir.mkdir(parents=True, exist_ok=True)
    profile_name = re.sub(r"[^a-z0-9-]+", "-", f"customer-service-e2e-{condition['id']}-{args.run_id[-8:]}".lower())[:63].strip("-")
    with httpx.Client(base_url=args.api_base, timeout=args.http_timeout) as client:
        login(client, email, password)
        auth_lock = Lock()
        def reauth() -> None:
            with auth_lock:
                login(client, email, password)

        profile_id = str(existing_profile_id or args.resume_profile_id or "")
        reused_profile = bool(profile_id)
        if not reused_profile:
            profile = post(client, "/api/v1/profiles", profile_body(condition, args.datasource_id, profile_name))
            profile_id = str(profile.get("profile_id") or profile.get("id") or "")
            if not profile_id: raise RuntimeError(f"Profile creation returned no ID for {condition['id']}")
        detail = api_data(client.get(f"/api/v1/profiles/{profile_id}"), "profile detail")
        if reused_profile:
            validate_reusable_profile(detail, profile_id=profile_id, datasource_id=args.datasource_id)
        profile_name = str(detail.get("name") or profile_name)
        (condition_dir / "profile.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if not reused_profile:
            sync = post(client, f"/api/v1/profiles/{profile_id}/sync", params={"offset": 0, "limit": args.expected_documents})
            (condition_dir / "sync.json").write_text(json.dumps(sync, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            (condition_dir / "reuse.json").write_text(json.dumps({"profile_id": profile_id, "indexing_dispatched": False, "reason": "existing indexed profile"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        completion = poll_documents(client, profile_id, args.expected_documents, args.sync_timeout, args.poll_interval, condition_dir / "polling.jsonl", reauth=reauth)
        (condition_dir / "completion.json").write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        progress_lock = Lock()
        completed_questions = 0

        def one(question: dict[str, str]) -> dict[str, Any]:
            nonlocal completed_questions
            started = time.perf_counter()
            done = chat(
                client,
                profile_id,
                question["question"],
                args.chat_timeout,
                reauth=reauth,
            )
            elapsed = (time.perf_counter() - started) * 1000
            metadata = ((done.get("message") or {}).get("metadata") or {}).get("rag") or {}
            intent = metadata.get("intent") or {}; guardrail = metadata.get("guardrail") or {}
            if intent.get("decided_by") not in (None, "passthrough"):
                raise RuntimeError(f"Intent was not passthrough for {question['question_id']}: {intent}")
            row = score_row(
                question,
                done,
                elapsed,
                gold_row=gold.get(question["question_id"]),
                metric_mode=args.metric_mode,
            )
            with progress_lock:
                completed_questions += 1
                print(
                    f"[question] {completed_questions}/{len(questions)} "
                    f"id={question['question_id']} language={question['language']} "
                    f"elapsed_ms={elapsed:.0f}",
                    flush=True,
                )
            return row

        rows: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=args.question_workers) as pool:
            futures = {pool.submit(one, question): question["question_id"] for question in questions}
            for future in as_completed(futures): rows.append(future.result())
        rows.sort(key=lambda row: row["question_id"])
        with (condition_dir / "per-question-results.jsonl").open("w", encoding="utf-8") as handle:
            for row in rows: handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        if args.metric_mode == "single-block":
            summary_metrics = {
                "chunk_precision@10": fmean(row["chunk_precision@10"] for row in rows),
                "chunk_success@10": fmean(row["chunk_success@10"] for row in rows),
                "gold_block_recall@10": fmean(row["gold_block_recall@10"] for row in rows),
                "chunk_ndcg@10": fmean(row["chunk_ndcg@10"] for row in rows),
            }
        else:
            summary_metrics = {
                "evidence_recall@10": fmean(row["evidence_recall@10"] for row in rows),
                "evidence_precision@10": fmean(row["evidence_precision@10"] for row in rows),
                "ndcg@10": fmean(row["ndcg@10"] for row in rows),
            }
        summary = {"condition_id": condition["id"], "profile_id": profile_id, "profile_name": profile_name, "question_count": len(rows), "valid_trace_count": len(rows), "failed_question_count": 0, "document_count": completion["document_count"], "metric_mode": args.metric_mode, "use_reranker": False, "intent_provider": "passthrough", "answer_generation_provider": "deterministic", "kg_mode": "none", **summary_metrics, "median_latency_ms": median(row["elapsed_ms"] for row in rows)}
        (condition_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[done] {condition['id']} profile={profile_id} questions={len(rows)}", flush=True)
        return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://localhost:8001")
    parser.add_argument("--email", default=os.environ.get("BOOTSTRAP_ADMIN_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("BOOTSTRAP_ADMIN_PASSWORD"))
    parser.add_argument("--datasource-id", default=DEFAULT_DATASOURCE)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--run-id", default=datetime.now(UTC).strftime("e2e-%Y%m%dT%H%M%SZ"))
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--expected-documents", type=int, default=9)
    parser.add_argument("--sync-timeout", type=float, default=7200)
    parser.add_argument("--poll-interval", type=float, default=10)
    parser.add_argument("--chat-timeout", type=float, default=300)
    parser.add_argument("--http-timeout", type=float, default=120)
    parser.add_argument("--question-workers", type=int, default=4)
    parser.add_argument("--metric-mode", choices=METRIC_MODES, default="multiblock")
    parser.add_argument("--condition-id", action="append")
    parser.add_argument("--resume-profile-id", help="Resume polling and evaluation for an existing profile; skips profile creation and sync")
    parser.add_argument("--profile-map", type=Path, help="JSON object mapping condition IDs to existing profile IDs; skips profile creation and sync")
    args = parser.parse_args()
    if not args.email or not args.password: raise SystemExit("Provide --email/--password or BOOTSTRAP_ADMIN_*")
    questions = load_questions(args.questions)
    gold = load_gold(args.gold)
    question_ids = {row["question_id"] for row in questions}
    gold_ids = set(gold)
    if question_ids != gold_ids:
        raise ValueError(f"Question/gold IDs differ; missing={sorted(question_ids - gold_ids)} extra={sorted(gold_ids - question_ids)}")
    if args.metric_mode == "single-block":
        invalid = [question_id for question_id, row in gold.items() if len(row.get("gold_evidence", [])) != 1]
        if invalid:
            raise ValueError(f"single-block mode requires exactly one gold evidence block per question; invalid={invalid[:5]}")
    conditions = [condition for condition in CONDITIONS if not args.condition_id or condition["id"] in set(args.condition_id)]
    if not conditions: raise SystemExit("No conditions selected")
    if args.resume_profile_id and (args.profile_map or len(conditions) != 1):
        raise SystemExit("Use --resume-profile-id for exactly one condition, or use --profile-map for multiple existing profiles")
    profile_map = load_profile_map(args.profile_map) if args.profile_map else {}
    if profile_map and not args.condition_id:
        conditions = [condition for condition in CONDITIONS if condition["id"] in profile_map]
    if profile_map:
        missing = [condition["id"] for condition in conditions if condition["id"] not in profile_map]
        if missing:
            raise SystemExit(f"Profile map is missing selected conditions: {', '.join(missing)}")
    run_dir = args.run_root / args.run_id; run_dir.mkdir(parents=True, exist_ok=False)
    started = datetime.now(UTC)
    summaries: list[dict[str, Any]] = []
    for condition in conditions:
        existing_profile_id = profile_map.get(condition["id"]) if profile_map else None
        summaries.append(run_condition(args, condition, questions, gold, run_dir, args.email, args.password, existing_profile_id=existing_profile_id))
    with (run_dir / "condition-results.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = list(summaries[0]); writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(summaries)
    manifest = {"schema_version": "1.0", "run_id": args.run_id, "execution_mode": "api-e2e-retrieval-only", "metric_mode": args.metric_mode, "datasource_id": args.datasource_id, "expected_document_count": args.expected_documents, "question_count": len(questions), "question_sha256": sha256_file(args.questions), "gold_sha256": sha256_file(args.gold), "condition_count": len(summaries), "use_reranker": False, "intent_provider": "passthrough", "answer_generation_provider": "deterministic", "llm_generation_called": False, "kg_mode": "none", "started_at_utc": started.isoformat(), "finished_at_utc": datetime.now(UTC).isoformat(), "conditions": summaries}
    (run_dir / "run-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "condition_count": len(summaries), "question_count": len(questions)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
