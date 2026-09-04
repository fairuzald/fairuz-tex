#!/usr/bin/env python3
"""Audit customer-service question context against PostgreSQL and MinIO.

The audit is read-only.  It verifies that every selected question slot resolves to
one of the nine active documents, that the raw object bytes match the database hash,
and that the ready canonical-document parser artifact is present and internally
consistent.  No questions, profiles, indexes, or retrieval artifacts are created.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import boto3
import psycopg
from psycopg.rows import dict_row

DATASOURCE = "netgear-customer-service"
DEFAULT_DSN = "postgresql://dpo:dpo@localhost:5437/dpo"
DEFAULT_S3_ENDPOINT = "http://localhost:9005"
DEFAULT_BUCKET = "legal-chunks"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV is empty: {path}")
    return rows


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-slots", type=Path, required=True)
    parser.add_argument("--context-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--s3-endpoint", default=DEFAULT_S3_ENDPOINT)
    parser.add_argument("--s3-access-key", default="minioadmin")
    parser.add_argument("--s3-secret-key", default="minioadmin")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    args = parser.parse_args()

    slots = read_csv(args.question_slots)
    selected_document_ids = sorted({row["document_id"] for row in slots})
    if len(slots) != 200 or len(selected_document_ids) != 9:
        raise ValueError("question-slots.csv must contain 200 language slots spanning 9 documents")

    with psycopg.connect(args.dsn, row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        datasource = connection.execute(
            """
            SELECT id::text AS id, name, status::text AS status, description
            FROM datasources WHERE name = %s
            """,
            (DATASOURCE,),
        ).fetchone()
        if datasource is None:
            raise ValueError(f"Datasource not found: {DATASOURCE}")
        documents = connection.execute(
            """
            SELECT id::text AS document_id, source_identifier, filename, object_key,
                   byte_size, content_sha256, status::text AS status
            FROM datasource_documents
            WHERE datasource_id = %s AND status::text = 'active'
            ORDER BY filename, id
            """,
            (datasource["id"],),
        ).fetchall()
        artifacts = connection.execute(
            """
            SELECT DISTINCT ON (document_id)
                   document_id::text AS document_id,
                   cache_object_key, artifact_sha256, content_sha256,
                   size_bytes, status::text AS status, updated_at::text AS updated_at
            FROM stage_artifacts
            WHERE stage_type::text = 'parser'
              AND output_contract::text = 'canonical-document'
              AND status::text = 'ready'
              AND document_id = ANY(%s::uuid[])
            ORDER BY document_id, updated_at DESC
            """,
            (selected_document_ids,),
        ).fetchall()

    document_by_id = {row["document_id"]: dict(row) for row in documents}
    artifact_by_id = {row["document_id"]: dict(row) for row in artifacts}
    missing_documents = sorted(set(selected_document_ids) - set(document_by_id))
    inactive_or_extra = sorted(
        set(document_by_id) - set(selected_document_ids)
    )

    s3 = boto3.client(
        "s3",
        endpoint_url=args.s3_endpoint,
        aws_access_key_id=args.s3_access_key,
        aws_secret_access_key=args.s3_secret_key,
        region_name="us-east-1",
    )
    object_checks: list[dict[str, Any]] = []
    parser_checks: list[dict[str, Any]] = []
    for document_id in selected_document_ids:
        document = document_by_id.get(document_id)
        artifact = artifact_by_id.get(document_id)
        if document is None:
            continue
        check: dict[str, Any] = {
            "document_id": document_id,
            "filename": document["filename"],
            "raw_object_key": document["object_key"],
            "database_byte_size": int(document["byte_size"] or 0),
            "database_content_sha256": document["content_sha256"],
            "storage_byte_size": None,
            "storage_content_sha256": None,
            "byte_size_match": False,
            "content_hash_match": False,
            "error": "",
        }
        try:
            raw = s3.get_object(Bucket=args.bucket, Key=document["object_key"])["Body"].read()
            check["storage_byte_size"] = len(raw)
            check["storage_content_sha256"] = sha256_bytes(raw)
            check["byte_size_match"] = len(raw) == int(document["byte_size"] or 0)
            check["content_hash_match"] = check["storage_content_sha256"] == document[
                "content_sha256"
            ]
        except Exception as exc:  # noqa: BLE001 - audit keeps per-document diagnostics
            check["error"] = f"{type(exc).__name__}: {exc}"
        object_checks.append(check)

        parser_check: dict[str, Any] = {
            "document_id": document_id,
            "filename": document["filename"],
            "parser_artifact_present": artifact is not None,
            "parser_status": artifact.get("status") if artifact else "missing",
            "cache_object_key": artifact.get("cache_object_key") if artifact else "",
            "artifact_declared_sha256": artifact.get("artifact_sha256") if artifact else "",
            "artifact_content_sha256": artifact.get("content_sha256") if artifact else "",
            "artifact_size_bytes": artifact.get("size_bytes") if artifact else None,
            "raw_input_hash_match": False,
            "document_id_match": False,
            "canonical_content_hash_match": False,
            "parser_block_count": 0,
            "error": "",
        }
        if artifact is not None:
            try:
                body = s3.get_object(Bucket=args.bucket, Key=artifact["cache_object_key"])[
                    "Body"
                ].read()
                payload = json.loads(body)
                content = payload.get("content", {})
                parser_check["raw_input_hash_match"] = (
                    payload.get("input", {}).get("content_sha256") == document["content_sha256"]
                )
                parser_check["document_id_match"] = (
                    content.get("document_id") == document_id
                )
                parser_check["canonical_content_hash_match"] = (
                    payload.get("content_sha256") == canonical_hash(content)
                )
                parser_check["parser_block_count"] = len(content.get("blocks", []))
            except Exception as exc:  # noqa: BLE001 - audit keeps per-document diagnostics
                parser_check["error"] = f"{type(exc).__name__}: {exc}"
        parser_checks.append(parser_check)

    manifest = json.loads(args.context_manifest.read_text(encoding="utf-8"))
    packet_path = args.context_manifest.parent / manifest.get("outputs", {}).get("context_packets", "")
    packet_rows = []
    if packet_path.is_file():
        with packet_path.open(encoding="utf-8") as handle:
            packet_rows = [json.loads(line) for line in handle if line.strip()]
    packet_ready_count = sum(
        row.get("packet_status") in {"ready", "ready_over_soft_limit"} for row in packet_rows
    )
    report = {
        "process": "03.01-database-context-audit",
        "read_only": True,
        "datasource": dict(datasource),
        "database": {
            "active_document_count": len(documents),
            "selected_document_count": len(selected_document_ids),
            "selected_document_ids": selected_document_ids,
            "missing_selected_documents": missing_documents,
            "active_documents_not_selected": inactive_or_extra,
        },
        "object_storage": {
            "endpoint": args.s3_endpoint,
            "bucket": args.bucket,
            "checks": object_checks,
        },
        "parser_artifacts": {
            "expected_contract": "canonical-document",
            "checks": parser_checks,
        },
        "context_materialization": {
            "manifest_path": args.context_manifest.as_posix(),
            "manifest_sha256": sha256_bytes(args.context_manifest.read_bytes()),
            "packet_count": manifest.get("candidate_packet_count", len(packet_rows)),
            "packet_ready_count": manifest.get("packet_ready_count", packet_ready_count),
        },
    }
    report["ready_for_question_authoring"] = bool(
        report["database"]["active_document_count"] == 9
        and not missing_documents
        and all(check["byte_size_match"] and check["content_hash_match"] for check in object_checks)
        and all(
            check["parser_artifact_present"]
            and check["raw_input_hash_match"]
            and check["document_id_match"]
            and check["canonical_content_hash_match"]
            and not check["error"]
            for check in parser_checks
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ready_for_question_authoring"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
