# Generation prompt — budgetdirect-pds-01

**Model:** used during original fixture authoring (2026-06-13, Claude Sonnet —
commit dee61d5, "feat: real PDS fixtures — Cover-More baggage, Budget Direct
cancellation").

**Prompt used to produce `ai_output`:**

> Based only on the following PDS sections, write a 3-5 sentence summary of
> cancellation cover. Do not add information not present in the text.
>
> Budget Direct Travel Insurance — Combined FSG and PDS (International
> Comprehensive, effective 19 February 2025).
>
> If due to circumstances outside Your control and unforeseeable at the
> Relevant Time You have to cancel the Journey, We will pay You the value of
> the unused portion of Your prepaid travel and accommodation arrangements
> that are non-refundable and not recoverable in any other way, the travel
> agent's commission (limited to the lesser of $4,000 or the amount earned),
> and the value of frequent flyer or similar flight reward points lost by You.
>
> International Comprehensive cancellation benefit: $10,000 (default) or cover
> chosen as shown on Your Certificate of Insurance.
>
> We will not pay for cancellation caused by: An Epidemic, Pandemic or
> outbreak of an infectious disease or any derivative or mutation of such
> viruses.
>
> We will not pay for cancellation caused by: Any contractual or business
> obligation or Your financial situation. This exclusion does not apply to
> claims where You are involuntarily made redundant from Your permanent
> full-time or permanent part-time employment in Australia and where You would
> not have been aware before, or at the Relevant Time, that the redundancy was
> to occur.

**Note:** this prompt is reconstructed to document the generation
methodology (per FUTURE.md's Fixture Provenance item), not re-run — the
existing `ai_output` text in the committed fixture is unchanged. The
fixture's flagged claims (c2 "partial" — redundancy cover overstated as
unconditional; c3 "unsupported" — pandemic cancellation claimed covered when
the source excludes it) are inversions of the redundancy and pandemic
exclusions above — this is the deliberate injected-error pattern the fixture
was authored to demonstrate, not an artefact of this reconstruction.
