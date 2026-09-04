# LLM authoring draft

This directory is the only input location for the new authoring run. The model must receive the
complete `context_text` from each packet and return variable-size `evidence_block_ids`.

Run `generate_multiblock_question_candidates.py` with an explicit OpenAI-compatible endpoint,
API key, and model. Until that command completes, the older files in this run directory are
superseded audit artifacts and must not be frozen or sent to retrieval.
