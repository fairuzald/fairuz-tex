# Frozen output status

These files are the canonical Codex current-model full-context review output. The model read
the complete `context_text` for every packet and selected the minimal evidence set. The current
content has 200 bilingual rows, no `context_block_ids` column, and variable evidence cardinality:
32 rows use one block, 136 use two blocks, 26 use three blocks, 4 use four blocks, and 2 use five
blocks.

The 84 multi-block pairs are genuine single-workflow questions. Each selected block contributes
a necessary part of the answer; unrelated candidates in the same packet remain context-only.

The 16 one-block pairs are intentionally retained because their leaf already contains the complete
answer (for example, package contents or one status meaning). Adding unrelated siblings would pad
gold and make precision look worse. Therefore cardinality is variable from 1 to 5, never fixed at 2.

`question-evidence-relevance-audit.md` records the per-pair provenance and relevance checks;
all 100 pairs currently pass.

The earlier fixed-two artifacts remain only in the superseded draft files and are not used for
retrieval evaluation.
