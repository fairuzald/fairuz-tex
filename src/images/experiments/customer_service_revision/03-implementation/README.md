# 03 — Retrieval Customer Service Revision

Folder ini sekarang memiliki dua lane yang terpisah:

1. **Single-block** — lane final untuk keputusan retrieval. Setiap pertanyaan memiliki satu
   gold block dan dianalisis pada `K=5,10,15,...,60`.
2. **Multiblock** — benchmark pembanding yang dipertahankan untuk audit; bukan lane keputusan.

Keduanya memakai layout yang sama: `raw-e2e-existing-k60/` untuk trace dan `analysis/` untuk
hasil. Multiblock hanya menampilkan ringkasan di `analysis/`; detail audit berada di
`analysis/secondary/`.

## Konfigurasi bersama

- [`configuration-matrix.md`](configuration-matrix.md) — kondisi matched OFAT.
- [`existing-profile-map.json`](existing-profile-map.json) — lima profile existing yang dipakai ulang.
- [`metrics-and-scoring.md`](metrics-and-scoring.md) — definisi unit, provenance, dan denominator.
- [`implementation-plan.md`](implementation-plan.md) — urutan eksekusi dan gate.

## Single-block: lane final

- Raw retrieval: [`runs/single-block/raw-e2e-existing-k60/`](runs/single-block/raw-e2e-existing-k60/)
- Analisis lengkap: [`runs/single-block/analysis/analysis-report.md`](runs/single-block/analysis/analysis-report.md)
- Diagram cutoff: [`runs/single-block/analysis/retrieval-quality-by-cutoff.png`](runs/single-block/analysis/retrieval-quality-by-cutoff.png)
- Diagram bahasa: [`runs/single-block/analysis/language-quality-by-cutoff.png`](runs/single-block/analysis/language-quality-by-cutoff.png)
- Metrik per pertanyaan: [`runs/single-block/analysis/question-metrics.csv`](runs/single-block/analysis/question-metrics.csv)
- Sweet spot cutoff: [`runs/single-block/analysis/k-sweet-spot-report.md`](runs/single-block/analysis/k-sweet-spot-report.md)
- Analyzer: [`scripts/analyze_single_block_retrieval.py`](scripts/analyze_single_block_retrieval.py)

Analisis single-block mencakup overall, English/Indonesian, question family, product,
question pair, first-hit rank, candidate-pool size, latency, empty result, dan metrik
setiap `question_id`. Retrieval tidak memanggil LLM generation, reranker, intent classifier,
atau knowledge graph.

## Multiblock: benchmark yang dipertahankan

- Raw retrieval: [`runs/multiblock/raw-e2e-existing-k60/`](runs/multiblock/raw-e2e-existing-k60/)
- Ringkasan analysis: [`runs/multiblock/analysis/analysis-report.md`](runs/multiblock/analysis/analysis-report.md)
- Detail OFAT sekunder: [`runs/multiblock/analysis/secondary/ofat/analysis-report.md`](runs/multiblock/analysis/secondary/ofat/analysis-report.md)
- Analyzer: [`scripts/analyze_multiblock_retrieval.py`](scripts/analyze_multiblock_retrieval.py)

Cutoff turunan tetap berada di [`runs/multiblock/analysis/secondary/cutoff-chunker/`](runs/multiblock/analysis/secondary/cutoff-chunker/)
dan [`runs/multiblock/analysis/secondary/cutoff-indexer/`](runs/multiblock/analysis/secondary/cutoff-indexer/). Jangan gabungkan
angka multiblock dengan score single-block karena denominator precision berbeda.

Kedua lane selalu dianalisis overall serta terpisah untuk 100 English dan 100 Indonesian pada
seluruh cutoff K=5,10,...,60; hasil tanpa kedua bahasa dianggap tidak lengkap.
