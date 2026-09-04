# Bab 1--2: Omni-RAG implementation and literature audit

Status: VERIFIED for repository facts; PARTIAL for research outcomes. No experiment result is claimed here.

## Source-of-truth rule

For research-facing claims, `dpo/experiments/` is authoritative. The current
reading order begins at `dpo/experiments/indonesian-law-rag/READING-GUIDE.md` and
then follows the overview, implementation audit, shared contracts, corpus plan,
question matrix, metrics plan, and combination design. Runtime code and tests are
used to verify implementation details; the experiment documents determine factor
status, compatibility, scope, metric eligibility, and whether a result may be
reported.

## Scope and evidence

- Repositories audited: `dpo`, `fe`, `admin-fe`, and `report-tex`.
- Canonical implementation path: `CanonicalDocument -> CanonicalChunks -> CanonicalIndex/CanonicalGraph`.
- Offline components verified in `dpo/src/plugins`: generic/legal chunkers, dense/lexical/hybrid indexers, and deterministic legal graph.
- Online components verified in `dpo/src/modules/rag/chat`: preprocessing, guardrails, session memory compaction, retrieval memory projection, context assembly, and output handling.
- `dpo/experiments/indonesian-law-rag` explicitly states that corpus, qrels, gold graph, and frozen runs must exist before performance claims are made.

## Claims used in the chapters

| Claim | Status | Evidence or qualification |
|---|---|---|
| DPO is a plugin-based offline pipeline with canonical artifacts and compatibility gates. | VERIFIED | `dpo/src/plugins`, `dpo/experiments/combination-design/pre-experiment-implementation-audit.md`. |
| Current legal chunking is structure-aware parent--child with Ayat overlap and recursive fallback. | VERIFIED | `dpo/src/plugins/chunkers/legal_pasal`, `legal_structure_aware`. |
| Current lexical index is fielded `multi_match`, not a sparse-vector embedding. | VERIFIED | `dpo/src/plugins/indexers/_legal_common.py`, sparse-keyword plugin. |
| Legal graph relations are deterministic `HAS`, `AMENDS`, `REVOKES`, and `ESTABLISHES`; traversal is bounded. | VERIFIED | `dpo/src/plugins/kg/legal_graph`, `neo4j_kg_relation_retriever.py`. |
| Compaction has token trigger, recent window, rolling summary, memory items, timeout, and deterministic fallback. | VERIFIED | `dpo/src/modules/rag/chat/application/session_memory`. |
| PII is anonymized before intent/retrieval and output/input guardrails exist. | VERIFIED as code path; runtime privacy effectiveness PARTIAL | `preprocessing_service.py`, `nemo.py`, `orchestrator.py`; no leakage benchmark or production privacy control was claimed. |
| HukumPedia is an active seeded profile. | VERIFIED | `dpo/src/interface/cli/seed_legal_profile.py`. |
| Customer-service profile and benchmark are active. | NOT FOUND | Repository search found no customer-service seed/profile; report frames it as a target generalization. |
| End-to-end performance or component winner is established. | REJECTED for these chapters | Experiment docs prohibit result claims before frozen runs and integrity checks. |
| Primary experiment is a full factorial over chunker, indexer, and KG. | REJECTED | The selected design is compatibility-aware and staged: 9 generic, 3 legal, 7 KG logical cells, plus deployment aliases. |
| PII, compaction, and guardrail are primary factors in the current matrix. | REJECTED | Their implementation notes mark them fixed and outside the primary chunker--indexer--KG study; online evaluation is deferred. |

## Literature sources

- Lewis et al., RAG: https://arxiv.org/abs/2005.11401
- Hogan et al., Knowledge Graphs: https://doi.org/10.1145/3447772
- Edge et al., GraphRAG: https://arxiv.org/abs/2404.16130
- Akarajaradwong et al., NitiBench: https://aclanthology.org/2025.emnlp-main.1739.pdf
- Cormack, Clarke, and Buettcher, RRF: https://doi.org/10.1145/1571941.1572114
- Wu et al., LongMemEval: https://openreview.net/pdf?id=pZiyCaVuti
- NIST SP 800-122: https://csrc.nist.gov/pubs/sp/800/122/final
- NVIDIA NeMo Guardrails catalog: https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/guardrail-catalog
- UU 12/2011 on the formation of laws: https://peraturan.bpk.go.id/Details/39188/uu-no-12-tahun-2011

## Writing decisions

1. `Omni-RAG` is explicitly labeled as a project architectural term, not a standard literature term.
2. The former proposal language “sparse embedding” is replaced by “representasi leksikal berbasis field” because the implementation uses `multi_match`.
3. `context AI` is defined as context assembly/selection/hydration in the current chat path, not as a separate model.
4. Customer service is described as a target of reuse, not as an evaluated implementation.
5. Exact thresholds, provider/model choices, and performance numbers are omitted unless frozen in the experiment artifacts.
6. The experiment matrix is treated as a staged compatibility-aware design, not a nominal full factorial.
7. Retrieval/KG metrics are the primary current scorecard; compaction, PII, and guardrail are runtime verification or deferred online studies.
