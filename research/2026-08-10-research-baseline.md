# Baseline Riset Terverifikasi

## Status

- **Tanggal:** 2026-08-10
- **Status:** `PARTIAL` dan siap dipakai sebagai baseline audit, belum sebagai hasil eksperimen.
- **Batas audit:** implementasi yang tersedia pada `../dpo`, `../admin-fe`, dan `../fe`, serta proposal/laporan pada workspace ini.
- **Aturan atribusi:** DPO dan Query Pre-Planning dipisahkan dari komponen Capstone yang lebih luas.

## Ringkasan temuan terverifikasi

| Area | Bukti implementasi utama | Kesimpulan yang aman |
|---|---|---|
| Chunking | `../dpo/src/plugins/chunkers/legal_pasal/plugin.py:59-715`; `../dpo/src/plugins/chunkers/__init__.py` | Tersedia chunking hierarchy-aware Pasal–Ayat dengan parent `context`, child `retrieval`, overlap ayat, dan recursive fallback. Belum ada bukti konfigurasi runtime final atau keunggulan akurasi. |
| Indexing/retrieval | `../dpo/src/plugins/indexers/legal_pasal/plugin.py:50-430`; `../dpo/src/plugins/retrieval_orchestrators/legal_hybrid/plugin.py:56-311` | Tersedia channel dense dan lexical, fusion RRF, opsi reranking, parent hydration, dan metadata filter. Model/provider aktif dan hasil qrels belum dibekukan. |
| Knowledge Graph | `../dpo/src/plugins/kg/legal_graph/plugin.py:43-304`; `../dpo/src/infrastructure/knowledge_graph/neo4j_kg_relation_retriever.py:21-134` | Tersedia builder rule-based, opsi LLM graph, artifact Neo4j, dan bounded traversal. Akurasi graph/path serta builder aktif pada profile belum terbukti. |
| PII Query Pre-Planning | `../dpo/src/modules/rag/preprocessor/application/services/preprocessing_service.py:37-140`; `../dpo/src/modules/rag/preprocessor/adapters/privacy/presidio.py:25-209` | Query dinormalisasi, diberi guardrail, dianonimkan sebelum intent/retrieval, lalu dapat dipulihkan pada output. Default yang terverifikasi memakai model spaCy Inggris; fallback no-op tersedia. Recall, leakage, encryption, TTL, dan access control belum terbukti. |
| History compactor | `../dpo/src/modules/rag/chat/application/session_memory/compactor.py:27-194`; `../dpo/src/modules/rag/chat/application/use_cases/chat_service.py:90-216` | Ada token-triggered compaction, recent window, summary/memory-item persistence, timeout, dan fallback deterministik. Wiring LLM summarizer aktif belum terbukti; komponen ini bukan otomatis kontribusi individual. |

## Batas kontribusi individual

Kontribusi individual yang dapat dipertahankan dari bukti saat ini adalah:

1. **DPO:** analisis dan/atau implementasi pipeline pemrosesan dokumen yang benar-benar ditugaskan, termasuk kontrak, plugin, artifact, dan integrasi yang dapat ditelusuri.
2. **Query Pre-Planning:** alur preprocessing query, guardrail, sanitasi PII, dan penggunaan query tersanitasi untuk intent/retrieval, sesuai batas yang dibuktikan pada kode.
3. **Bukan klaim otomatis:** seluruh chatbot, frontend, KG explorer, generation, XAI, atau history compactor. Khusus history compactor, kepemilikan harus dikonfirmasi sebelum masuk sebagai kontribusi tesis (`research/component-history-compactor.md:144`).

## Kontradiksi penting

- Proposal/laporan menggambarkan RCS atau segmentasi semantik, sedangkan implementasi chunking yang ditemukan adalah parent–child berbasis struktur legal dengan recursive fallback (`research/component-chunking.md:138-139`).
- Proposal memakai istilah “sparse embedding”, sedangkan implementasi legal memakai lexical text dan OpenSearch `multi_match` (`research/component-indexing.md:110`).
- Default KG adalah `llm-graph`, sementara manifest retrieval legal kompatibel eksplisit dengan `legal-graph`; profile aktif diperlukan (`research/component-knowledge-graph.md:29,124`).
- Proposal menyebut NER Bahasa Indonesia, tetapi konfigurasi Presidio yang ditemukan menggunakan `en_core_web_sm` dan recognizer custom berbahasa Inggris (`research/component-pii-sanitization.md:28`).
- Nama compactor menunjukkan abstractive summarization, tetapi `ChatService` yang diaudit tidak memasok callback LLM sehingga fallback aktif pada jalur tersebut (`research/component-history-compactor.md:41,137`).

## Data yang masih hilang

- Profile/runtime snapshot: plugin, version, model/provider, parameter, dan capability aktif.
- Korpus final, versi/tanggal akses dokumen, qrels, anotasi boundary, gold graph, dan dataset PII legal Indonesia.
- Hasil eksperimen: Recall/Precision/MRR/nDCG, parent completeness, graph precision/recall, PII precision/recall/leakage, retention/factuality memory, latency, dan biaya.
- Bukti keamanan mapping PII: enkripsi, TTL, authorization, audit access, scope isolation, serta kebijakan provider eksternal.

## Verifikasi tambahan pada baseline

- Metadata dan DOI LoCoMo terkonfirmasi pada ACL Anthology: https://aclanthology.org/2024.acl-long.747/.
- Metadata LexID terkonfirmasi melalui DOI/laman jurnal: https://doi.org/10.21609/jiki.v16i1.1096.
- UU No. 27 Tahun 2022 dan ringkasan cakupannya terkonfirmasi pada JDIH BPK: https://peraturan.bpk.go.id/Details/229798. Sumber ini mendukung dasar hukum, bukan kepatuhan implementasi.
- Metadata BM25 terkonfirmasi pada DOI publisher: https://doi.org/10.1561/1500000019.
- Test suite DPO belum dapat dijalankan di environment saat ini. Tanpa `PYTHONPATH=src`, import package gagal; dengan `PYTHONPATH=src`, collection berhenti karena dependency `pydantic` tidak terpasang. Ini adalah keterbatasan environment, bukan bukti test gagal secara fungsional.

## Langkah riset berikutnya

1. Bekukan profile/runtime dan artefak input sebelum mengumpulkan angka.
2. Siapkan qrels legal Indonesia, gold graph, anotasi boundary, dan dataset PII sintetis beranotasi.
3. Jalankan ablation chunker/retriever/KG serta uji privacy–utility dengan konfigurasi yang dicatat.
4. Perbaiki metadata bibliografi yang sudah ditandai pada `research/2026-08-10-literature-review-rag-legal-kg.md:151-160` sebelum memasukkan referensi ke tesis.
5. Siapkan environment DPO sesuai dependency proyek, lalu ulangi test kontrak sebagai verifikasi regresi terpisah dari benchmark penelitian.

## Berkas audit terkait

- `research/2026-08-09-implementation-audit.md`
- `research/2026-08-10-literature-review-rag-legal-kg.md`
- `research/component-chunking.md`
- `research/component-indexing.md`
- `research/component-knowledge-graph.md`
- `research/component-pii-sanitization.md`
- `research/component-history-compactor.md`

**Perubahan tesis/bibliografi:** tidak dilakukan.
