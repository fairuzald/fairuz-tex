#!/usr/bin/env python3
"""Analyze frozen Customer Service OFAT results with stage-scoped figures."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_CHUNKER_DIR = ROOT / (
    "experiments/offline-rag-experiments/customer_service_revision/"
    "03-implementation/runs/multiblock/analysis/secondary/cutoff-chunker"
)
DEFAULT_INDEXER_DIR = ROOT / (
    "experiments/offline-rag-experiments/customer_service_revision/"
    "03-implementation/runs/multiblock/analysis/secondary/cutoff-indexer"
)
DEFAULT_QUESTIONS = ROOT / (
    "experiments/offline-rag-experiments/customer_service_revision/"
    "02-question-budget-and-gold/03-question-generation-and-gold/runs/selection-v2-multiblock/"
    "03-frozen/question-set.csv"
)
CUTOFFS = (5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60)
FOCUS_CUTOFFS = (10, 60)
DASHBOARD_CUTOFFS = (5, 10, 60)

LEGACY_FIGURES = (
    "retrieval-quality-by-cutoff.png",
    "retrieval-quality-at-k60.png",
    "component-absolute-means.png",
    "component-paired-distributions.png",
    "component-rank-deltas.png",
    "question-winner-counts.png",
    "question-zero-hit-heatmap.png",
    "execution-latency.png",
    "execution-edge-cases.png",
)

CONDITION_META: dict[str, dict[str, str]] = {
    "baseline-generic-hybrid": {
        "component_group": "baseline",
        "variant": "hybrid",
        "parser": "generic-outline",
        "chunker": "generic-structure-aware",
        "indexer": "hybrid-semantic-keyword",
        "orchestrator": "hybrid-semantic-keyword-orchestrator",
        "label": "Baseline hybrid",
    },
    "chunker-generic-recursive": {
        "component_group": "chunker",
        "variant": "generic-recursive",
        "parser": "generic-outline",
        "chunker": "generic-recursive",
        "indexer": "hybrid-semantic-keyword",
        "orchestrator": "hybrid-semantic-keyword-orchestrator",
        "label": "Chunker: recursive",
    },
    "chunker-generic-sliding-window": {
        "component_group": "chunker",
        "variant": "generic-sliding-window",
        "parser": "generic-outline",
        "chunker": "generic-sliding-window",
        "indexer": "hybrid-semantic-keyword",
        "orchestrator": "hybrid-semantic-keyword-orchestrator",
        "label": "Chunker: sliding-window",
    },
    "indexer-generic-sparse": {
        "component_group": "indexer",
        "variant": "sparse-keyword",
        "parser": "generic-outline",
        "chunker": "generic-structure-aware",
        "indexer": "sparse-keyword",
        "orchestrator": "sparse-keyword-orchestrator",
        "label": "Indexer: sparse",
    },
    "indexer-generic-dense": {
        "component_group": "indexer",
        "variant": "dense-semantic (BAAI/bge-m3)",
        "parser": "generic-outline",
        "chunker": "generic-structure-aware",
        "indexer": "dense-semantic",
        "orchestrator": "dense-semantic-orchestrator",
        "label": "Indexer: dense",
    },
}

# Component views use matched baselines; overall uses the latest indexer baseline.
SCOPE_CONDITIONS = {
    "chunker": (
        "baseline-generic-hybrid",
        "chunker-generic-recursive",
        "chunker-generic-sliding-window",
    ),
    "indexer": ("baseline-generic-hybrid", "indexer-generic-sparse", "indexer-generic-dense"),
    "overall": (
        "baseline-generic-hybrid",
        "chunker-generic-recursive",
        "chunker-generic-sliding-window",
        "indexer-generic-sparse",
        "indexer-generic-dense",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_questions(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 200:
        raise ValueError(f"Expected 200 frozen questions, found {len(rows)}")
    required = {"question_id", "question_pair_id", "language", "question_family"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Question set is missing columns: {sorted(missing)}")
    result = {row["question_id"]: row for row in rows}
    if len(result) != 200:
        raise ValueError("question_id values are not unique")
    languages = Counter(row["language"] for row in rows)
    if languages != Counter({"en": 100, "id": 100}):
        raise ValueError(f"Expected 100 en and 100 id questions, found {languages}")
    return result


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_cutoff_rows(directory: Path, source_name: str) -> list[dict[str, Any]]:
    path = directory / "per-question-cutoff-results.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            raw = json.loads(line)
            condition = str(raw.get("condition_id", ""))
            if condition not in CONDITION_META:
                raise ValueError(f"Unknown condition {condition!r} at {path}:{line_number}")
            row = dict(raw)
            row["source_run"] = source_name
            row["condition_key"] = f"{condition}__{source_name}"
            row.update(CONDITION_META[condition])
            row["retrieved_count"] = int(_number(row.get("retrieved_count")))
            row["retrieval_empty"] = bool(row.get("retrieval_empty", False))
            row["elapsed_ms"] = _number(row.get("elapsed_ms"))
            for cutoff in CUTOFFS:
                for metric in ("evidence_recall", "evidence_precision", "ndcg"):
                    key = f"{metric}@{cutoff}"
                    if key not in row:
                        raise ValueError(f"Missing {key} at {path}:{line_number}")
                    row[key] = _number(row[key])
            rows.append(row)
    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_condition[row["condition_id"]].append(row)
    for condition, condition_rows in by_condition.items():
        if len(condition_rows) != 200:
            raise ValueError(
                f"{source_name}/{condition} has {len(condition_rows)} rows; expected 200"
            )
        identities = {(r.get("question_id"), r.get("language")) for r in condition_rows}
        if len(identities) != 200:
            raise ValueError(f"Duplicate question rows in {source_name}/{condition}")
        language_counts = Counter(str(r.get("language", "")) for r in condition_rows)
        if language_counts != Counter({"en": 100, "id": 100}):
            raise ValueError(
                f"{source_name}/{condition} has language counts {language_counts}; "
                "expected 100 en and 100 id"
            )
    return rows


def add_question_metadata(
    rows: Iterable[dict[str, Any]], questions: dict[str, dict[str, str]]
) -> None:
    for row in rows:
        question = questions.get(str(row.get("question_id")))
        if question is None:
            raise ValueError(f"Result references unknown question {row.get('question_id')}")
        for field in ("question_pair_id", "language", "question_family"):
            if str(row.get(field)) != str(question[field]):
                raise ValueError(
                    f"Question metadata mismatch for {row['question_id']} field {field}"
                )


def aggregate(rows: list[dict[str, Any]], group_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(field, "") for field in group_fields)].append(row)
    result: list[dict[str, Any]] = []

    def sort_key(item: tuple[tuple[Any, ...], list[dict[str, Any]]]) -> tuple[tuple[int, Any], ...]:
        return tuple(
            (0, value) if isinstance(value, int | float) else (1, str(value)) for value in item[0]
        )

    for key, group in sorted(groups.items(), key=sort_key):
        record = {field: value for field, value in zip(group_fields, key, strict=True)}
        languages = Counter(str(row.get("language", "")) for row in group)
        record.update(
            {
                "question_count": len(group),
                "english_count": languages.get("en", 0),
                "indonesian_count": languages.get("id", 0),
                "empty_retrieval_count": sum(bool(row.get("retrieval_empty")) for row in group),
                "mean_retrieved_count": round(fmean(row["retrieved_count"] for row in group), 6),
                "median_latency_ms": round(median(row["elapsed_ms"] for row in group), 6),
            }
        )
        cutoff = int(record["cutoff_k"])
        for metric in ("evidence_recall", "evidence_precision", "ndcg"):
            value_key = f"{metric}@{cutoff}" if f"{metric}@{cutoff}" in group[0] else metric
            record[metric] = round(fmean(row[value_key] for row in group), 12)
        result.append(record)
    return result


def expand_cutoffs(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert wide per-question cutoff columns into one row per cutoff."""
    expanded: list[dict[str, Any]] = []
    for row in rows:
        for cutoff in CUTOFFS:
            item = dict(row)
            item["cutoff_k"] = cutoff
            for metric in ("evidence_recall", "evidence_precision", "ndcg"):
                item[metric] = float(row[f"{metric}@{cutoff}"])
            expanded.append(item)
    return expanded


def enrich_aggregate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for record in records:
        condition = str(record.get("condition_id", ""))
        meta = CONDITION_META.get(condition, {})
        item = dict(record)
        for field in (
            "condition_key",
            "component_group",
            "variant",
            "parser",
            "chunker",
            "indexer",
            "orchestrator",
            "label",
        ):
            if field not in item:
                item[field] = meta.get(field, "")
        enriched.append(item)
    return enriched


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    if fields is None:
        fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def metric_fields() -> list[str]:
    return [
        f"{metric}@{cutoff}"
        for cutoff in CUTOFFS
        for metric in ("evidence_recall", "evidence_precision", "ndcg")
    ]


def make_question_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "analysis_scope",
        "source_run",
        "condition_id",
        "condition_key",
        "profile_id",
        "component_group",
        "variant",
        "question_id",
        "question_pair_id",
        "language",
        "question_family",
        "retrieved_count",
        "retrieval_empty",
        "elapsed_ms",
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        item = {field: row.get(field, "") for field in fields}
        item.update({field: row.get(field, 0.0) for field in metric_fields()})
        result.append(item)
    return sorted(result, key=lambda row: (row["question_id"], row["condition_id"]))


def make_language_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        pairs[(str(row["condition_id"]), str(row["question_pair_id"]))][str(row["language"])] = row
    result: list[dict[str, Any]] = []
    for (condition, pair_id), languages in sorted(pairs.items()):
        if "en" not in languages or "id" not in languages:
            continue
        en, ind = languages["en"], languages["id"]
        meta = CONDITION_META[condition]
        for cutoff in FOCUS_CUTOFFS:
            item: dict[str, Any] = {
                "condition_id": condition,
                "condition_key": en["condition_key"],
                "component_group": meta["component_group"],
                "variant": meta["variant"],
                "question_pair_id": pair_id,
                "question_id_en": en["question_id"],
                "question_id_id": ind["question_id"],
                "cutoff_k": cutoff,
            }
            for metric in ("evidence_recall", "evidence_precision", "ndcg"):
                en_value = float(en[f"{metric}@{cutoff}"])
                id_value = float(ind[f"{metric}@{cutoff}"])
                item[f"en_{metric}"] = en_value
                item[f"id_{metric}"] = id_value
                item[f"id_minus_en_{metric}"] = round(id_value - en_value, 12)
            item["en_latency_ms"] = en["elapsed_ms"]
            item["id_latency_ms"] = ind["elapsed_ms"]
            item["id_minus_en_latency_ms"] = round(ind["elapsed_ms"] - en["elapsed_ms"], 6)
            result.append(item)
    return result


def make_winners(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for cutoff in FOCUS_CUTOFFS:
            groups[(str(row["question_id"]), str(row["language"]), cutoff)].append(row)
    result: list[dict[str, Any]] = []
    for (question_id, language, cutoff), group in sorted(groups.items()):
        ranked = sorted(
            group,
            key=lambda row: (
                -float(row[f"evidence_recall@{cutoff}"]),
                -float(row[f"ndcg@{cutoff}"]),
                -float(row[f"evidence_precision@{cutoff}"]),
                str(row["condition_id"]),
            ),
        )
        best = ranked[0]
        best_tuple = (
            float(best[f"evidence_recall@{cutoff}"]),
            float(best[f"ndcg@{cutoff}"]),
            float(best[f"evidence_precision@{cutoff}"]),
        )
        ties = [
            row["condition_id"]
            for row in ranked
            if (
                float(row[f"evidence_recall@{cutoff}"]),
                float(row[f"ndcg@{cutoff}"]),
                float(row[f"evidence_precision@{cutoff}"]),
            )
            == best_tuple
        ]
        result.append(
            {
                "question_id": question_id,
                "language": language,
                "cutoff_k": cutoff,
                "winner_condition_id": best["condition_id"],
                "winner_label": CONDITION_META[best["condition_id"]]["label"],
                "best_recall": best_tuple[0],
                "best_ndcg": best_tuple[1],
                "best_precision": best_tuple[2],
                "tied_condition_ids": ";".join(ties),
            }
        )
    return result


def _condition_labels() -> dict[str, str]:
    return {
        condition: CONDITION_META[condition]["label"] for condition in SCOPE_CONDITIONS["overall"]
    }


def _condition_colors() -> dict[str, str]:
    return {
        "baseline-generic-hybrid": "#1f4e79",
        "chunker-generic-recursive": "#c55a11",
        "chunker-generic-sliding-window": "#2f7d32",
        "indexer-generic-sparse": "#7f3c8d",
        "indexer-generic-dense": "#117a8b",
    }


def _metric_labels() -> tuple[tuple[str, str], ...]:
    return (
        ("evidence_recall", "Gold-block recall"),
        ("evidence_precision", "Chunk precision"),
        ("ndcg", "Chunk NDCG"),
    )


def _short_condition_label(label: str) -> str:
    return label.split(": ", 1)[1] if ": " in label else label


def _annotate_bars(axis: Any, bars: Any, *, decimals: int = 2) -> None:
    for bar in bars:
        value = float(bar.get_height())
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            min(value + 0.018, 1.02),
            f"{value:.{decimals}f}",
            ha="center",
            va="bottom",
            fontsize=7,
        )


def _cleanup_legacy_figures(output_dir: Path) -> None:
    """Remove only old figures generated by this analyzer."""
    for filename in LEGACY_FIGURES:
        path = output_dir / filename
        if path.exists():
            path.unlink()


def _component_deltas(component_rows: list[dict[str, Any]], cutoff: int) -> list[dict[str, Any]]:
    metric_names = tuple(metric for metric, _ in _metric_labels())
    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in component_rows:
        grouped[(str(row["analysis_scope"]), str(row["condition_id"]))][str(row["question_id"])] = (
            row
        )
    effects: list[dict[str, Any]] = []
    for scope in ("chunker", "indexer"):
        reference = grouped[(scope, "baseline-generic-hybrid")]
        targets = [
            condition
            for condition in SCOPE_CONDITIONS[scope]
            if condition != "baseline-generic-hybrid"
        ]
        for target in targets:
            target_rows = grouped[(scope, target)]
            for metric in metric_names:
                key = f"{metric}@{cutoff}"
                deltas = [
                    float(target_rows[question_id][key]) - float(reference[question_id][key])
                    for question_id in sorted(reference.keys() & target_rows.keys())
                ]
                effects.append(
                    {
                        "component": scope,
                        "target_condition": target,
                        "metric": metric,
                        "deltas": deltas,
                        "mean_delta": fmean(deltas) if deltas else 0.0,
                        "median_delta": median(deltas) if deltas else 0.0,
                        "win_rate": sum(value > 0 for value in deltas) / len(deltas)
                        if deltas
                        else 0.0,
                    }
                )
    return effects


def _plot_scope_cutoff_dashboard(
    output_dir: Path,
    component: list[dict[str, Any]],
    scope: str,
    labels: dict[str, str],
    colors: dict[str, str],
    plt: Any,
) -> None:
    """Render all retrieval metrics at K=5, 10, and 60 for one OFAT scope."""
    conditions = list(SCOPE_CONDITIONS[scope])
    metrics = _metric_labels()
    figure, axes = plt.subplots(
        len(metrics), len(DASHBOARD_CUTOFFS),
        figsize=(max(13, len(conditions) * 3.6), 10.5),
        sharey="row",
    )
    x = list(range(len(conditions)))
    for row_index, (metric, title) in enumerate(metrics):
        for column_index, cutoff in enumerate(DASHBOARD_CUTOFFS):
            axis = axes[row_index][column_index]
            rows = {
                row["condition_id"]: row
                for row in component
                if row.get("analysis_scope") == scope and int(row["cutoff_k"]) == cutoff
            }
            values = [float(rows[condition][metric]) for condition in conditions]
            bars = axis.bar(x, values, color=[colors[condition] for condition in conditions], width=0.72)
            _annotate_bars(axis, bars)
            axis.set_title(f"K={cutoff}")
            axis.set_xticks(x, [labels[condition] for condition in conditions], rotation=28, ha="right")
            axis.grid(axis="y", alpha=0.25)
            upper = 1.0 if metric != "evidence_precision" else max(0.08, max(values) * 1.6)
            axis.set_ylim(0, upper)
            if column_index == 0:
                axis.set_ylabel(title)
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=colors[condition])
        for condition in conditions
    ]
    figure.legend(handles, [labels[condition] for condition in conditions], loc="upper center", ncol=len(conditions), frameon=False, bbox_to_anchor=(0.5, 1.01))
    figure.suptitle(f"Customer Service {scope.title()} OFAT — all retrieval metrics", y=1.05, fontsize=15)
    figure.tight_layout()
    figure.savefig(output_dir / f"{scope}-cutoff-dashboard.png", dpi=200, bbox_inches="tight")
    plt.close(figure)


def _plot_language_scoped(
    output_dir: Path,
    component_language: list[dict[str, Any]],
    labels: dict[str, str],
    colors: dict[str, str],
    plt: Any,
) -> None:
    """Compare English and Indonesian within each matched OFAT scope."""
    metrics = _metric_labels()
    scopes = ("chunker", "indexer")
    figure, axes = plt.subplots(2, len(metrics), figsize=(18, 9), sharex=True, sharey=False)
    for row_index, scope in enumerate(scopes):
        conditions = list(SCOPE_CONDITIONS[scope])
        for column_index, (metric, title) in enumerate(metrics):
            axis = axes[row_index][column_index]
            for condition in conditions:
                for language_code, linestyle in (("en", "-"), ("id", "--")):
                    series = sorted(
                        (
                            row
                            for row in component_language
                            if row.get("analysis_scope") == scope
                            and row["condition_id"] == condition
                            and row.get("language") == language_code
                        ),
                        key=lambda row: int(row["cutoff_k"]),
                    )
                    axis.plot(
                        [int(row["cutoff_k"]) for row in series],
                        [float(row[metric]) for row in series],
                        color=colors[condition],
                        linestyle=linestyle,
                        linewidth=1.7,
                    )
            axis.set_title(f"{scope.title()} — {title}")
            axis.set_xticks(list(CUTOFFS))
            axis.grid(axis="y", alpha=0.25)
            if metric == "evidence_precision":
                values = [
                    float(row[metric])
                    for row in component_language
                    if row.get("analysis_scope") == scope
                ]
                axis.set_ylim(0, max(0.05, max(values) * 1.3) if values else 0.05)
            else:
                axis.set_ylim(0, 1)
            if row_index == 1:
                axis.set_xlabel("Candidate cutoff K")
            if column_index == 0:
                axis.set_ylabel("Mean score")
    for row_index, scope in enumerate(scopes):
        condition_handles = [
            plt.Line2D([0], [0], color=colors[condition], linewidth=3, label=labels[condition])
            for condition in SCOPE_CONDITIONS[scope]
        ]
        axes[row_index][0].legend(
            handles=condition_handles,
            loc="upper left",
            bbox_to_anchor=(0, 1.24),
            ncol=len(condition_handles),
            frameon=False,
            fontsize=8,
        )
    language_handles = [
        plt.Line2D([0], [0], color="#4b5563", linestyle=style, linewidth=2, label=language)
        for language, style in (("English", "-"), ("Indonesian", "--"))
    ]
    figure.legend(
        language_handles,
        [handle.get_label() for handle in language_handles],
        loc="upper right",
        frameon=False,
        bbox_to_anchor=(0.99, 1.01),
        fontsize=8,
    )
    figure.suptitle("Customer Service — language quality within matched OFAT scopes", y=1.08)
    figure.tight_layout(rect=(0, 0, 1, 0.94))
    figure.savefig(output_dir / "language-quality-by-cutoff.png", dpi=200, bbox_inches="tight")
    plt.close(figure)


def _plot_component_deltas(
    output_dir: Path, effects: list[dict[str, Any]], labels: dict[str, str], plt: Any
) -> None:
    import numpy as np

    metric_names = [metric for metric, _ in _metric_labels()]
    metric_titles = [title for _, title in _metric_labels()]
    row_specs = [
        (effect["component"], effect["target_condition"])
        for effect in effects
        if effect["metric"] == metric_names[0]
    ]
    matrix = []
    row_labels = []
    for scope, target in row_specs:
        row_labels.append(f"{scope.title()}: {_short_condition_label(labels[target])}")
        matrix.append(
            [
                next(
                    effect["mean_delta"]
                    for effect in effects
                    if effect["component"] == scope
                    and effect["target_condition"] == target
                    and effect["metric"] == metric
                )
                for metric in metric_names
            ]
        )
    values = np.asarray(matrix, dtype=float)
    limit = max(float(abs(values).max()) if values.size else 0.01, 0.01)
    figure, axis = plt.subplots(figsize=(12.5, max(4.4, len(row_labels) * 0.75)))
    image = axis.imshow(values, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    axis.set_xticks(range(len(metric_names)), metric_titles, rotation=20, ha="right")
    axis.set_yticks(range(len(row_labels)), row_labels)
    for row_index in range(values.shape[0]):
        for column_index in range(values.shape[1]):
            axis.text(
                column_index,
                row_index,
                f"{values[row_index, column_index]:+.3f}",
                ha="center",
                va="center",
                fontsize=8,
            )
    axis.set_title("Paired change at K=60 (variant − matched baseline)")
    figure.colorbar(image, ax=axis, label="Mean paired delta")
    figure.tight_layout()
    figure.savefig(output_dir / "component-delta-heatmap.png", dpi=200, bbox_inches="tight")
    plt.close(figure)


FAMILY_LABELS = {
    "facts_specifications": "Facts & specifications",
    "features_security_maintenance_limitations": "Features, security & maintenance",
    "setup_configuration": "Setup & configuration",
    "troubleshooting_diagnostics": "Troubleshooting & diagnostics",
}


def _plot_family_coverage_scoped(
    output_dir: Path,
    component_rows: list[dict[str, Any]],
    labels: dict[str, str],
    plt: Any,
) -> None:
    """Show family coverage separately for the chunker and indexer OFAT scopes."""
    import numpy as np

    families = list(FAMILY_LABELS)
    scopes = ("chunker", "indexer")
    figure, axes = plt.subplots(2, 3, figsize=(18, 9), sharey=True, constrained_layout=True)
    last_image = None
    for row_index, scope in enumerate(scopes):
        conditions = list(SCOPE_CONDITIONS[scope])
        for column_index, language_code in enumerate(("all", "en", "id")):
            axis = axes[row_index][column_index]
            matrix = []
            counts = []
            for family in families:
                row_values = []
                row_counts = []
                for condition in conditions:
                    rows = [
                        row
                        for row in component_rows
                        if row.get("analysis_scope") == scope
                        and row["condition_id"] == condition
                        and row["question_family"] == family
                        and (language_code == "all" or row["language"] == language_code)
                    ]
                    row_values.append(
                        fmean(float(row["evidence_recall@60"]) for row in rows)
                        if rows
                        else float("nan")
                    )
                    row_counts.append(len(rows))
                matrix.append(row_values)
                counts.append(row_counts)
            values = np.asarray(matrix, dtype=float)
            last_image = axis.imshow(values, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
            axis.set_title(f"{scope.title()} — {language_code.upper()}")
            axis.set_xticks(
                range(len(conditions)),
                [labels[condition] for condition in conditions],
                rotation=28,
                ha="right",
            )
            axis.set_yticks(range(len(families)), [FAMILY_LABELS[family] for family in families])
            for family_index in range(values.shape[0]):
                for condition_index in range(values.shape[1]):
                    if not np.isnan(values[family_index, condition_index]):
                        axis.text(
                            condition_index,
                            family_index,
                            f"{values[family_index, condition_index]:.2f}\n(n={counts[family_index][condition_index]})",
                            ha="center",
                            va="center",
                            fontsize=7,
                        )
    axes[0][0].set_ylabel("Question family")
    axes[1][0].set_ylabel("Question family")
    figure.colorbar(last_image, ax=axes.ravel().tolist(), label="Gold-block recall @ K=60")
    figure.suptitle("Customer Service — family coverage within matched OFAT scopes")
    figure.savefig(output_dir / "question-family-coverage-heatmap.png", dpi=200, bbox_inches="tight")
    plt.close(figure)


def _profile_scope_rows(component_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build one logical profile row per condition and deduplicate the baseline ID."""
    physical: dict[str, set[str]] = defaultdict(set)
    for row in component_rows:
        physical[str(row["condition_id"])].add(str(row.get("profile_id", "")))
    rows = []
    for condition, meta in CONDITION_META.items():
        if condition == "baseline-generic-hybrid":
            used_in = "Chunker OFAT + Indexer OFAT"
            scope = "G1 shared baseline"
        elif condition.startswith("chunker-"):
            used_in = "Chunker OFAT"
            scope = "single-stage variant"
        else:
            used_in = "Indexer OFAT"
            scope = "single-stage variant"
        rows.append(
            {
                "condition_id": condition,
                "condition": meta["label"],
                "profile_ids": ";".join(sorted(profile for profile in physical[condition] if profile)),
                "profile_scope": scope,
                "used_in": used_in,
                "parser": meta["parser"],
                "chunker": meta["chunker"],
                "indexer": meta["indexer"],
                "orchestrator": meta["orchestrator"],
            }
        )
    return rows


def _plot_profile_scope(
    output_dir: Path,
    component_rows: list[dict[str, Any]],
    plt: Any,
) -> dict[str, Any]:
    """Write the logical profile scope table and a compact visual audit."""
    rows = _profile_scope_rows(component_rows)
    fields = ["condition_id", "condition", "profile_ids", "profile_scope", "used_in", "parser", "chunker", "indexer", "orchestrator"]
    with (output_dir / "profile-scope.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    def short(value: str) -> str:
        replacements = {
            "Baseline hybrid": "baseline hybrid",
            "Chunker: recursive": "recursive",
            "Chunker: sliding-window": "sliding",
            "Indexer: sparse": "sparse",
            "Indexer: dense": "dense",
            "generic-structure-aware": "structure-aware",
            "generic-outline": "outline",
            "hybrid-semantic-keyword": "hybrid",
            "sparse-keyword": "sparse",
            "dense-semantic": "dense",
            "hybrid-semantic-keyword-orchestrator": "hybrid-orch",
            "sparse-keyword-orchestrator": "sparse-orch",
            "dense-semantic-orchestrator": "dense-orch",
            "Chunker OFAT + Indexer OFAT": "chunker + indexer",
            "G1 shared baseline": "G1 (shared)",
            "single-stage variant": "variant",
            "generic-sliding-window": "sliding-window",
        }
        value = replacements.get(value, value or "—")
        return value if len(value) <= 18 else value[:15] + "…"

    display_fields = ["condition", "profile_scope", "used_in", "parser", "chunker", "indexer", "orchestrator"]
    headers = ["Condition", "Profile scope", "Used in", "Parser", "Chunker", "Indexer", "Retriever"]
    cells = [[short(row[field]) for field in display_fields] for row in rows]
    figure, axis = plt.subplots(figsize=(17, max(4.8, len(rows) * 0.7)))
    axis.axis("off")
    table = axis.table(
        cellText=cells,
        colLabels=headers,
        cellLoc="center",
        loc="center",
        colWidths=[0.15, 0.13, 0.15, 0.10, 0.14, 0.10, 0.15],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.65)
    for (row_index, column_index), cell in table.get_celld().items():
        cell.set_edgecolor("#d1d5db")
        if row_index == 0:
            cell.set_facecolor("#1e3a8a")
            cell.set_text_props(color="white", weight="bold")
        elif row_index % 2 == 0:
            cell.set_facecolor("#f8fafc")
        if row_index == 1:
            cell.set_facecolor("#dbeafe")
            if column_index == 1:
                cell.set_text_props(color="#1e40af", weight="bold")
    axis.set_title(
        "Customer Service profile scope — one shared baseline, four stage variants",
        pad=18,
        fontsize=13,
    )
    figure.tight_layout()
    figure.savefig(output_dir / "profile-scope.png", dpi=200, bbox_inches="tight")
    plt.close(figure)
    return {"logical_profiles": rows, "physical_profile_count": len({profile for row in rows for profile in row["profile_ids"].split(";") if profile})}


def _execution_audits(overall_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    audits = []
    for condition in SCOPE_CONDITIONS["overall"]:
        rows = [row for row in overall_rows if row["condition_id"] == condition]
        latencies = [float(row["elapsed_ms"]) for row in rows]
        audits.append(
            {
                "condition_id": condition,
                "trace_count": len(rows),
                "empty_count": sum(bool(row["retrieval_empty"]) for row in rows),
                "latency_ms": latencies,
                "median_ms": median(latencies) if latencies else 0.0,
                "p95_ms": sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)]
                if latencies
                else 0.0,
            }
        )
    return audits


def _plot_execution_validity(
    output_dir: Path, audits: list[dict[str, Any]], labels: dict[str, str], plt: Any
) -> None:
    figure, axis = plt.subplots(figsize=(13, 5.2))
    x = list(range(len(audits)))
    complete = [audit["trace_count"] - audit["empty_count"] for audit in audits]
    empty = [audit["empty_count"] for audit in audits]
    bars = axis.bar(x, complete, color="#2f855a", label="non-empty retrieval traces")
    axis.bar(x, empty, bottom=complete, color="#dd6b20", label="empty retrieval traces")
    axis.axhline(200, color="#1d4ed8", linestyle="--", linewidth=1, label="required traces = 200")
    for bar, value in zip(bars, complete, strict=True):
        axis.text(bar.get_x() + bar.get_width() / 2, value + 1, str(value), ha="center", fontsize=8)
    axis.set_ylim(0, 210)
    axis.set_ylabel("Question traces")
    axis.set_title("Execution validity and retrieval availability")
    axis.set_xticks(x, [labels[audit["condition_id"]] for audit in audits], rotation=28, ha="right")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    figure.savefig(output_dir / "execution-validity.png", dpi=200, bbox_inches="tight")
    plt.close(figure)


def plot_outputs(
    output_dir: Path,
    overall_raw: list[dict[str, Any]],
    component_language: list[dict[str, Any]],
    component: list[dict[str, Any]],
    component_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = _condition_labels()
    colors = _condition_colors()
    effects = _component_deltas(component_rows, 60)
    audits = _execution_audits(overall_raw)
    _cleanup_legacy_figures(output_dir)
    _plot_scope_cutoff_dashboard(output_dir, component, "chunker", labels, colors, plt)
    _plot_scope_cutoff_dashboard(output_dir, component, "indexer", labels, colors, plt)
    _plot_language_scoped(output_dir, component_language, labels, colors, plt)
    _plot_component_deltas(output_dir, effects, labels, plt)
    _plot_family_coverage_scoped(output_dir, component_rows, labels, plt)
    _plot_execution_validity(output_dir, audits, labels, plt)
    return _plot_profile_scope(output_dir, component_rows, plt)


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def report_table(records: list[dict[str, Any]], cutoff: int, language: str | None = None) -> str:
    rows = [r for r in records if int(r["cutoff_k"]) == cutoff]
    if language is not None:
        rows = [r for r in rows if r.get("language") == language]
    rows.sort(key=lambda r: (str(r.get("component_group", "")), str(r.get("condition_id", ""))))
    lines = [
        "| Condition | N | Gold-block recall | Chunk precision | Chunk NDCG | Median latency |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('label', row.get('condition_id'))} | {row['question_count']} | "
            f"{fmt(float(row['evidence_recall']))} | {fmt(float(row['evidence_precision']))} | "
            f"{fmt(float(row['ndcg']))} | {fmt(float(row['median_latency_ms']))} ms |"
        )
    return "\n".join(lines)


def profile_scope_table(scope: dict[str, Any]) -> str:
    lines = [
        "| Condition | Profile scope | Used in | Parser | Chunker | Indexer | Retriever |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in scope["logical_profiles"]:
        lines.append(
            f"| {row['condition']} | {row['profile_scope']} | {row['used_in']} | {row['parser']} | "
            f"{row['chunker']} | {row['indexer']} | {row['orchestrator']} |"
        )
    return "\n".join(lines)


def write_report(
    path: Path,
    *,
    overall: list[dict[str, Any]],
    component: list[dict[str, Any]],
    component_language: list[dict[str, Any]],
    winners: list[dict[str, Any]],
    provenance: list[dict[str, Any]],
    inputs: dict[str, Any],
    profile_scope: dict[str, Any],
) -> None:
    def stage_winner(scope: str, cutoff: int) -> dict[str, Any]:
        candidates = [
            row
            for row in component
            if row.get("analysis_scope") == scope and int(row["cutoff_k"]) == cutoff
        ]
        return max(
            candidates,
            key=lambda row: (
                float(row["evidence_recall"]),
                float(row["ndcg"]),
                float(row["evidence_precision"]),
            ),
        )

    chunker_winner = stage_winner("chunker", 10)
    indexer_winner = stage_winner("indexer", 10)
    chunker_winner_60 = stage_winner("chunker", 60)
    indexer_winner_60 = stage_winner("indexer", 60)
    lines = [
        "# Customer Service OFAT — scoped analysis",
        "",
        "This report is generated from frozen cutoff results and does not call the API.",
        "",
        f"- Generated: `{datetime.now(UTC).isoformat()}`",
        f"- Frozen question count: `{inputs['question_count']}` (`{inputs['english_count']} en + {inputs['indonesian_count']} id`)",
        f"- Question-set SHA-256: `{inputs['question_sha256']}`",
        f"- Cutoffs: `{', '.join(str(k) for k in CUTOFFS)}`",
        "- Metrics: complete gold-block recall, chunk precision, and chunk NDCG.",
        "",
        "## Scope and profile reduction",
        "",
        "The previous pooled overall charts were removed because they mixed chunker and indexer factors. The valid comparison is matched OFAT: chunker variants share the hybrid indexer baseline, and indexer variants share the structure-aware chunker baseline.",
        "",
        f"There are `{profile_scope['physical_profile_count']}` physical profile IDs and `{len(profile_scope['logical_profiles'])}` logical conditions. The hybrid baseline is one shared profile used by both OFAT scopes, not two independent observations.",
        "",
        profile_scope_table(profile_scope),
        "",
        "[Detailed profile scope CSV](profile-scope.csv) and [profile scope diagram](profile-scope.png).",
        "",
        "## Decisions",
        "",
        f"- Chunker: select {CONDITION_META[chunker_winner['condition_id']]['label']} at K=10 ({float(chunker_winner['evidence_recall']):.3f}); at K=60 the winner is {CONDITION_META[chunker_winner_60['condition_id']]['label']} ({float(chunker_winner_60['evidence_recall']):.3f}).",
        f"- Indexer: select {CONDITION_META[indexer_winner['condition_id']]['label']} at K=10 ({float(indexer_winner['evidence_recall']):.3f}); at K=60 the winner is {CONDITION_META[indexer_winner_60['condition_id']]['label']} ({float(indexer_winner_60['evidence_recall']):.3f}).",
        "- Precision and NDCG remain diagnostics; they are not pooled with another OFAT scope.",
        "",
        "## Chunker OFAT",
        "",
        "Hybrid indexer is held fixed; only the chunker changes.",
        "",
        "### K=10",
        "",
        report_table([r for r in component if r.get("analysis_scope") == "chunker"], 10),
        "",
        "### K=60",
        "",
        report_table([r for r in component if r.get("analysis_scope") == "chunker"], 60),
        "",
        "![Chunker cutoff dashboard](chunker-cutoff-dashboard.png)",
        "",
        "## Indexer OFAT",
        "",
        "Structure-aware chunker is held fixed; only the indexer/retriever changes.",
        "",
        "### K=10",
        "",
        report_table([r for r in component if r.get("analysis_scope") == "indexer"], 10),
        "",
        "### K=60",
        "",
        report_table([r for r in component if r.get("analysis_scope") == "indexer"], 60),
        "",
        "![Indexer cutoff dashboard](indexer-cutoff-dashboard.png)",
        "",
        "![Matched component deltas](component-delta-heatmap.png)",
        "",
        "## English versus Indonesian",
        "",
        "Language metrics are computed from paired question IDs within each matched scope; no cross-stage aggregate is used.",
        "",
    ]
    for scope in ("chunker", "indexer"):
        lines.extend(
            [
                f"### {scope.title()} OFAT — English, K=60",
                "",
                report_table([r for r in component_language if r.get("analysis_scope") == scope], 60, "en"),
                "",
                f"### {scope.title()} OFAT — Indonesian, K=60",
                "",
                report_table([r for r in component_language if r.get("analysis_scope") == scope], 60, "id"),
                "",
            ]
        )
    lines.extend(
        [
            "![Scoped language quality](language-quality-by-cutoff.png)",
            "",
            "## Per-question and family diagnostics",
            "",
            f"`question-metrics.csv` contains `{inputs['overall_question_rows']}` overall condition × question rows with every cutoff metric.",
            f"`question-winners.csv` contains `{len(winners)}` rows for K=10 and K=60; it is retained as a diagnostic and is not used to pool stage decisions.",
            "",
            "![Scoped family coverage](question-family-coverage-heatmap.png)",
            "",
            "## Execution validity",
            "",
            "This is an operational check, not a retrieval-quality score.",
            "",
            "![Execution validity](execution-validity.png)",
            "",
            "## Provenance",
            "",
            "| Analysis scope | Condition | Source run | Selection |",
            "|---|---|---|---|",
        ]
    )
    for row in provenance:
        lines.append(f"| {row['analysis_scope']} | {row['condition_id']} | {row['source_run']} | {row['selection']} |")
    lines.extend(
        [
            "",
            "## Artefacts",
            "",
            "- `overall-metrics.csv`: retained five-condition aggregate for audit; not used for cross-stage ranking.",
            "- `component-metrics.csv`: matched chunker and indexer OFAT metrics.",
            "- `component-language-metrics.csv`: scoped English/Indonesian aggregate for every K.",
            "- `language-metrics.csv`: retained overall language aggregate for audit.",
            "- `family-metrics.csv`: question-family × language breakdown.",
            "- `question-metrics.csv`: per-question metrics for every K.",
            "- `paired-language-delta.csv`: paired Indonesian-minus-English comparison.",
            "- `question-winners.csv`: per-question diagnostic winners at K=10 and K=60.",
            "- `chunker-cutoff-dashboard.png`: all three metrics at K=5, 10, and 60 for chunker OFAT.",
            "- `indexer-cutoff-dashboard.png`: all three metrics at K=5, 10, and 60 for indexer OFAT.",
            "- `component-delta-heatmap.png`: matched variant-minus-baseline effects at K=60.",
            "- `language-quality-by-cutoff.png`: scoped English/Indonesian quality across K.",
            "- `question-family-coverage-heatmap.png`: family coverage within each OFAT scope.",
            "- `execution-validity.png`: trace completeness and empty-retrieval availability.",
            "- `profile-scope.png` and `profile-scope.csv`: logical profile reduction and physical IDs.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# Main populates this so report hard-case counts match the exported CSV.
overall_question_rows: list[dict[str, Any]] = []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunker-dir", type=Path, default=DEFAULT_CHUNKER_DIR)
    parser.add_argument("--indexer-dir", type=Path, default=DEFAULT_INDEXER_DIR)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    questions = read_questions(args.questions)
    chunker_rows = load_cutoff_rows(args.chunker_dir, "chunker-cutoff")
    indexer_rows = load_cutoff_rows(args.indexer_dir, "indexer-cutoff")
    add_question_metadata(chunker_rows + indexer_rows, questions)
    by_source = {"chunker": chunker_rows, "indexer": indexer_rows}

    def choose(scope: str) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        for condition in SCOPE_CONDITIONS[scope]:
            if scope == "chunker":
                source = "chunker"
            elif scope == "indexer":
                source = "indexer"
            else:
                # Overall uses the latest indexer baseline; variants use their component run.
                source = (
                    "indexer"
                    if condition == "baseline-generic-hybrid" or condition.startswith("indexer-")
                    else "chunker"
                )
            source_rows = [r for r in by_source[source] if r["condition_id"] == condition]
            for row in source_rows:
                item = dict(row)
                item["analysis_scope"] = scope
                item["condition_key"] = f"{condition}__{source}"
                selected.append(item)
        return selected

    overall_rows = choose("overall")
    chunker_scope_rows = choose("chunker")
    indexer_scope_rows = choose("indexer")
    component_rows = chunker_scope_rows + indexer_scope_rows
    global overall_question_rows
    overall_question_rows = make_question_rows(overall_rows)

    overall_long = expand_cutoffs(overall_rows)
    component_long = expand_cutoffs(component_rows)
    language_rows = [dict(row, analysis_scope="overall") for row in overall_long]
    overall_metrics = enrich_aggregate(
        aggregate(
            overall_long,
            ("analysis_scope", "condition_id", "condition_key", "profile_id", "cutoff_k"),
        )
    )
    component_metrics = enrich_aggregate(
        aggregate(
            component_long,
            ("analysis_scope", "condition_id", "condition_key", "profile_id", "cutoff_k"),
        )
    )
    component_language_metrics = enrich_aggregate(
        aggregate(
            component_long,
            (
                "analysis_scope",
                "condition_id",
                "condition_key",
                "profile_id",
                "language",
                "cutoff_k",
            ),
        )
    )
    language_metrics = enrich_aggregate(
        aggregate(
            language_rows,
            (
                "analysis_scope",
                "condition_id",
                "condition_key",
                "profile_id",
                "language",
                "cutoff_k",
            ),
        )
    )
    family_metrics = enrich_aggregate(
        aggregate(
            language_rows,
            (
                "analysis_scope",
                "condition_id",
                "condition_key",
                "profile_id",
                "language",
                "question_family",
                "cutoff_k",
            ),
        )
    )
    paired = make_language_pairs(overall_rows)
    winners = make_winners(overall_rows)

    provenance = [
        {
            "analysis_scope": "overall",
            "condition_id": condition,
            "source_run": (
                "indexer-cutoff"
                if condition == "baseline-generic-hybrid" or condition.startswith("indexer-")
                else "chunker-cutoff"
            ),
            "selection": "latest baseline for overall"
            if condition == "baseline-generic-hybrid"
            else "selected condition",
        }
        for condition in SCOPE_CONDITIONS["overall"]
    ]
    provenance += [
        {
            "analysis_scope": "chunker",
            "condition_id": condition,
            "source_run": "chunker-cutoff",
            "selection": "matched chunker comparison",
        }
        for condition in SCOPE_CONDITIONS["chunker"]
    ]
    provenance += [
        {
            "analysis_scope": "indexer",
            "condition_id": condition,
            "source_run": "indexer-cutoff",
            "selection": "matched indexer comparison",
        }
        for condition in SCOPE_CONDITIONS["indexer"]
    ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    common_fields = [
        "analysis_scope",
        "condition_id",
        "condition_key",
        "profile_id",
        "component_group",
        "variant",
        "parser",
        "chunker",
        "indexer",
        "orchestrator",
        "cutoff_k",
        "question_count",
        "english_count",
        "indonesian_count",
        "empty_retrieval_count",
        "mean_retrieved_count",
        "median_latency_ms",
        "evidence_recall",
        "evidence_precision",
        "ndcg",
        "label",
    ]
    write_csv(args.output_dir / "overall-metrics.csv", overall_metrics, common_fields)
    write_csv(args.output_dir / "component-metrics.csv", component_metrics, common_fields)
    write_csv(
        args.output_dir / "component-language-metrics.csv",
        component_language_metrics,
        common_fields + ["language"],
    )
    write_csv(
        args.output_dir / "language-metrics.csv", language_metrics, common_fields + ["language"]
    )
    write_csv(
        args.output_dir / "family-metrics.csv",
        family_metrics,
        common_fields + ["language", "question_family"],
    )
    question_fields = [
        "analysis_scope",
        "source_run",
        "condition_id",
        "condition_key",
        "profile_id",
        "component_group",
        "variant",
        "question_id",
        "question_pair_id",
        "language",
        "question_family",
        "retrieved_count",
        "retrieval_empty",
        "elapsed_ms",
        *metric_fields(),
    ]
    write_csv(args.output_dir / "question-metrics.csv", overall_question_rows, question_fields)
    if paired:
        write_csv(args.output_dir / "paired-language-delta.csv", paired)
    if winners:
        write_csv(args.output_dir / "question-winners.csv", winners)
    write_csv(args.output_dir / "provenance.csv", provenance)
    profile_scope = plot_outputs(
        args.output_dir,
        overall_rows,
        component_language_metrics,
        component_metrics,
        component_rows,
    )

    inputs = {
        "question_count": len(questions),
        "english_count": sum(row["language"] == "en" for row in questions.values()),
        "indonesian_count": sum(row["language"] == "id" for row in questions.values()),
        "question_sha256": sha256(args.questions),
        "overall_question_rows": len(overall_question_rows),
        "chunker_input": str(args.chunker_dir),
        "indexer_input": str(args.indexer_dir),
        "cutoffs": list(CUTOFFS),
        "focus_cutoffs": list(FOCUS_CUTOFFS),
        "physical_profile_count": profile_scope["physical_profile_count"],
        "logical_profile_count": len(profile_scope["logical_profiles"]),
    }
    (args.output_dir / "analysis-manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "analysis": "customer-service-ofat-scoped-component-question-language",
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "inputs": inputs,
                "conditions": CONDITION_META,
                "scopes": SCOPE_CONDITIONS,
                "profile_scope": profile_scope,
                "metrics": ["evidence_recall", "evidence_precision", "ndcg", "median_latency_ms"],
                "metric_definitions": {
                    "evidence_recall": "complete gold-block coverage",
                    "evidence_precision": "hit chunks divided by returned chunks",
                    "ndcg": "binary chunk relevance ranked directly",
                },
                "visualizations": sorted(path.name for path in args.output_dir.glob("*.png")),
                "no_llm_generation": True,
                "use_reranker": False,
                "intent_provider": "passthrough",
                "kg_mode": "none",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_report(
        args.output_dir / "analysis-report.md",
        overall=overall_metrics,
        component=component_metrics,
        component_language=component_language_metrics,
        winners=winners,
        provenance=provenance,
        inputs=inputs,
        profile_scope=profile_scope,
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "overall_rows": len(overall_question_rows),
                "paired_rows": len(paired),
            }
        )
    )


if __name__ == "__main__":
    main()
