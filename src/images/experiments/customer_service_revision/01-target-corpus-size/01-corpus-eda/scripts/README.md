# Script EDA

`run_customer_eda.py` membaca datasource dan parser artifact secara read-only.
Output utamanya:

- `outline-report.md` — tree lengkap parent/child per dokumen;
- `transition/outline_inventory.csv` — detail setiap node outline;
- `transition/outline_summary.csv` — ringkasan per dokumen;
- `question_outline_frame.csv` — 1.240 leaf outline untuk random pick; dan
- `question_source_frame.csv` — 1.566 text block untuk lookup context.

```bash
uv run python 01-corpus-eda/scripts/run_customer_eda.py \
  --dsn 'postgresql://dpo:dpo@localhost:5437/dpo' \
  --s3-endpoint http://localhost:9005 \
  --bucket legal-chunks
```

Script tidak membuat profile, index, question set, context packet, atau retrieval run.
