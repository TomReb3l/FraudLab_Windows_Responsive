# Station 4 v0.4.3 — Semantic Router + Approved Response Engine

## Goal

v0.4.3 removes free visitor-facing LLM generation from the live Station 4
conversation path.

The local model is now used only as a semantic classifier when the fast
deterministic rules cannot confidently map a visitor utterance to a known
topic.

## Runtime

Visitor speech
→ local STT
→ deterministic broad intent / score / stage
→ rules-first semantic topic router
→ local Ollama enum classification only when needed
→ approved authored response bank
→ local Greek TTS

The LLM does not write the caller's sentence.

## Topics

- accident
- injury
- location
- phone_reason
- identity
- amount
- action
- urgency_reason
- other_person
- verification
- payment_method
- sensitive_credentials
- general

## Reliability rules

- terminal verification and stop outcomes bypass the semantic router,
- common questions are handled by local rules with no LLM inference,
- ambiguous wording may use local Ollama structured output,
- low-confidence, invalid, unavailable or timed-out routing fails closed,
- every visitor-facing non-terminal reply comes from `approved_responses`,
- the deterministic canonical reply remains the last-resort fallback,
- live v0.4.3 sends no conversation memory to the local model.

## Why this replaces free naturalization

The v0.4.1/v0.4.2 naturalizer could produce fluent-looking but semantically
wrong Greek and introduced unnecessary multi-second generation latency.
v0.4.3 keeps natural free-text input while constraining AI to classification,
where a compact local model is substantially easier to validate.

## Benchmark

Common rules-first routing:

```bash
python3 scripts/benchmark_station4_router.py --models qwen3.5:4b
```

Force Ollama classification to measure the model-only router:

```bash
python3 scripts/benchmark_station4_router.py \
  --models qwen3.5:4b \
  --force-llm
```

The legacy `benchmark_station4_llm.py` is retained for comparison only; its
free-generation path is no longer used by the live station.
