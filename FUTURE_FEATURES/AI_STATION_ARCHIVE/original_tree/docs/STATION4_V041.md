# Station 4 v0.4.1 — Conversational Quality + Latency

## Purpose

v0.4.1 keeps the deterministic scenario controller authoritative while making
local-LLM responses more coherent, less repetitive and easier to measure.

## Safety boundary

The deterministic engine still decides:

- visitor intent
- scenario stage
- score
- terminal outcomes
- approved canonical reply meaning

The local LLM may only produce the natural-language surface form for a
non-terminal reply.

## New context contract

The local LLM receives:

1. current stage goal
2. pressure level (1–5)
3. stage-specific allowed facts
4. current classified intent
5. approved canonical reply meaning
6. at most 2 recent sanitized visitor/caller exchanges

Raw visitor utterances are not written to disk. The short conversational memory
lives only inside the existing in-memory kiosk session and expires with it.

## Latency changes

- Ollama `keep_alive=-1` for exhibition mode
- compact context (`num_ctx=2048`)
- short output cap (`num_predict=72`)
- thinking disabled
- response metrics captured from Ollama:
  - total/load/prompt-eval/eval duration
  - prompt/output token counts
  - generation tokens per second
  - local wall-clock duration

## Optional model comparison

First install another model, for example:

```bash
ollama pull qwen3.5:2b
```

Then compare synthetic Station 4 turns:

```bash
python3 scripts/benchmark_station4_llm.py \
  --models qwen3.5:4b qwen3.5:2b
```

The benchmark does not change the configured Fraud Lab model.
