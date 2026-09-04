"""Build the customer-service census manifest and detailed corpus EDA.

The script is read-only against PostgreSQL and S3. It reads the nine active
documents in ``netgear-customer-service``, validates the current generic-outline
artifacts, and writes local CSV/JSON/PNG artifacts. It does not create profiles, indexes,
questions, or retrieval runs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
import fitz
import matplotlib
import psycopg
from psycopg.rows import dict_row

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from modules.dpo.parser.domain.contracts import CanonicalDocument

DATASOURCE = "netgear-customer-service"
DATASOURCE_ID = "077b19c1-b65c-4447-8394-d96a91d07337"
DEFAULT_DSN = "postgresql://dpo:dpo@localhost:5437/dpo"
DEFAULT_S3_ENDPOINT = "http://localhost:9005"
DEFAULT_BUCKET = "legal-chunks"
DEFAULT_REGION = "us-east-1"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1]

TABLE_RE = re.compile(r"\btable\s*(?:\d+|[A-Z])\b", re.IGNORECASE)
FIGURE_RE = re.compile(r"\b(?:figure|fig\.)\s*(?:\d+|[A-Z])\b", re.IGNORECASE)
STEP_RE = re.compile(r"(?:^|\n)\s*(?:\d+[.)]|[•●▪◦*-])\s+", re.MULTILINE)
MODEL_RE = re.compile(r"\b(?:CM|LM|RAXE?|RBK|XR|R)\d{2,5}[A-Z0-9-]*\b", re.IGNORECASE)
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


@dataclass(frozen=True)
class DocumentRow:
    document_id: str
    source_identifier: str
    source_url: str
    filename: str
    extension: str
    object_key: str
    byte_size: int
    content_sha256: str
    status: str
    metadata: dict[str, Any]
    parser_artifact: dict[str, Any] | None


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def fetch_catalog(dsn: str, datasource: str) -> tuple[dict[str, Any], list[DocumentRow]]:
    """Read datasource and active document metadata in read-only transactions."""

    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        ds = connection.execute(
            """
            SELECT id::text AS id, name, description, status::text AS status,
                   file_extensions, scraper_plugin_id::text AS scraper_plugin_id,
                   scraper_enabled, scraper_config_json
            FROM datasources
            WHERE name = %s
            """,
            (datasource,),
        ).fetchone()
        if ds is None:
            raise RuntimeError(f"Datasource not found: {datasource!r}")

        rows = connection.execute(
            """
            SELECT id::text AS document_id, source_identifier, source_url, filename,
                   extension, object_key, byte_size, content_sha256,
                   status::text AS status, metadata_json
            FROM datasource_documents
            WHERE datasource_id = %s AND status::text = 'active'
            ORDER BY filename, id
            """,
            (ds["id"],),
        ).fetchall()
        artifacts = connection.execute(
            """
            SELECT DISTINCT ON (document_id)
                   document_id::text AS document_id,
                   stage_type::text AS stage_type,
                   output_contract::text AS output_contract,
                   status::text AS status,
                   cache_object_key, artifact_sha256, content_sha256,
                   size_bytes, updated_at::text AS updated_at
            FROM stage_artifacts
            WHERE stage_type::text = 'parser'
              AND output_contract::text = 'canonical-document'
              AND status::text = 'ready'
            ORDER BY document_id, updated_at DESC
            """
        ).fetchall()

    by_document = {str(row["document_id"]): dict(row) for row in artifacts}
    documents = [
        DocumentRow(
            document_id=str(row["document_id"]),
            source_identifier=_clean(row["source_identifier"]),
            source_url=_clean(row["source_url"]),
            filename=_clean(row["filename"]),
            extension=_clean(row["extension"]),
            object_key=_clean(row["object_key"]),
            byte_size=int(row["byte_size"] or 0),
            content_sha256=_clean(row["content_sha256"]),
            status=_clean(row["status"]),
            metadata=_metadata(row["metadata_json"]),
            parser_artifact=by_document.get(str(row["document_id"])),
        )
        for row in rows
    ]
    if not documents:
        raise RuntimeError(f"Datasource has no active documents: {datasource!r}")
    return dict(ds), documents


def _s3_client(args: argparse.Namespace) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=args.s3_endpoint,
        aws_access_key_id=args.s3_access_key,
        aws_secret_access_key=args.s3_secret_key,
        region_name=args.s3_region,
        use_ssl=args.s3_use_ssl,
    )


def _load_parser(
    client: Any, args: argparse.Namespace, record: DocumentRow
) -> tuple[dict[str, Any] | None, bytes | None, dict[str, Any]]:
    """Fetch and validate a parser artifact, returning payload and diagnostics."""

    artifact = record.parser_artifact
    checks: dict[str, Any] = {
        "parser_status": artifact.get("status") if artifact else "missing",
        "parser_plugin": "",
        "parser_version": "",
        "parser_input_hash_match": False,
        "parser_content_hash_match": False,
        "parser_document_id_match": False,
        "parser_payload_hash_match": False,
        "parser_error": "",
    }
    if artifact is None or not artifact.get("cache_object_key"):
        checks["parser_error"] = "no ready canonical-document artifact"
        return None, None, checks
    try:
        body = client.get_object(Bucket=args.bucket, Key=artifact["cache_object_key"])[
            "Body"
        ].read()
        payload = json.loads(body)
        producer = payload.get("producer") if isinstance(payload, dict) else {}
        producer = producer if isinstance(producer, dict) else {}
        checks["parser_plugin"] = producer.get("name", "")
        checks["parser_version"] = producer.get("version", "")
        checks["parser_input_hash_match"] = (
            payload.get("input", {}).get("content_sha256") == record.content_sha256
        )
        checks["parser_document_id_match"] = (
            payload.get("content", {}).get("document_id") == record.document_id
        )
        checks["parser_content_hash_match"] = not artifact.get("content_sha256") or str(
            artifact["content_sha256"]
        ).strip() == payload.get("content_sha256")
        checks["parser_payload_hash_match"] = not payload.get("content_sha256") or _json_hash(
            payload.get("content")
        ) == payload.get("content_sha256")
        canonical = CanonicalDocument.model_validate(payload["content"])
        return payload, canonical.model_dump(mode="json"), checks
    except Exception as exc:  # noqa: BLE001 - diagnostics keep one bad row visible
        checks["parser_error"] = f"{type(exc).__name__}: {_clean(exc)}"
        return None, None, checks


def _page_bin(page_number: int, page_count: int) -> str:
    if page_count <= 0:
        return "unknown"
    return f"P{min(5, ((page_number - 1) * 5 // page_count) + 1)}"


def _token_estimate(text: str) -> int:
    return max(0, math.ceil(len(text) / 4))


def _normalise_exact(text: str) -> str:
    return " ".join(text.casefold().split())


def _normalise_template(text: str) -> str:
    value = _normalise_exact(text)
    value = MODEL_RE.sub("<model>", value)
    value = NUMBER_RE.sub("<num>", value)
    return value


def _evidence_shape(text: str) -> str:
    if TABLE_RE.search(text) or re.search(r"\btable\b", text, re.IGNORECASE):
        return (
            "table_or_figure_textual" if not FIGURE_RE.search(text) else "table_or_figure_textual"
        )
    if FIGURE_RE.search(text):
        return "table_or_figure_textual"
    if len(STEP_RE.findall(text)) >= 2:
        return "multi_block_procedure"
    if re.search(r"\b(if|when|unless|otherwise)\b", text, re.IGNORECASE) and re.search(
        r"\b(troubleshoot|problem|error|issue)\b", text, re.IGNORECASE
    ):
        return "multi_page_or_conditional"
    return "single_block"


def _question_allowed(text: str, shape: str) -> tuple[bool, str]:
    clean = _clean(text)
    if len(clean) < 40:
        return False, "text block shorter than 40 characters"
    if re.fullmatch(r"(?:figure|fig\.?|table)\s*\d*\.?", clean, re.IGNORECASE):
        return False, "caption-only block"
    if shape == "table_or_figure_textual":
        return True, "text-backed table/figure; reviewer must verify"
    return True, "text-backed candidate; reviewer required"


def _walk_blocks(
    blocks: Iterable[dict[str, Any]],
    *,
    document: DocumentRow,
    page_count: int,
    parents: tuple[str, ...] = (),
    heading_path: tuple[str, ...] = (),
    depth: int = 0,
) -> Iterable[dict[str, Any]]:
    for block in blocks:
        block_id = str(block.get("block_id") or "")
        block_type = str(block.get("type") or "").upper()
        text = str(block.get("text") or "")
        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        location = metadata.get("location") if isinstance(metadata.get("location"), dict) else {}
        page_start = int(location.get("page_start") or 0)
        page_end = int(location.get("page_end") or page_start)
        is_heading = block_type == "HEADING"
        current_path = (
            (*heading_path, _clean(text)) if is_heading and _clean(text) else heading_path
        )
        current_parents = (*parents, block_id) if is_heading else parents
        row = {
            "document_id": document.document_id,
            "filename": document.filename,
            "product_model": Path(document.filename).stem.removeprefix("netgear-").upper(),
            "block_id": block_id,
            "block_type": block_type,
            "text": text,
            "char_count": len(text),
            "word_count": len(text.split()),
            "token_estimate": _token_estimate(text),
            "page_start": page_start,
            "page_end": page_end,
            "page_bin": _page_bin(page_start, page_count),
            "heading_depth": int(metadata.get("level") or depth) if is_heading else depth,
            "parent_heading_ids": ";".join(parents),
            "section_path": " > ".join(item for item in current_path if item) or "[ROOT]",
            # Defer topic labels to reviewed annotation; keyword heuristics were misleading.
            "topic_labels": "",
            "topic_classification": "manual_review_pending",
            "evidence_shape": _evidence_shape(text),
            "table_figure_flag": bool(TABLE_RE.search(text) or FIGURE_RE.search(text)),
        }
        yield row
        children = block.get("children") if isinstance(block.get("children"), list) else []
        yield from _walk_blocks(
            children,
            document=document,
            page_count=page_count,
            parents=current_parents,
            heading_path=current_path,
            depth=depth + 1 if is_heading else depth,
        )


def _assign_clusters(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    template: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["block_type"] != "TEXT_BLOCK" or not _clean(row["text"]):
            continue
        exact[_normalise_exact(row["text"])].append(row)
        template[_normalise_template(row["text"])].append(row)

    def ids(groups: dict[str, list[dict[str, Any]]], prefix: str) -> dict[str, str]:
        result: dict[str, str] = {}
        number = 1
        for _key, members in sorted(groups.items()):
            if len(members) < 2:
                continue
            cluster_id = f"{prefix}-{number:03d}"
            number += 1
            for member in members:
                result[member["block_id"]] = cluster_id
        return result

    exact_ids = ids(exact, "EXACT")
    template_ids = ids(template, "TEMPLATE")
    for row in rows:
        row["exact_duplicate_cluster_id"] = exact_ids.get(row["block_id"], "")
        row["template_duplicate_cluster_id"] = template_ids.get(row["block_id"], "")
    return rows


def _parent_section_path(section_path: str) -> str:
    if " > " not in section_path:
        return "[ROOT]"
    return section_path.rsplit(" > ", 1)[0]


def _outline_inventory(
    parser_rows_by_document: dict[str, list[dict[str, Any]]],
    documents: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Build a heading-level inventory and a leaf-outline question frame.

    ``section_inventory.csv`` is a low-level section/block diagnostic. This inventory is
    intentionally different: one row represents one emitted heading node, with direct and
    descendant coverage. The question frame contains only leaf outlines with text, so
    question selection can happen from the outline rather than a heuristic topic label.
    """

    document_by_id = {row["document_id"]: row for row in documents}
    outline_rows: list[dict[str, Any]] = []
    question_outline_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for document_id, parser_rows in parser_rows_by_document.items():
        document = document_by_id.get(document_id, {})
        headings = [row for row in parser_rows if row.get("block_type") == "HEADING"]
        text_rows = [row for row in parser_rows if row.get("block_type") == "TEXT_BLOCK"]
        child_heading_ids: dict[str, list[str]] = defaultdict(list)
        for heading in headings:
            parents = [value for value in heading.get("parent_heading_ids", "").split(";") if value]
            if parents:
                child_heading_ids[parents[-1]].append(heading["block_id"])

        for outline_order, heading in enumerate(headings, start=1):
            heading_id = heading["block_id"]
            parent_ids = [
                value for value in heading.get("parent_heading_ids", "").split(";") if value
            ]
            descendant_rows = [
                row
                for row in parser_rows
                if row.get("block_id") == heading_id
                or heading_id
                in {value for value in row.get("parent_heading_ids", "").split(";") if value}
            ]
            direct_text_rows = [
                row
                for row in text_rows
                if row.get("parent_heading_ids", "").split(";")[-1:] == [heading_id]
            ]
            descendant_text_rows = [
                row for row in descendant_rows if row.get("block_type") == "TEXT_BLOCK"
            ]
            section_path = str(heading.get("section_path") or "[ROOT]")
            child_ids = child_heading_ids.get(heading_id, [])
            descendant_candidate_rows = [
                row for row in descendant_text_rows if row.get("question_allowed")
            ]
            direct_candidate_rows = [row for row in direct_text_rows if row.get("question_allowed")]
            page_values = [
                int(row.get("page_start") or 0) for row in descendant_rows if row.get("page_start")
            ]
            page_end_values = [
                int(row.get("page_end") or 0) for row in descendant_rows if row.get("page_end")
            ]
            outline_id = f"{document_id}:OUTLINE:{_sha256(section_path.encode('utf-8'))[:16]}"
            parent_outline_id = ""
            if parent_ids:
                parent_section_path = next(
                    (
                        item.get("section_path", "")
                        for item in headings
                        if item.get("block_id") == parent_ids[-1]
                    ),
                    "",
                )
                if parent_section_path:
                    parent_outline_id = (
                        f"{document_id}:OUTLINE:"
                        f"{_sha256(parent_section_path.encode('utf-8'))[:16]}"
                    )
            direct_block_ids = [row["block_id"] for row in direct_text_rows]
            descendant_block_ids = [row["block_id"] for row in descendant_text_rows]
            row = {
                "outline_order": outline_order,
                "outline_id": outline_id,
                "document_id": document_id,
                "filename": document.get("filename", heading.get("filename", "")),
                "product_model": Path(document.get("filename", heading.get("filename", "")))
                .stem.removeprefix("netgear-")
                .upper(),
                "heading_block_id": heading_id,
                "heading_text": _clean(heading.get("text", "")),
                "section_path": section_path,
                "parent_section_path": _parent_section_path(section_path),
                "parent_outline_id": parent_outline_id,
                "depth": int(heading.get("heading_depth") or 0),
                "is_leaf_outline": not bool(child_ids),
                "child_outline_count": len(child_ids),
                "descendant_outline_count": sum(
                    1
                    for other in headings
                    if other.get("block_id") != heading_id
                    and heading_id
                    in {value for value in other.get("parent_heading_ids", "").split(";") if value}
                ),
                "direct_text_block_count": len(direct_text_rows),
                "descendant_text_block_count": len(descendant_text_rows),
                "direct_question_candidate_count": len(direct_candidate_rows),
                "descendant_question_candidate_count": len(descendant_candidate_rows),
                "direct_char_count": sum(
                    int(item.get("char_count") or 0) for item in direct_text_rows
                ),
                "descendant_char_count": sum(
                    int(item.get("char_count") or 0) for item in descendant_text_rows
                ),
                "direct_token_estimate": sum(
                    int(item.get("token_estimate") or 0) for item in direct_text_rows
                ),
                "descendant_token_estimate": sum(
                    int(item.get("token_estimate") or 0) for item in descendant_text_rows
                ),
                "page_start": min(page_values, default=0),
                "page_end": max(page_end_values, default=0),
                "page_bin": _page_bin(
                    min(page_values, default=0), int(document.get("page_count") or 0)
                )
                if page_values and document.get("page_count")
                else "",
                "table_figure_block_count": sum(
                    bool(item.get("table_figure_flag")) for item in descendant_text_rows
                ),
                "exact_duplicate_block_count": sum(
                    bool(item.get("exact_duplicate_cluster_id")) for item in descendant_text_rows
                ),
                "template_duplicate_block_count": sum(
                    bool(item.get("template_duplicate_cluster_id")) for item in descendant_text_rows
                ),
                "direct_block_ids": ";".join(direct_block_ids),
                "descendant_block_ids": ";".join(descendant_block_ids),
                "direct_source_frame_ids": ";".join(
                    f"{document_id}:{item['block_id']}" for item in direct_text_rows
                ),
                "question_outline_allowed": bool(not child_ids and direct_candidate_rows),
                "review_reason": (
                    "leaf outline with direct text candidate"
                    if not child_ids and direct_candidate_rows
                    else "parent outline, heading-only, or no structural text candidate"
                ),
            }
            outline_rows.append(row)
            if row["question_outline_allowed"]:
                question_outline_rows.append(
                    {
                        **row,
                        "outline_frame_id": row["outline_id"],
                    }
                )

        top_level = [
            row for row in outline_rows if row["document_id"] == document_id and row["depth"] == 1
        ]
        document_outlines = [row for row in outline_rows if row["document_id"] == document_id]
        question_candidates = [
            row for row in question_outline_rows if row["document_id"] == document_id
        ]
        summary_rows.append(
            {
                "document_id": document_id,
                "filename": document.get("filename", ""),
                "product_model": Path(document.get("filename", ""))
                .stem.removeprefix("netgear-")
                .upper(),
                "page_count": int(document.get("page_count") or 0),
                "outline_node_count": len(document_outlines),
                "top_level_outline_count": len(top_level),
                "leaf_outline_count": sum(
                    bool(row["is_leaf_outline"]) for row in document_outlines
                ),
                "question_outline_candidate_count": len(question_candidates),
                "max_outline_depth": max(
                    (int(row["depth"]) for row in document_outlines), default=0
                ),
                "direct_text_block_count": len(text_rows),
                "question_source_candidate_count": sum(
                    bool(row.get("question_allowed")) for row in text_rows
                ),
                "top_level_outline_paths": " || ".join(row["section_path"] for row in top_level),
            }
        )

    return outline_rows, summary_rows, question_outline_rows


def _outline_report(
    path: Path,
    *,
    outline_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
) -> None:
    """Write a human-readable outline tree while keeping CSVs machine-readable."""

    lines = [
        "# Analisis outline corpus customer service",
        "",
        "Laporan ini menampilkan heading/section yang benar-benar dikeluarkan parser, "
        "bukan label topic. Satu node outline dapat memiliki child node; angka block "
        "langsung dan descendant dibedakan agar section besar tidak disalahartikan sebagai "
        "satu evidence.",
        "",
        "## Ringkasan per dokumen",
        "",
        "| Dokumen | Halaman | Node outline | Top-level | Leaf | Kandidat outline | "
        "Kedalaman maksimum |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['filename']} | {row['page_count']} | {row['outline_node_count']} | "
            f"{row['top_level_outline_count']} | {row['leaf_outline_count']} | "
            f"{row['question_outline_candidate_count']} | {row['max_outline_depth']} |"
        )

    by_document: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in outline_rows:
        by_document[row["document_id"]].append(row)
    lines.extend(["", "## Daftar outline per dokumen", ""])
    for summary in summary_rows:
        document_id = summary["document_id"]
        rows = by_document.get(document_id, [])
        lines.extend(
            [
                f"### {summary['filename']} — {summary['product_model']}",
                "",
                f"{summary['page_count']} halaman; {summary['outline_node_count']} node outline; "
                f"{summary['question_outline_candidate_count']} leaf outline kandidat.",
                "",
            ]
        )
        children: dict[str, list[dict[str, Any]]] = defaultdict(list)
        roots: list[dict[str, Any]] = []
        for row in rows:
            parent = row.get("parent_outline_id", "")
            if parent:
                children[parent].append(row)
            else:
                roots.append(row)

        def emit(
            node: dict[str, Any],
            indent: int,
            *,
            children_by_parent: dict[str, list[dict[str, Any]]] = children,
        ) -> None:
            marker = " [KANDIDAT]" if node.get("question_outline_allowed") else ""
            lines.append(
                f"{'  ' * indent}- **{node['heading_text']}**{marker} — "
                f"hal. {node['page_start']}–{node['page_end']}; "
                f"block langsung {node['direct_text_block_count']}; "
                f"block descendant {node['descendant_text_block_count']}; "
                f"candidate langsung {node['direct_question_candidate_count']}"
            )
            for child in children_by_parent.get(node["outline_id"], []):
                emit(child, indent + 1)

        for root in roots:
            emit(root, 0)
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _quantile(values: list[int], probability: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return int(ordered[lower])
    fraction = index - lower
    return int(round(ordered[lower] + fraction * (ordered[upper] - ordered[lower])))


def _plot_pipeline(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 2.4))
    ax.axis("off")
    boxes = [
        (0.04, "SUMBER\n9 PDF"),
        (0.29, "PARSER\ngeneric-outline"),
        (0.60, "FRAME OUTLINE + BLOCK\nhandoff pertanyaan"),
    ]
    for x, label in boxes:
        ax.text(
            x,
            0.5,
            label,
            ha="center",
            va="center",
            fontsize=11,
            bbox={"boxstyle": "round,pad=0.7", "facecolor": "#e8f1fb", "edgecolor": "#3268a8"},
        )
    for x in (0.17, 0.47):
        ax.annotate(
            "", xy=(x + 0.07, 0.5), xytext=(x, 0.5), arrowprops={"arrowstyle": "->", "lw": 1.8}
        )
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_inventory(path: Path, doc_rows: list[dict[str, Any]]) -> None:
    rows = sorted(doc_rows, key=lambda row: int(row.get("page_count") or 0))
    labels = [row.get("product_model") or row["filename"].removesuffix(".pdf") for row in rows]
    pages = [int(row.get("page_count") or 0) for row in rows]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    bars = ax.barh(labels, pages, color="#4779a8", height=0.62)
    ax.set_xlabel("Halaman")
    ax.set_title("Skala manual customer service: jumlah halaman")
    ax.grid(axis="x", color="#d9e2ec", linewidth=0.8)
    ax.set_axisbelow(True)
    max_pages = max(pages, default=0)
    for bar, page_count in zip(bars, pages, strict=True):
        ax.text(
            page_count + max_pages * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{page_count} halaman",
            va="center",
            fontsize=9,
        )
    ax.set_xlim(0, max_pages * 1.32 if max_pages else 1)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_outline(
    path: Path,
    outline_summary_rows: list[dict[str, Any]],
) -> None:
    """Plot outline candidates, not a forced three-series parser comparison."""

    rows = sorted(
        outline_summary_rows, key=lambda row: int(row.get("question_outline_candidate_count") or 0)
    )
    labels = [row.get("product_model") or row["filename"].removesuffix(".pdf") for row in rows]
    values = [int(row.get("question_outline_candidate_count") or 0) for row in rows]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    bars = ax.barh(labels, values, color="#4779a8", height=0.62)
    ax.set_xlabel("Kandidat leaf outline")
    ax.set_title("Leaf outline eligible untuk random pick yang direview")
    ax.grid(axis="x", color="#d9e2ec", linewidth=0.8)
    ax.set_axisbelow(True)
    max_value = max(values, default=0)
    for bar, row, value in zip(bars, rows, values, strict=True):
        ax.text(
            value + max_value * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{value} kandidat · {row['outline_node_count']} node · "
            f"depth {row['max_outline_depth']}",
            va="center",
            fontsize=8.5,
        )
    ax.set_xlim(0, max_value * 1.32 if max_value else 1)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _report(
    path: Path,
    *,
    datasource: dict[str, Any],
    documents: list[dict[str, Any]],
    page_rows: list[dict[str, Any]],
    block_rows: list[dict[str, Any]],
    frame_rows: list[dict[str, Any]],
    manifest_hash: str,
    question_frame_path: Path,
    question_frame_hash: str,
    outline_report_path: Path,
    question_outline_path: Path,
    question_outline_hash: str,
    outline_summary_rows: list[dict[str, Any]],
    output_root: Path,
) -> None:
    total_pages = sum(int(row.get("page_count") or 0) for row in documents)
    total_chars = sum(int(row.get("text_chars") or 0) for row in documents)
    text_blocks = [row for row in block_rows if row["block_type"] == "TEXT_BLOCK"]
    allowed = sum(bool(row.get("question_allowed")) for row in frame_rows)
    outline_candidates = sum(
        int(row.get("question_outline_candidate_count") or 0)
        for row in outline_summary_rows
    )
    block_lengths = [int(row["char_count"]) for row in text_blocks]
    template_cluster_count = sum(
        bool(row.get("template_duplicate_cluster_id")) for row in block_rows
    )
    exact_cluster_membership_count = sum(
        bool(row.get("exact_duplicate_cluster_id")) for row in block_rows
    )
    blank_pages = sum(bool(row.get("is_blank")) for row in page_rows)
    image_pages = sum(bool(row.get("image_count")) for row in page_rows)
    table_pages = sum(bool(row.get("table_flag")) for row in page_rows)
    figure_pages = sum(bool(row.get("figure_flag")) for row in page_rows)
    p50 = _quantile(block_lengths, 0.50)
    p90 = _quantile(block_lengths, 0.90)
    p95 = _quantile(block_lengths, 0.95)
    p99 = _quantile(block_lengths, 0.99)
    max_block = max(block_lengths) if block_lengths else 0
    lines = [
        "# EDA corpus customer service",
        "",
        f"Dibuat: `{datetime.now(UTC).isoformat()}`  ",
        f"Datasource: `{datasource.get('name')}` (`{datasource.get('id')}`)  ",
        f"Manifest SHA-256: `{manifest_hash}`",
        "",
        "## Snapshot",
        "",
        f"- Dokumen aktif: **{len(documents)}**",
        f"- Halaman: **{total_pages:,}**",
        f"- Teks hasil parsing: **{total_chars:,} karakter**",
        f"- Text block parser: **{len(text_blocks):,}**",
        f"- Leaf outline kandidat untuk random pick: **{outline_candidates:,}**",
        f"- Text block yang lolos diagnostic source: **{allowed:,}** "
        "(lookup context, bukan pool pertanyaan)",
        "",
        "## Diagnostics halaman dan block",
        "",
        f"- Halaman kosong: **{blank_pages:,}**; halaman dengan gambar: **{image_pages:,}**",
        f"- Halaman dengan teks tabel: **{table_pages:,}**; teks figure: **{figure_pages:,}**",
        f"- Kuantil karakter text block: p50 **{p50:,}**, p90 **{p90:,}**, "
        f"p95 **{p95:,}**, p99 **{p99:,}**, max **{max_block:,}**",
        f"- Keanggotaan cluster duplicate exact: **{exact_cluster_membership_count:,}**; "
        f"template: **{template_cluster_count:,}**",
        "",
        "## Coverage per dokumen",
        "",
        "| Dokumen | Halaman | Byte | Bookmark | Heading | Text block | "
        "Karakter teks | Parser | Raw hash |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in documents:
        lines.append(
            f"| {row['filename']} | {row.get('page_count', 0)} | {row.get('byte_size', 0):,} | "
            f"{row.get('outline_bookmark_count', 0)} | {row.get('headings_emitted', 0)} | "
            f"{row.get('text_blocks_emitted', 0)} | {row.get('text_chars', 0):,} | "
            f"{row.get('parser_plugin', '')}@{row.get('parser_version', '')} | "
            f"{'PASS' if row.get('raw_hash_match') else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Analisis outline",
            "",
            "Satu node outline merepresentasikan satu heading parser. `Leaf` adalah outline "
            "tanpa child heading dan menjadi unit kandidat untuk random pick; parent outline "
            "tetap disimpan untuk memahami hierarki dan context.",
            "",
            "| Dokumen | Node outline | Top-level | Leaf | Kandidat outline | Kedalaman maksimum |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in outline_summary_rows:
        lines.append(
            f"| {row['filename']} | {row['outline_node_count']} | "
            f"{row['top_level_outline_count']} | {row['leaf_outline_count']} | "
            f"{row['question_outline_candidate_count']} | {row['max_outline_depth']} |"
        )
    lines.extend(
        [
            "",
            "### Outline tingkat atas per dokumen",
            "",
            "Daftar ini menunjukkan cakupan besar manual sebelum melihat leaf outline. "
            "Tree lengkap dan page span setiap node berada di `outline-report.md`.",
            "",
            "| Dokumen | Outline tingkat atas |",
            "|---|---|",
        ]
    )
    for row in outline_summary_rows:
        top_level = "<br>".join(
            part.strip() for part in str(row.get("top_level_outline_paths") or "").split("||")
        )
        lines.append(f"| {row['filename']} | {top_level} |")
    lines.extend(
        [
            "",
            f"Daftar lengkap outline per dokumen: `{outline_report_path}`.",
            f"Frame outline untuk random pick: `{question_outline_path}` "
            f"(SHA-256 `{question_outline_hash}`).",
        ]
    )
    page_bins = ("P1", "P2", "P3", "P4", "P5")
    lines.extend(
        [
            "",
            "## Coverage struktural question-source",
            "",
            "Pelabelan topic otomatis dinonaktifkan. Tabel ini adalah diagnostic text-block "
            "berdasarkan dokumen dan page bin relatif; ia bukan dasar random pick. Random pick "
            "menggunakan `question_outline_frame.csv`, sedangkan topic/family ditetapkan saat "
            "review anotasi pertanyaan.",
            "",
            "| Document | " + " | ".join(page_bins) + " | Total |",
            "|---|" + "---:|" * (len(page_bins) + 1),
        ]
    )
    for document in documents:
        filename = document["filename"]
        counts = [
            sum(
                bool(row.get("question_allowed"))
                for row in frame_rows
                if row.get("filename") == filename and row.get("page_bin") == page_bin
            )
            for page_bin in page_bins
        ]
        lines.append(
            f"| {filename} | "
            + " | ".join(f"{count:,}" for count in counts)
            + f" | {sum(counts):,} |"
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "- Census berisi 9 row dan setiap row memiliki raw hash unik.",
            "- Identitas/config parser generic-outline dan checksum artifact dicatat per dokumen.",
            "- Cluster duplicate/template hanya diagnostics; tidak ada dokumen sumber yang "
            "dihapus.",
            "- Source frame adalah lookup text block; random pick pertanyaan dilakukan pada "
            "leaf outline frame dan tetap memerlukan review manusia pada Langkah 2.",
            "- Klasifikasi keyword/topic otomatis dinonaktifkan; tidak ada topic "
            "comparison/model yang diinferensikan.",
            "",
            "## Artefak",
            "",
            f"Tabel transition: `{output_root / 'transition'}`  ",
            f"Handoff question-source: `{question_frame_path}`  ",
            f"SHA-256 frame question-source: `{question_frame_hash}`  ",
            f"Analisis outline lengkap: `{outline_report_path}`  ",
            f"Frame outline question: `{question_outline_path}` "
            f"(SHA-256 `{question_outline_hash}`)  ",
            f"Visual yang dipertahankan: `{output_root / '00_corpus_pipeline_flow.png'}`, "
            f"`{output_root / '01_document_page_bytes.png'}`, dan "
            f"`{output_root / '02_outline_and_block_coverage.png'}`",
            "Diagnostics parser dan redundancy tetap berada di file CSV/JSON transition; "
            "frame question-source berada di luar transition karena menjadi input Langkah 2.",
            "",
            "Laporan ini hanya untuk Langkah 1. Tidak ada question set, profile, index, atau "
            "retrieval run yang dibuat.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    output_root = args.output_dir
    transition = output_root / "transition"
    output_root.mkdir(parents=True, exist_ok=True)
    transition.mkdir(parents=True, exist_ok=True)

    datasource, records = fetch_catalog(args.dsn, args.datasource)
    client = _s3_client(args)
    document_rows: list[dict[str, Any]] = []
    block_rows: list[dict[str, Any]] = []
    page_rows: list[dict[str, Any]] = []
    section_rows: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    parser_rows_by_document: dict[str, list[dict[str, Any]]] = {}
    manifest_documents: list[dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        print(f"[{index}/{len(records)}] {record.filename}", flush=True)
        base: dict[str, Any] = {
            "document_index": index,
            "document_id": record.document_id,
            "source_identifier": record.source_identifier,
            "source_url": record.source_url,
            "filename": record.filename,
            "extension": record.extension,
            "object_key": record.object_key,
            "byte_size": record.byte_size,
            "content_sha256": record.content_sha256,
            "active_status": record.status,
            "raw_hash_match": False,
            "raw_fetch_status": "FAILED",
            "page_count": 0,
            "text_chars": 0,
            "word_count": 0,
            "token_estimate": 0,
            "blank_pages": 0,
            "image_pages": 0,
            "table_pages": 0,
            "figure_pages": 0,
            "outline_bookmark_count": 0,
            "headings_emitted": 0,
            "text_blocks_emitted": 0,
        }
        parser_payload, canonical_payload, parser_checks = _load_parser(client, args, record)
        base.update(parser_checks)
        try:
            raw = client.get_object(Bucket=args.bucket, Key=record.object_key)["Body"].read()
            actual_hash = _sha256(raw)
            base["raw_hash_match"] = actual_hash == record.content_sha256
            base["raw_hash_actual"] = actual_hash
            base["raw_fetch_status"] = "READY"
            pdf = fitz.open(stream=raw, filetype="pdf")
            base["page_count"] = pdf.page_count
            for page_index in range(pdf.page_count):
                page = pdf.load_page(page_index)
                text = page.get_text("text") or ""
                words = page.get_text("words") or []
                pdf_blocks = page.get_text("blocks") or []
                images = page.get_images(full=True) or []
                drawings = page.get_drawings() or []
                has_table = bool(TABLE_RE.search(text))
                has_figure = bool(FIGURE_RE.search(text))
                row = {
                    "document_index": index,
                    "document_id": record.document_id,
                    "filename": record.filename,
                    "page_index": page_index,
                    "page_number": page_index + 1,
                    "page_bin": _page_bin(page_index + 1, pdf.page_count),
                    "text_chars": len(text),
                    "word_count": len(words),
                    "token_estimate": _token_estimate(text),
                    "pdf_text_blocks": len(pdf_blocks),
                    "image_count": len(images),
                    "drawing_count": len(drawings),
                    "has_text": bool(_clean(text)),
                    "is_blank": not bool(_clean(text)),
                    "table_flag": has_table,
                    "figure_flag": has_figure,
                }
                page_rows.append(row)
                base["text_chars"] += len(text)
                base["word_count"] += len(words)
                base["token_estimate"] += _token_estimate(text)
                base["blank_pages"] += int(row["is_blank"])
                base["image_pages"] += int(bool(images))
                base["table_pages"] += int(has_table)
                base["figure_pages"] += int(has_figure)
            pdf.close()
        except Exception as exc:  # noqa: BLE001 - one document remains visible
            base["raw_error"] = f"{type(exc).__name__}: {_clean(exc)}"

        parser_rows: list[dict[str, Any]] = []
        canonical: CanonicalDocument | None = None
        if parser_payload and canonical_payload:
            canonical = CanonicalDocument.model_validate(canonical_payload)
            metadata = canonical.metadata
            base["outline_bookmark_count"] = int(metadata.get("outline_bookmark_count") or 0)
            base["headings_emitted"] = int(metadata.get("headings_emitted") or 0)
            base["text_blocks_emitted"] = int(metadata.get("text_blocks_emitted") or 0)
            base["parser_page_count"] = int(metadata.get("page_count") or 0)
            parser_rows = list(
                _walk_blocks(
                    canonical.model_dump(mode="json")["blocks"],
                    document=record,
                    page_count=base["page_count"] or int(canonical.metadata.get("page_count") or 0),
                )
            )
            text_char_cursor = 0
            text_sequence = 0
            for block_sequence, row in enumerate(parser_rows, start=1):
                row["block_sequence"] = block_sequence
                if row["block_type"] != "TEXT_BLOCK":
                    continue
                row["text_block_sequence"] = text_sequence
                row["char_start"] = text_char_cursor
                row["char_end"] = text_char_cursor + int(row["char_count"])
                text_char_cursor = row["char_end"] + 1
                text_sequence += 1
            for row in parser_rows:
                row["text_sha256"] = _sha256(row["text"].encode("utf-8"))
                row["question_allowed"], row["review_reason"] = _question_allowed(
                    row["text"], row["evidence_shape"]
                )
            block_rows.extend(parser_rows)
            text_parser_rows = [row for row in parser_rows if row["block_type"] == "TEXT_BLOCK"]
            for path, grouped in _group_sections(parser_rows):
                section_rows.append(
                    {
                        "document_id": record.document_id,
                        "filename": record.filename,
                        "section_path": path,
                        "depth": max(0, path.count(" > ") + (0 if path == "[ROOT]" else 1)),
                        "block_count": len(grouped),
                        "text_block_count": sum(
                            row["block_type"] == "TEXT_BLOCK" for row in grouped
                        ),
                        "char_count": sum(
                            row["char_count"]
                            for row in grouped
                            if row["block_type"] == "TEXT_BLOCK"
                        ),
                        "page_start": min(
                            (row["page_start"] for row in grouped if row["page_start"]), default=0
                        ),
                        "page_end": max((row["page_end"] for row in grouped), default=0),
                    }
                )
            frame_rows.extend(
                {
                    **row,
                    "source_frame_id": f"{record.document_id}:{row['block_id']}",
                    "duplicate_cluster_id": row.get("template_duplicate_cluster_id", ""),
                }
                for row in text_parser_rows
            )
            parser_rows_by_document[record.document_id] = parser_rows
        document_rows.append(base)
        manifest_documents.append(
            {
                "document_index": index,
                "document_id": record.document_id,
                "source_identifier": record.source_identifier,
                "filename": record.filename,
                "object_key": record.object_key,
                "byte_size": record.byte_size,
                "content_sha256": record.content_sha256,
                "page_count": base["page_count"],
                "parser_artifact": record.parser_artifact,
                "parser_artifact_checksum": (record.parser_artifact or {}).get(
                    "artifact_sha256", ""
                ),
            }
        )

    _assign_clusters(block_rows)
    # Propagate cluster IDs into the question-source frame after the assignment pass.
    by_source = {(row["document_id"], row["block_id"]): row for row in block_rows}
    for row in frame_rows:
        source = by_source.get((row["document_id"], row["block_id"]))
        if source:
            row["exact_duplicate_cluster_id"] = source.get("exact_duplicate_cluster_id", "")
            row["template_duplicate_cluster_id"] = source.get("template_duplicate_cluster_id", "")
            row["duplicate_cluster_id"] = source.get("template_duplicate_cluster_id", "")

    outline_rows, outline_summary_rows, question_outline_rows = _outline_inventory(
        parser_rows_by_document,
        document_rows,
    )

    manifest_core = {
        "run_type": "customer_service_census_eda",
        "datasource": datasource,
        "selection": "all active PDF documents ordered by filename and document_id",
        "document_count": len(manifest_documents),
        "documents": manifest_documents,
    }
    # Exclude generation time so the corpus-manifest hash stays stable across reruns.
    manifest_hash = _json_hash(manifest_core)
    manifest = {"generated_at": datetime.now(UTC).isoformat(), **manifest_core}
    manifest["manifest_sha256"] = manifest_hash
    _json(transition / "corpus-manifest.json", manifest)

    _csv(
        transition / "document_inventory.csv",
        document_rows,
        list(document_rows[0].keys()) if document_rows else [],
    )
    quality_fields = [
        "document_index",
        "document_id",
        "filename",
        "page_count",
        "parser_page_count",
        "outline_bookmark_count",
        "headings_emitted",
        "text_blocks_emitted",
        "parser_status",
        "parser_plugin",
        "parser_version",
        "parser_input_hash_match",
        "parser_content_hash_match",
        "parser_document_id_match",
        "parser_payload_hash_match",
        "parser_error",
    ]
    _csv(transition / "parser_quality.csv", document_rows, quality_fields)
    _csv(
        transition / "page_inventory.csv", page_rows, list(page_rows[0].keys()) if page_rows else []
    )
    _csv(
        transition / "section_inventory.csv",
        section_rows,
        list(section_rows[0].keys()) if section_rows else [],
    )
    question_frame_path = output_root / "question_source_frame.csv"
    _csv(
        question_frame_path,
        frame_rows,
        list(frame_rows[0].keys()) if frame_rows else [],
    )
    question_frame_hash = _sha256(question_frame_path.read_bytes())
    outline_inventory_path = transition / "outline_inventory.csv"
    outline_inventory_fields = [
        "outline_order",
        "outline_id",
        "document_id",
        "filename",
        "product_model",
        "heading_block_id",
        "heading_text",
        "section_path",
        "parent_section_path",
        "parent_outline_id",
        "depth",
        "is_leaf_outline",
        "child_outline_count",
        "descendant_outline_count",
        "direct_text_block_count",
        "descendant_text_block_count",
        "direct_question_candidate_count",
        "descendant_question_candidate_count",
        "direct_char_count",
        "descendant_char_count",
        "direct_token_estimate",
        "descendant_token_estimate",
        "page_start",
        "page_end",
        "page_bin",
        "table_figure_block_count",
        "exact_duplicate_block_count",
        "template_duplicate_block_count",
        "direct_block_ids",
        "descendant_block_ids",
        "direct_source_frame_ids",
        "question_outline_allowed",
        "review_reason",
    ]
    _csv(outline_inventory_path, outline_rows, outline_inventory_fields)
    outline_summary_path = transition / "outline_summary.csv"
    _csv(
        outline_summary_path,
        outline_summary_rows,
        list(outline_summary_rows[0].keys()) if outline_summary_rows else [],
    )
    question_outline_path = output_root / "question_outline_frame.csv"
    question_outline_fields = [
        "outline_frame_id",
        "outline_id",
        "document_id",
        "filename",
        "product_model",
        "heading_block_id",
        "heading_text",
        "section_path",
        "parent_section_path",
        "depth",
        "page_start",
        "page_end",
        "page_bin",
        "direct_text_block_count",
        "descendant_text_block_count",
        "direct_question_candidate_count",
        "descendant_question_candidate_count",
        "direct_char_count",
        "descendant_char_count",
        "direct_token_estimate",
        "descendant_token_estimate",
        "table_figure_block_count",
        "direct_block_ids",
        "descendant_block_ids",
        "direct_source_frame_ids",
        "question_outline_allowed",
        "review_reason",
    ]
    _csv(question_outline_path, question_outline_rows, question_outline_fields)
    question_outline_hash = _sha256(question_outline_path.read_bytes())
    outline_report_path = output_root / "outline-report.md"
    _outline_report(
        outline_report_path,
        outline_rows=outline_rows,
        summary_rows=outline_summary_rows,
    )
    redundancy_rows: list[dict[str, Any]] = []
    clusters: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in block_rows:
        for kind in ("exact_duplicate_cluster_id", "template_duplicate_cluster_id"):
            cluster_id = row.get(kind, "")
            if cluster_id:
                clusters[(kind, cluster_id)].append(row)
    for (kind, cluster_id), members in sorted(clusters.items()):
        redundancy_rows.append(
            {
                "cluster_type": kind.removesuffix("_duplicate_cluster_id"),
                "cluster_id": cluster_id,
                "member_count": len(members),
                "document_count": len({row["document_id"] for row in members}),
                "documents": ";".join(sorted({row["filename"] for row in members})),
                "sample_text": _clean(members[0]["text"])[:300],
                "member_block_ids": ";".join(row["block_id"] for row in members),
            }
        )
    _csv(
        transition / "redundancy_clusters.csv",
        redundancy_rows,
        list(redundancy_rows[0].keys())
        if redundancy_rows
        else [
            "cluster_type",
            "cluster_id",
            "member_count",
            "document_count",
            "documents",
            "sample_text",
            "member_block_ids",
        ],
    )

    text_lengths = [
        int(row["char_count"]) for row in block_rows if row["block_type"] == "TEXT_BLOCK"
    ]
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "datasource": datasource,
        "datasource_id": datasource.get("id"),
        "document_count": len(document_rows),
        "active_document_count": sum(row.get("active_status") == "active" for row in document_rows),
        "raw_hash_match_count": sum(bool(row.get("raw_hash_match")) for row in document_rows),
        "page_count": sum(int(row.get("page_count") or 0) for row in document_rows),
        "text_chars": sum(int(row.get("text_chars") or 0) for row in document_rows),
        "blank_pages": sum(bool(row.get("is_blank")) for row in page_rows),
        "image_pages": sum(bool(row.get("image_count")) for row in page_rows),
        "table_pages": sum(bool(row.get("table_flag")) for row in page_rows),
        "figure_pages": sum(bool(row.get("figure_flag")) for row in page_rows),
        "text_block_char_quantiles": {
            "p50": _quantile(text_lengths, 0.50),
            "p90": _quantile(text_lengths, 0.90),
            "p95": _quantile(text_lengths, 0.95),
            "p99": _quantile(text_lengths, 0.99),
            "max": max(text_lengths) if text_lengths else 0,
        },
        "parser_headings": sum(int(row.get("headings_emitted") or 0) for row in document_rows),
        "parser_text_blocks": sum(
            int(row.get("text_blocks_emitted") or 0) for row in document_rows
        ),
        "question_source_candidates": sum(bool(row.get("question_allowed")) for row in frame_rows),
        "question_source_frame_path": str(question_frame_path),
        "question_source_frame_sha256": question_frame_hash,
        "outline_node_count": len(outline_rows),
        "outline_document_count": len(outline_summary_rows),
        "outline_leaf_count": sum(bool(row.get("is_leaf_outline")) for row in outline_rows),
        "question_outline_candidate_count": len(question_outline_rows),
        "outline_report_path": str(outline_report_path),
        "outline_summary_path": str(outline_summary_path),
        "question_outline_frame_path": str(question_outline_path),
        "question_outline_frame_sha256": question_outline_hash,
        "question_source_classification": {
            "method": "outline_random_pick_planned",
            "status": "outline_review_pending",
            "reason": (
                "Question selection uses a seeded random pick from eligible leaf outlines; "
                "substring topic/comparison labels are not used."
            ),
        },
        "template_duplicate_cluster_count": sum(
            row["cluster_type"] == "template" for row in redundancy_rows
        ),
        "exact_duplicate_cluster_count": sum(
            row["cluster_type"] == "exact" for row in redundancy_rows
        ),
        "manifest_sha256": manifest_hash,
        "parser_plugin_versions": sorted(
            {
                f"{row.get('parser_plugin')}@{row.get('parser_version')}"
                for row in document_rows
                if row.get("parser_plugin")
            }
        ),
        "gates": {
            "nine_documents": len(document_rows) == 9,
            "all_raw_hashes_match": all(bool(row.get("raw_hash_match")) for row in document_rows),
            "all_parser_generic_outline": all(
                row.get("parser_plugin") == "generic-outline" for row in document_rows
            ),
            "all_parser_input_hashes_match": all(
                bool(row.get("parser_input_hash_match")) for row in document_rows
            ),
            "all_parser_content_hashes_match": all(
                bool(row.get("parser_content_hash_match")) for row in document_rows
            ),
        },
    }
    _json(transition / "summary.json", summary)
    _report(
        output_root / "eda-report.md",
        datasource=datasource,
        documents=document_rows,
        page_rows=page_rows,
        block_rows=block_rows,
        frame_rows=frame_rows,
        manifest_hash=manifest_hash,
        question_frame_path=question_frame_path,
        question_frame_hash=question_frame_hash,
        outline_report_path=outline_report_path,
        question_outline_path=question_outline_path,
        question_outline_hash=question_outline_hash,
        outline_summary_rows=outline_summary_rows,
        output_root=output_root,
    )

    _plot_pipeline(output_root / "00_corpus_pipeline_flow.png")
    _plot_inventory(output_root / "01_document_page_bytes.png", document_rows)
    _plot_outline(output_root / "02_outline_and_block_coverage.png", outline_summary_rows)
    print(f"EDA complete: {output_root / 'eda-report.md'}", flush=True)
    print(f"Manifest SHA-256: {manifest_hash}", flush=True)
    return 0


def _group_sections(rows: list[dict[str, Any]]) -> Iterable[tuple[str, list[dict[str, Any]]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["section_path"]].append(row)
    return sorted(groups.items())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasource", default=DATASOURCE)
    parser.add_argument("--dsn", default=os.getenv("CUSTOMER_EDA_DSN", DEFAULT_DSN))
    parser.add_argument(
        "--s3-endpoint", default=os.getenv("CUSTOMER_EDA_S3_ENDPOINT", DEFAULT_S3_ENDPOINT)
    )
    parser.add_argument("--s3-access-key", default=os.getenv("S3_ACCESS_KEY_ID", "minioadmin"))
    parser.add_argument("--s3-secret-key", default=os.getenv("S3_SECRET_ACCESS_KEY", "minioadmin"))
    parser.add_argument("--s3-region", default=os.getenv("S3_REGION_NAME", DEFAULT_REGION))
    parser.add_argument("--s3-use-ssl", action="store_true")
    parser.add_argument("--bucket", default=os.getenv("S3_BUCKET_NAME", DEFAULT_BUCKET))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser


if __name__ == "__main__":
    raise SystemExit(run(_parser().parse_args()))
