#!/usr/bin/env python3
"""Analyze single-block retrieval traces with the explicit chunk-level contract."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_RUN_DIR = ROOT / (
    "experiments/offline-rag-experiments/customer_service_revision/"
    "03-implementation/runs/single-block/raw-e2e-existing-k60"
)
DEFAULT_OUTPUT_DIR = ROOT / (
    "experiments/offline-rag-experiments/customer_service_revision/"
    "03-implementation/runs/single-block/analysis"
)
CUTOFFS = tuple(range(5, 61, 5))
CONDITIONS = (
    "baseline-generic-hybrid",
    "chunker-generic-recursive",
    "chunker-generic-sliding-window",
    "indexer-generic-sparse",
    "indexer-generic-dense",
)
LABELS = {
    "baseline-generic-hybrid": "Hybrid baseline",
    "chunker-generic-recursive": "Recursive chunker",
    "chunker-generic-sliding-window": "Sliding-window chunker",
    "indexer-generic-sparse": "Sparse indexer",
    "indexer-generic-dense": "Dense indexer",
}
COLORS = {
    "baseline-generic-hybrid": "#1f4e79",
    "chunker-generic-recursive": "#c55a11",
    "chunker-generic-sliding-window": "#2f7d32",
    "indexer-generic-sparse": "#7f3c8d",
    "indexer-generic-dense": "#117a8b",
}
METRICS = (
    ("chunk_precision", "Chunk precision"),
    ("chunk_success", "Chunk success"),
    ("gold_block_recall", "Gold-block recall"),
    ("chunk_ndcg", "Chunk NDCG"),
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def metric(row: dict[str, Any], name: str, cutoff: int) -> float:
    return float(row.get(f"{name}@{cutoff}", 0.0) or 0.0)


def aggregate(rows: list[dict[str, Any]], cutoff: int, scope: str = "combined") -> dict[str, Any]:
    return {
        "analysis_scope": scope,
        "condition_id": rows[0]["condition_id"],
        "condition_label": LABELS.get(rows[0]["condition_id"], rows[0]["condition_id"]),
        "cutoff_k": cutoff,
        "question_count": len(rows),
        "mean_retrieved_count": fmean(float(row.get("retrieved_count", 0)) for row in rows),
        "mean_hit_chunk_count": fmean(float(row.get(f"hit_chunk_count@{cutoff}", 0)) for row in rows),
        "chunk_precision": fmean(metric(row, "chunk_precision", cutoff) for row in rows),
        "chunk_success": fmean(metric(row, "chunk_success", cutoff) for row in rows),
        "gold_block_recall": fmean(metric(row, "gold_block_recall", cutoff) for row in rows),
        "chunk_ndcg": fmean(metric(row, "chunk_ndcg", cutoff) for row in rows),
        "empty_rate": fmean(float(bool(row.get("retrieval_empty"))) for row in rows),
        "median_latency_ms": median(float(row.get("elapsed_ms", 0.0)) for row in rows),
    }


def load_trace_rows(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        path = run_dir / condition / "per-question-results.jsonl"
        if not path.exists():
            raise FileNotFoundError(path)
        condition_rows = read_jsonl(path)
        if len(condition_rows) != 200:
            raise ValueError(f"{condition}: expected 200 rows, found {len(condition_rows)}")
        language_counts = {
            language: sum(str(row.get("language")) == language for row in condition_rows)
            for language in ("en", "id")
        }
        if language_counts != {"en": 100, "id": 100}:
            raise ValueError(f"{condition}: expected 100 English and 100 Indonesian rows, found {language_counts}")
        for row in condition_rows:
            if len(row.get("gold_evidence_block_ids", [])) != 1:
                raise ValueError(f"{condition}/{row.get('question_id')}: single-block analysis requires one gold block")
            row["condition_id"] = condition
            candidates = row.get("retrieval_candidates")
            prefix = [item for item in candidates if isinstance(item, dict)] if isinstance(candidates, list) else []
            for cutoff in CUTOFFS:
                row[f"hit_chunk_count@{cutoff}"] = sum(
                    1
                    for item in prefix[:cutoff]
                    if item.get("source_block_ids")
                    and set(item["source_block_ids"] if isinstance(item["source_block_ids"], list) else [item["source_block_ids"]])
                    & set(row.get("gold_evidence_block_ids", []))
                )
            hit_ranks = [
                index + 1
                for index, item in enumerate(prefix)
                if item.get("source_block_ids")
                and set(item["source_block_ids"] if isinstance(item["source_block_ids"], list) else [item["source_block_ids"]])
                & set(row.get("gold_evidence_block_ids", []))
            ]
            row["first_hit_rank"] = hit_ranks[0] if hit_ranks else None
            row["first_hit_reciprocal_rank"] = 1.0 / hit_ranks[0] if hit_ranks else 0.0
            row["first_hit_cutoff"] = next(
                (cutoff for cutoff in CUTOFFS if row[f"chunk_success@{cutoff}"]),
                None,
            )
            for cutoff in CUTOFFS:
                if float(row[f"gold_block_recall@{cutoff}"]) != float(row[f"chunk_success@{cutoff}"]):
                    raise ValueError(f"{condition}/{row.get('question_id')}: single-block success and recall diverge")
        rows.extend(condition_rows)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
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


def build_aggregates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["condition_id"], "combined")].append(row)
        grouped[(row["condition_id"], str(row.get("language", "unknown")))].append(row)
        grouped[(row["condition_id"], f"family:{row.get('question_family', 'unknown')}")].append(row)
        grouped[(row["condition_id"], f"product:{row.get('product_model', 'unknown')}")].append(row)
    result: list[dict[str, Any]] = []
    for (condition, scope), group in grouped.items():
        for cutoff in CUTOFFS:
            result.append(aggregate(group, cutoff, scope))
    return result


def plot_quality(output_dir: Path, aggregates: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    combined = {
        condition: [row for row in aggregates if row["condition_id"] == condition and row["analysis_scope"] == "combined"]
        for condition in CONDITIONS
    }
    figure, axes = plt.subplots(2, 2, figsize=(15, 9), sharex=True)
    for axis, (name, title) in zip(axes.flat, METRICS, strict=True):
        for condition in CONDITIONS:
            series = combined[condition]
            axis.plot(
                [row["cutoff_k"] for row in series],
                [row[name] for row in series],
                marker="o",
                markersize=3,
                linewidth=2,
                color=COLORS[condition],
                label=LABELS[condition],
            )
        axis.set_title(title)
        axis.set_ylabel("Mean score")
        axis.set_ylim(0, 1.02)
        axis.set_xticks(CUTOFFS)
        axis.grid(axis="y", alpha=0.25)
    axes[1, 0].set_xlabel("Retrieval cutoff K")
    axes[1, 1].set_xlabel("Retrieval cutoff K")
    axes[0, 1].legend(loc="lower right", fontsize=8, frameon=False)
    figure.suptitle("Customer Service single-block retrieval quality")
    figure.tight_layout()
    figure.savefig(output_dir / "retrieval-quality-by-cutoff.png", dpi=190, bbox_inches="tight")
    plt.close(figure)


def plot_language(output_dir: Path, aggregates: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 4, figsize=(20, 8), sharex=True, sharey="col")
    for row_index, language in enumerate(("en", "id")):
        for column_index, (name, title) in enumerate(METRICS):
            axis = axes[row_index, column_index]
            for condition in CONDITIONS:
                series = [
                    row for row in aggregates
                    if row["condition_id"] == condition and row["analysis_scope"] == language
                ]
                axis.plot(
                    [row["cutoff_k"] for row in series],
                    [row[name] for row in series],
                    color=COLORS[condition],
                    linewidth=1.6,
                    label=LABELS[condition],
                )
            axis.set_title(f"{language.upper()} — {title}")
            axis.set_xticks(CUTOFFS)
            axis.set_ylim(0, 1.02)
            axis.grid(axis="y", alpha=0.25)
    axes[1, 1].legend(loc="lower right", fontsize=7, frameon=False)
    figure.suptitle("Single-block quality by language")
    figure.tight_layout()
    figure.savefig(output_dir / "language-quality-by-cutoff.png", dpi=190, bbox_inches="tight")
    plt.close(figure)


def plot_cutoff_bars(output_dir: Path, aggregates: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 4, figsize=(18, 8), sharey="col")
    for row_index, cutoff in enumerate((10, 60)):
        for column_index, (name, title) in enumerate(METRICS):
            axis = axes[row_index, column_index]
            rows = {
                row["condition_id"]: row
                for row in aggregates
                if row["analysis_scope"] == "combined" and int(row["cutoff_k"]) == cutoff
            }
            values = [rows[condition][name] for condition in CONDITIONS]
            bars = axis.bar(range(len(CONDITIONS)), values, color=[COLORS[c] for c in CONDITIONS])
            for bar, value in zip(bars, values, strict=True):
                axis.text(bar.get_x() + bar.get_width() / 2, value + 0.02, f"{value:.2f}", ha="center", fontsize=8)
            axis.set_title(f"{title} @ K={cutoff}")
            axis.set_xticks(range(len(CONDITIONS)), [LABELS[c].replace(" chunker", "") for c in CONDITIONS], rotation=35, ha="right")
            axis.set_ylim(0, 1.08)
            axis.grid(axis="y", alpha=0.25)
    figure.suptitle("Single-block condition comparison")
    figure.tight_layout()
    figure.savefig(output_dir / "condition-quality-at-k10-k60.png", dpi=190, bbox_inches="tight")
    plt.close(figure)


def plot_execution(output_dir: Path, aggregates: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    rows = [row for row in aggregates if row["analysis_scope"] == "combined" and int(row["cutoff_k"]) == 10]
    figure, axis = plt.subplots(figsize=(11, 5))
    x = list(range(len(CONDITIONS)))
    latency = [next(row["median_latency_ms"] for row in rows if row["condition_id"] == condition) / 1000 for condition in CONDITIONS]
    empty = [next(row["empty_rate"] for row in rows if row["condition_id"] == condition) for condition in CONDITIONS]
    bars = axis.bar(x, latency, color=[COLORS[c] for c in CONDITIONS], alpha=0.85)
    for bar, value in zip(bars, latency, strict=True):
        axis.text(bar.get_x() + bar.get_width() / 2, value + 0.05, f"{value:.1f}s", ha="center", fontsize=9)
    axis.set_ylabel("Median latency (seconds)")
    axis.set_xticks(x, [LABELS[c] for c in CONDITIONS], rotation=25, ha="right")
    axis.set_title("Execution latency at K=10; all empty rates are shown in the report")
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_dir / "execution-latency.png", dpi=190, bbox_inches="tight")
    plt.close(figure)
    (output_dir / "execution-empty-rate.csv").write_text(
        "condition_id,empty_rate_at_10\n" + "".join(f"{condition},{value:.6f}\n" for condition, value in zip(CONDITIONS, empty, strict=True)),
        encoding="utf-8",
    )


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def build_pair_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[(row["condition_id"], str(row["question_pair_id"]))][str(row["language"])] = row
    result: list[dict[str, Any]] = []
    for (condition, pair_id), languages in sorted(grouped.items()):
        if set(languages) != {"en", "id"}:
            raise ValueError(f"{condition}/{pair_id}: expected exactly one en and one id row")
        en, ind = languages["en"], languages["id"]
        output: dict[str, Any] = {
            "condition_id": condition,
            "condition_label": LABELS.get(condition, condition),
            "question_pair_id": pair_id,
            "question_family": en.get("question_family", ""),
            "product_model": en.get("product_model", ""),
        }
        for cutoff in CUTOFFS:
            for name in ("chunk_precision", "chunk_success", "gold_block_recall", "chunk_ndcg"):
                en_value = metric(en, name, cutoff)
                id_value = metric(ind, name, cutoff)
                output[f"en_{name}@{cutoff}"] = en_value
                output[f"id_{name}@{cutoff}"] = id_value
                output[f"id_minus_en_{name}@{cutoff}"] = id_value - en_value
            output[f"both_language_success@{cutoff}"] = int(metric(en, "chunk_success", cutoff) and metric(ind, "chunk_success", cutoff))
            output[f"language_disagreement@{cutoff}"] = int(metric(en, "chunk_success", cutoff) != metric(ind, "chunk_success", cutoff))
        result.append(output)
    return result


def build_condition_diagnostics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        group = [row for row in rows if row["condition_id"] == condition]
        hit_ranks = [float(row["first_hit_rank"]) for row in group if row.get("first_hit_rank")]
        first_cutoffs = [float(row["first_hit_cutoff"]) for row in group if row.get("first_hit_cutoff")]
        result.append(
            {
                "condition_id": condition,
                "condition_label": LABELS[condition],
                "question_count": len(group),
                "mean_candidate_pool": fmean(float(row.get("retrieved_count", 0)) for row in group),
                "p90_candidate_pool": percentile([float(row.get("retrieved_count", 0)) for row in group], 0.9),
                "first_hit_rank_mean": fmean(hit_ranks) if hit_ranks else 0.0,
                "first_hit_rank_median": median(hit_ranks) if hit_ranks else 0.0,
                "first_hit_rank_p90": percentile(hit_ranks, 0.9),
                "first_hit_reciprocal_rank": fmean(float(row.get("first_hit_reciprocal_rank", 0.0)) for row in group),
                "first_hit_cutoff_mean": fmean(first_cutoffs) if first_cutoffs else 0.0,
                "no_hit_rate_at_10": fmean(1.0 - metric(row, "chunk_success", 10) for row in group),
                "no_hit_rate_at_60": fmean(1.0 - metric(row, "chunk_success", 60) for row in group),
                "median_latency_ms": median(float(row.get("elapsed_ms", 0.0)) for row in group),
                "p90_latency_ms": percentile([float(row.get("elapsed_ms", 0.0)) for row in group], 0.9),
            }
        )
    return result


def plot_product_recall(output_dir: Path, aggregates: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    products = sorted({row["analysis_scope"].partition(":")[2] for row in aggregates if row["analysis_scope"].startswith("product:")})
    figure, axes = plt.subplots(1, 2, figsize=(17, 7), sharey=True, constrained_layout=True)
    for axis, cutoff in zip(axes, (10, 60), strict=True):
        matrix = []
        for product in products:
            values = {
                row["condition_id"]: row["gold_block_recall"]
                for row in aggregates
                if row["analysis_scope"] == f"product:{product}" and int(row["cutoff_k"]) == cutoff
            }
            matrix.append([values.get(condition, 0.0) for condition in CONDITIONS])
        image = axis.imshow(matrix, vmin=0.0, vmax=1.0, aspect="auto", cmap="YlGnBu")
        axis.set_title(f"Gold-block recall @ K={cutoff}")
        axis.set_xticks(range(len(CONDITIONS)), [LABELS[c].replace(" chunker", "") for c in CONDITIONS], rotation=35, ha="right")
        axis.set_yticks(range(len(products)), products)
        for row_index, values in enumerate(matrix):
            for column_index, value in enumerate(values):
                axis.text(column_index, row_index, f"{value:.2f}", ha="center", va="center", fontsize=8)
    figure.colorbar(image, ax=axes, shrink=0.75, pad=0.03, label="Mean recall")
    figure.suptitle("Single-block product coverage")
    figure.savefig(output_dir / "product-recall-at-k10-k60.png", dpi=190, bbox_inches="tight")
    plt.close(figure)


def plot_first_hit_rank(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(11, 6))
    for condition in CONDITIONS:
        ranks = sorted(float(row["first_hit_rank"]) for row in rows if row["condition_id"] == condition and row.get("first_hit_rank"))
        if not ranks:
            continue
        axis.step(ranks, [(index + 1) / len(ranks) for index in range(len(ranks))], where="post", color=COLORS[condition], linewidth=2, label=LABELS[condition])
    axis.set_xlabel("Rank of first hit chunk (hit questions only)")
    axis.set_ylabel("Cumulative fraction of hit questions")
    axis.set_xlim(1, 60)
    axis.set_ylim(0, 1.02)
    axis.grid(axis="both", alpha=0.25)
    axis.legend(frameon=False)
    axis.set_title("First-hit rank distribution")
    figure.tight_layout()
    figure.savefig(output_dir / "first-hit-rank-cdf.png", dpi=190, bbox_inches="tight")
    plt.close(figure)


def plot_language_delta(output_dir: Path, pair_rows: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    metrics = (("chunk_precision", "Precision"), ("gold_block_recall", "Gold recall"), ("chunk_ndcg", "NDCG"))
    figure, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=False)
    x = list(range(len(CONDITIONS)))
    width = 0.35
    for axis, (name, title) in zip(axes, metrics, strict=True):
        means = {}
        for cutoff in (10, 60):
            means[cutoff] = [
                fmean(float(row[f"id_minus_en_{name}@{cutoff}"]) for row in pair_rows if row["condition_id"] == condition)
                for condition in CONDITIONS
            ]
        axis.bar([value - width / 2 for value in x], means[10], width, label="ID − EN @10", color="#6a3d9a")
        axis.bar([value + width / 2 for value in x], means[60], width, label="ID − EN @60", color="#1b9e77")
        axis.axhline(0.0, color="#333333", linewidth=0.8)
        axis.set_title(title)
        axis.set_xticks(x, [LABELS[c].replace(" chunker", "") for c in CONDITIONS], rotation=35, ha="right")
        axis.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Indonesian minus English mean")
    axes[-1].legend(frameon=False, fontsize=8)
    figure.suptitle("Paired language deltas")
    figure.tight_layout()
    figure.savefig(output_dir / "language-paired-delta-at-k10-k60.png", dpi=190, bbox_inches="tight")
    plt.close(figure)


def plot_precision_recall_tradeoff(output_dir: Path, aggregates: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(10, 7))
    for condition in CONDITIONS:
        series = sorted(
            (row for row in aggregates if row["condition_id"] == condition and row["analysis_scope"] == "combined"),
            key=lambda row: int(row["cutoff_k"]),
        )
        axis.plot([row["gold_block_recall"] for row in series], [row["chunk_precision"] for row in series], marker="o", markersize=4, color=COLORS[condition], label=LABELS[condition])
        for row in series:
            if int(row["cutoff_k"]) in {5, 10, 20, 40, 60}:
                axis.annotate(str(row["cutoff_k"]), (row["gold_block_recall"], row["chunk_precision"]), fontsize=7, xytext=(3, 3), textcoords="offset points")
    axis.set_xlabel("Gold-block recall")
    axis.set_ylabel("Chunk precision (hit chunks / K)")
    axis.set_xlim(0, 1.02)
    axis.set_ylim(0, 0.14)
    axis.grid(axis="both", alpha=0.25)
    axis.legend(frameon=False)
    axis.set_title("Precision–recall trade-off across cutoff K")
    figure.tight_layout()
    figure.savefig(output_dir / "precision-recall-tradeoff.png", dpi=190, bbox_inches="tight")
    plt.close(figure)


def fmt(value: float) -> str:
    return f"{value:.3f}"


def write_report(
    output_dir: Path,
    rows: list[dict[str, Any]],
    aggregates: list[dict[str, Any]],
    pair_rows: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
) -> None:
    def at(condition: str, cutoff: int) -> dict[str, Any]:
        return next(row for row in aggregates if row["condition_id"] == condition and row["analysis_scope"] == "combined" and int(row["cutoff_k"]) == cutoff)

    lines = [
        "# Customer Service single-block retrieval analysis",
        "",
        "Scoring contract: `chunk_precision@K = hit chunks / K`; `chunk_success@K` is any hit; `gold_block_recall@K` is gold-block coverage; `chunk_ndcg@K` ranks hit chunks.",
        "",
        f"- Retrieval traces: `{len(rows)}` (`{len(CONDITIONS)} conditions × 200 questions`).",
        f"- Cutoffs: `{', '.join(map(str, CUTOFFS))}`.",
        f"- Returned candidate pool: mean `{fmean(float(row.get('retrieved_count', 0)) for row in rows):.2f}` chunks, maximum `{max(int(row.get('retrieved_count', 0)) for row in rows)}`; single-block precision still uses the requested K denominator.",
        "- No indexing, question generation, reranker, intent classifier, or LLM answer generation was run by this analysis.",
        "",
        "## Overall comparison",
        "",
        "| Condition | K | Precision | Success | Gold recall | NDCG | Median latency | Empty rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cutoff in (10, 60):
        for condition in CONDITIONS:
            row = at(condition, cutoff)
            lines.append(
                f"| {LABELS[condition]} | {cutoff} | {fmt(row['chunk_precision'])} | {fmt(row['chunk_success'])} | {fmt(row['gold_block_recall'])} | {fmt(row['chunk_ndcg'])} | {row['median_latency_ms'] / 1000:.1f}s | {fmt(row['empty_rate'])} |"
            )
    for cutoff in (10, 60):
        recall_winner = max(CONDITIONS, key=lambda c: at(c, cutoff)["gold_block_recall"])
        precision_winner = max(CONDITIONS, key=lambda c: at(c, cutoff)["chunk_precision"])
        success_winner = max(CONDITIONS, key=lambda c: at(c, cutoff)["chunk_success"])
        ndcg_winner = max(CONDITIONS, key=lambda c: at(c, cutoff)["chunk_ndcg"])
        lines.extend(
            [
                "",
                f"At K={cutoff}, gold recall winner: **{LABELS[recall_winner]}** ({fmt(at(recall_winner, cutoff)['gold_block_recall'])}); precision winner: **{LABELS[precision_winner]}** ({fmt(at(precision_winner, cutoff)['chunk_precision'])}); success winner: **{LABELS[success_winner]}** ({fmt(at(success_winner, cutoff)['chunk_success'])}); NDCG winner: **{LABELS[ndcg_winner]}** ({fmt(at(ndcg_winner, cutoff)['chunk_ndcg'])}).",
            ]
        )
    lines.extend(
        [
            "",
            "## Metrik terpisah per bahasa",
            "",
            "Pemisahan ini wajib: setiap condition memiliki tepat 100 pertanyaan English dan 100 Indonesian. `language-by-cutoff.csv` berisi seluruh grid K; tabel berikut menampilkan titik keputusan K=10 dan K=60.",
            "",
            "| Condition | Bahasa | K | Precision | Success | Gold recall | NDCG | Empty rate |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for cutoff in (10, 60):
        for condition in CONDITIONS:
            for language in ("en", "id"):
                row = next(
                    row for row in aggregates
                    if row["condition_id"] == condition
                    and row["analysis_scope"] == language
                    and int(row["cutoff_k"]) == cutoff
                )
                lines.append(
                    f"| {LABELS[condition]} | {language.upper()} | {cutoff} | {fmt(row['chunk_precision'])} | {fmt(row['chunk_success'])} | {fmt(row['gold_block_recall'])} | {fmt(row['chunk_ndcg'])} | {fmt(row['empty_rate'])} |"
                )
    lines.extend(
        [
            "",
            "## Cara membaca hasil single-block",
            "",
            "Karena setiap pertanyaan memiliki tepat satu gold block, `chunk_success@K` dan `gold_block_recall@K` sama-sama biner pada level pertanyaan. Nilai agregatnya adalah proporsi pertanyaan yang menemukan block tersebut. `chunk_precision@K` tetap menghitung jumlah hit chunk dibagi K, sehingga nilainya turun ketika K bertambah dan kandidat tambahan tidak relevan.",
            "",
            "## Ranking dan validitas eksekusi",
            "",
            "| Condition | First-hit median | First-hit P90 | MRR | No-hit @10 | No-hit @60 | Median latency | P90 latency |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in diagnostics:
        lines.append(
            f"| {row['condition_label']} | {row['first_hit_rank_median']:.1f} | {row['first_hit_rank_p90']:.1f} | {row['first_hit_reciprocal_rank']:.3f} | {row['no_hit_rate_at_10']:.3f} | {row['no_hit_rate_at_60']:.3f} | {row['median_latency_ms'] / 1000:.1f}s | {row['p90_latency_ms'] / 1000:.1f}s |"
        )
    lines.extend(
        [
            "",
            "## Konsistensi English–Indonesian",
            "",
            "Delta dihitung berpasangan untuk `question_pair_id`: Indonesia dikurangi English. Nilai positif berarti Indonesia lebih baik pada metrik tersebut.",
            "",
            "| Condition | Recall EN @10 | Recall ID @10 | Δ @10 | Both @10 | Recall EN @60 | Recall ID @60 | Δ @60 | Both @60 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for condition in CONDITIONS:
        group = [row for row in pair_rows if row["condition_id"] == condition]
        en10 = fmean(float(row["en_gold_block_recall@10"]) for row in group)
        id10 = fmean(float(row["id_gold_block_recall@10"]) for row in group)
        en60 = fmean(float(row["en_gold_block_recall@60"]) for row in group)
        id60 = fmean(float(row["id_gold_block_recall@60"]) for row in group)
        both10 = fmean(float(row["both_language_success@10"]) for row in group)
        both60 = fmean(float(row["both_language_success@60"]) for row in group)
        lines.append(f"| {LABELS[condition]} | {en10:.3f} | {id10:.3f} | {id10 - en10:+.3f} | {both10:.3f} | {en60:.3f} | {id60:.3f} | {id60 - en60:+.3f} | {both60:.3f} |")
    lines.extend(
        [
            "",
            "## Variasi antarproduk",
            "",
            "`product-by-cutoff.csv` menyimpan semua product × condition × cutoff. Tabel berikut menunjukkan rentang product pada K=60 agar rata-rata keseluruhan tidak menyembunyikan model yang sulit.",
            "",
            "| Condition | Terendah | Tertinggi |",
            "|---|---|---|",
        ]
    )
    product_scopes = sorted({row["analysis_scope"] for row in aggregates if row["analysis_scope"].startswith("product:")})
    for condition in CONDITIONS:
        product_values = []
        for scope in product_scopes:
            matches = [row for row in aggregates if row["condition_id"] == condition and row["analysis_scope"] == scope and int(row["cutoff_k"]) == 60]
            if matches:
                product_values.append((scope.partition(":")[2], float(matches[0]["gold_block_recall"])))
        lowest = min(product_values, key=lambda item: item[1])
        highest = max(product_values, key=lambda item: item[1])
        lines.append(f"| {LABELS[condition]} | {lowest[0]} ({lowest[1]:.3f}) | {highest[0]} ({highest[1]:.3f}) |")
    lines.extend(
        [
            "",
            "## Variasi question family",
            "",
            "`family-by-cutoff.csv` menyimpan empat family pertanyaan secara terpisah. Ringkasan ini memperlihatkan family terlemah dan terkuat pada K=10 agar keputusan tidak hanya mengikuti komposisi agregat.",
            "",
            "| Condition | Terendah @10 | Tertinggi @10 | Terendah @60 | Tertinggi @60 |",
            "|---|---|---|---|---|",
        ]
    )
    family_scopes = sorted({row["analysis_scope"] for row in aggregates if row["analysis_scope"].startswith("family:")})
    for condition in CONDITIONS:
        family_values: dict[int, list[tuple[str, float]]] = {10: [], 60: []}
        for cutoff in (10, 60):
            for scope in family_scopes:
                matches = [row for row in aggregates if row["condition_id"] == condition and row["analysis_scope"] == scope and int(row["cutoff_k"]) == cutoff]
                if matches:
                    family_values[cutoff].append((scope.partition(":")[2], float(matches[0]["gold_block_recall"])))
        low10, high10 = min(family_values[10], key=lambda item: item[1]), max(family_values[10], key=lambda item: item[1])
        low60, high60 = min(family_values[60], key=lambda item: item[1]), max(family_values[60], key=lambda item: item[1])
        lines.append(f"| {LABELS[condition]} | {low10[0]} ({low10[1]:.3f}) | {high10[0]} ({high10[1]:.3f}) | {low60[0]} ({low60[1]:.3f}) | {high60[0]} ({high60[1]:.3f}) |")
    lines.extend(
        [
            "",
            "## Keputusan sementara",
            "",
            "Dense indexer menjadi kondisi terbaik pada K=10 dan K=60 untuk keempat metrik agregat. Gunakan K=10 jika prioritasnya menjaga daftar hasil tetap pendek; gunakan K=40–60 jika prioritasnya coverage, sambil menerima precision yang lebih rendah. Pemilihan K final tetap harus mempertimbangkan biaya context downstream.",
        ]
    )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- `overall-by-cutoff.csv`: combined metrics for every condition and K.",
            "- `language-by-cutoff.csv` and `family-by-cutoff.csv`: subgroup metrics.",
            "- `product-by-cutoff.csv`: product × condition × cutoff.",
            "- `pair-metrics.csv`: paired English–Indonesian metrics for every question pair and cutoff.",
            "- `condition-diagnostics.csv`: first-hit rank, MRR, candidate pool, latency, and no-hit rate.",
            "- `question-metrics.csv`: one row per condition × question with all four metrics at every K.",
            "- `retrieval-quality-by-cutoff.png`: four metric curves across K.",
            "- `language-quality-by-cutoff.png`: English and Indonesian curves.",
            "- `condition-quality-at-k10-k60.png`: compact decision comparison.",
            "- `execution-latency.png`: latency view; empty rate is in CSV and report.",
            "- `product-recall-at-k10-k60.png`: recall heatmap per product.",
            "- `first-hit-rank-cdf.png`: distribution of the first hit rank.",
            "- `language-paired-delta-at-k10-k60.png`: paired ID−EN deltas.",
            "- `precision-recall-tradeoff.png`: precision versus coverage across K.",
        ]
    )
    (output_dir / "analysis-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    rows = load_trace_rows(args.run_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    aggregates = build_aggregates(rows)
    overall = [row for row in aggregates if row["analysis_scope"] == "combined"]
    language = [row for row in aggregates if row["analysis_scope"] in {"en", "id"}]
    family = [row for row in aggregates if row["analysis_scope"].startswith("family:")]
    product = [row for row in aggregates if row["analysis_scope"].startswith("product:")]
    pair_rows = build_pair_rows(rows)
    diagnostics = build_condition_diagnostics(rows)
    write_csv(args.output_dir / "overall-by-cutoff.csv", overall)
    write_csv(args.output_dir / "language-by-cutoff.csv", language)
    write_csv(args.output_dir / "family-by-cutoff.csv", family)
    write_csv(args.output_dir / "product-by-cutoff.csv", product)
    write_csv(args.output_dir / "pair-metrics.csv", pair_rows)
    write_csv(args.output_dir / "condition-diagnostics.csv", diagnostics)
    question_rows: list[dict[str, Any]] = []
    for row in rows:
        output = {key: value for key, value in row.items() if key not in {"retrieval_candidates"}}
        question_rows.append(output)
    write_csv(args.output_dir / "question-metrics.csv", question_rows)
    plot_quality(args.output_dir, aggregates)
    plot_language(args.output_dir, aggregates)
    plot_cutoff_bars(args.output_dir, aggregates)
    plot_execution(args.output_dir, aggregates)
    plot_product_recall(args.output_dir, aggregates)
    plot_first_hit_rank(args.output_dir, rows)
    plot_language_delta(args.output_dir, pair_rows)
    plot_precision_recall_tradeoff(args.output_dir, aggregates)
    manifest = {
        "analysis": "customer-service-single-block-retrieval",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "run_dir": str(args.run_dir),
        "condition_ids": list(CONDITIONS),
        "question_count_per_condition": 200,
        "cutoffs": list(CUTOFFS),
        "metrics": {
            "chunk_precision": "hit chunks divided by K",
            "chunk_success": "1 if any hit chunk exists in top K, otherwise 0",
            "gold_block_recall": "unique gold blocks found through source_block_ids divided by all gold blocks",
            "chunk_ndcg": "binary hit-chunk NDCG in returned ranking",
        },
        "outputs": [
            "overall-by-cutoff.csv",
            "language-by-cutoff.csv",
            "family-by-cutoff.csv",
            "product-by-cutoff.csv",
            "pair-metrics.csv",
            "condition-diagnostics.csv",
            "question-metrics.csv",
            "retrieval-quality-by-cutoff.png",
            "language-quality-by-cutoff.png",
            "condition-quality-at-k10-k60.png",
            "execution-latency.png",
            "product-recall-at-k10-k60.png",
            "first-hit-rank-cdf.png",
            "language-paired-delta-at-k10-k60.png",
            "precision-recall-tradeoff.png",
        ],
    }
    (args.output_dir / "analysis-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(args.output_dir, rows, aggregates, pair_rows, diagnostics)
    print(json.dumps({"run_dir": str(args.run_dir), "output_dir": str(args.output_dir), "rows": len(rows), "conditions": len(CONDITIONS)}))


if __name__ == "__main__":
    main()
