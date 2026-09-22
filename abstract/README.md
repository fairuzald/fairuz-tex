# Bilingual Abstract PDFs

This directory contains two standalone abstract PDFs that use the same XeLaTeX
font, report class, margins, heading hierarchy, and body typography as the
individual report. Their content follows the IEEE paper rather than the full
individual report, with a natural English version prepared independently from
the Indonesian wording:

- `output/pdf/abstract-indonesia.pdf`
- `output/pdf/abstract-english.pdf`

Regenerate both files with:

```bash
python3 abstract/build_abstracts.py
```

The builder invokes XeLaTeX with the same shared configuration used by the
report, so it falls back to TeX Gyre Termes in environments without Times New
Roman instead of substituting a separate sans-serif font.
