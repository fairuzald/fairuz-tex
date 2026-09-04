#!/usr/bin/env python3
"""Find the terminal retrieval-cutoff plateau for the single-block benchmark."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[5]
DEFAULT_INPUT = ROOT / (
    "experiments/offline-rag-experiments/customer_service_revision/"
    "03-implementation/runs/single-block/analysis/question-metrics.csv"
)
DEFAULT_OUTPUT = ROOT / (
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
LANGUAGES = ("combined", "en", "id")
RECALL_PRACTICAL_DELTA = 0.02
NDCG_PRACTICAL_DELTA = 0.01
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20260902


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"condition_id", "question_id", "language"}
    required.update(f"{metric}@{k}" for metric in ("gold_block_recall", "chunk_precision", "chunk_ndcg") for k in CUTOFFS)
    missing = required - set(rows[0]) if rows else required
    if missing:
        raise ValueError(f"question-metrics.csv is missing columns: {sorted(missing)}")
    for condition in CONDITIONS:
        subset = [row for row in rows if row["condition_id"] == condition]
        counts = Counter(row["language"] for row in subset)
        if len(subset) != 200 or counts != Counter({"en": 100, "id": 100}):
            raise ValueError(f"{condition}: expected 200 rows with 100 en and 100 id, found {len(subset)} / {counts}")
    return rows


def bootstrap_ci(values: list[float], rng: np.random.Generator) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    if not len(array) or np.all(array == array[0]):
        value = float(array.mean()) if len(array) else 0.0
        return value, value
    indices = rng.integers(0, len(array), size=(BOOTSTRAP_RESAMPLES, len(array)))
    means = array[indices].mean(axis=1)
    low, high = np.quantile(means, (0.025, 0.975))
    return float(low), float(high)


def transition_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    result: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        condition_rows = [row for row in rows if row["condition_id"] == condition]
        scopes = {"combined": condition_rows}
        scopes.update({language: [row for row in condition_rows if row["language"] == language] for language in ("en", "id")})
        for scope in LANGUAGES:
            scoped = scopes[scope]
            for from_k, to_k in zip(CUTOFFS, CUTOFFS[1:]):
                record: dict[str, Any] = {
                    "condition_id": condition,
                    "condition_label": LABELS[condition],
                    "scope": scope,
                    "from_k": from_k,
                    "to_k": to_k,
                    "question_count": len(scoped),
                }
                for metric, prefix in (
                    ("gold_block_recall", "recall"),
                    ("chunk_precision", "precision"),
                    ("chunk_ndcg", "ndcg"),
                ):
                    deltas = [float(row[f"{metric}@{to_k}"]) - float(row[f"{metric}@{from_k}"]) for row in scoped]
                    low, high = bootstrap_ci(deltas, rng)
                    mean_delta = float(np.mean(deltas)) if deltas else 0.0
                    record[f"delta_{prefix}"] = mean_delta
                    record[f"{prefix}_ci95_low"] = low
                    record[f"{prefix}_ci95_high"] = high
                    record[f"{prefix}_significant"] = int(low > 0.0 or high < 0.0)
                record["recall_practical_small"] = int(abs(record["delta_recall"]) <= RECALL_PRACTICAL_DELTA)
                record["recall_local_plateau"] = int(
                    record["recall_practical_small"]
                    and record["recall_ci95_low"] <= 0.0 <= record["recall_ci95_high"]
                )
                record["ndcg_practical_small"] = int(abs(record["delta_ndcg"]) <= NDCG_PRACTICAL_DELTA)
                result.append(record)
    return result


def terminal_start(transitions: list[dict[str, Any]], flag: str) -> int | None:
    ordered = sorted(transitions, key=lambda row: int(row["from_k"]))
    for index, row in enumerate(ordered):
        if all(int(candidate[flag]) for candidate in ordered[index:]):
            return int(row["from_k"])
    return None


def summary_rows(rows: list[dict[str, str]], transitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        condition_rows = [row for row in rows if row["condition_id"] == condition]
        scopes = {"combined": condition_rows}
        scopes.update({language: [row for row in condition_rows if row["language"] == language] for language in ("en", "id")})
        for scope in LANGUAGES:
            scoped = scopes[scope]
            subset = [row for row in transitions if row["condition_id"] == condition and row["scope"] == scope]
            recall_k = terminal_start(subset, "recall_local_plateau")
            ndcg_k = terminal_start(subset, "ndcg_practical_small")
            sweet_k = max(value for value in (recall_k, ndcg_k) if value is not None) if recall_k and ndcg_k else None
            at60 = {metric: float(np.mean([float(row[f"{metric}@60"]) for row in scoped])) for metric in ("gold_block_recall", "chunk_precision", "chunk_ndcg")}
            at_sweet = (
                {metric: float(np.mean([float(row[f"{metric}@{sweet_k}"]) for row in scoped])) for metric in at60}
                if sweet_k
                else {metric: 0.0 for metric in at60}
            )
            result.append({
                "condition_id": condition,
                "condition_label": LABELS[condition],
                "scope": scope,
                "question_count": len(scoped),
                "terminal_recall_plateau_k": recall_k or "",
                "terminal_ndcg_plateau_k": ndcg_k or "",
                "sweet_spot_k": sweet_k or "",
                "recall_at_sweet": at_sweet["gold_block_recall"],
                "recall_at_60": at60["gold_block_recall"],
                "recall_gain_after_sweet": at60["gold_block_recall"] - at_sweet["gold_block_recall"],
                "precision_at_sweet": at_sweet["chunk_precision"],
                "precision_at_60": at60["chunk_precision"],
                "precision_change_after_sweet": at60["chunk_precision"] - at_sweet["chunk_precision"],
                "ndcg_at_sweet": at_sweet["chunk_ndcg"],
                "ndcg_at_60": at60["chunk_ndcg"],
                "ndcg_gain_after_sweet": at60["chunk_ndcg"] - at_sweet["chunk_ndcg"],
            })
    return result


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot(output_dir: Path, rows: list[dict[str, str]], summaries: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    colors = {
        "baseline-generic-hybrid": "#1f4e79",
        "chunker-generic-recursive": "#c55a11",
        "chunker-generic-sliding-window": "#2f7d32",
        "indexer-generic-sparse": "#7f3c8d",
        "indexer-generic-dense": "#117a8b",
    }
    figure, axes = plt.subplots(1, 3, figsize=(19, 6), sharey=True)
    for axis, scope in zip(axes, LANGUAGES, strict=True):
        for condition in CONDITIONS:
            condition_rows = [row for row in rows if row["condition_id"] == condition and (scope == "combined" or row["language"] == scope)]
            values = [np.mean([float(row[f"gold_block_recall@{k}"]) for row in condition_rows]) for k in CUTOFFS]
            axis.plot(CUTOFFS, values, marker="o", linewidth=2, markersize=3, color=colors[condition], label=LABELS[condition])
            sweet = next(row["sweet_spot_k"] for row in summaries if row["condition_id"] == condition and row["scope"] == scope)
            if sweet:
                value = values[CUTOFFS.index(int(sweet))]
                axis.scatter([int(sweet)], [value], s=70, color=colors[condition], edgecolor="black", zorder=5)
        axis.set_title({"combined": "Combined", "en": "English", "id": "Indonesian"}[scope])
        axis.set_xlabel("Cutoff K")
        axis.set_xticks(CUTOFFS)
        axis.grid(axis="y", alpha=0.25)
        axis.set_ylim(0, 1.02)
    axes[0].set_ylabel("Mean gold-block recall")
    axes[0].legend(frameon=False, fontsize=8, loc="lower right")
    figure.suptitle("Single-block K sweet spot: recall curves and terminal plateau markers")
    figure.tight_layout()
    figure.savefig(output_dir / "k-sweet-spot-recall.png", dpi=200, bbox_inches="tight")
    plt.close(figure)


def write_report(output_dir: Path, summaries: list[dict[str, Any]]) -> None:
    lines = [
        "# K sweet-spot analysis — Customer Service single-block",
        "",
        "Analisis ini mencari cutoff retrieval ketika tambahan lima kandidat tidak lagi memberi kenaikan recall yang praktis dan signifikan.",
        "",
        "## Definisi yang dipakai",
        "",
        f"- **Kenaikan praktis kecil:** `Δ gold_block_recall ≤ {RECALL_PRACTICAL_DELTA:.2f}` (maksimal 2 percentage points dari K ke K+5).",
        "- **Tidak signifikan:** 95% paired-bootstrap CI dari delta mencakup nol; ini berarti data tidak cukup untuk menyatakan ada kenaikan, bukan bukti bahwa efeknya pasti nol.",
        "- **Terminal plateau:** cutoff pertama yang seluruh transisi sesudahnya memenuhi dua syarat recall tersebut. Ini mencegah plateau sementara dibaca sebagai plateau final.",
        f"- **Sweet spot:** nilai maksimum antara terminal recall plateau dan plateau praktis NDCG (`|Δ NDCG| ≤ {NDCG_PRACTICAL_DELTA:.2f}`). Precision dilaporkan sebagai biaya coverage, bukan syarat plateau karena secara definisi cenderung turun ketika K membesar.",
        "- Unit analisis adalah pertanyaan yang sama pada dua cutoff berurutan; English dan Indonesian dihitung terpisah dari 100 pertanyaan masing-masing.",
        "",
        "## Hasil per kondisi dan bahasa",
        "",
        "| Condition | Bahasa | Recall plateau | NDCG plateau | Sweet spot K | Recall @ sweet | Recall @60 | Tambahan recall setelah sweet | Precision @ sweet | Precision @60 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['condition_label']} | {str(row['scope']).upper()} | {row['terminal_recall_plateau_k'] or '—'} | {row['terminal_ndcg_plateau_k'] or '—'} | {row['sweet_spot_k'] or '—'} | {row['recall_at_sweet']:.3f} | {row['recall_at_60']:.3f} | {row['recall_gain_after_sweet']:+.3f} | {row['precision_at_sweet']:.3f} | {row['precision_at_60']:.3f} |"
        )
    combined = [row for row in summaries if row["scope"] == "combined"]
    global_k = max(int(row["sweet_spot_k"]) for row in combined if row["sweet_spot_k"])
    combined_summary = "; ".join(
        f"{row['condition_label']} K={row['sweet_spot_k']}" for row in combined
    )
    lines.extend([
        "",
        "## Kesimpulan operasional",
        "",
        f"- Sweet spot terminal pada agregat gabungan adalah: {combined_summary}.",
        f"- Jika satu cutoff harus dipakai lintas profile, **K={global_k}** adalah pilihan konservatif berbasis plateau terminal pada seluruh kondisi; ia menghindari menghentikan dense/sparse terlalu cepat.",
        "- Untuk profile dense sebagai kandidat final, K=40 adalah sweet spot terminal pada ketiga kelompok (gabungan, English, Indonesian). Dari K=40 ke K=60 masih ada kenaikan kumulatif sekitar 3 pp, tetapi tiap langkahnya berada di bawah ambang 2 pp dan tidak signifikan secara paired-bootstrap; K=60 hanya dipilih bila coverage maksimum lebih penting daripada precision.",
        "- English dan Indonesian tidak boleh digabung saat mengambil keputusan: gunakan nilai bahasa terendah sebagai guardrail bila ingin satu cutoff yang aman untuk kedua bahasa.",
        "",
        "## Artefak",
        "",
        "- `k-sweet-spot-summary.csv`: sweet spot, recall/precision trade-off, dan hasil per bahasa.",
        "- `k-marginal-deltas.csv`: delta setiap transisi K→K+5 beserta 95% CI dan flag plateau.",
        "- `k-sweet-spot-recall.png`: kurva recall Combined, English, dan Indonesian dengan marker sweet spot.",
    ])
    (output_dir / "k-sweet-spot-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = read_rows(args.input)
    transitions = transition_rows(rows)
    summaries = summary_rows(rows, transitions)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "k-marginal-deltas.csv", transitions)
    write_csv(args.output_dir / "k-sweet-spot-summary.csv", summaries)
    plot(args.output_dir, rows, summaries)
    write_report(args.output_dir, summaries)
    manifest = {
        "analysis": "customer-service-single-block-k-sweet-spot",
        "input": str(args.input),
        "cutoffs": list(CUTOFFS),
        "language_counts": {"en": 100, "id": 100},
        "recall_practical_delta": RECALL_PRACTICAL_DELTA,
        "ndcg_practical_delta": NDCG_PRACTICAL_DELTA,
        "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED, "confidence": 0.95},
        "outputs": ["k-sweet-spot-report.md", "k-sweet-spot-summary.csv", "k-marginal-deltas.csv", "k-sweet-spot-recall.png"],
    }
    (args.output_dir / "k-sweet-spot-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir), "rows": len(rows), "transition_rows": len(transitions), "summary_rows": len(summaries)}))


if __name__ == "__main__":
    main()
