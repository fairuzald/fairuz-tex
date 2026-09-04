# Customer Service Revision — hasil retrieval

Hanya ada dua lane aktif. `single-block` adalah lane final yang dipakai untuk keputusan;
`multiblock` dipertahankan sebagai benchmark historis dan tidak dihapus.

## Struktur

```text
runs/
├── single-block/
│   ├── raw-e2e-existing-k60/   # 5 profile × 200 pertanyaan, retrieval API
│   └── analysis/               # scoring single-block dan semua diagram
└── multiblock/
    ├── raw-e2e-existing-k60/   # raw benchmark multiblock
    └── analysis/               # ringkasan multiblock; detail sekunder di bawahnya
        └── secondary/          # OFAT dan cutoff untuk audit historis
```

Tidak ada profile baru atau indexing ulang pada raw run single-block; lima profile
existing memakai datasource yang sama dan seluruh 9 dokumen berstatus `succeeded`.

## Lane final: single-block

- Raw: [`single-block/raw-e2e-existing-k60/`](single-block/raw-e2e-existing-k60/)
- Report: [`single-block/analysis/analysis-report.md`](single-block/analysis/analysis-report.md)
- Diagram utama: [`single-block/analysis/retrieval-quality-by-cutoff.png`](single-block/analysis/retrieval-quality-by-cutoff.png)
- Perbandingan K=10/K=60: [`single-block/analysis/condition-quality-at-k10-k60.png`](single-block/analysis/condition-quality-at-k10-k60.png)
- Per-question: [`single-block/analysis/question-metrics.csv`](single-block/analysis/question-metrics.csv)

Scoring single-block memakai tepat satu gold block per pertanyaan:

```python
hit_chunk = bool(set(chunk["source_block_ids"]) & set(gold_block_ids))
chunk_precision_at_k = hit_chunks / K
chunk_success_at_k = int(hit_chunks > 0)
gold_block_recall_at_k = len(found_gold_blocks & gold_block_ids) / len(gold_block_ids)
chunk_ndcg_at_k = binary_ndcg(ranked_hit_flags, K)
```

Analyzer offline dapat dijalankan ulang tanpa API:

```bash
.venv/bin/python experiments/offline-rag-experiments/customer_service_revision/03-implementation/scripts/analyze_single_block_retrieval.py
```

Perintah default membaca raw single-block dan menulis kembali ke `single-block/analysis/`.

## Benchmark historis: multiblock

Gunakan [`multiblock/analysis/analysis-report.md`](multiblock/analysis/analysis-report.md)
untuk ringkasan multiblock. Detail OFAT dan cutoff tetap disimpan di
[`multiblock/analysis/secondary/`](multiblock/analysis/secondary/) agar provenance analisis lama
dapat diaudit tanpa memenuhi folder utama.

Analyzer multiblock tidak digunakan untuk keputusan single-block dan memakai kontrak
precision lama (`hit chunks / returned prefix`). Definisi lengkap ada di
[`../metrics-and-scoring.md`](../metrics-and-scoring.md).
