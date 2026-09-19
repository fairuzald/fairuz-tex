# 02 — Question budget dan gold

## Tujuan

Membuat 100 pasangan pertanyaan customer-facing (200 row: English + Indonesian) dan
`gold evidence` yang sama untuk semua konfigurasi retrieval.
Langkah ini dimulai setelah EDA Langkah 1 disetujui.

## Separation of concern

| Proses | Input | Keputusan | Output |
|---|---|---|---|
| 02.01 Budget | 1.240 leaf outline | Random pick 100 slot anchor dengan coverage dokumen/page, lalu buat 2 varian bahasa | `candidate-pool.csv`, `question-slots.csv` |
| 02.02 Context | 100 slot + source frame | Materialisasi seluruh bounded parent-subtree candidate context secara deterministik | `context-selection.csv`, `context-packets.jsonl` |
| 02.03 Question/gold | Packet yang siap | LLM membaca `context_text`, menulis pertanyaan bilingual, dan memilih evidence variable-size | `question-set.csv`, `gold-evidence.jsonl` |

Tidak ada sampling corpus kedua, retrieval, embedding, chunker, profile, atau index di
Langkah 2.

## Input bersama

```text
01-target-corpus-size/01-corpus-eda/
├── question_outline_frame.csv   # pool random pick
├── question_source_frame.csv     # lookup text block
└── transition/
    ├── corpus-manifest.json
    └── summary.json
```

## Budget

| Family | Target (200 row) |
|---|---:|
| Fakta langsung/spesifikasi | 50 |
| Penyiapan/konfigurasi | 50 |
| Pemecahan masalah/diagnostik | 50 |
| Fitur/keamanan/pemeliharaan/limitasi | 50 |
| **Total** | **200** |

Bahasa dibekukan sebagai 100 English (`Q-001..Q-100`) dan 100 Indonesian
(`Q-101..Q-200`). `question_pair_id` menghubungkan dua varian slot yang sama.

## Gate

Lanjutkan ke retrieval hanya jika:

1. tepat 100 slot outline dan 200 language row disetujui serta allocation report cocok;
2. setiap slot memiliki outline, source block, page, section, dan hash yang stabil;
3. semua packet berstatus `ready` atau `ready_over_soft_limit` dan provenance valid; serta
4. question set, gold, dan annotation manifest memiliki checksum.

Detail setiap concern:

- [02.01 — Budget dan distribusi](01-question-budget-and-distribution/README.md)
- [02.02 — Context materialization](02-context-materialization/README.md)
- [02.03 — Question dan gold](03-question-generation-and-gold/README.md)
- [Rencana ringkas Langkah 2](question-and-gold-plan.md)
- [Rencana multi-block parent-subtree](multiblock-question-and-gold-plan.md)

Folder `runs/selection-v1/` adalah run single-block historis yang sudah frozen. Run canonical
multi-block berisi 100 slot, 200 language row, 100 shared context packet, 200 question,
dan 200 gold records (masing-masing berisi satu atau beberapa evidence block) dengan checksum serta provenance database-backed. OAT/OFAT berikutnya
wajib memakai kedua bahasa dan melaporkan hasil overall, per bahasa, per produk, per family,
serta per `question_pair_id`.

Run multi-block disimpan terpisah pada `02-context-materialization/runs/selection-v2-multiblock/`
dan `03-question-generation-and-gold/runs/selection-v2-multiblock/`. Authoring Codex current
model menerima seluruh `context_text` dan memilih evidence variable-size. Pada pass saat ini, distribusi
gold per pasangan adalah 16 pasangan dengan 1 block, 68 dengan 2 block, 13 dengan 3 block,
2 dengan 4 block, dan 1 dengan 5 block (bilingual: 32, 136, 26, 4, dan 2 row). Endpoint LLM eksternal tidak dipanggil; retrieval/OAT/OFAT
tetap tidak memanggil LLM. Manifest, gold, quote, offset, dan provenance sudah dibekukan untuk
review sebelum retrieval.
Enam belas pasangan satu-block dipertahankan karena leaf-nya sudah menjawab slot secara lengkap;
candidate lain tetap context-only agar gold tidak dipadatkan dengan evidence yang tidak diperlukan.
