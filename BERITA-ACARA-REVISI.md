# Daftar Revisi dan Tindak Lanjut Berita Acara Sidang

Dokumen ini merupakan daftar tindak lanjut yang berdiri sendiri dan tidak menjadi
bagian dari berkas PDF laporan. Lokasi yang dicantumkan merujuk pada sumber laporan
di repositori `report-tex` dan artefak eksperimen di repositori `dpo`.

## Tabel tindak lanjut

| No. | Masukan sidang | Tindak lanjut yang terverifikasi | Lokasi revisi | Status pemeriksaan |
|---:|---|---|---|---|
| 1 | Jelaskan apakah sistem menggunakan *Naive RAG* atau *GraphRAG*. | Ditambahkan perbandingan mekanisme kedua pendekatan. Laporan menetapkan OMNI-RAG sebagai *Naive RAG* dengan *knowledge graph* opsional. Pencarian utama tetap berasal dari indeks teks, sedangkan graf berfungsi sebagai pelengkap untuk menelusuri hubungan. | `report-tex/src/chapters/02-Kajian-Pustaka.tex`, subbab `Pembedaan *Naive RAG* dan *GraphRAG*`, label `subsec:naive-vs-graphrag`, serta Gambar `fig:graphrag-framework-literature`. | Terlihat pada *working tree*. Belum ada *commit* khusus untuk catatan ini. |
| 2 | *Generation* tidak dapat dipisahkan dari *retrieval*, sehingga perlu pengujian yang menunjukkan dampak hasil pencarian terhadap jawaban. | Bab IV disusun ulang untuk menghubungkan kedua tahap. Pada *User Manual*, ditambahkan *generation* untuk 100 pertanyaan Inggris dengan K = 10, serta metrik *correctness* dan *faithfulness*. Pada kasus hukum, dataset 25 pertanyaan yang disusun untuk eksperimen dan diverifikasi oleh ahli, *retrieval*, *generation*, dan penilaian jawaban dijalankan dalam alur yang sama. *Retrieval* menggunakan K = 30 sebagai daftar kandidat, sedangkan *generation* menggunakan K = 10 sebagai *evidence*. | `report-tex/src/chapters/04-Rencana-Pelaksanaan.tex`, label `subsec:user-manual-generation`, `subsec:legal-revision-system-updated`, dan gambar *generation* pada masing-masing *use case*. Artefak: `dpo/experiments/offline-rag-experiments/customer_service_revision/final_eda/generation.md`, `dpo/experiments/offline-rag-experiments/legal_revision/final_eda/all-retrieval.md`, serta `dpo/output/rm4-256-current-run/final-k10-luna-high/generation-summary.json`. | Benchmark aktif menggunakan 25 pertanyaan yang disusun untuk eksperimen dan diverifikasi oleh ahli. |
| 3 | Mekanisme pemodelan graf perlu dijelaskan. | Dijelaskan kontrak masukan dan keluaran graf, pembentukan simpul dan sisi deterministik, tipe relasi hukum, pemilihan hasil *top-K* sebagai *seed*, penelusuran relasi sampai kedalaman dua, penyaringan arah dan tipe relasi, deduplikasi, serta pemetaan kembali ke teks parser. Graf tidak menggantikan pencarian teks. | `report-tex/src/chapters/03-Analisis-dan-Rancangan.tex`, subbab `Rancangan *Knowledge Graph Plugin*`, label `subsec:solusi-knowledge-graph`, `subsubsec:kontrak-canonical-graph`, `subsubsec:graph-deterministik`, dan `subsubsec:mekanisme-retrieval-knowledge-graph`. Konfigurasi *plugin* juga dijelaskan di `src/chapters/03-Rancangan-Solusi.tex`. | Terlihat pada *working tree*. |
| 4 | Makna semantik istilah “setiap orang” dapat berbeda dan perlu dijelaskan. | Ditambahkan batasan semantik pada domain hukum. Istilah tersebut dijelaskan dapat merujuk pada orang perseorangan, badan hukum, korporasi, instansi, organisasi, atau kelompok, bergantung pada definisi dan relasi dalam peraturan. Skor *dense* tidak diperlakukan sebagai putusan kesamaan makna hukum. | `report-tex/src/chapters/03-Analisis-dan-Rancangan.tex`, paragraf `Batasan representasi semantik pada domain hukum`, terutama pembahasan istilah “orang”. | Terlihat pada *working tree*. |
| 5 | *Baseline* harus berupa pendekatan paling sederhana yang perlu dikalahkan. | *Sliding-window* ditetapkan sebagai *baseline chunker*. *Structure-aware sparse* ditetapkan sebagai *baseline indexer*. Analisis Bab IV membandingkan konfigurasi yang diusulkan terhadap kedua *baseline* tersebut, termasuk delta *recall* pada tabel dan diagram hasil *sweet spot*. | `report-tex/src/chapters/04-Rencana-Pelaksanaan.tex`, label `subsubsec:user-manual-chunking`, `subsubsec:user-manual-indexing`, `subsec:legal-revision-chunker-updated`, `subsec:legal-revision-indexer-updated`, dan bagian rekap sistem. Penetapan yang sama juga tercantum pada `dpo/experiments/offline-rag-experiments/*/final_eda/README.md`. | Terlihat pada *working tree*. |
| 6 | Sertakan analisis volume *token* terhadap pilihan K, serta analisis K = 1 untuk kasus *Customer Service*. | Ditambahkan diagnosis *top-1* untuk 200 pertanyaan *User Manual*, termasuk jumlah hit per konfigurasi dan alasan K = 1 tidak digunakan sebagai batas operasional. Ditambahkan tabel volume kandidat K = 30 untuk *reranker*, diagram volume *evidence* K = 10 untuk *generation*, dan penjelasan bahwa kedua volume tersebut adalah tahap yang berbeda. | `report-tex/src/chapters/04-Rencana-Pelaksanaan.tex`, label `subsec:user-manual-system-retrieval`, tabel `tab:customer-k1-diagnostic` dan `tab:customer-system-volume`, serta `subsec:user-manual-generation`. Artefak pendukung: `dpo/experiments/offline-rag-experiments/customer_service_revision/final_eda/retrieval.md`, `generation.md`, dan `generation-context-volume.png`. | Terlihat pada *working tree* dan artefak eksperimen. |
| 7 | Gambar terlalu kecil dan tidak terbaca. Tangkapan layar aplikasi perlu menggunakan *light mode*. | Berkas PNG tangkapan layar pada alur *User Manual*, konfigurasi *plugin*, *knowledge graph*, dan pengarsipan diperbarui. Ukuran gambar di sumber LaTeX dipertahankan melalui `width`, `height`, dan `keepaspectratio` agar gambar dapat diperbesar tanpa distorsi. | Aset pada `report-tex/src/images/manual/**` dan pemanggilannya pada `report-tex/src/chapters/03-Rancangan-Solusi.tex`. | Banyak aset PNG berubah pada *working tree*. PDF tidak dibangun ulang dalam pemeriksaan ini, sehingga verifikasi visual terakhir tetap perlu dilakukan pada hasil *render* PDF. |
| 8 | Penjelasan metrik dan interpretasinya perlu diperjelas. | Bab IV menjelaskan *Recall*, *Precision*, *MRR*, *NDCG*, *Correctness*, dan *Faithfulness*, termasuk rumus atau definisi operasional serta arti nilai tinggi dan rendah. *Recall* ditetapkan sebagai metrik utama. *Precision*, *MRR*, dan *NDCG* menjadi metrik pendukung untuk membaca kepadatan dan urutan kandidat. *NDCG* memakai *framework* RAG dengan model `openai/gpt-5.6-luna` dan label relevansi 0, 1, dan 2. | `report-tex/src/chapters/04-Rencana-Pelaksanaan.tex`, subbab `Konfigurasi dan Metodologi Eksperimen` pada *User Manual* dan hukum, serta pembahasan metrik di `report-tex/src/chapters/02-Kajian-Pustaka.tex`. | Penjelasan tersedia. Nama model diseragamkan menjadi `openai/gpt-5.6-luna`. |

## Dasar pemeriksaan Git

Pemeriksaan dilakukan pada dua repositori yang menjadi sumber tabel ini.

| Repositori | *HEAD* yang diperiksa | Ringkasan `git status --short` sebelum dokumen ini dibuat |
|---|---|---:|
| `/home/fairuz/Documents/TA/FR/report-tex` | `1bdf80f Update thesis report, paper, and poster` | 99 berkas berubah, 1 dihapus, 28 belum dilacak |
| `/home/fairuz/Documents/TA/FR/dpo` | `f31dfe60 fix: error pydantic` | 76 berkas berubah, 306 dihapus, 121 belum dilacak |

Riwayat yang relevan menunjukkan adanya pembaruan laporan pada `1bdf80f`,
penyeragaman istilah pada `d0c7a93`, konsolidasi artefak eksperimen pada
`1fba60a6`, pembersihan artefak lama pada `816e29b9`, serta pengembangan eksperimen
*Customer Service* pada `414ba4cb`. Banyak hasil terbaru masih berada pada *working
tree*, sehingga tabel ini membedakan perubahan yang sudah terlihat pada berkas dari
perubahan yang sudah tersimpan sebagai *commit*.

## Catatan konsistensi sebelum finalisasi

1. Blok hukum historis yang tidak lagi dipakai telah dihapus dari Bab IV. Bab tersebut
   kini hanya memuat satu blok hukum aktif dengan label yang digunakan oleh gambar dan tabel.
2. `legal_revision/final_eda/README.md` menetapkan benchmark kanonik 25 pertanyaan
   yang disusun untuk eksperimen dan diverifikasi oleh ahli. Bab IV, lampiran, dan
   artefak analisis menggunakan definisi benchmark yang sama.
3. Nama model pada laporan dan berita acara diseragamkan menjadi
   `openai/gpt-5.6-luna`. Pengaturan *reasoning effort* ditulis terpisah jika diperlukan.
