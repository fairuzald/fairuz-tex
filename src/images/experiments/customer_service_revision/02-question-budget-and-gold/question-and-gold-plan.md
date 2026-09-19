# Rencana ringkas Langkah 2

Target: **100 slot × 2 bahasa = 200 question/gold** yang sama untuk semua konfigurasi retrieval.

```text
question_outline_frame (1.240 leaf outline)
        ↓ random seeded: 20260831
100 frozen slots → 200 language rows (100 en + 100 id)
        ↓ deterministic complete bounded parent-subtree materialization
context-packets + context_text
        ↓ LLM authoring chooses evidence + structural provenance checks
question-set + gold-evidence
```

Keputusan yang dibekukan:

- Unit sampling adalah leaf outline, bukan text block atau `evidence_shape`.
- Strata hanya `document × page_bin` (P1–P5).
- Floor 8 per manual; sisa dialokasikan berdasarkan page count.
- Candidate pool sekitar 200; reviewer membekukan 100 slot anchor.
- Setiap slot memiliki dua row dengan `question_pair_id` yang sama: 100 `en` dan 100 `id`.
- Family: 50 fakta, 50 setup, 50 troubleshooting, 50 fitur/limitasi (25 pair per family).
- Wording customer-facing dan awam; istilah teknis hanya dipertahankan jika diperlukan untuk
  membedakan produk atau membuat pertanyaan dapat diaudit.
- `question_source_frame.csv` hanya lookup context, bukan pool sampling kedua.

Input dan hash yang wajib dicatat:

```text
01-target-corpus-size/01-corpus-eda/
├── question_outline_frame.csv
├── question_source_frame.csv
└── transition/{corpus-manifest.json,summary.json}
```

Gold evidence boleh satu atau beberapa canonical block per question. Tidak ada fixed-two
requirement; model memilih dari `context_text` lengkap.

Gate sebelum retrieval/OAT: 100 slot dan 200 language row approved, provenance
outline/source lengkap, packet `ready` atau `ready_over_soft_limit` (<8.000 token),
question/gold approved, dan seluruh checksum tersedia.

Detail proses:

- [02.01 Budget](01-question-budget-and-distribution/README.md)
- [02.02 Context](02-context-materialization/README.md)
- [02.03 Question/gold](03-question-generation-and-gold/README.md)
