# Grounding Inspector

A Layer-3 groundedness evaluation tool for LLM outputs. Decomposes AI-generated text into atomic claims, verifies each claim against a source document using [MiniCheck](https://github.com/Liyan06/MiniCheck), and surfaces grounded / partial / unsupported verdicts in a two-pane inspector UI.

Built as a proof-of-concept in the travel insurance domain (Australian PDS documents), but the engine and fixture contract are domain-agnostic.

## What it does

1. **Decompose** — break an AI output into individual atomic claims
2. **Verify** — score each claim against all document chunks using MiniCheck (no retrieval gate; max-pool over the full document). This trades higher cost/latency at longer document lengths for exhaustive recall (no chunk is skipped by a retrieval step) — validated on short-to-medium documents (PDS-length, a few pages); a 100+ page document would need a retrieval pre-filter, which is not yet built or benchmarked.
3. **Label** — aggregate sub-claim scores into `grounded`, `partial`, or `unsupported`
4. **Localise** — map grounded claims back to the source span and page number
5. **Inspect** — browse results in a Vue 3 two-pane viewer (claim list left, source doc right, click-to-highlight)

## Architecture

```
fixtures/          JSON fixtures (source doc + AI output + labelled claims + scorecard)
contract/          fixture.schema.json — shared JSON Schema between engine and web
engine/
  grounding/       Python pipeline (decompose, verify, label, localise, metrics)
  tests/           39 pytest unit tests
  notebook/        validation.ipynb — RAGTruth benchmark runner (Ollama-backed)
web/
  src/             Hono API server + Vue 3 frontend
  tests/           Vitest unit tests + Playwright E2E
```

## Fixtures

| ID | Source | Type |
|----|--------|------|
| `travel-pds-01` | SunSafe Travel Insurance PDS (synthetic) | 3 claims — grounded / partial / unsupported |
| `travel-pds-02` | Blue Pacific Travel PDS (synthetic) | cancellation and delay edge cases |
| `travel-pds-03` | Alpine Trek PDS (synthetic) | winter sports / exclusion edge cases |
| `covermore-pds-01` | Cover-More Comprehensive Travel PDS (Oct 2025, real) | Australian PDS real-world fixture |
| `budgetdirect-pds-01` | Budget Direct Comprehensive Travel Insurance PDS (Feb 2025, real) | Australian PDS real-world fixture |

## Getting started

### Engine

Requires Python 3.11+.

```bash
cd engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

> **macOS 26 Tahoe (Darwin 25) note:** PyTorch >= 2.4 wheels are not yet published for this platform. `requirements.txt` pins `numpy<2` and `transformers==4.45.2` to maintain compatibility with the highest available torch (2.2.2). Remove those pins once torch 2.4+ ships for your platform.

### MiniCheck model weights

MiniCheck downloads `flan-t5-large` (~300 MB) to `engine/ckpts/` on first use. The `ckpts/` directory is gitignored — weights are never committed. Subsequent runs load from the cache.

### Web

Requires Node 20+.

```bash
cd web
npm install
npm run build          # compile Vue frontend into dist/
npm run serve          # start Hono server on http://localhost:3000
```

Or run frontend in dev mode (with hot reload) against a running server:

```bash
npm run serve &        # API server on :3000
npm run dev            # Vite dev server on :5173
```

## Verifier modes

The pipeline supports two verifier backends, selectable at runtime:

| Mode | Verifier | Decomposer | Cost | Recall | κ |
|------|----------|------------|------|--------|---|
| `minicheck` (default) | MiniCheck flan-t5-large (local) | Ollama qwen2.5:7b-instruct | free | 0.69 | 0.195 |
| `haiku` | Claude Haiku 4.5 (API) | Claude Haiku 4.5 (API) | ~$0.03/doc | 0.90 | 0.331 |

κ (Cohen's kappa) measures agreement with human judgment beyond chance:
0.195 is "slight agreement" and 0.331 is "fair agreement" per the standard
Landis & Koch scale. Recall is the metric this tool prioritises, since a
missed hallucination (false negative) is costlier than a false alarm for
this tool's intended use.

Both validated on RAGTruth n=300, seed=0.

**Default (MiniCheck)** — no API key required, fully local:
```python
from grounding.validate import run_sample
run_sample(n=300, verifier="minicheck")
```

**Claude Haiku** — set `ANTHROPIC_API_KEY` in `engine/.env` or `repo/.env`:
```python
run_sample(n=300, verifier="haiku")
# or from the command line:
python pilot_claude.py 300
```

To use Haiku in `label_claims` (fixture generation):
```python
from grounding.verify import make_claude_verifier
from grounding.pipeline import label_claims
verifier_fn = make_claude_verifier()
claims = label_claims(decomposed, full_text, sections, verifier_fn)
```

### RAGTruth validation

`engine/notebook/validation.ipynb` re-runs the benchmark. MiniCheck mode requires Ollama (`ollama pull qwen2.5:7b-instruct`); Haiku mode requires `ANTHROPIC_API_KEY`.

```bash
# MiniCheck (local, free, ~30-60 min)
python -c "from grounding.validate import run_sample; print(run_sample(n=300))"

# Claude Haiku (~35 min, ~$6 USD for n=300)
python pilot_claude.py 300
```

## Fixture contract

Each fixture is a JSON file conforming to `contract/fixture.schema.json`. Key fields:

- `source.sections[]` — document chunks with `id`, `page`, `char_start`, `char_end`, `text`
- `ai_output` — the LLM-generated text under evaluation
- `claims[]` — labelled claims with `label` (`grounded` | `partial` | `unsupported`), `evidence_span_ids`, `quote`, `page`, `rationale`
- `groundedness` — aggregate score (0–100) and counts
- `scorecard` — recall, CI, false negatives, and domain note

## License

MIT
