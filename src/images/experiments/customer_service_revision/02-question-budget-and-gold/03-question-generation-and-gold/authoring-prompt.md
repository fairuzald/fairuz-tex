# Prompt authoring question Customer Service

Gunakan satu row `question-slots.csv` dan packet dengan `packet_status=ready` untuk
menulis satu draft JSON object per `question_pair_id`. Model menerima seluruh field
`context_text`, bukan hanya anchor block. Dua bahasa harus menguji intent yang sama.

## Aturan

- Ikuti `question_family` dan `language` pada slot.
- Tulis pertanyaan customer-service yang natural, umum, dan mudah dibayangkan oleh pelanggan awam.
- Hindari memulai pertanyaan dengan menu path, nama protokol, atau istilah internal; detail teknis
  tetap boleh berada di reference answer bila diperlukan oleh manual.
- Tulis `reference_answer` hanya dari packet.
- `evidence_block_ids` harus menunjuk block yang benar-benar diperlukan untuk jawaban.
  Jumlahnya bebas dan tidak boleh dipadding hanya untuk mencapai angka tertentu.
- Jangan menampilkan `block_id`, `source_frame_id`, hash, atau metadata pipeline dalam
  question/answer.
- Jika packet tidak cukup, jangan menebak; tandai untuk review dan jangan masukkan ke
  frozen set.

## Format JSONL

```json
{
  "question_pair_id": "Q-001",
  "question_en": "How can I safely reset my cable modem?",
  "question_id": "Bagaimana cara mereset modem kabel dengan aman?",
  "reference_answer_en": "...",
  "reference_answer_id": "...",
  "evidence_block_ids": ["..."],
  "evidence_rationale": "These blocks jointly describe the reset workflow."
}
```

Output satu file:

```text
02-question-budget-and-gold/03-question-generation-and-gold/runs/selection-v2-multiblock/00-draft/llm-question-candidates.jsonl
```

Validator Python akan memeriksa 100 pair, quota 50/50/50/50, bahasa 100/100,
kesesuaian evidence IDs dengan packet, dan provenance source sebelum membuat `03-frozen/`.
Validator tidak memaksakan jumlah evidence; authoring LLM dipanggil hanya oleh command
`generate_multiblock_question_candidates.py` dengan konfigurasi endpoint eksplisit.
Frozen benchmark saat ini dibuat melalui sesi Codex current model dengan prosedur full-context
yang sama; command endpoint adalah jalur reproducibility opsional dan tidak dipanggil otomatis.
