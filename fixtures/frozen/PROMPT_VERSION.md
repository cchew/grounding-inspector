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

## v3

Also 2026-08-28 (cycle 2 final review). The untrusted span in the user turn
is now neutralised before wrapping: any `<candidate_text>`, `<claim>` or
`<document_context>` delimiter occurring in the data has its `<` rewritten as
`&lt;`, so a payload cannot close its own wrapper and reach the trusted
top level of the user turn. The system prompt states that the escaping is
applied. The regex is narrow, so prose containing none of those three tag
names is byte-identical to v2 — the fixtures are unaffected in practice and
were again not regenerated.
