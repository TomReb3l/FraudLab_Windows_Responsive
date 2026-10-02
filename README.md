# FRAUD LAB — Fraud Call Booth MVP

Local-first, browser-based educational simulation for a public anti-fraud exhibition.

## Run

Python 3.12+ recommended.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python run_local.py
```

Open: `http://127.0.0.1:8080`

If port 8080 is occupied:

```bash
FRAUDLAB_PORT=18080 python run_local.py
```

## Operator recovery

- **ΑΡΧΙΚΗ**: immediate reset from any normal screen.
- Inactivity warning at 65 seconds; automatic reset at 75 seconds.
- If audio fails, the full transcript remains visible.
- If the station enters an error state, use **ΑΡΧΙΚΗ** or restart `python run_local.py`.
- No visitor account, no backend session, no visitor data persistence.

## Scenario content

Edit `data/call_scenarios.json`. The UI renders branches from data; it does not hard-code scenario decisions.

## Tests

```bash
pytest -q
```
