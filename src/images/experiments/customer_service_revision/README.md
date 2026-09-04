# Customer Service Revision

Benchmark retrieval untuk datasource `netgear-customer-service`.

## Alur

| Tahap | Keputusan | Output |
|---|---|---|
| 01 — Corpus dan EDA | Gunakan seluruh 9 PDF; analisis outline dan provenance | `question_outline_frame.csv`, `question_source_frame.csv`, manifest |
| 02.01 — Budget | Random pick 100 leaf outline/intents dengan seed, coverage dokumen/page; setiap intent dibuat dua language slot | `question-slots.csv`, allocation report |
| 02.02 — Context | Expand 100 outline terpilih secara deterministik menjadi 100 shared bounded context packets yang dipakai dua bahasa | `context-packets.jsonl`, context manifest |
| 02.03 — Question/gold | Tulis 100 pasangan pertanyaan customer-facing English–Indonesia dan gold dari packet saja | `question-set.csv`, `gold-evidence.jsonl` |
| 03 — Retrieval | Dua lane terpisah: single-block final dan multiblock benchmark; generic structure-aware, tanpa KG | Empat metrik single-block per cutoff, bahasa, family, product, pasangan, dan question |

## Aturan utama

- Corpus adalah census 9/9; tidak ada sampling dokumen.
- Random pick dilakukan pada `question_outline_frame.csv`, bukan pada label heuristic.
- `question_source_frame.csv` hanya lookup text block untuk context dan gold.
- Setiap intent memiliki dua varian pertanyaan: 100 English (`Q-001..Q-100`) dan 100 Indonesian (`Q-101..Q-200`); `question_pair_id` menghubungkan keduanya.
- Family pertanyaan seimbang pada seluruh 200 row: 50 fakta, 50 setup, 50 troubleshooting, 50 fitur/limitasi.
- Wording memakai gaya customer awam; istilah teknis hanya dipertahankan jika memang diperlukan agar manual dapat menjawabnya.
- Implementasi memakai `generic-structure-aware` sebagai chunker acuan. Tidak ada knowledge graph, LLM graph, atau metrik KG.
- Lane final single-block memakai satu canonical `block_id` per pertanyaan; multiblock tetap
  memakai evidence variable-size sebagai benchmark. Definisi executable dan perbedaan denominator
  ada di [`03-implementation/metrics-and-scoring.md`](03-implementation/metrics-and-scoring.md).
- Struktur artefak hanya memiliki dua lane di [`03-implementation/runs/README.md`](03-implementation/runs/README.md):
  `single-block/` untuk keputusan final dan `multiblock/` untuk audit.
- Setiap analisis retrieval selalu melaporkan agregat gabungan serta English dan Indonesian
  secara terpisah pada seluruh cutoff `K=5,10,15,...,60`.

## Mulai dari sini

- [Langkah 1: target corpus dan EDA](01-target-corpus-size/README.md)
- [Outline tree lengkap per dokumen](01-target-corpus-size/01-corpus-eda/outline-report.md)
- [Langkah 2: question budget dan gold](02-question-budget-and-gold/README.md)
- [Rencana ringkas Langkah 2](02-question-budget-and-gold/question-and-gold-plan.md)
- [Rencana implementasi retrieval](03-implementation/implementation-plan.md)
- [Analisis single-block final dan diagram](03-implementation/runs/single-block/analysis/analysis-report.md)
- [Analisis sweet spot K dan plateau](03-implementation/runs/single-block/analysis/k-sweet-spot-report.md)
- [Ringkasan benchmark multiblock](03-implementation/runs/multiblock/analysis/analysis-report.md)
