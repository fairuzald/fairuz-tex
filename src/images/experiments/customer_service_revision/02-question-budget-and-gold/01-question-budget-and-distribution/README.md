# 02.01 — Budget dan distribusi pertanyaan

## Tujuan

Memilih 100 **leaf outline** sebagai anchor slot pertanyaan. Pemilihan random, reproducible,
dan tetap mencakup semua dokumen serta posisi halaman. Tidak ada topic classifier,
`evidence_shape` quota, context packet, atau wording pertanyaan di tahap ini.

## Input

```text
01-target-corpus-size/01-corpus-eda/
├── question_outline_frame.csv   # 1.240 leaf outline; pool sampling
├── question_source_frame.csv     # 1.566 text block; lookup context
└── transition/
    ├── corpus-manifest.json
    └── summary.json
```

Satu outline bukan satu pertanyaan final. Ia adalah section berjudul, misalnya
`Hardware Setup > Front Panel and LEDs`, dengan page span dan ID source block. Source frame
baru dipakai setelah outline disetujui.

## Metode

1. Validasi hash, dokumen, `outline_id`, page, `section_path`, dan
   `direct_source_frame_ids`.
2. Bentuk strata struktural `document × page_bin`; `page_bin` = P1–P5 berdasarkan posisi
   relatif halaman. Tidak ada strata topic atau `evidence_shape`.
3. Tetapkan floor 8 slot per manual, lalu bagi 28 slot sisa berdasarkan page count.
4. Sort deterministik `filename → page_start → section_path → outline_id`, lalu lakukan
   random pick dengan seed `20260831` di dalam strata.
5. Simpan candidate pool 200 outline (2× target) sebagai audit/cadangan; 100 slot final
   sudah dipilih reproducibly.
6. Buat dua varian bahasa untuk setiap slot: English (`Q-001..Q-100`) dan Indonesian
   (`Q-101..Q-200`), dengan `question_pair_id` yang sama. Family ditetapkan setelah complete
   context dibaca, bukan dari label heuristic parser.

## Alokasi target

| Produk | Halaman | Slot |
|---|---:|---:|
| CM2000 | 26 | 9 |
| LM1200 | 105 | 10 |
| R6350 | 204 | 12 |
| R7000 | 186 | 12 |
| RAX120 | 175 | 12 |
| RAX50 | 160 | 11 |
| RAXE500 | 169 | 11 |
| RBK852 | 161 | 11 |
| XR500 | 214 | 12 |
| **Total** | **1.400** | **100** |

Family final: masing-masing 50 row (25 slot pair) untuk fakta, setup, troubleshooting,
dan fitur/limitasi.

## Mengapa demikian?

- Outline memberi batas section yang dapat dibaca dan diperluas secara deterministik.
- Random tanpa label heuristic menghindari klasifikasi heading yang keliru.
- Floor menjaga manual pendek tetap muncul; page-weighted remainder mencegah manual panjang
  mendominasi.
- Pool 2× memberi cadangan untuk duplicate, boilerplate, atau section yang tidak answerable.

Daftar outline lengkap ada di [`outline-report.md`](../../01-target-corpus-size/01-corpus-eda/outline-report.md).

## Output dan gate

```text
runs/selection-v1/
├── candidate-pool.csv
├── question-slots.csv
└── allocation-report.json
```

`question-slots.csv` berisi 200 language row dari 100 outline slot dengan
`outline_frame_id`, `question_pair_id`, `section_path`, page, source IDs, family, bahasa,
dan status authoring. Pada run `selection-v1`, quota 50/50/50/50 dan 100/100 sudah terisi
setelah membaca complete context. Hentikan proses bila hash tidak cocok, outline tidak
dapat di-resolve, atau allocation bukan 100 slot/200 row.
