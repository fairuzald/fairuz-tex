# Paper IEEE: Konstruksi Basis Pengetahuan OMNI-RAG

Paper ini merupakan naskah LaTeX terpisah yang disusun ulang dari laporan tugas
akhir individu pada `src/IF4092_Laporan_SidangTA_13522057.pdf` dan sumber di
`src/`. Konteks proyek Capstone hanya digunakan untuk menjelaskan posisi sistem;
kontribusi, rancangan, dan hasil paper berfokus pada pipeline konstruksi basis
pengetahuan.

Ruang lingkup paper meliputi:

- kontrak artefak kanonik dan arsitektur berbasis plugin;
- empat strategi chunker;
- sparse, dense, dan hybrid indexer;
- legal knowledge graph deterministik; serta
- eksperimen retrieval, generation, dan neighborhood recall pada dua korpus.

## Build

```bash
make
```

Perintah tersebut menghasilkan `OMNI-RAG_Individual_Knowledge_Base_IEEE.pdf`.
Artefak sementara berada di `build/` dan tidak perlu dikomit.
