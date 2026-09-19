# K sweet-spot analysis — Customer Service single-block

Analisis ini mencari cutoff retrieval ketika tambahan lima kandidat tidak lagi memberi kenaikan recall yang praktis dan signifikan.

## Definisi yang dipakai

- **Kenaikan praktis kecil:** `Δ gold_block_recall ≤ 0.02` (maksimal 2 percentage points dari K ke K+5).
- **Tidak signifikan:** 95% paired-bootstrap CI dari delta mencakup nol; ini berarti data tidak cukup untuk menyatakan ada kenaikan, bukan bukti bahwa efeknya pasti nol.
- **Terminal plateau:** cutoff pertama yang seluruh transisi sesudahnya memenuhi dua syarat recall tersebut. Ini mencegah plateau sementara dibaca sebagai plateau final.
- **Sweet spot:** nilai maksimum antara terminal recall plateau dan plateau praktis NDCG (`|Δ NDCG| ≤ 0.01`). Precision dilaporkan sebagai biaya coverage, bukan syarat plateau karena secara definisi cenderung turun ketika K membesar.
- Unit analisis adalah pertanyaan yang sama pada dua cutoff berurutan; English dan Indonesian dihitung terpisah dari 100 pertanyaan masing-masing.

## Hasil per konfigurasi dan bahasa

| Configuration | Bahasa | Recall plateau | NDCG plateau | Sweet spot K | Recall @ sweet | Recall @60 | Tambahan recall setelah sweet | Precision @ sweet | Precision @60 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hybrid baseline | COMBINED | 25 | 25 | 25 | 0.740 | 0.745 | +0.005 | 0.055 | 0.025 |
| Hybrid baseline | EN | 25 | 30 | 30 | 0.800 | 0.810 | +0.010 | 0.052 | 0.027 |
| Hybrid baseline | ID | 20 | 25 | 25 | 0.680 | 0.680 | +0.000 | 0.052 | 0.023 |
| Recursive chunker | COMBINED | 20 | 25 | 25 | 0.610 | 0.630 | +0.020 | 0.036 | 0.016 |
| Recursive chunker | EN | 25 | 25 | 25 | 0.680 | 0.700 | +0.020 | 0.040 | 0.018 |
| Recursive chunker | ID | 20 | 20 | 20 | 0.540 | 0.560 | +0.020 | 0.036 | 0.015 |
| Sliding-window chunker | COMBINED | 25 | 25 | 25 | 0.675 | 0.685 | +0.010 | 0.048 | 0.021 |
| Sliding-window chunker | EN | 25 | 25 | 25 | 0.720 | 0.730 | +0.010 | 0.052 | 0.023 |
| Sliding-window chunker | ID | 25 | 25 | 25 | 0.630 | 0.640 | +0.010 | 0.043 | 0.019 |
| Sparse indexer | COMBINED | 45 | 30 | 45 | 0.465 | 0.495 | +0.030 | 0.023 | 0.019 |
| Sparse indexer | EN | 45 | 45 | 45 | 0.600 | 0.640 | +0.040 | 0.027 | 0.023 |
| Sparse indexer | ID | 30 | 25 | 30 | 0.300 | 0.350 | +0.050 | 0.022 | 0.016 |
| Dense indexer | COMBINED | 40 | 40 | 40 | 0.830 | 0.860 | +0.030 | 0.048 | 0.038 |
| Dense indexer | EN | 40 | 40 | 40 | 0.850 | 0.880 | +0.030 | 0.051 | 0.039 |
| Dense indexer | ID | 40 | 40 | 40 | 0.810 | 0.840 | +0.030 | 0.046 | 0.036 |

## Kesimpulan operasional

- Sweet spot terminal pada agregat gabungan adalah: Hybrid baseline K=25; Recursive chunker K=25; Sliding-window chunker K=25; Sparse indexer K=45; Dense indexer K=40.
- Jika satu cutoff harus dipakai lintas profile, **K=45** adalah pilihan konservatif berbasis plateau terminal pada seluruh konfigurasi; ia menghindari menghentikan dense/sparse terlalu cepat.
- Untuk profile dense sebagai kandidat final, K=40 adalah sweet spot terminal pada ketiga kelompok (gabungan, English, Indonesian). Dari K=40 ke K=60 masih ada kenaikan kumulatif sekitar 3 pp, tetapi tiap langkahnya berada di bawah ambang 2 pp dan tidak signifikan secara paired-bootstrap; K=60 hanya dipilih bila coverage maksimum lebih penting daripada precision.
- English dan Indonesian tidak boleh digabung saat mengambil keputusan: gunakan nilai bahasa terendah sebagai guardrail bila ingin satu cutoff yang aman untuk kedua bahasa.

## Artefak

- `k-sweet-spot-summary.csv`: sweet spot, recall/precision trade-off, dan hasil per bahasa.
- `k-marginal-deltas.csv`: delta setiap transisi K→K+5 beserta 95% CI dan flag plateau.
- `k-sweet-spot-recall.png`: kurva recall Combined, English, dan Indonesian dengan marker sweet spot.
