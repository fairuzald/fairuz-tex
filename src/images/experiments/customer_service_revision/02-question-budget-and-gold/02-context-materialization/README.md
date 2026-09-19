# 02.02 — Context materialization

Tahap ini membuat satu packet konteks per slot dari anchor yang sudah dipilih di 02.01.
Packet bukan hasil top-K retrieval dan bukan gold. Ia adalah seluruh candidate context yang
akan dibaca authoring LLM.

## Input

```text
01-target-corpus-size/01-corpus-eda/question_outline_frame.csv
01-target-corpus-size/01-corpus-eda/question_source_frame.csv
02-question-budget-and-gold/01-question-budget-and-distribution/runs/selection-v1/question-slots.csv
```

`question_outline_frame.csv` menentukan section dan anchor. `question_source_frame.csv`
menyediakan teks canonical, page, sequence, character offset, dan hash. `question-slots.csv`
menyediakan 100 slot; pasangan English–Indonesia memakai packet yang sama.

## Aturan materialisasi

Untuk setiap anchor, script:

1. memverifikasi outline, source ID, dokumen, section, page, offset, dan hash;
2. menemukan nearest parent heading yang valid;
3. mengumpulkan semua descendant block dalam subtree parent, berurutan menurut `block_sequence`;
4. mempertahankan boundary heading, procedure, table/figure, dan continuation block; dan
5. menerapkan soft target 4.000 token serta hard limit 8.000 token agar packet dapat dikirim
   dalam satu request model.

Jika subtree terlalu besar, script membuat deterministic bounded window di sekitar anchor.
Ini adalah batas operasional packet, bukan pemilihan gold. Tidak ada random pick kedua,
retrieval, reranker, intent classifier, atau LLM pada tahap ini.

## Output utama

```text
runs/selection-v2-multiblock/
├── context-selection.csv       # satu row per candidate block
├── context-packets.jsonl       # satu row per slot
└── context-manifest.json
```

Setiap record `context-packets.jsonl` memiliki:

- `candidate_block_ids`: seluruh ID candidate dalam packet;
- `candidate_blocks`: metadata dan teks canonical setiap candidate; dan
- `context_text`: string lengkap berlabel `[CONTEXT BLOCK ...]` yang dikirim utuh ke LLM.

Istilah “seluruh context” di sini berarti seluruh candidate block di packet parent-subtree
slot tersebut, bukan sembilan manual sekaligus. Batas ini menjaga konteks tetap relevan dan
muat dalam satu request model.

Jumlah candidate berbeda antar slot. LLM kemudian memilih `evidence_block_ids` sendiri;
jumlah gold boleh satu atau beberapa block dan tidak dipaksa menjadi dua.

## Gate

Packet boleh diteruskan ke 02.03 jika provenance lulus dan statusnya `ready` atau
`ready_over_soft_limit` (tetap di bawah hard limit). Authoring LLM tidak boleh mengambil teks
di luar `context_text`.
