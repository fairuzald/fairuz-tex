# Paper IEEE: Konstruksi Basis Pengetahuan OMNI-RAG

Artefak ini adalah paper LaTeX terpisah untuk kontribusi individual pada proyek Capstone OMNI-RAG. Paper menggunakan kelas `IEEEtran` dan menghasilkan PDF yang berbeda dari laporan tugas akhir.

Fokus paper adalah jalur offline pembentukan basis pengetahuan:

- arsitektur `plugin`, `profile`, dan kontrak artefak kanonik;
- `chunker` generik dan legal structure-aware;
- `indexer` sparse, dense, dan hybrid;
- pembentukan serta traversal `knowledge graph`;
- reproducibility melalui pipeline run, attempt, provenance, dan monitoring; serta
- evaluasi retrieval pada korpus User Manual dan peraturan pendidikan.

Komponen percakapan di luar jalur pembentukan basis pengetahuan tidak menjadi bahasan atau klaim evaluasi paper ini.

## Build

Dari direktori ini, jalankan:

```bash
make
```

Hasilnya adalah `Omni-RAG_Knowledge_Base_IEEE.pdf`. Artefak sementara berada di `build/`.
Kelas `IEEEtran.cls` disimpan lokal agar paper dapat dibangun ulang tanpa mengubah laporan utama.

