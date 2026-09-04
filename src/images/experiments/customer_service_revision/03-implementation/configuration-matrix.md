# Matriks konfigurasi Customer Service

Semua baris memakai datasource `netgear-customer-service`, 200 question row yang sama,
100 pasangan bahasa, `use_reranker=false`, dan `kg=none`. OAT mengubah embedding saja;
OFAT mengubah satu chunker atau indexer setelah embedding winner core dibekukan.

Baris OAT di bawah dipertahankan sebagai catatan preflight. Lane eksekusi final saat ini
adalah single-block dengan lima profile existing; benchmark multiblock disimpan terpisah
di `runs/multiblock/`.

| Tahap | ID | Embedding | Chunker | Indexer | KG | Gate |
|---|---|---|---|---|---|---|
| OAT core | `oat-qwen3` | `Qwen/Qwen3-Embedding-0.6B` | generic-structure-aware | dense-semantic | none | wajib |
| OAT core | `oat-bge-m3` | `BAAI/bge-m3` | generic-structure-aware | dense-semantic | none | wajib |
| OAT research | `oat-jina-v5-small-retrieval` | `jinaai/jina-embeddings-v5-text-small-retrieval` | generic-structure-aware | dense-semantic | none | license + runtime + operational |
| OFAT baseline | `baseline-generic-hybrid` | pemenang core | generic-structure-aware | hybrid-semantic-keyword | none | OAT winner frozen |
| OFAT chunker | `chunker-generic-recursive` | pemenang core | generic-recursive | hybrid-semantic-keyword | none | hanya chunker berubah |
| OFAT chunker | `chunker-generic-sliding-window` | pemenang core | generic-sliding-window | hybrid-semantic-keyword | none | hanya chunker berubah |
| OFAT indexer | `indexer-generic-sparse` | pemenang core | generic-structure-aware | sparse-keyword | none | hanya indexer berubah |
| OFAT indexer | `indexer-generic-dense` | pemenang core | generic-structure-aware | dense-semantic | none | hanya indexer berubah |

## Konfigurasi chunker acuan

```text
target_level: text_block
include_parent_context: true
size_unit: character
max_size: 512
```

Nilai ini dibekukan untuk OAT. Pada OFAT chunker, parameter masing-masing plugin dicatat
di manifest dan tidak boleh berubah di tengah run.

## Kontrak scorecard

Definisi lengkap ada di [`metrics-and-scoring.md`](metrics-and-scoring.md). Scorecard memakai
**gold-block recall@K** (coverage semua gold block), **chunk precision@K** (hit chunk dibagi
chunk yang benar-benar kembali), dan **chunk NDCG@K** (ranking chunk biner). Grid K adalah
`5,10,15,20,25,...,60`; K=10 dipakai sebagai titik keputusan utama dan seluruh kurva dipakai
untuk melihat plateau serta trade-off noise. Jumlah chunk kembali, hit chunk, latency, empty
rate, dan valid trace rate adalah diagnostic operasional. Semua metrik dikelompokkan minimal
menurut `language`, `question_family`, `product_model`, dan `question_pair_id`.

Tidak ada kolom, output, atau evaluasi KG. Jika kode umum memiliki field KG, nilainya harus
`none`/kosong dan `llm_graph_tested=false`; jangan menambahkan metrik graph baru atau
mengganti evidence retrieval dengan graph score.
