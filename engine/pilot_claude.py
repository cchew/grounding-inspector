#!/usr/bin/env python3
"""Benchmark runner: Claude Haiku verifier on RAGTruth.

Usage (from engine/, venv active):
    python pilot_claude.py          # n=20
    python pilot_claude.py 300      # n=300

Reads ANTHROPIC_API_KEY from .env in this directory or the repo root.
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")

from grounding.validate import run_sample

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    print(f"Running Claude Haiku verifier on n={n} RAGTruth examples...")
    result = run_sample(n=n, verifier="haiku")
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    out = results_dir / f"grounding_scorecard_claude_n{n}.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nWritten to {out}")
