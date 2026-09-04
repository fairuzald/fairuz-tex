# Corpus Visualization Report

Snapshot: `legal-snapshot-report.Z6SWZH`

Laporan ini dibangun dari artifact canonical dan hanya menghasilkan derived visualizations. Ia tidak mengubah selection, parser units, atau question candidates.

Scorecard retrieval terbaru berada di [`production-20260825-legal-retrieval-final-bypass`](../../../../../../../../implementation/analysis/production-20260825-legal-retrieval-final-bypass/analysis.md). Gambar pada folder ini hanya memvisualisasikan corpus dan benchmark input.

## Ringkasan scope

- Selected documents: `263` dari target `263`.
- Selected clusters: `137`; selected relation edges: `361`.
- Parser units: `28,208`.
- Question candidates: `100` pada `25` clusters.
- Graph sebelum selection: `3,863` clusters dan `1,963` edges.

## Visualizations

- [`01_pipeline_overview.png`](01_pipeline_overview.png)
- [`01a_pipeline_document_selection.png`](01a_pipeline_document_selection.png)
- [`02_join_integrity.png`](02_join_integrity.png)
- [`02a_preselection_vs_selected.png`](02a_preselection_vs_selected.png)
- [`03_document_composition.png`](03_document_composition.png)
- [`04_cluster_structure.png`](04_cluster_structure.png)
- [`05_question_benchmark.png`](05_question_benchmark.png)

## Key audit numbers

| Checkpoint | Value | Interpretation |
| --- | ---: | --- |
| BPK datasource rows | 8,745 | Source rows for the census join |
| Vector census rows | 4,459 | Vector-side census rows |
| Exact matched rows | 4,453 | 99.9% of vector census |
| Stale / hash mismatch | 6 | 6 stale, 0 hash mismatch |
| Selected graph | 137 clusters / 361 edges | 288 internal |
| Benchmark | 100 questions / 25 clusters | 35 relation-backed |

## Evaluasi penggunaan visual

- Pipeline overview menggunakan flow diagram agar jumlah dokumen, cluster, dan question tidak disalahbaca sebagai satu deret angka yang homogen.
- Partial pipeline hanya memperbesar keputusan document selection; ini membantu membaca penurunan dari matched documents ke target 263.
- Join integrity memisahkan coverage datasource/vector dari alasan eksklusi stale dan hash mismatch.
- Preselection comparison memperlihatkan distribusi corpus matched sebelum selection dan perubahan setelah complete-cluster selection; angka sebelum selection berasal dari process-3 cluster summary.
- Document composition mencakup tahun, bentuk hukum, status, dan subject karena keempatnya memengaruhi interpretasi representativeness corpus.
- Cluster structure menegaskan bahwa angka relation edges adalah edge yang dipertahankan pada selected corpus, bukan seluruh graph sebelum selection.
- Question benchmark menampilkan persona, subtype, relation-backed evidence, dan coverage question per cluster; detail parser tetap dibaca dari artifact canonical.

## Distribution quick tables

### Legal status

| Status | Documents |
| --- | ---: |
| BERLAKU | 223 |
| TIDAK_BERLAKU | 40 |

### Tahun teratas

| Tahun | Documents |
| ---: | ---: |
| 2020 | 27 |
| 2013 | 18 |
| 2017 | 18 |
| 2018 | 15 |
| 2019 | 15 |
| 2010 | 12 |
| 2011 | 12 |
| 2021 | 12 |
| 2023 | 12 |
| 2025 | 12 |

### Bentuk hukum teratas

| Bentuk | Documents |
| --- | ---: |
| PERWALI | 46 |
| PERBUP | 36 |
| PERDA | 36 |
| PP | 25 |
| PERATURAN_MENAG | 17 |
| PERGUB | 10 |
| KEPPRES | 9 |
| PERPRES | 7 |
| PERMENKUMHAM | 6 |
| PERMENDIKBUD | 6 |

### Subjek teratas

| Subjek | Document-subject assignments |
| --- | ---: |
| PENDIDIKAN | 242 |
| STANDAR_PEDOMAN | 23 |
| PENDIDIKAN_DAN_PELATIHAN | 23 |
| KEPEGAWAIAN_APARATUR_NEGARA | 17 |
| STRUKTUR_ORGANISASI | 14 |
| BANTUAN_SUMBANGAN_BENCANA_KEBENCANAAN_DAN_PENANGGULANGAN_BENCANA | 10 |
| PENGELOLAAN_KEUANGAN_NEGARA_DAERAH | 8 |
| KEAGAMAAN_IBADAH_DAN_PENYELENGGARAAN_HAJI | 7 |
| PROGRAM_RENCANA_PEMBANGUNAN_DAN_RENCANA_KERJA | 5 |
| DASAR_PEMBENTUKAN_KEMENTERIAN_LEMBAGA_BADAN_ORGANISASI | 4 |
Catatan: satu dokumen dapat memiliki lebih dari satu subject, sehingga angka assignment dapat melebihi jumlah dokumen.

## Cara membaca

1. Mulai dari pipeline dan join integrity untuk memahami perubahan skala serta exclusions.
2. Periksa komposisi tahun, bentuk hukum, status, dan subject untuk memahami corpus terpilih.
3. Periksa cluster structure untuk menilai ukuran cluster, relation edges, dan coverage relasi internal.
4. Periksa question benchmark untuk memastikan persona, subtype, dan coverage cluster tersedia.

Angka inti dan audit detail tetap tersedia pada artifact canonical proses; grafik hanya menampilkan agregasi yang dibuat agar terbaca.

### Catatan interpretasi

- Document composition menggambarkan 263 dokumen selected corpus, bukan seluruh datasource BPK.
- Question candidates masih berstatus pending legal review dan belum boleh disebut final gold.
