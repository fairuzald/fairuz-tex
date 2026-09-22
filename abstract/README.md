# Bilingual Abstract PDFs

This directory contains two content variants, each in Indonesian and English.
All four standalone PDFs use the same XeLaTeX font, report class, margins,
heading hierarchy, and body typography as the individual report.

Paper variant:

- `output/pdf/abstract-indonesia.pdf`
- `output/pdf/abstract-english.pdf`

Report variant:

- `output/pdf/abstract-laporan-indonesia.pdf`
- `output/pdf/abstract-laporan-english.pdf`

Regenerate all four files with:

```bash
python3 abstract/build_abstracts.py
```

The builder invokes XeLaTeX with the same shared configuration used by the
report, so it falls back to TeX Gyre Termes in environments without Times New
Roman instead of substituting a separate sans-serif font.
