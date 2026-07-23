# Generation prompt — covermore-pds-01

**Model:** used during original fixture authoring (2026-06-13, Claude Sonnet —
commit dee61d5, "feat: real PDS fixtures — Cover-More baggage, Budget Direct
cancellation").

**Prompt used to produce `ai_output`:**

> Based only on the following PDS sections, write a 3-5 sentence summary of
> luggage and personal effects cover. Do not add information not present in
> the text.
>
> Cover-More Travel Insurance — Combined FSG and PDS (Comprehensive Plan,
> effective 15 October 2025).
>
> International Benefits Table — Luggage and Travel Documents (Comprehensive
> Plan): Total limit $15,000. Per-item limits: Phone or Smart Watch $1,500;
> Camera or Video Camera $4,000; Laptop Computer $4,000; Tablet Computer
> $3,000; Drone $1,200; Jewellery, watch or any other item $1,200; Delayed
> Luggage Allowance $1,100.
>
> If during the Period of Insurance Your luggage or personal effects are lost,
> stolen or damaged, after deducting depreciation We will repair the item if
> it is practical and economic to do so. If it is not practical and economic
> to repair the item, We will replace the item or provide You with a
> replacement voucher. If the above do not apply, We will pay You the monetary
> value of the item.
>
> We will not pay for: Items left Unattended in any motor vehicle or towed
> land vehicle overnight even if they were in a Concealed Storage Compartment.
> Any amount exceeding $500 per item and $2,000 in total for all items left
> Unattended in any motor vehicle or towed land vehicle.
>
> We will not pay for: Items left Unattended in a Public Place. Valuables
> placed in checked baggage with a Transport Provider.

**Note:** this prompt is reconstructed to document the generation
methodology (per FUTURE.md's Fixture Provenance item), not re-run — the
existing `ai_output` text in the committed fixture is unchanged. The
fixture's flagged claims are all figure inflations or an exclusion inversion
against the source table above: c1 "unsupported" ($20,000 total vs. $15,000),
c2 "partial" (laptop $5,000 vs. $4,000), c4 "partial" (jewellery/watch $2,000
vs. $1,200 per-item), c5 "unsupported" (vehicle storage claimed fully covered
when the source caps it at $500/$2,000 and excludes overnight storage
entirely). This is the deliberate injected-error pattern the fixture was
authored to demonstrate, not an artefact of this reconstruction.
