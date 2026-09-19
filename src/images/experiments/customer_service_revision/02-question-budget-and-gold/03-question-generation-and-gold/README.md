# 02.03 — Question generation dan gold

Tahap ini mengirim `context_text` lengkap dari setiap packet ke authoring LLM. Model menulis
satu pasangan pertanyaan customer-facing dalam English dan Indonesia, reference answer, lalu memilih sendiri
block evidence yang benar-benar diperlukan. Jumlah evidence boleh satu atau beberapa block;
tidak ada aturan “tepat dua”.

## Input

```text
../01-question-budget-and-distribution/runs/selection-v1/question-slots.csv
../02-context-materialization/runs/selection-v2-multiblock/context-packets.jsonl
../02-context-materialization/runs/selection-v2-multiblock/context-manifest.json
```

Satu packet dipakai bersama oleh dua bahasa pada `question_pair_id` yang sama. `context_text`
adalah string lengkap berlabel yang berisi semua candidate block hasil materialisasi. “Lengkap”
berarti seluruh context packet untuk slot itu, bukan seluruh sembilan manual sekaligus. LLM
tidak boleh mengambil teks di luar string tersebut.

## Authoring command

```bash
python generate_multiblock_question_candidates.py \
  --base-url "$LLM_QUESTION_BASE_URL" \
  --api-key "$LLM_QUESTION_API_KEY" \
  --model "$LLM_QUESTION_MODEL"
```

Endpoint, API key, dan model harus diberikan eksplisit oleh operator. Command menghasilkan:

```text
runs/selection-v2-multiblock/00-draft/
├── llm-question-candidates.jsonl
└── llm-authoring-summary.json
```

Frozen run yang dipakai benchmark ini diauthoring di sesi Codex current model setelah seluruh
`context_text` dibaca. Command di atas adalah jalur reproducibility opsional; retrieval/OAT/OFAT
tidak memanggil endpoint eksternal.

Satu record draft berisi `question_pair_id`, pertanyaan EN/ID, reference answer EN/ID,
`evidence_block_ids`, dan rationale. Model bebas memilih ukuran evidence set, tanpa padding.

## Kontrak dan safety check

Python tidak memilih evidence dan tidak memaksakan cardinality. Ia hanya menolak keluaran yang
secara struktural tidak aman: evidence kosong, duplicate ID, ID di luar packet, field wajib
kosong, atau provenance source tidak cocok. Check ini menjaga traceability dan bukan penilaian
semantik terhadap pilihan model.

Finalizer:

```bash
python finalize_multiblock_questions.py
```

Finalizer membuat:

```text
runs/selection-v2-multiblock/
├── 01-candidates/question-candidates.jsonl
├── 02-review/question-review.csv
└── 03-frozen/
    ├── question-set.csv          # hanya evidence_block_ids; tidak ada context_block_ids
    ├── question-context.jsonl    # full context_text + candidate IDs + model evidence IDs
    ├── gold-evidence.jsonl       # selected evidence, quote, page, offset, hash
    ├── generation-checkpoints.json
    └── annotation-manifest.json
```

`question-context.jsonl` sengaja menyimpan full context dan selected evidence secara terpisah:
candidate context tetap lengkap untuk audit, sedangkan `evidence_block_ids` adalah keputusan
model yang dipakai scorer. Artefak fixed-two lama hanya audit history dan tidak boleh dipakai
untuk OAT/OFAT.

## Relevance audit

`audit_question_evidence_relevance.py` memeriksa 100 pasangan dan 200 row bilingual. Audit
memastikan ID evidence ada di packet yang sama dan dokumen yang sama, ID English/Indonesia
identik, quote/hash/offset cocok dengan source frame, serta setiap block memiliki overlap
content-token dengan pertanyaan atau jawaban. Hasil frozen saat ini `pass=100`, tanpa row
yang perlu review; laporan per pasangan ada di `03-frozen/question-evidence-relevance-audit.md`.

## Hasil pass Codex saat ini

Seluruh 100 packet (942 candidate block) dibaca dari `context_text`. Gold tidak memakai jumlah
block tetap: 16 pasangan memakai satu block, 68 memakai dua block, 13 memakai tiga block, 2
memakai empat block, dan 1 memakai lima block. Karena setiap pasangan memiliki dua bahasa,
frozen output berisi 32, 136, 26, 4, dan 2 row dengan cardinality tersebut. Block tambahan hanya
dipertahankan jika menyumbang bagian yang diperlukan dari satu alur jawaban; candidate yang tidak
relevan tetap context-only.
