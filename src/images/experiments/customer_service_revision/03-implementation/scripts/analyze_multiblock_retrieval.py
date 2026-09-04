#!/usr/bin/env python3
"""Analyze bilingual multi-block retrieval runs and write compact PNG reports."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


K_VALUES = tuple(range(5, 61, 5))
EXPECTED_LANGUAGE_COUNTS = {"en": 100, "id": 100}
CONDITION_ORDER = (
    "oat-qwen3",
    "oat-bge-m3",
    "oat-jina-v5-small-retrieval",
    "baseline-generic-hybrid",
    "chunker-generic-recursive",
    "chunker-generic-sliding-window",
    "indexer-generic-sparse",
    "indexer-generic-dense",
)
# Decision diagrams show only the retained matched OFAT lanes.
DIAGRAM_CONDITION_ORDER = (
    "baseline-generic-hybrid",
    "chunker-generic-recursive",
    "chunker-generic-sliding-window",
    "indexer-generic-sparse",
    "indexer-generic-dense",
)
CONDITION_LABELS = {
    "oat-qwen3": "OAT Qwen3",
    "oat-bge-m3": "OAT bge-m3",
    "oat-jina-v5-small-retrieval": "OAT Jina v5",
    "baseline-generic-hybrid": "Hybrid baseline",
    "chunker-generic-recursive": "Recursive chunker",
    "chunker-generic-sliding-window": "Sliding chunker",
    "indexer-generic-sparse": "Sparse indexer",
    "indexer-generic-dense": "Dense indexer",
}
COMPONENTS = {
    "oat-qwen3": "OAT model control",
    "oat-bge-m3": "OAT model control",
    "oat-jina-v5-small-retrieval": "OAT research model",
    "baseline-generic-hybrid": "OFAT baseline",
    "chunker-generic-recursive": "OFAT chunker",
    "chunker-generic-sliding-window": "OFAT chunker",
    "indexer-generic-sparse": "OFAT indexer",
    "indexer-generic-dense": "OFAT indexer",
}
COLORS = ((34, 90, 160), (220, 110, 45), (50, 145, 85), (160, 75, 150), (205, 165, 35), (70, 150, 170))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = font(30, True)
FONT_SUBTITLE = font(20)
FONT_AXIS = font(17)
FONT_SMALL = font(14)
FONT_TINY = font(12)


def json_value(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return default


def candidate_ids(candidate: dict[str, Any]) -> list[str]:
    raw = candidate.get("source_block_ids", [])
    if isinstance(raw, str):
        raw = [raw]
    return [str(value) for value in raw] if isinstance(raw, list) else []


def chunk_is_hit(candidate: dict[str, Any], gold: set[str]) -> bool:
    """A chunk is relevant when any provenance ID overlaps the gold IDs."""
    return bool(set(candidate_ids(candidate)) & gold)


def dcg(gains: list[int]) -> float:
    return sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))


def chunk_ndcg(candidates: list[Any], gold: set[str], k: int) -> float:
    """Rank chunks directly; use the full returned pool as the ideal list."""
    pool_gains = [
        int(chunk_is_hit(candidate, gold))
        for candidate in candidates
        if isinstance(candidate, dict)
    ]
    actual = pool_gains[:k]
    ideal = sorted(pool_gains, reverse=True)[:k]
    ideal_dcg = dcg(ideal)
    return dcg(actual) / ideal_dcg if ideal_dcg else 0.0


def score(row: dict[str, Any], k: int) -> dict[str, Any]:
    candidates = row.get("retrieval_candidates")
    if not isinstance(candidates, list):
        candidates = []
    gold = {str(value) for value in json_value(row.get("gold_evidence_block_ids"), [])}
    prefix = [candidate for candidate in candidates[:k] if isinstance(candidate, dict)]
    hit_flags = [chunk_is_hit(candidate, gold) for candidate in prefix]
    hit_chunk_count = sum(hit_flags)
    retrieved_block_ids = set().union(*(set(candidate_ids(candidate)) for candidate in prefix))
    matched_gold_blocks = retrieved_block_ids & gold
    return {
        "question_id": row.get("question_id", ""),
        "question_pair_id": row.get("question_pair_id", ""),
        "language": row.get("language", ""),
        "question_family": row.get("question_family", ""),
        "product_model": row.get("product_model", ""),
        "k": k,
        "gold_block_count": len(gold),
        "gold_block_hits": len(matched_gold_blocks),
        "retrieved_chunk_count": len(prefix),
        "hit_chunk_count": hit_chunk_count,
        "retrieved_unique_source_block_count": len(retrieved_block_ids),
        "gold_block_recall": len(matched_gold_blocks) / len(gold) if gold else 0.0,
        "chunk_precision": hit_chunk_count / len(prefix) if prefix else 0.0,
        "chunk_ndcg": chunk_ndcg(candidates, gold, k),
        "exact_gold_block_hit": float(bool(gold) and matched_gold_blocks == gold),
        "retrieval_empty": int(not candidates),
        "elapsed_ms": float(row.get("elapsed_ms") or 0.0),
    }


def read_results(run_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_path = run_dir / "run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    rows: list[dict[str, Any]] = []
    for condition in CONDITION_ORDER:
        path = run_dir / condition / "per-question-results.jsonl"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    row["condition_id"] = condition
                    rows.append(row)
    return rows, manifest


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[tuple(row.get(key, "") for key in keys)].append(row)
    output: list[dict[str, Any]] = []
    metrics = ("gold_block_recall", "chunk_precision", "chunk_ndcg", "exact_gold_block_hit", "retrieval_empty", "elapsed_ms")
    for values, bucket in sorted(buckets.items(), key=lambda item: tuple(str(v) for v in item[0])):
        result = {key: value for key, value in zip(keys, values)}
        result["n"] = len(bucket)
        result["mean_returned_chunk_count"] = mean([float(row["retrieved_chunk_count"]) for row in bucket])
        result["mean_hit_chunk_count"] = mean([float(row["hit_chunk_count"]) for row in bucket])
        for metric in metrics:
            result[metric] = mean([float(row[metric]) for row in bucket])
        output.append(result)
    return output


def label(value: str, limit: int = 28) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def save_line_chart(rows: list[dict[str, Any]], metric: str, path: Path, title: str) -> None:
    conditions = [condition for condition in DIAGRAM_CONDITION_ORDER if any(row["condition_id"] == condition for row in rows)]
    width, height = 1500, 900
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = 115, 85, 1280, 760
    draw.text((left, 25), title, fill=(20, 20, 20), font=FONT_TITLE)
    draw.text((left, 58), "Each point is the mean over 200 bilingual questions; K is the candidate cutoff.", fill=(80, 80, 80), font=FONT_SUBTITLE)
    metric_values = [float(row[metric]) for row in rows]
    if metric == "chunk_precision":
        observed_max = max(metric_values, default=0.0)
        upper = max(0.10, math.ceil(observed_max * 1.25 * 100) / 100)
        ticks = tuple(round(upper * index / 4, 4) for index in range(5))
    else:
        upper = 1.0
        ticks = (0.0, 0.25, 0.5, 0.75, 1.0)
    for tick in ticks:
        y = bottom - int((tick / upper) * (bottom - top))
        draw.line((left, y, right, y), fill=(225, 225, 225), width=1)
        draw.text((45, y - 9), f"{tick:.2f}", fill=(70, 70, 70), font=FONT_AXIS)
    for index, k in enumerate(K_VALUES):
        x = left + int(index * (right - left) / (len(K_VALUES) - 1))
        draw.line((x, bottom, x, bottom + 6), fill=(80, 80, 80), width=1)
        draw.text((x - 10, bottom + 12), str(k), fill=(70, 70, 70), font=FONT_AXIS)
    draw.text((right - 22, bottom + 45), "K", fill=(50, 50, 50), font=FONT_AXIS)
    points_by_condition: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for row in rows:
        if row["k"] in K_VALUES:
            points_by_condition[row["condition_id"]].append((int(row["k"]), float(row[metric])))
    for index, condition in enumerate(conditions):
        color = COLORS[index % len(COLORS)]
        points = sorted(points_by_condition[condition])
        coords: list[tuple[int, int]] = []
        for k, value in points:
            x = left + int(K_VALUES.index(k) * (right - left) / (len(K_VALUES) - 1))
            y = bottom - int(max(0.0, min(upper, value)) / upper * (bottom - top))
            coords.append((x, y))
        if len(coords) > 1:
            draw.line(coords, fill=color, width=4)
        for x, y in coords:
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)
        legend_y = top + index * 37
        draw.line((1310, legend_y + 10, 1350, legend_y + 10), fill=color, width=4)
        draw.text((1360, legend_y), CONDITION_LABELS.get(condition, condition), fill=(40, 40, 40), font=FONT_AXIS)
    image.save(path)


def save_profile_language_cutoff_chart(
    scored: list[dict[str, Any]], condition: str, path: Path
) -> None:
    """Plot combined, English, and Indonesian curves for one profile."""
    width, height = 1900, 920
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((55, 22), f"{CONDITION_LABELS.get(condition, condition)} — cutoff sweep", fill=(20, 20, 20), font=FONT_TITLE)
    draw.text((55, 62), "K=5–60; recall is gold-block coverage, precision and NDCG are chunk-level.", fill=(80, 80, 80), font=FONT_SUBTITLE)
    panels = (("combined", "Combined (English + Indonesian)"), ("en", "English"), ("id", "Indonesian"))
    metrics = (("gold_block_recall", "Gold-block recall", (35, 105, 180)), ("chunk_precision", "Chunk precision", (215, 110, 35)), ("chunk_ndcg", "Chunk NDCG", (45, 145, 85)))
    panel_w, panel_h = 570, 700
    lefts = (55, 665, 1275)
    top, bottom = 145, 790
    for panel_index, (language, panel_title) in enumerate(panels):
        left = lefts[panel_index]
        right = left + panel_w
        draw.text((left, 105), panel_title, fill=(35, 35, 35), font=FONT_AXIS)
        for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = bottom - int(tick * (bottom - top))
            draw.line((left, y, right, y), fill=(225, 225, 225), width=1)
            draw.text((left - 45, y - 8), f"{tick:.2f}", fill=(75, 75, 75), font=FONT_TINY)
        for index, k in enumerate(K_VALUES):
            x = left + int(index * (right - left) / (len(K_VALUES) - 1))
            draw.line((x, bottom, x, bottom + 5), fill=(90, 90, 90), width=1)
            if index % 2 == 0 or k == 60:
                draw.text((x - 9, bottom + 12), str(k), fill=(75, 75, 75), font=FONT_TINY)
        for metric, metric_label, color in metrics:
            points: list[tuple[int, int]] = []
            for index, k in enumerate(K_VALUES):
                bucket = [
                    row for row in scored
                    if row["condition_id"] == condition and int(row["k"]) == k
                    and (language == "combined" or row.get("language") == language)
                ]
                value = mean([float(row[metric]) for row in bucket])
                x = left + int(index * (right - left) / (len(K_VALUES) - 1))
                y = bottom - int(max(0.0, min(1.0, value)) * (bottom - top))
                points.append((x, y))
            if len(points) > 1:
                draw.line(points, fill=color, width=4)
            for x, y in points:
                draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)
        legend_x = left + 18
        for index, (_, metric_label, color) in enumerate(metrics):
            x = legend_x + index * 165
            draw.line((x, top - 20, x + 24, top - 20), fill=color, width=4)
            draw.text((x + 32, top - 28), metric_label, fill=(55, 55, 55), font=FONT_SMALL)
        draw.text((right - 18, bottom + 38), "K", fill=(55, 55, 55), font=FONT_SMALL)
    image.save(path)


def save_bar_chart(rows: list[dict[str, Any]], path: Path, title: str, metrics: tuple[str, ...]) -> None:
    conditions = [condition for condition in DIAGRAM_CONDITION_ORDER if any(row["condition_id"] == condition for row in rows)]
    width, height = 1600, 900
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = 120, 100, 1480, 735
    draw.text((left, 25), title, fill=(20, 20, 20), font=FONT_TITLE)
    draw.text((left, 62), "Mean values at K=20; higher is better for recall, precision, and NDCG.", fill=(80, 80, 80), font=FONT_SUBTITLE)
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = bottom - int(tick * (bottom - top))
        draw.line((left, y, right, y), fill=(225, 225, 225), width=1)
        draw.text((55, y - 9), f"{tick:.2f}", fill=(70, 70, 70), font=FONT_AXIS)
    values = {(row["condition_id"], row["metric"]): float(row["value"]) for row in rows}
    group_width = (right - left) / max(len(conditions), 1)
    bar_width = min(34, group_width / (len(metrics) + 1))
    for index, condition in enumerate(conditions):
        center = left + (index + 0.5) * group_width
        for metric_index, metric in enumerate(metrics):
            value = max(0.0, min(1.0, values.get((condition, metric), 0.0)))
            x0 = int(center + (metric_index - (len(metrics) - 1) / 2) * bar_width - bar_width * 0.42)
            x1 = int(x0 + bar_width * 0.84)
            y = bottom - int(value * (bottom - top))
            color = COLORS[metric_index % len(COLORS)]
            draw.rectangle((x0, y, x1, bottom), fill=color)
            if value > 0.07:
                draw.text((x0, y - 20), f"{value:.2f}", fill=(45, 45, 45), font=FONT_TINY)
        draw.text((int(center - 65), bottom + 14), label(CONDITION_LABELS.get(condition, condition), 18), fill=(45, 45, 45), font=FONT_SMALL)
    metric_labels = {
        "gold_block_recall": "Gold-block recall",
        "chunk_precision": "Chunk precision",
        "chunk_ndcg": "Chunk NDCG",
    }
    for metric_index, metric in enumerate(metrics):
        x = right - 470 + metric_index * 155
        draw.rectangle((x, 55, x + 14, 69), fill=COLORS[metric_index % len(COLORS)])
        draw.text((x + 20, 51), metric_labels.get(metric, metric), fill=(55, 55, 55), font=FONT_SMALL)
    image.save(path)


def save_heatmap(matrix: dict[tuple[str, str], float], row_labels: list[str], col_labels: list[str], path: Path, title: str, cell_format: str = ".2f") -> None:
    width = max(1200, 340 + 150 * len(col_labels))
    height = max(420, 150 + 34 * len(row_labels))
    left, top = 300, 110
    cell_w, cell_h = max(100, (width - left - 40) // max(len(col_labels), 1)), 29
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 25), title, fill=(20, 20, 20), font=FONT_TITLE)
    draw.text((40, 63), "Cells are mean values; darker blue means better retrieval quality.", fill=(80, 80, 80), font=FONT_SUBTITLE)
    for col_index, col in enumerate(col_labels):
        x = left + col_index * cell_w
        draw.text((x + 4, top - 32), label(col, 16), fill=(45, 45, 45), font=FONT_SMALL)
    for row_index, row in enumerate(row_labels):
        y = top + row_index * cell_h
        draw.text((40, y + 7), label(row, 30), fill=(45, 45, 45), font=FONT_SMALL)
        for col_index, col in enumerate(col_labels):
            value = max(0.0, min(1.0, float(matrix.get((row, col), 0.0))))
            shade = int(245 - 185 * value)
            color = (shade, min(230, shade + 12), 255)
            x = left + col_index * cell_w
            draw.rectangle((x, y, x + cell_w - 2, y + cell_h - 2), fill=color, outline=(215, 215, 215))
            text = format(value, cell_format)
            tw = draw.textbbox((0, 0), text, font=FONT_TINY)[2]
            draw.text((x + (cell_w - tw) // 2, y + 7), text, fill=(20, 35, 60), font=FONT_TINY)
    image = image.crop((0, 0, width, min(height, top + len(row_labels) * cell_h + 35)))
    image.save(path)


def save_latency_chart(summary: list[dict[str, Any]], path: Path) -> None:
    conditions = [condition for condition in DIAGRAM_CONDITION_ORDER if any(row["condition_id"] == condition for row in summary)]
    width, height = 1500, 800
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = 120, 100, 1400, 670
    draw.text((left, 25), "Execution validity and latency", fill=(20, 20, 20), font=FONT_TITLE)
    draw.text((left, 62), "Median latency is shown in seconds; empty-rate is the red marker on the right axis.", fill=(80, 80, 80), font=FONT_SUBTITLE)
    max_latency = max((float(row.get("median_latency_ms", 0.0)) for row in summary if row.get("condition_id") in conditions), default=1.0) / 1000
    group_width = (right - left) / max(len(conditions), 1)
    for tick in range(0, 6):
        y = bottom - int(tick / 5 * (bottom - top))
        draw.line((left, y, right, y), fill=(230, 230, 230), width=1)
        draw.text((55, y - 9), f"{max_latency * tick / 5:.1f}", fill=(70, 70, 70), font=FONT_AXIS)
    for index, condition in enumerate(conditions):
        row = next(item for item in summary if item["condition_id"] == condition)
        latency = float(row.get("median_latency_ms", 0.0)) / 1000
        empty = float(row.get("empty_rate", 0.0))
        center = left + (index + 0.5) * group_width
        y = bottom - int((latency / max_latency if max_latency else 0.0) * (bottom - top))
        draw.rectangle((int(center - 30), y, int(center + 30), bottom), fill=COLORS[index % len(COLORS)])
        draw.text((int(center - 28), y - 22), f"{latency:.1f}s", fill=(45, 45, 45), font=FONT_TINY)
        draw.ellipse((int(center - 7), bottom - int(empty * (bottom - top)) - 7, int(center + 7), bottom - int(empty * (bottom - top)) + 7), fill=(190, 45, 45))
        draw.text((int(center - 65), bottom + 14), label(CONDITION_LABELS.get(condition, condition), 18), fill=(45, 45, 45), font=FONT_SMALL)
    image.save(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", action="append", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for run_dir in args.run_dir:
        rows, manifest = read_results(run_dir)
        raw_rows.extend(rows)
        manifests.append({
            "run_dir": str(run_dir),
            "run_id": manifest.get("run_id", run_dir.name),
            "datasource_id": manifest.get("datasource_id", ""),
            "question_count": manifest.get("question_count", 0),
            "condition_count": manifest.get("condition_count", 0),
            "question_sha256": manifest.get("question_sha256", ""),
            "gold_sha256": manifest.get("gold_sha256", ""),
        })
    if not raw_rows:
        raise SystemExit("No per-question-results.jsonl files found")
    condition_languages: dict[str, dict[str, int]] = defaultdict(dict)
    condition_counts: defaultdict[str, int] = defaultdict(int)
    for row in raw_rows:
        condition = str(row.get("condition_id", ""))
        language = str(row.get("language", ""))
        condition_counts[condition] += 1
        condition_languages[condition][language] = condition_languages[condition].get(language, 0) + 1
    for condition, count in condition_counts.items():
        observed = condition_languages[condition]
        if count != sum(EXPECTED_LANGUAGE_COUNTS.values()) or observed != EXPECTED_LANGUAGE_COUNTS:
            raise ValueError(
                f"{condition} has {count} rows with language counts {observed}; "
                f"expected 200 rows with {EXPECTED_LANGUAGE_COUNTS}"
            )
    scored = [score(row, k) | {"condition_id": row["condition_id"]} for row in raw_rows for k in K_VALUES]
    write_csv(args.output_dir / "metrics-long.csv", scored)
    overall = aggregate(scored, ("condition_id", "k"))
    write_csv(args.output_dir / "overall-by-cutoff.csv", overall)
    at20 = [row for row in scored if row["k"] == 20]
    language_by_cutoff = aggregate(scored, ("condition_id", "language", "k"))
    by_language = aggregate(at20, ("condition_id", "language"))
    by_family = aggregate(at20, ("condition_id", "question_family"))
    by_product = aggregate(at20, ("condition_id", "product_model"))
    by_question = aggregate(at20, ("condition_id", "question_id", "question_pair_id", "language"))
    write_csv(args.output_dir / "language-by-cutoff.csv", language_by_cutoff)
    write_csv(args.output_dir / "by-language-at-k20.csv", by_language)
    write_csv(args.output_dir / "by-family-at-k20.csv", by_family)
    write_csv(args.output_dir / "by-product-at-k20.csv", by_product)
    write_csv(args.output_dir / "by-question-at-k20.csv", by_question)

    pair_buckets: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in scored:
        pair_buckets[(row["condition_id"], row["question_pair_id"], int(row["k"]))][row["language"]] = row
    paired: list[dict[str, Any]] = []
    for (condition, pair_id, cutoff), languages in sorted(pair_buckets.items()):
        if "en" not in languages or "id" not in languages:
            continue
        en, ind = languages["en"], languages["id"]
        paired.append({
            "condition_id": condition,
            "question_pair_id": pair_id,
            "k": cutoff,
            "en_gold_block_recall": en["gold_block_recall"],
            "id_gold_block_recall": ind["gold_block_recall"],
            "id_minus_en_gold_block_recall": ind["gold_block_recall"] - en["gold_block_recall"],
            "en_chunk_precision": en["chunk_precision"],
            "id_chunk_precision": ind["chunk_precision"],
            "id_minus_en_chunk_precision": ind["chunk_precision"] - en["chunk_precision"],
            "en_chunk_ndcg": en["chunk_ndcg"],
            "id_chunk_ndcg": ind["chunk_ndcg"],
            "id_minus_en_chunk_ndcg": ind["chunk_ndcg"] - en["chunk_ndcg"],
        })
    write_csv(args.output_dir / "paired-en-id-by-cutoff.csv", paired)
    write_csv(args.output_dir / "paired-en-id-at-k20.csv", [row for row in paired if int(row["k"]) == 20])

    condition_summary: list[dict[str, Any]] = []
    for condition in CONDITION_ORDER:
        rows = [row for row in at20 if row["condition_id"] == condition]
        if not rows:
            continue
        condition_summary.append({"condition_id": condition, "component": COMPONENTS.get(condition, ""), "n": len(rows), "mean_returned_chunk_count": mean([row["retrieved_chunk_count"] for row in rows]), "mean_hit_chunk_count": mean([row["hit_chunk_count"] for row in rows]), "gold_block_recall": mean([row["gold_block_recall"] for row in rows]), "chunk_precision": mean([row["chunk_precision"] for row in rows]), "chunk_ndcg": mean([row["chunk_ndcg"] for row in rows]), "exact_gold_block_hit": mean([row["exact_gold_block_hit"] for row in rows]), "empty_rate": mean([row["retrieval_empty"] for row in rows]), "median_latency_ms": statistics.median([row["elapsed_ms"] for row in rows])})
    write_csv(args.output_dir / "condition-summary-at-k20.csv", condition_summary)

    charts = args.output_dir / "diagrams"
    charts.mkdir(exist_ok=True)
    save_line_chart(overall, "gold_block_recall", charts / "recall-by-cutoff.png", "Gold-block recall by cutoff")
    save_line_chart(overall, "chunk_precision", charts / "precision-by-cutoff.png", "Chunk precision by cutoff")
    save_line_chart(overall, "chunk_ndcg", charts / "ndcg-by-cutoff.png", "Chunk NDCG by cutoff")
    bar_rows = [{"condition_id": row["condition_id"], "metric": metric, "value": row[metric]} for row in condition_summary for metric in ("gold_block_recall", "chunk_precision", "chunk_ndcg")]
    save_bar_chart(bar_rows, charts / "condition-quality-at-k20.png", "Condition quality at K=20", ("gold_block_recall", "chunk_precision", "chunk_ndcg"))
    language_matrix = {(CONDITION_LABELS.get(row["condition_id"], row["condition_id"]), row["language"]): row["gold_block_recall"] for row in by_language}
    save_heatmap(language_matrix, [CONDITION_LABELS.get(c, c) for c in DIAGRAM_CONDITION_ORDER if any(r["condition_id"] == c for r in by_language)], ["en", "id"], charts / "language-recall-at-k20.png", "Recall by language at K=20")
    family_names = sorted({row["question_family"] for row in by_family})
    family_matrix = {(CONDITION_LABELS.get(row["condition_id"], row["condition_id"]), row["question_family"]): row["gold_block_recall"] for row in by_family}
    family_conditions = [CONDITION_LABELS.get(c, c) for c in DIAGRAM_CONDITION_ORDER if any(r["condition_id"] == c for r in by_family)]
    save_heatmap(family_matrix, family_conditions, family_names, charts / "family-recall-at-k20.png", "Recall by question family at K=20")
    products = sorted({row["product_model"] for row in by_product})
    product_matrix = {(CONDITION_LABELS.get(row["condition_id"], row["condition_id"]), row["product_model"]): row["gold_block_recall"] for row in by_product}
    product_conditions = [CONDITION_LABELS.get(c, c) for c in DIAGRAM_CONDITION_ORDER if any(r["condition_id"] == c for r in by_product)]
    save_heatmap(product_matrix, product_conditions, products, charts / "product-recall-at-k20.png", "Recall by product model at K=20")
    pair_ids = sorted({row["question_pair_id"] for row in at20}, key=lambda value: int(str(value).split("-")[-1]) if str(value).split("-")[-1].isdigit() else 0)
    question_matrix = {(pair, CONDITION_LABELS.get(condition, condition)): next((row["gold_block_recall"] for row in at20 if row["question_pair_id"] == pair and row["condition_id"] == condition), 0.0) for pair in pair_ids for condition in DIAGRAM_CONDITION_ORDER}
    question_conditions = [CONDITION_LABELS.get(c, c) for c in DIAGRAM_CONDITION_ORDER if any(r["condition_id"] == c for r in at20)]
    save_heatmap(question_matrix, pair_ids, question_conditions, charts / "question-pair-recall-at-k20.png", "Per-question-pair multi-block recall at K=20")
    save_latency_chart(condition_summary, charts / "latency-and-empty-rate.png")
    profile_charts = charts / "profile-cutoff-sweeps"
    profile_charts.mkdir(exist_ok=True)
    for stale in profile_charts.glob("oat-*-cutoff-sweep.png"):
        stale.unlink()
    available_conditions = [condition for condition in DIAGRAM_CONDITION_ORDER if any(row["condition_id"] == condition for row in scored)]
    for condition in available_conditions:
        save_profile_language_cutoff_chart(scored, condition, profile_charts / f"{condition}-cutoff-sweep.png")

    report_lines = [
        "# Customer Service multi-block retrieval analysis",
        "",
        f"- Input rows: {len(raw_rows)} retrieval traces ({len({row['condition_id'] for row in raw_rows})} conditions).",
        f"- Scored rows: {len(scored)} across cutoffs K={','.join(map(str, K_VALUES))}.",
        "- Gold definition: variable-size audited block IDs per bilingual question; recall is complete gold-block coverage.",
        "- Precision counts relevant chunks divided by returned chunks at K.",
        "- NDCG ranks chunks directly with binary relevance (any source ID overlaps gold); its ideal list is formed from the returned candidate pool.",
        "- Empty retrieval is retained as a valid zero score and separately reported; it is not silently dropped.",
        "",
        "## Condition summary at K=20",
        "",
        "| Condition | Component | Mean chunks | Mean hit chunks | Gold-block recall | Chunk precision | Chunk NDCG | Complete gold hit | Median latency | Empty rate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in condition_summary:
        report_lines.append(f"| {CONDITION_LABELS.get(row['condition_id'], row['condition_id'])} | {row['component']} | {row['mean_returned_chunk_count']:.1f} | {row['mean_hit_chunk_count']:.2f} | {row['gold_block_recall']:.3f} | {row['chunk_precision']:.3f} | {row['chunk_ndcg']:.3f} | {row['exact_gold_block_hit']:.3f} | {row['median_latency_ms'] / 1000:.1f}s | {row['empty_rate']:.3f} |")
    report_lines.extend([
        "",
        "## English dan Indonesian (terpisah)",
        "",
        "Setiap kondisi divalidasi memiliki 100 pertanyaan English dan 100 Indonesian. CSV `language-by-cutoff.csv` menyimpan semua cutoff; tabel ringkas berikut menampilkan K=20 dan K=60.",
        "",
        "| Condition | Language | K | Gold-block recall | Chunk precision | Chunk NDCG |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for cutoff in (20, 60):
        for row in language_by_cutoff:
            if int(row["k"]) != cutoff:
                continue
            report_lines.append(
                f"| {CONDITION_LABELS.get(row['condition_id'], row['condition_id'])} | {str(row['language']).upper()} | {cutoff} | {float(row['gold_block_recall']):.3f} | {float(row['chunk_precision']):.3f} | {float(row['chunk_ndcg']):.3f} |"
            )
    def best_at(k: int, metric: str) -> dict[str, Any]:
        return max(
            (row for row in overall if int(row["k"]) == k),
            key=lambda row: float(row[metric]),
        )
    recall20 = best_at(20, "gold_block_recall")
    precision20 = best_at(20, "chunk_precision")
    ndcg20 = best_at(20, "chunk_ndcg")
    recall60 = best_at(60, "gold_block_recall")
    report_lines.extend([
        "",
        "## Interpretation",
        "",
        f"- At K=20, {CONDITION_LABELS.get(recall20['condition_id'], recall20['condition_id'])} has the highest gold-block recall ({float(recall20['gold_block_recall']):.3f}); {CONDITION_LABELS.get(precision20['condition_id'], precision20['condition_id'])} has the highest chunk precision ({float(precision20['chunk_precision']):.3f}); and {CONDITION_LABELS.get(ndcg20['condition_id'], ndcg20['condition_id'])} has the highest chunk NDCG ({float(ndcg20['chunk_ndcg']):.3f}).",
        f"- At K=60, {CONDITION_LABELS.get(recall60['condition_id'], recall60['condition_id'])} has the highest gold-block recall ({float(recall60['gold_block_recall']):.3f}).",
        "- Precision uses the number of chunks actually returned in the first K positions; the mean returned-chunk and hit-chunk counts are shown so short result lists remain visible.",
        "- Recall and precision answer different questions: recall measures how much gold evidence is covered, while precision measures how many returned chunks support at least one gold block.",
    ])
    report_lines.extend([
        "",
        "## Outputs",
        "",
        "- `metrics-long.csv`: one row per trace and cutoff.",
        "- `overall-by-cutoff.csv`: condition-level cutoff curve.",
        "- `language-by-cutoff.csv`: English/Indonesian metrics for every condition and K.",
        "- `by-language-at-k20.csv`, `by-family-at-k20.csv`, `by-product-at-k20.csv`: subgroup analyses at K=20.",
        "- `by-question-at-k20.csv`, `paired-en-id-by-cutoff.csv`, and `paired-en-id-at-k20.csv`: question-level and bilingual-pair checks.",
        "- `diagrams/profile-cutoff-sweeps/`: one diagram per retained OFAT profile with Combined, English, and Indonesian panels across K=5,10,...,60.",
        "- `diagrams/`: recall/precision/NDCG curves, condition comparison, language/family/product heatmaps, per-pair heatmap, and latency/empty-rate chart.",
    ])
    (args.output_dir / "analysis-report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    (args.output_dir / "analysis-manifest.json").write_text(json.dumps({"run_inputs": manifests, "raw_trace_count": len(raw_rows), "language_counts_per_condition": EXPECTED_LANGUAGE_COUNTS, "cutoffs": K_VALUES, "gold_blocks_per_question": "variable (1–5)", "diagram_condition_ids": DIAGRAM_CONDITION_ORDER, "scoring": {"gold_block_recall": "unique gold source_block_ids found across first K chunks / gold source_block_ids", "chunk_precision": "hit chunks / returned chunks in first K", "chunk_ndcg": "binary chunk relevance ranked directly; ideal uses full returned candidate pool"}, "outputs": ["analysis-report.md", "metrics-long.csv", "overall-by-cutoff.csv", "language-by-cutoff.csv", "by-language-at-k20.csv", "by-family-at-k20.csv", "by-product-at-k20.csv", "by-question-at-k20.csv", "paired-en-id-by-cutoff.csv", "paired-en-id-at-k20.csv", "condition-summary-at-k20.csv", "diagrams/recall-by-cutoff.png", "diagrams/precision-by-cutoff.png", "diagrams/ndcg-by-cutoff.png", "diagrams/profile-cutoff-sweeps/*.png"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir), "raw_trace_count": len(raw_rows), "condition_count": len({row['condition_id'] for row in raw_rows}), "cutoffs": K_VALUES}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
