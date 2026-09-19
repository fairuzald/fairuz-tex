# Bilingual Abstract PDFs

This directory contains the source for two standalone abstract PDFs derived
from `src/IF4092_Laporan_SidangTA_13522057.pdf` and the supporting material in
`src/`:

- `output/pdf/abstract-indonesia.pdf`
- `output/pdf/abstract-english.pdf`

The English abstract is written as an independent academic text rather than as
a sentence-by-sentence translation of the Indonesian version. Both abstracts
use the same scope, datasets, metrics, and results as the individual report.

Regenerate both files with:

```bash
python3 abstract/build_abstracts.py
```
