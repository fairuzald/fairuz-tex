# Poster Tugas Akhir Omni-RAG

Poster bahasa Indonesia satu halaman, A1 potret (594 × 841 mm), dengan diagram dan grafik vektor. PDF dapat dicetak pada ukuran asli. PNG adalah pratinjau, bukan berkas utama untuk pencetakan.

Jalankan `make poster` dari root repository, atau `make preview` dari folder ini untuk membuat PDF dan PNG. Kebutuhan: Python 3, ReportLab, font DejaVu Sans, dan Poppler untuk pratinjau. Python dapat dipilih dengan `make poster PYTHON=/path/to/python3`.

Sumber yang dapat diedit: `build_poster.py`. Grafik digambar ulang dari hasil TA, bukan hasil eksperimen baru. Logo menggunakan aset ITB yang sudah ada di repository. Versi panjang dan paper tidak diubah.

## Dasar isi

- Arsitektur: Bab III, tiga tahap konstruksi dan kontrak artifact.
- Grafik User Manual: Bab IV, tabel hasil keseluruhan pada K=45. Dense 0,835, hybrid 0,745, sparse 0,465.
- Grafik peraturan: Bab IV, perbandingan indexer pada K=25. Hybrid 0,67, dense dan sparse 0,64.
- KG recall: Bab IV, 30 pertanyaan relasi pada K=25. Sparse 0,517 dan hybrid 0,417.
- Kesimpulan chunker: Bab IV–V, K=25. Manual 0,740 dengan hybrid indexer, peraturan 0,64 dengan dense indexer.

Korpus peraturan terbatas pada pendidikan di Indonesia, sedangkan User Manual terbatas pada produk Netgear. Grafik hanya membandingkan strategi di dalam korpus masing-masing. Angka antarkorpus tidak mengukur perbandingan tingkat kesulitan atau kualitas jawaban chatbot.
