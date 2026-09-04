# Definisi metrik retrieval

Kontrak lintas domain untuk membandingkan structure-aware dengan Legal ada di
[`structure-aware-comparison`](../../structure-aware-comparison/README.md).

Dokumen ini adalah kontrak scoring untuk dua lane retrieval Customer Service Revision.
Angka pada laporan canonical dihitung dengan definisi di bawah; laporan lama dengan kontrak
berbeda tidak boleh dibandingkan.

## Unit yang dibandingkan

- `gold_ids` adalah himpunan `block_id` canonical dari `gold-evidence.jsonl` untuk satu
  pertanyaan. Ukurannya boleh 1, 2, 3, dan seterusnya sesuai evidence yang dipilih saat
  authoring; tidak ada padding fixed-two.
- `candidates` adalah daftar chunk retrieval yang sudah diurutkan API berdasarkan ranking.
  Satu chunk dapat memiliki beberapa `source_block_ids` (misalnya parent dan leaf).
- `prefix = candidates[:K]` adalah maksimal K chunk pertama. Jika API hanya mengembalikan lebih
  sedikit chunk, skor memakai chunk yang benar-benar dikembalikan; hasil tidak dipadding.
- `hit(chunk)` bernilai benar jika **salah satu** `source_block_ids` chunk beririsan dengan
  `gold_ids`. Ini adalah status relevansi sebuah chunk, bukan unit recall.

## Rumus yang dipakai

```python
prefix = [c for c in retrieval_candidates[:K] if isinstance(c, dict)]
gold_ids = {e["block_id"] for e in gold_evidence}

def hit(chunk):
    return bool(set(chunk["source_block_ids"]) & gold_ids)

retrieved_source_ids = set().union(
    *(set(c["source_block_ids"]) for c in prefix)
)
matched_gold_ids = retrieved_source_ids & gold_ids
hit_chunks = sum(hit(c) for c in prefix)

gold_block_recall_at_k = len(matched_gold_ids) / len(gold_ids) if gold_ids else 0.0
chunk_precision_at_k = hit_chunks / len(prefix) if prefix else 0.0
```

Jika `gold_ids` atau `prefix` kosong, metrik yang pembaginya kosong bernilai `0.0` dan
`retrieval_empty` tetap dilaporkan sebagai diagnostic. Dengan demikian:

- **Gold-block recall@K** mengukur proporsi block gold yang tercakup oleh seluruh provenance
  chunk pada prefix. Satu chunk bisa menemukan beberapa gold block, tetapi setiap gold block
  dihitung paling banyak sekali.
- **Chunk precision@K** mengukur proporsi chunk yang relevan dari chunk yang benar-benar kembali:
  `jumlah hit_chunks / jumlah prefix`. Chunk duplikat tetap dihitung sebagai chunk berbeda karena
  precision menilai noise pada daftar hasil.
- **Chunk NDCG@K** memakai flag relevansi biner `hit(chunk)` pada urutan chunk. DCG memakai
  prefix pertama, sedangkan ideal list dibentuk dari seluruh candidate pool yang dikembalikan,
  lalu diambil K teratas. NDCG ini menilai kualitas urutan chunk, bukan ranking flattened
  `source_block_ids`.

`exact_gold_block_hit`, jumlah chunk, jumlah hit chunk, dan jumlah unique source ID hanya
diagnostic; nilai tersebut bukan scorecard utama.

### Contoh singkat

Jika `gold_ids={A,B,C}` dan tiga chunk pertama memiliki provenance `[X,A]`, `[Y]`, dan `[B,C]`,
maka dua chunk adalah hit, `chunk_precision@3 = 2/3`, dan semua tiga gold block tercakup sehingga
`gold_block_recall@3 = 3/3`. Flag NDCG-nya adalah `[1,0,1]`; ia membandingkan posisi chunk hit
dengan urutan ideal `[1,1,0]`.

## Kontrak khusus single-block

Run baseline single-block memakai frozen question set `selection-v1`. Setiap pertanyaan
memiliki tepat satu `gold_id`, sehingga `gold_block_recall@K` dan `chunk_success@K`
menjadi nilai biner per pertanyaan, lalu dirata-ratakan pada laporan. Kontrak ini sengaja
memakai denominator K yang diminta untuk sweep cutoff:

```python
prefix = [c for c in retrieval_candidates[:K] if isinstance(c, dict)]
hit_chunks = sum(hit(c) for c in prefix)

chunk_precision_at_k = hit_chunks / K
chunk_success_at_k = int(hit_chunks > 0)
gold_block_recall_at_k = len(matched_gold_ids) / len(gold_ids) if gold_ids else 0.0
chunk_ndcg_at_k = chunk_ndcg(retrieval_candidates, gold_ids, K)
```

`chunk_precision@K` tetap dibagi K walaupun API mengembalikan kurang dari K kandidat;
trace kosong bernilai nol. Ini berbeda dari kontrak multiblock di atas yang memakai
`hit_chunks / len(prefix)`. Run dan analisisnya adalah:

- Raw retrieval: `runs/single-block/raw-e2e-existing-k60/`.
- Analisis dan diagram: `runs/single-block/analysis/`.
- Reproducible analyzer: `scripts/analyze_single_block_retrieval.py`.

## Interpretasi dan pelaporan

Recall dan precision sengaja memakai unit berbeda: recall memakai coverage block gold, sedangkan
precision memakai chunk hasil retrieval. Karena itu precision dapat turun saat K bertambah walau
recall naik. Semua hasil wajib dilaporkan pada K=`5,10,15,20,25,...,60`, overall, English, Indonesian,
family, produk, dan `question_pair_id`; English dan Indonesian tidak boleh hanya digabung menjadi
satu rata-rata. Perbandingan OFAT selalu matched: chunker dibandingkan
dengan indexer hybrid yang sama, dan indexer dibandingkan dengan chunker structure-aware yang
sama.

Tidak ada LLM generation saat retrieval/OAT/OFAT, tidak ada reranker atau intent classifier,
dan tidak ada knowledge-graph metric. Gold tetap berasal dari evidence canonical yang diaudit;
`chunk_id` hanya identitas hasil retrieval.
