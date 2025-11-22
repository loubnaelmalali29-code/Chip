# Tests Overview

Unit tests cover:

- app.adapters.loop.LoopClient request building and error handling (mocked with respx)
- Normalization and verification helpers
- Adapter registry behavior
- Webhook route end-to-end flows (FastAPI TestClient), including auth, happy path, and error paths
- Health and root endpoints

The LLM is stubbed in tests via `override_generate_reply` context manager.
No live network calls are made; all HTTP to Loop is mocked.

Run tests locally:

```bash
uv run pytest -q
# or if uv is unavailable
python -m pytest -q
```

Environment variables are set by `conftest.py` for safe defaults.

