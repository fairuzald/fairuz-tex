# Single-block — lane final

Lane ini adalah hasil yang dipakai untuk keputusan retrieval Customer Service Revision.
Satu pertanyaan memiliki satu gold block canonical; chunk dianggap hit jika salah satu
`source_block_ids`-nya sama dengan gold block.

- Raw retrieval: [`raw-e2e-existing-k60/`](raw-e2e-existing-k60/)
- Full analysis: [`analysis/analysis-report.md`](analysis/analysis-report.md)
- Cutoff curves: [`analysis/retrieval-quality-by-cutoff.png`](analysis/retrieval-quality-by-cutoff.png)
- Language curves: [`analysis/language-quality-by-cutoff.png`](analysis/language-quality-by-cutoff.png)
- Language metrics: [`analysis/language-by-cutoff.csv`](analysis/language-by-cutoff.csv)
- K sweet-spot analysis: [`analysis/k-sweet-spot-report.md`](analysis/k-sweet-spot-report.md)
- Paired language deltas: [`analysis/language-paired-delta-at-k10-k60.png`](analysis/language-paired-delta-at-k10-k60.png)
- Per-question metrics: [`analysis/question-metrics.csv`](analysis/question-metrics.csv)

Semua cutoff `K=5,10,15,...,60` dihitung. Precision selalu `hit_chunks / K`,
termasuk ketika API mengembalikan kurang dari K kandidat.
English dan Indonesian selalu dianalisis sebagai dua kelompok terpisah; angka gabungan
tidak menggantikan laporan per bahasa.

Sweet spot K memakai delta recall berpasangan pada transisi K→K+5, confidence interval
bootstrap, dan guardrail NDCG; detailnya ada di report sweet-spot.
