# Paper Omni-RAG

Versi artikel ringkas dari Tugas Akhir, dalam bahasa Indonesia dengan tata letak dua kolom. Ini merupakan draf artikel umum, belum mengikuti template jurnal atau konferensi tertentu. Nama penulis mengikuti laporan TA. Daftar penulis dan afiliasi untuk pengiriman publikasi perlu disesuaikan dengan kontribusi serta ketentuan tujuan publikasi.

## Build

Dari root repository, jalankan `make paper`. Dari folder ini, jalankan `make`.

Kebutuhan: XeLaTeX, Biber, dan font TeX Gyre Termes. Hasil: `paper/Omni-RAG_Paper_13522057.pdf`. File sementara berada di `paper/build/` dan tidak masuk Git. `make clean` dari folder ini membersihkan file sementara tanpa menghapus PDF final.

Versi panjang tetap berada di `src/IF4092_Laporan_SidangTA_13522057.pdf` dan dibangun dengan `make pdf` dari root. Build paper terpisah dari build TA. Gambar dan bibliografi yang diperlukan digunakan langsung dari `src/` tanpa menduplikasi aset.

## Isi dan sumber

| Bagian paper | Sumber utama TA |
| --- | --- |
| Pendahuluan | Bab I dan landasan pustaka Bab II |
| Metode | Bab III, termasuk rancangan solusi |
| Eksperimen | Bab IV, korpus, pemilihan sampel, konfigurasi, dan metrik |
| Hasil | Bab IV, tabel hasil per komponen, perbandingan pada K bersama, dan KG recall |
| Kesimpulan | Bab V dan batasan eksperimen Bab IV |

Detail antarmuka, daftar API, ERD lengkap, daftar istilah, dan lampiran pertanyaan tetap tersedia pada TA. Paper merangkum arsitektur, kontribusi utama, komponen pendukung, metode, hasil, dan keterbatasan. Tidak ada eksperimen baru yang dijalankan untuk penyusunan artikel ini.

Angka pada artikel mengikuti konfigurasi akhir dengan retrieval pada K=30 dan generation pada K=10.
Benchmark hukum berisi 25 pertanyaan yang disusun untuk eksperimen dan diverifikasi oleh ahli.
KG recall dilaporkan sebagai eksperimen terpisah pada graf hukum global. Hasil tidak menyatakan
kualitas jawaban akhir di luar pengukuran generation, signifikansi statistik, atau efektivitas keamanan.
