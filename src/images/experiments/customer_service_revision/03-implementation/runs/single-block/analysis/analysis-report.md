# Customer Service single-block retrieval analysis

Scoring contract: `chunk_precision@K = hit chunks / K`; `chunk_success@K` is any hit; `gold_block_recall@K` is gold-block coverage; `chunk_ndcg@K` ranks hit chunks.

- Retrieval traces: `1000` (`5 conditions × 200 questions`).
- Cutoffs: `5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60`.
- Returned candidate pool: mean `36.88` chunks, maximum `60`; single-block precision still uses the requested K denominator.
- No indexing, question generation, reranker, intent classifier, or LLM answer generation was run by this analysis.

## Overall comparison

| Condition | K | Precision | Success | Gold recall | NDCG | Median latency | Empty rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Hybrid baseline | 10 | 0.083 | 0.575 | 0.575 | 0.248 | 11.2s | 0.000 |
| Recursive chunker | 10 | 0.062 | 0.490 | 0.490 | 0.235 | 5.9s | 0.000 |
| Sliding-window chunker | 10 | 0.077 | 0.535 | 0.535 | 0.253 | 5.9s | 0.000 |
| Sparse indexer | 10 | 0.039 | 0.265 | 0.265 | 0.103 | 3.5s | 0.015 |
| Dense indexer | 10 | 0.098 | 0.625 | 0.625 | 0.272 | 3.6s | 0.000 |
| Hybrid baseline | 60 | 0.025 | 0.745 | 0.745 | 0.339 | 11.2s | 0.000 |
| Recursive chunker | 60 | 0.016 | 0.630 | 0.630 | 0.294 | 5.9s | 0.000 |
| Sliding-window chunker | 60 | 0.021 | 0.685 | 0.685 | 0.325 | 5.9s | 0.000 |
| Sparse indexer | 60 | 0.019 | 0.495 | 0.495 | 0.190 | 3.5s | 0.015 |
| Dense indexer | 60 | 0.038 | 0.860 | 0.860 | 0.400 | 3.6s | 0.000 |

At K=10, gold recall winner: **Dense indexer** (0.625); precision winner: **Dense indexer** (0.098); success winner: **Dense indexer** (0.625); NDCG winner: **Dense indexer** (0.272).

At K=60, gold recall winner: **Dense indexer** (0.860); precision winner: **Dense indexer** (0.038); success winner: **Dense indexer** (0.860); NDCG winner: **Dense indexer** (0.400).

## Metrik terpisah per bahasa

Pemisahan ini wajib: setiap condition memiliki tepat 100 pertanyaan English dan 100 Indonesian. `language-by-cutoff.csv` berisi seluruh grid K; tabel berikut menampilkan titik keputusan K=10 dan K=60.

| Condition | Bahasa | K | Precision | Success | Gold recall | NDCG | Empty rate |
|---|---|---:|---:|---:|---:|---:|---:|
| Hybrid baseline | EN | 10 | 0.085 | 0.600 | 0.600 | 0.273 | 0.000 |
| Hybrid baseline | ID | 10 | 0.081 | 0.550 | 0.550 | 0.223 | 0.000 |
| Recursive chunker | EN | 10 | 0.070 | 0.530 | 0.530 | 0.274 | 0.000 |
| Recursive chunker | ID | 10 | 0.053 | 0.450 | 0.450 | 0.196 | 0.000 |
| Sliding-window chunker | EN | 10 | 0.087 | 0.550 | 0.550 | 0.276 | 0.000 |
| Sliding-window chunker | ID | 10 | 0.067 | 0.520 | 0.520 | 0.231 | 0.000 |
| Sparse indexer | EN | 10 | 0.049 | 0.360 | 0.360 | 0.142 | 0.000 |
| Sparse indexer | ID | 10 | 0.029 | 0.170 | 0.170 | 0.063 | 0.030 |
| Dense indexer | EN | 10 | 0.107 | 0.660 | 0.660 | 0.295 | 0.000 |
| Dense indexer | ID | 10 | 0.090 | 0.590 | 0.590 | 0.249 | 0.000 |
| Hybrid baseline | EN | 60 | 0.027 | 0.810 | 0.810 | 0.381 | 0.000 |
| Hybrid baseline | ID | 60 | 0.023 | 0.680 | 0.680 | 0.297 | 0.000 |
| Recursive chunker | EN | 60 | 0.018 | 0.700 | 0.700 | 0.339 | 0.000 |
| Recursive chunker | ID | 60 | 0.015 | 0.560 | 0.560 | 0.249 | 0.000 |
| Sliding-window chunker | EN | 60 | 0.023 | 0.730 | 0.730 | 0.354 | 0.000 |
| Sliding-window chunker | ID | 60 | 0.019 | 0.640 | 0.640 | 0.296 | 0.000 |
| Sparse indexer | EN | 60 | 0.023 | 0.640 | 0.640 | 0.247 | 0.000 |
| Sparse indexer | ID | 60 | 0.016 | 0.350 | 0.350 | 0.133 | 0.030 |
| Dense indexer | EN | 60 | 0.039 | 0.880 | 0.880 | 0.420 | 0.000 |
| Dense indexer | ID | 60 | 0.036 | 0.840 | 0.840 | 0.380 | 0.000 |

## Cara membaca hasil single-block

Karena setiap pertanyaan memiliki tepat satu gold block, `chunk_success@K` dan `gold_block_recall@K` sama-sama biner pada level pertanyaan. Nilai agregatnya adalah proporsi pertanyaan yang menemukan block tersebut. `chunk_precision@K` tetap menghitung jumlah hit chunk dibagi K, sehingga nilainya turun ketika K bertambah dan kandidat tambahan tidak relevan.

## Ranking dan validitas eksekusi

| Condition | First-hit median | First-hit P90 | MRR | No-hit @10 | No-hit @60 | Median latency | P90 latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Hybrid baseline | 5.0 | 17.2 | 0.231 | 0.425 | 0.255 | 11.2s | 13.2s |
| Recursive chunker | 6.0 | 17.0 | 0.216 | 0.510 | 0.370 | 5.9s | 7.2s |
| Sliding-window chunker | 6.0 | 18.0 | 0.232 | 0.465 | 0.315 | 5.9s | 7.1s |
| Sparse indexer | 10.0 | 42.2 | 0.122 | 0.735 | 0.505 | 3.5s | 4.6s |
| Dense indexer | 5.0 | 22.8 | 0.315 | 0.375 | 0.140 | 3.6s | 4.6s |

## Konsistensi English–Indonesian

Delta dihitung berpasangan untuk `question_pair_id`: Indonesia dikurangi English. Nilai positif berarti Indonesia lebih baik pada metrik tersebut.

| Condition | Recall EN @10 | Recall ID @10 | Δ @10 | Both @10 | Recall EN @60 | Recall ID @60 | Δ @60 | Both @60 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hybrid baseline | 0.600 | 0.550 | -0.050 | 0.440 | 0.810 | 0.680 | -0.130 | 0.640 |
| Recursive chunker | 0.530 | 0.450 | -0.080 | 0.370 | 0.700 | 0.560 | -0.140 | 0.530 |
| Sliding-window chunker | 0.550 | 0.520 | -0.030 | 0.390 | 0.730 | 0.640 | -0.090 | 0.580 |
| Sparse indexer | 0.360 | 0.170 | -0.190 | 0.130 | 0.640 | 0.350 | -0.290 | 0.330 |
| Dense indexer | 0.660 | 0.590 | -0.070 | 0.560 | 0.880 | 0.840 | -0.040 | 0.840 |

## Variasi antarproduk

`product-by-cutoff.csv` menyimpan semua product × condition × cutoff. Tabel berikut menunjukkan rentang product pada K=60 agar rata-rata keseluruhan tidak menyembunyikan model yang sulit.

| Condition | Terendah | Tertinggi |
|---|---|---|
| Hybrid baseline | RAX50 (0.545) | CM2000 (0.944) |
| Recursive chunker | LM1200 (0.500) | XR500 (0.750) |
| Sliding-window chunker | RAX50 (0.545) | XR500 (0.875) |
| Sparse indexer | RAX50 (0.364) | XR500 (0.625) |
| Dense indexer | LM1200 (0.650) | CM2000 (1.000) |

## Variasi question family

`family-by-cutoff.csv` menyimpan empat family pertanyaan secara terpisah. Ringkasan ini memperlihatkan family terlemah dan terkuat pada K=10 agar keputusan tidak hanya mengikuti komposisi agregat.

| Condition | Terendah @10 | Tertinggi @10 | Terendah @60 | Tertinggi @60 |
|---|---|---|---|---|
| Hybrid baseline | troubleshooting_diagnostics (0.500) | facts_specifications (0.660) | features_security_maintenance_limitations (0.720) | facts_specifications (0.780) |
| Recursive chunker | troubleshooting_diagnostics (0.360) | facts_specifications (0.540) | troubleshooting_diagnostics (0.560) | facts_specifications (0.700) |
| Sliding-window chunker | troubleshooting_diagnostics (0.440) | features_security_maintenance_limitations (0.580) | troubleshooting_diagnostics (0.660) | facts_specifications (0.700) |
| Sparse indexer | troubleshooting_diagnostics (0.140) | features_security_maintenance_limitations (0.360) | troubleshooting_diagnostics (0.300) | features_security_maintenance_limitations (0.580) |
| Dense indexer | features_security_maintenance_limitations (0.540) | facts_specifications (0.660) | features_security_maintenance_limitations (0.780) | facts_specifications (0.960) |

## Keputusan sementara

Dense indexer menjadi kondisi terbaik pada K=10 dan K=60 untuk keempat metrik agregat. Gunakan K=10 jika prioritasnya menjaga daftar hasil tetap pendek; gunakan K=40–60 jika prioritasnya coverage, sambil menerima precision yang lebih rendah. Pemilihan K final tetap harus mempertimbangkan biaya context downstream.

## Outputs

- `overall-by-cutoff.csv`: combined metrics for every condition and K.
- `language-by-cutoff.csv` and `family-by-cutoff.csv`: subgroup metrics.
- `product-by-cutoff.csv`: product × condition × cutoff.
- `pair-metrics.csv`: paired English–Indonesian metrics for every question pair and cutoff.
- `condition-diagnostics.csv`: first-hit rank, MRR, candidate pool, latency, and no-hit rate.
- `question-metrics.csv`: one row per condition × question with all four metrics at every K.
- `retrieval-quality-by-cutoff.png`: four metric curves across K.
- `language-quality-by-cutoff.png`: English and Indonesian curves.
- `condition-quality-at-k10-k60.png`: compact decision comparison.
- `execution-latency.png`: latency view; empty rate is in CSV and report.
- `product-recall-at-k10-k60.png`: recall heatmap per product.
- `first-hit-rank-cdf.png`: distribution of the first hit rank.
- `language-paired-delta-at-k10-k60.png`: paired ID−EN deltas.
- `precision-recall-tradeoff.png`: precision versus coverage across K.
