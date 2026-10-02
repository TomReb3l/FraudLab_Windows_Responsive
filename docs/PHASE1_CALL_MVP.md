# PHASE 1 — Fraud Call Booth MVP

## Architecture

```text
Visitor
  │ touch / mouse / optional HID keys 1-3
  ▼
Browser UI (HTML/CSS/Vanilla JS)
  │ fetch local scenario at startup
  ▼
FastAPI localhost
  ├── /                  UI
  ├── /static/*          CSS / JS / local WAV
  ├── /api/health        operator health check
  └── /api/scenarios/*   validated scenario data
            │
            ▼
     call_scenarios.json
            │
            ▼
 ScenarioEngine startup validation
```

No visitor account. No backend visitor session. No form fields. No visitor data persistence.

## Visitor flow

Attract → Incoming Call → Decision → Pressure branch → Decision → Consequence → Red flags → STOP / CHECK / VERIFY → Retry or automatic reset.

## Decision tree

```text
Incoming Call
├─ Do not answer + verify ──────────────────────────────► SAFE VERIFY END
└─ Answer
   ├─ Close + verify ──────────────────────────────────► SAFE VERIFY END
   ├─ Ask questions
   │  ├─ Close + official channel ─────────────────────► SAFE VERIFY END
   │  ├─ Ask how to verify
   │  │  ├─ Close + verify ────────────────────────────► SAFE VERIFY END
   │  │  └─ Stay on line ─► code request
   │  └─ Follow instructions ─► code request
   └─ Continue ─► urgency / OTP-style code request
      ├─ Share code ───────────────────────────────────► UNSAFE CONSEQUENCE
      ├─ Ask why ─► stronger pressure
      │  ├─ Close ─────────────────────────────────────► SAFE STOP END
      │  └─ Close + verify ────────────────────────────► SAFE VERIFY END
      └─ Close + official call ────────────────────────► SAFE VERIFY END
```

## Recovery

- Home button from every normal state.
- Inactivity warning at 65 seconds.
- Hard reset to attract screen at 75 seconds.
- Transcript remains available if audio playback fails.
- `H` = Home, `R` = Replay audio, `1/2/3` = choice buttons.
- Server port can be overridden with `FRAUDLAB_PORT`.

## Prototype acceptance

- Offline operation: implemented.
- Local prerecorded branching audio: implemented (prototype WAV voice assets).
- At least three meaningful decision branches: implemented.
- Data-driven scenario graph: implemented.
- No real credentials or personal data fields: implemented.
- No persistent visitor state: implemented.
- Touch/mouse + HID-friendly input: implemented.
- Assisted mode: implemented.
- Home/restart/timeout: implemented.
- Automated graph/API/audio checks: implemented.
