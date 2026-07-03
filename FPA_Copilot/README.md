# FP&A Copilot — Orchestration Layer

Phase 3 of the FP&A AI Stack. Combines the Month-End Close Toolkit's judgment
logic, the Forecasting Agent, and the Data Layer behind a single natural-
language interface — the "FP&A copilot" from the roadmap.

## Architecture — orchestrator-worker pattern

```
User (natural language)
        |
        v
  Orchestrator (LLM, via OpenRouter)  <- decides WHICH tool(s) to call, extracts args
        |
        v
  Deterministic Python tools (tools.py) <- ALL financial judgment happens here, not in the LLM
        |
        +-- get_forecast()               reads fpa_data_layer/warehouse.duckdb
        +-- get_variance_commentary()    materiality gate + Confirmed-vs-Hypothesis
        +-- get_reconciliation_check()   duplicate/high-risk detection, tie != clean
        |
        v
  Orchestrator (LLM) <- summarizes tool results, does NOT add its own numbers/judgment
        |
        v
  Response to user
```

**Why this design, not a single do-everything LLM call:** the LLM's only job
is routing and summarizing. Every actual number, every materiality decision,
every sign-off gate is plain, testable Python — the same discipline carried
through from the Month-End Close Toolkit and the Forecasting Agent. This is
what "explainable" means in practice: you can unit-test `tools.py` with zero
LLM involvement (see `tools.py`'s own `if __name__ == "__main__"` self-test),
and the LLM can be swapped, retried, or removed without touching the
financial logic.

## Running it

```bash
cd FPA_Copilot
python orchestrator.py "What's the forecast for MNDY?"
python orchestrator.py "Check this rec: net diff 11800, explained 11800, item: vendor invoice posted twice for 11500, category duplicate"
```

Requires `OPENROUTER_API_KEY` in the environment (already wired on this
machine). Model is `openai/gpt-4o-mini` by default — cheap, reliable at tool
calling — swappable via the `MODEL` constant in `orchestrator.py`.

## Verified test cases

1. **Single-tool routing** — forecast query correctly called `get_forecast`,
   summarized without inventing numbers, preserved the "2 known data gaps" flag.
2. **Multi-tool routing** — one request asking for both a reconciliation
   check AND variance commentary correctly triggered both tools and combined
   results faithfully (including the "math ties but BLOCKED" nuance).
3. **Out-of-scope refusal** — "What's the weather like today?" correctly
   returned a refusal instead of a hallucinated financial answer.

## Files

- `tools.py` — 3 deterministic tools + their JSON schemas for LLM function-calling. Runnable standalone with zero LLM/API dependency (`python tools.py`).
- `orchestrator.py` — the LLM router. Sends the tool schemas to OpenRouter, executes whichever tool(s) it picks, returns a summarized response.

## Extending it

Adding a 4th tool: write the function in `tools.py`, add its JSON schema to
`TOOL_SCHEMAS`, add it to the `TOOL_FUNCTIONS` dict. No orchestrator changes
needed — the LLM picks up new tools automatically from the schema list.
