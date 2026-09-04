# Research Evidence Log

This directory stores reviewable research notes used to support the thesis. The notes are an audit trail, not a replacement for the Zotero library or the thesis bibliography.

## Workflow

1. Create one Markdown file for each research task using `_template.md`.
2. Record the research question and scope before searching.
3. Prefer official sources, original research papers, and authoritative documentation.
4. Record the exact claim supported by each source and include a short excerpt or page/section locator.
5. Mark every source as `VERIFIED`, `PARTIAL`, or `REJECTED`.
6. Add verified citation keys to `src/bib/agent.bib` when they are not already present in `src/bib/manual.bib`.
7. Update the thesis only from claims marked `VERIFIED` or explicitly qualified as `PARTIAL`.
8. Move accepted references into Zotero and re-export `src/bib/manual.bib` before final compilation.

## Naming

Use the format:

```text
YYYY-MM-DD-topic.md
```

Examples:

```text
2026-08-09-legal-document-chunking.md
2026-08-09-query-intent-detection.md
```

## Review Rules

- Do not cite a source only because its metadata is present.
- Do not present an interpretation as a source-supported fact.
- Do not use a source to support a stronger claim than the source actually makes.
- Record disagreements between sources instead of silently choosing one.
- Keep implementation facts separate from literature findings.
