# Frozen decompose fixtures — prompt version

`*.decomp.json` in this directory were generated with the **v1** decomposer
prompt (`grounding.decompose.DECOMPOSE_PROMPT`).

On 2026-08-28 the decomposer prompt moved to **v2** (system/user split +
`<candidate_text>` XML tagging for prompt-injection resistance — cycle 2
security hardening). These fixtures were **not** regenerated: the frozen
tests (`engine/tests/test_decompose_frozen.py`) only assert structural
shape (keys present, non-empty), which is unaffected, and regenerating
would incur real Claude spend for pedagogical fixtures that carry no
scorecard. Any committed recall/κ numbers derived from these predate v2.
