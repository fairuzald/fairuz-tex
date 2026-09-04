# 01 — Target corpus dan EDA

## Tujuan

Membekukan populasi dan memeriksa apakah struktur parser cukup untuk memilih sumber
pertanyaan. Tahap ini **tidak** membuat question, context, profile, index, atau retrieval.

## Keputusan corpus

| Item | Keputusan |
|---|---|
| Datasource | `netgear-customer-service` |
| Populasi | 9/9 PDF aktif (census penuh) |
| Halaman | Semua halaman dari sembilan manual |
| Corpus sampling | Tidak digunakan; sampling baru terjadi pada outline untuk question slot |
| Parser | `generic-outline@1.0.0` |

Alasan census: hanya ada sembilan manual dan setiap manual mewakili produk berbeda. Tidak
ada dokumen yang dibuang karena panjang, ukuran, duplicate, atau label topic.

## Yang dianalisis

EDA read-only memeriksa:

1. identitas dokumen, raw hash, byte size, dan page count;
2. page, heading, section, dan text block yang dihasilkan parser;
3. provenance block: page, urutan, character offset, dan text hash;
4. duplicate/template serta table/figure sebagai diagnostic; dan
5. outline tree per dokumen sebagai dasar random pick.

## Outline dan source frame

`question_outline_frame.csv` adalah pool sampling: satu row per **leaf outline** (heading
tanpa child heading) yang memiliki text langsung. Row ini berisi heading, `section_path`,
depth, page span, dan `direct_source_frame_ids`.

`question_source_frame.csv` adalah lookup: satu row per parser-emitted `TEXT_BLOCK`.
Frame ini menyediakan text, urutan, offset, page, dan hash setelah outline dipilih.

`evidence_shape` dan topic label tidak digunakan untuk sampling. Jika ada, nilainya hanya
diagnostic untuk review context.

## Hasil EDA

| Produk | Halaman | Node outline | Top-level | Leaf kandidat | Depth max |
|---|---:|---:|---:|---:|---:|
| CM2000 | 26 | 28 | 4 | 22 | 3 |
| LM1200 | 105 | 104 | 10 | 84 | 3 |
| R6350 | 204 | 225 | 16 | 175 | 4 |
| R7000 | 186 | 212 | 15 | 168 | 4 |
| RAX120 | 175 | 201 | 13 | 161 | 3 |
| RAX50 | 160 | 184 | 13 | 148 | 3 |
| RAXE500 | 169 | 191 | 12 | 155 | 3 |
| RBK852 | 161 | 182 | 11 | 144 | 3 |
| XR500 | 214 | 230 | 18 | 183 | 3 |
| **Total** | **1.400** | **1.557** | **112** | **1.240** | **4** |

Daftar top-level dan seluruh parent/child outline dapat dibaca di
[`outline-report.md`](01-corpus-eda/outline-report.md). Ringkasan machine-readable ada di
`transition/outline_summary.csv` dan `transition/outline_inventory.csv`.

## Artefak

```text
01-corpus-eda/
├── eda-report.md
├── outline-report.md
├── question_outline_frame.csv
├── question_source_frame.csv
├── 00_corpus_pipeline_flow.png
├── 01_document_page_bytes.png
├── 02_outline_and_block_coverage.png
└── transition/
    ├── corpus-manifest.json
    ├── document_inventory.csv
    ├── page_inventory.csv
    ├── parser_quality.csv
    ├── redundancy_clusters.csv
    ├── section_inventory.csv
    ├── outline_inventory.csv
    ├── outline_summary.csv
    └── summary.json
```

Frame hash:

```text
manifest:        7fdc2c78ad23bbd74fc790fb4395d8be0f97fb4c9242d91a3f6e52d58b30b42
outline frame:   b759d9417c9f7c4f9fc27bc767b7c8f75530ab6e5f2945e039169a8e9c55a966
source frame:    f1058eb82d4542c257f56689be0d40656cd4397776cd98ec9f9837ed1f8f51de
```

Diagram page hanya menampilkan jumlah halaman; byte size tetap tersedia di
`transition/document_inventory.csv`.

## Gate ke Langkah 2

Lanjutkan hanya jika 9 dokumen, raw/parser hash, outline count, page/block provenance, dan
outline report cocok dengan snapshot yang direview. Setelah disetujui, Langkah 2 melakukan
random pick ber-seed dari `question_outline_frame.csv`.

Jalankan ulang secara read-only:

```bash
uv run python 01-corpus-eda/scripts/run_customer_eda.py \
  --dsn 'postgresql://dpo:dpo@localhost:5437/dpo' \
  --s3-endpoint http://localhost:9005 \
  --bucket legal-chunks
```
