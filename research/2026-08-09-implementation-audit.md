# Research Note: Implementation Audit

## Metadata

- Date: 2026-08-09
- Research question: Which modules and workflows are present in the current implementation repositories, and which claims require qualification?
- Thesis section: Analisis dan Rancangan; Rencana Pelaksanaan; lampiran rancangan sistem
- Related implementation paths: `../admin-fe`; `../fe`; `../dpo`
- Research status: `PARTIAL`d

## Scope

This audit inspected repository structure, README files, package metadata, selected frontend components, and selected DPO application services. It did not run the applications, execute integration tests, inspect deployment state, or verify that every configured plugin is active in a runtime profile.

## Claims

### Claim 1

- Claim: The DPO repository contains an event-driven parser-to-chunker-to-indexer-to-knowledge-graph workflow with artifact references and per-stage run tracking.
- Evidence type: `DERIVED`
- Status: `VERIFIED`
- Intended use in thesis: Describe the proposed and implemented processing pipeline, with repository paths as implementation evidence.
- Limitation or qualification: This verifies code paths and event handoffs, not successful production execution.

### Claim 2

- Claim: The RAG runtime contains a deterministic legal query planner that extracts document form, number, year, location, and pasal identifiers, then produces scoped or global retrieval branches.
- Evidence type: `DERIVED`
- Status: `VERIFIED`
- Intended use in thesis: Explain query pre-planning and structured legal filtering.
- Limitation or qualification: The audit did not measure planner accuracy or retrieval quality.

### Claim 3

- Claim: The chat orchestration path includes retrieval, knowledge-graph expansion, tracing, warnings, answer generation, validation, and XAI extension points.
- Evidence type: `DERIVED`
- Status: `PARTIAL`
- Intended use in thesis: Describe the system architecture and explainability integration points.
- Limitation or qualification: The orchestrator has no-op fallbacks for several XAI components, so the thesis must identify which methods are active in the evaluated profile instead of implying that every extension point is enabled.

### Claim 4

- Claim: The user frontend exposes profile-scoped chat, process/reasoning displays, source citations, a regulation browser, graph views, and an XAI demo route.
- Evidence type: `DERIVED`
- Status: `VERIFIED`
- Intended use in thesis: Describe user-facing modules and the presentation of reasoning and source attribution.
- Limitation or qualification: This is a static code audit; browser behavior and backend connectivity were not tested in this note.

### Claim 5

- Claim: The admin frontend exposes profile and plugin management, document upload, document run/artifact inspection, and graph exploration surfaces.
- Evidence type: `DERIVED`
- Status: `VERIFIED`
- Intended use in thesis: Describe the administration and ingestion-support modules.
- Limitation or qualification: The upload UI accepts canonical JSON documents; this does not by itself establish that scraping and parsing are complete end to end.

### Claim 6

- Claim: The broad discovery-to-scraping-to-parsing pipeline should not currently be described as complete.
- Evidence type: `DERIVED`
- Status: `VERIFIED`
- Intended use in thesis: Qualify implementation status and define remaining integration work.
- Limitation or qualification: `../dpo/README.md` explicitly lists the real discovery consumer, BPK scraper execution, and parser pipeline integration as incomplete, although parser handlers and plugins are present in the source tree.

## Sources

### Source 1

- Citation key: N/A
- Title: DPO implementation source and repository documentation
- Authors or organization: Project repository
- Year: 2026
- Source type: Implementation repository
- DOI or official URL: Local path `../dpo`
- Access date: 2026-08-09
- Zotero item: `NO`
- PDF or full text checked: `NO`
- Relevant page, section, theorem, table, or figure: `README.md`; `src/modules/dpo`; `src/modules/rag`; `src/plugins`
- Supporting excerpt or evidence: Parser handling publishes chunk requests; chunk handling publishes index requests; index handling advances the pipeline toward KG; the legal planner creates structured retrieval branches.
- What the source does not establish: Runtime availability, deployment state, benchmark performance, or completion of the discovery/scraper integration.

### Source 2

- Citation key: N/A
- Title: User and admin frontend source and repository documentation
- Authors or organization: Project repositories
- Year: 2026
- Source type: Implementation repository
- DOI or official URL: Local paths `../fe` and `../admin-fe`
- Access date: 2026-08-09
- Zotero item: `NO`
- PDF or full text checked: `NO`
- Relevant page, section, theorem, table, or figure: frontend README files; chat, peraturan, graph, profile, plugin, and document components
- Supporting excerpt or evidence: User routes include chat, graph, regulation, and XAI surfaces; admin routes include profiles, plugins, documents, document runs, artifacts, and graph exploration.
- What the source does not establish: End-to-end usability, API availability, or correctness of all rendered interactions.

## Source Comparison

The DPO README describes the broader discovery/scraper/parser integration as incomplete, while the source tree contains parser handlers, parser plugins, chunking services, indexing, KG, RAG, and XAI modules. These statements are compatible when code existence is distinguished from an integrated, operational workflow.

## Decision

Use the verified module and event-flow claims for architecture descriptions. Qualify claims about active XAI methods, scraper completeness, runtime profiles, and measured behavior until they are confirmed through configured-profile inspection and executable tests.

## Citation Changes

- Added to `src/bib/agent.bib`: None
- Existing key in `src/bib/manual.bib`: None
- LaTeX files updated: None
- Zotero import pending: `NO`
