# Rencana implementasi retrieval Customer Service

## Keputusan struktur

Implementasi memiliki dua lane yang tidak dicampur:

| Lane | Peran | Status |
|---|---|---|
| `single-block` | Keputusan final retrieval | Aktif |
| `multiblock` | Benchmark dan audit historis | Dipertahankan |

Single-block memakai satu gold block canonical per pertanyaan. Multiblock tetap tersedia
untuk membandingkan perilaku evidence variable-size, tetapi angkanya tidak dipakai untuk
memilih profile final.

## Kontrol yang dibekukan

- Datasource `netgear-customer-service` dengan 9/9 PDF yang sama.
- 200 pertanyaan frozen: 100 English dan 100 Indonesian; `question_pair_id` berpasangan.
- Gold dan checksum tidak berubah selama run.
- Lima profile existing pada [`existing-profile-map.json`](existing-profile-map.json).
- Parser dan konfigurasi retrieval mengikuti [`configuration-matrix.md`](configuration-matrix.md).
- `use_reranker=false`, intent passthrough, LLM answer generation deterministic, dan `kg=none`.

## Eksekusi single-block

Runner [`scripts/run_e2e.py`](scripts/run_e2e.py) dijalankan dengan `--metric-mode single-block`
dan `--profile-map`, sehingga profile hanya divalidasi lalu dipakai untuk chat retrieval.
Tidak ada pembuatan profile atau `POST /sync`.

Setiap trace menyimpan hingga 60 candidate chunk dalam urutan ranking. Sebuah chunk adalah
hit bila:

```python
bool(set(chunk["source_block_ids"]) & set(gold_block_ids))
```

Satu chunk dihitung satu kali walaupun membawa beberapa provenance ID. Kontrak scoring lengkap
ada di [`metrics-and-scoring.md`](metrics-and-scoring.md); ringkasnya:

```python
chunk_precision@K = hit_chunks / K
chunk_success@K = int(hit_chunks > 0)
gold_block_recall@K = len(found_gold_blocks & gold_block_ids) / len(gold_block_ids)
chunk_ndcg@K = binary ranked hit NDCG
```

Grid cutoff adalah `K=5,10,15,20,25,30,35,40,45,50,55,60`. Karena gold hanya satu block,
success dan recall sama pada level pertanyaan. Precision tetap memakai denominator K walaupun
API mengembalikan lebih sedikit candidate.

## Analisis single-block

Analyzer [`scripts/analyze_single_block_retrieval.py`](scripts/analyze_single_block_retrieval.py)
menghasilkan:

- metrik overall untuk setiap profile dan cutoff;
- analisis terpisah English dan Indonesian untuk keempat metrik pada seluruh cutoff;
- kurva precision, success, recall, dan NDCG;
- split English/Indonesian serta delta berpasangan ID−EN;
- breakdown question family dan product model;
- `question_pair_id` metrics untuk konsistensi bilingual;
- first-hit rank, MRR, no-hit rate, candidate-pool size, median/P90 latency;
- metrik setiap `question_id` tanpa menyimpan ulang candidate payload pada CSV analisis;
- diagram condition pada K=10/K=60, heatmap product, CDF first-hit, dan precision–recall trade-off.

Artefak final berada di [`runs/single-block/analysis/analysis-report.md`](runs/single-block/analysis/analysis-report.md).

Sweet spot cutoff dihitung di [`runs/single-block/analysis/k-sweet-spot-report.md`](runs/single-block/analysis/k-sweet-spot-report.md): delta recall K→K+5 harus ≤2 percentage points dan 95% paired-bootstrap CI mencakup nol pada seluruh transisi setelah cutoff tersebut. NDCG memakai guardrail praktis ≤1 point. English dan Indonesian dihitung terpisah.

## Benchmark multiblock

Raw dan hasil multiblock tidak dihapus. Artefaknya berada di [`runs/multiblock/`](runs/multiblock/)
dan tetap dapat diaudit melalui `analysis/` serta `analysis/secondary/` untuk OFAT dan cutoff
chunker/indexer. Lane ini memakai gold evidence variable-size dan denominator precision
`hit_chunks / returned prefix`, sehingga tidak boleh dibandingkan langsung dengan single-block.

## Gate dan keputusan

1. Input question/gold harus frozen dan berjumlah 200 row dengan 100 row per bahasa.
2. Semua gold row harus memiliki tepat satu evidence block untuk lane single-block.
3. Setiap kondisi wajib memiliki 200 trace valid dan datasource 9/9 succeeded.
4. Tidak boleh ada indexing ulang ketika memakai profile map existing.
5. Report wajib memuat `language-by-cutoff.csv` dan tabel EN/ID terpisah; run tanpa salah satu
   bahasa dianggap tidak lengkap.
6. Profile final dipilih dari metrik single-block dengan mempertimbangkan recall/success,
   NDCG, precision, language gap, first-hit rank, latency, dan product/family coverage.
7. Multiblock hanya digunakan sebagai audit sensitivitas, bukan sebagai scorecard final.

Aturan bahasa berlaku untuk kedua lane: semua laporan harus menyertakan English dan Indonesian
secara terpisah pada seluruh cutoff, selain agregat gabungan.
