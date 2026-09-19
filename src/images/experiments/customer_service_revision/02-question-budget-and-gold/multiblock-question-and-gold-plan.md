# Multi-block question dan gold plan

## Tujuan

Run ini mendesain ulang bank pertanyaan Customer Service dengan candidate context lengkap dari
parent section. Sebagian slot akan membutuhkan beberapa block, sementara slot lain dapat
terjawab oleh satu block; LLM yang menentukan evidence set. Aturan lama tetap berlaku:
datasource `netgear-customer-service`, seluruh sembilan manual masuk census, sampling hanya
dilakukan pada leaf outline dengan seed tetap, dan hasil akhir 100 slot bilingual (100 English
+ 100 Indonesia = 200 row).

Run ini tidak menimpa `selection-v1`. Artefak baru harus disimpan sebagai
`selection-v2-multiblock` agar pertanyaan single-block lama tetap menjadi baseline audit.

## Perubahan dari `selection-v1`

| Concern | `selection-v1` | `selection-v2-multiblock` |
|---|---|---|
| Unit sampling | leaf outline | leaf outline yang sama dan reproducible |
| Context authoring | satu direct leaf block | nearest parent subtree yang bounded |
| Evidence gold | satu block | satu atau lebih block jika memang diperlukan |
| Pemilihan evidence | subset dari satu packet | Authoring LLM memilih subset dari `context_text` lengkap |
| Validasi | quote dan provenance | structural ID/provenance saja; jumlah evidence bebas |
| Retrieval/OAT/OFAT | belum digunakan | tetap belum digunakan pada proses question/gold |

Menambah block secara artifisial tidak diperbolehkan. Jika jawaban dapat lengkap dengan satu
block, model boleh memilih satu block itu. Nama `selection-v2-multiblock` merujuk pada
candidate context yang kaya, bukan kewajiban bahwa setiap gold harus memiliki dua block.

## Kontrol yang dipertahankan

- 100 slot dan dua row bahasa untuk setiap slot (`question_pair_id` sama).
- Quota family tetap 50 row per family: fakta, setup, troubleshooting, dan fitur/keamanan/
  pemeliharaan/limitasi.
- Sampling hanya dari `question_outline_frame.csv`; `question_source_frame.csv` adalah lookup
  teks dan provenance, bukan pool sampling kedua.
- Random pick memakai seed `20260831` dan strata struktural `document × page_bin`.
- Wording harus customer-facing, awam, dan tidak membocorkan ID internal.
- Tidak ada reranker, intent classifier, knowledge graph, atau retrieval dalam authoring; slot tidak dipakai sebagai label intent.
- Database/object-storage audit tetap wajib sebelum authoring model menerima context.

## Input frozen

```text
01-target-corpus-size/01-corpus-eda/
├── question_outline_frame.csv
├── question_source_frame.csv
└── transition/{corpus-manifest.json,summary.json}

01-question-budget-and-distribution/runs/selection-v1/
├── candidate-pool.csv
└── question-slots.csv
```

`question-slots.csv` tetap menjadi daftar 100 slot dan 200 language row. Jika anchor baru
dipilih, buat run budget baru dengan seed dan allocation report yang dicatat; jangan mengubah
file frozen `selection-v1`.

## Pemilihan candidate context

Candidate context bukan hasil top-K retrieval. Ia dibuat sebelum question authoring dari source
frame yang sama.

Untuk setiap anchor outline:

1. Resolve `outline_frame_id`, `document_id`, `section_path`, dan direct anchor block.
2. Resolve nearest semantic parent heading melalui `parent_heading_ids`; root dokumen tidak
   dipakai sebagai parent authoring.
3. Kumpulkan descendant `TEXT_BLOCK` dalam subtree parent, diurutkan oleh `block_sequence`.
4. Sertakan continuation procedure, child table/figure, dan block yang bersebelahan jika masih
   berada pada section yang sama.
5. Berhenti pada sibling heading dengan level yang sama/lebih tinggi, section boundary, atau
   hard limit 8.000 token. Soft target tetap sekitar 4.000 token.
6. Jika subtree terlalu besar, gunakan bounded window deterministik di sekitar anchor sampai
   hard limit. Jangan mengambil block dari dokumen lain secara diam-diam.

Parent heading dipakai sebagai label/context. Parent hanya boleh menjadi gold jika memiliki
teks faktual yang memang dikutip; heading kosong atau boilerplate tetap context-only.

Setiap candidate dicatat dalam `context-selection.csv` dengan `candidate_role` seperti
`anchor`, `procedure_child`, `table_figure_companion`, atau `supporting_child`. Packet boleh
memiliki lebih banyak candidate daripada gold; authoring model memilih evidence minimal yang diperlukan.

## Kontrak authoring LLM

Authoring menerima seluruh `context_text` dari packet yang sudah dimaterialisasi, bukan hanya
anchor dan satu sibling. Model menulis pertanyaan customer-facing, reference answer bilingual,
dan memilih evidence minimal yang benar-benar diperlukan. Jumlah evidence tidak ditetapkan:
model boleh memilih satu, dua, atau beberapa block. Python hanya memeriksa bentuk data,
keberadaan ID di packet, dan provenance; Python tidak memaksa jumlah block atau memilih evidence.

```json
{
  "question_pair_id": "Q-001",
  "question_en": "How do I turn this feature on?",
  "question_id": "Bagaimana cara mengaktifkan fitur ini?",
  "reference_answer_en": "...",
  "reference_answer_id": "...",
  "evidence_block_ids": ["BLOCK-A"],
  "evidence_rationale": "This block fully answers the slot question."
}
```

Pertanyaan English dan Indonesia untuk satu `question_pair_id` harus mempertahankan slot,
reference answer, dan set evidence yang sama. Pertanyaan wajib memakai bahasa umum; nama menu,
protokol, atau istilah teknis hanya dipakai jika memang diperlukan untuk membedakan tindakan.

`generate_multiblock_question_candidates.py` mengirim satu `context_text` lengkap per packet ke
endpoint OpenAI-compatible yang dipilih eksplisit melalui `--base-url`, `--api-key`, dan
`--model`. Tidak ada pengiriman otomatis; command hanya berjalan jika kredensial dan model
diberikan oleh operator.

## Validasi evidence dan multi-block

Authoring model menerima seluruh packet; Python validator hanya memeriksa hal yang deterministik:

- semua `block_id` dan `source_frame_id` ada di packet;
- selected IDs menunjuk source block yang benar;
- page, character offset, dan `text_sha256` cocok;
- satu atau lebih block gold yang dipilih model; jumlahnya boleh berbeda antar pertanyaan;
- tidak ada duplicate block ID;
- pasangan EN–ID memiliki evidence set yang sama;
- jumlah akhir tepat 200 row dan quota family/language tetap terpenuhi.

Gold berisi canonical `block_id`, quote, offset, page, dan hash. Gold tidak berisi `chunk_id`,
index ID, parent ID yang hanya dipakai sebagai metadata, atau seluruh isi candidate packet.

Draft model disimpan sebagai
`03-question-generation-and-gold/runs/selection-v2-multiblock/00-draft/llm-question-candidates.jsonl`.
Satu record mewakili satu `question_pair_id` dan memuat pertanyaan EN, pertanyaan Indonesia,
reference answer, evidence IDs pilihan model, rationale, serta status provenance. Jumlah evidence
tidak dipaksa sama antar record; full context tetap direferensikan melalui packet `context_text`.

## Scoring retrieval setelah gold frozen

`source_block_ids` tetap dipertahankan sebagai provenance setiap chunk. Recall memakai union
provenance hanya untuk menghitung coverage block gold; precision dan NDCG tetap memakai chunk
sebagai unit. Definisi executable yang sama untuk semua run ada di
[`03-implementation/metrics-and-scoring.md`](../03-implementation/metrics-and-scoring.md).

Untuk `gold_ids` dan `prefix = retrieval_candidates[:K]`:

```text
hit(chunk) = bool(set(chunk.source_block_ids) ∩ gold_ids)
retrieved_source_ids = union(chunk.source_block_ids for chunk in prefix)
gold_block_recall@K = |retrieved_source_ids ∩ gold_ids| / |gold_ids|
chunk_precision@K = jumlah hit(chunk) / jumlah chunk pada prefix
chunk_NDCG@K = NDCG flag hit(chunk) berdasarkan urutan chunk
```

Prefix tidak dipadding jika API mengembalikan kurang dari K. Ideal list NDCG dibentuk dari
candidate pool yang benar-benar dikembalikan. `exact_gold_block_hit` dan jumlah unique source
ID hanya diagnostic; keduanya tidak menjadi scorecard utama.

## Output run

```text
02-context-materialization/runs/selection-v2-multiblock/
├── context-selection.csv
├── context-packets.jsonl
└── context-manifest.json

03-question-generation-and-gold/runs/selection-v2-multiblock/
├── 00-draft/
├── 01-candidates/question-candidates.jsonl
├── 02-review/question-review.csv
└── 03-frozen/
    ├── question-set.csv
    ├── question-context.jsonl
    ├── gold-evidence.jsonl
    ├── generation-checkpoints.json
    └── annotation-manifest.json
```

Manifest wajib mencatat input hash, seed, parent-subtree rule, token limits, revisi sesi Codex,
jumlah block candidate per packet, jumlah gold block per question, dan alasan rejection.

## Gate sebelum OAT/OFAT

OAT/OFAT hanya boleh memakai run ini jika:

1. datasource dan sembilan dokumen cocok dengan audit database/object storage;
2. 100 slot dan 200 row bilingual sudah frozen;
3. seluruh packet berstatus `ready` dan berada di bawah hard token limit;
4. setiap evidence set berisi block yang benar-benar diperlukan; jumlahnya boleh berbeda antar pertanyaan;
5. quote, offset, page, hash, dan claim mapping lulus validator;
6. scorer baru sudah deterministic dan diuji pada fixture multi-block; serta
7. v1 dan v2 dilaporkan sebagai benchmark terpisah, bukan dicampur dalam satu aggregate.

## Prinsip keputusan

Multi-block dipakai untuk meningkatkan validitas evidence, bukan untuk menaikkan angka recall.
Jika audit menemukan hanya satu block yang diperlukan, pertanyaan tersebut harus tetap
single-block atau diganti dengan slot lain yang secara alami membutuhkan beberapa block.

Pada review Codex saat ini, seluruh 100 packet dibaca dari `context_text` lengkap. Setelah
evaluasi ulang, 16 pasangan memakai satu block, 68 memakai dua block, 13 memakai tiga block,
2 memakai empat block, dan 1 memakai lima block. Jadi keluaran bilingualnya memiliki 32, 136,
26, 4, dan 2 row dengan cardinality tersebut. Multi-block dipakai ketika setiap block menyumbang
fakta, prasyarat, diagnosis, alternatif, atau langkah penyelesaian yang diperlukan dalam satu
alur pertanyaan; kandidat yang tidak relevan tetap tidak dimasukkan ke gold.
