# Deploying `qless-solver` on Fly.io

This setup packages the stateless FastAPI + HTMX web app and the baked-in dictionaries (`dictionary.txt` ~10 MB and `common_words.txt` ~339 KB) into a slim Python 3.12 container running a single Uvicorn worker with `auto_stop_machines = "suspend"` for fast resume and low idle cost.

## 1. Prerequisites

- Install `flyctl` (`fly`) and sign in (`fly auth login`).
- Pick a globally unique Fly app name (e.g. `my-qless-solver`).

## 2. Configure `fly.toml`

Update `app` at the top of [fly.toml](../fly.toml) before your first deploy:

```toml
app = "my-qless-solver"
primary_region = "iad"
```

Default sizing and runtime settings in `fly.toml`:
- **VM:** `shared-cpu-1x` with `256mb` RAM (measured peak RSS stays ~117 MB using a single unified 281k-word bitmask index with per-word dictionary flags).
  - *Note:* If Phase 4 adds OCR dependencies later, bump memory to `512mb` (Tesseract/OpenCV) or `2gb` (EasyOCR/PyTorch).
- **Storage:** Stateless — no `[[mounts]]` volume required (`dictionary.txt` and `common_words.txt` are baked read-only into `/app/`).
- **Idle behavior:** `auto_stop_machines = "suspend"` (`min_machines_running = 0`), keeping the warmed dictionary index in suspended memory for quick wakeups.
- **Health check:** `GET /healthz` (`grace_period = "15s"`, `interval = "30s"`, `timeout = "5s"`).
- **Concurrency:** `soft_limit = 10`, `hard_limit = 20` requests per machine (`--workers 1`).

## 3. Create the App and Deploy

```bash
fly apps create my-qless-solver
fly deploy --remote-only
```

*(Note: Build context excludes tests, `.git`, and `.venv` via `.dockerignore` so uploads stay ~10 MB.)*

## 4. Verify

Check `/healthz`:

```bash
curl -fsS https://my-qless-solver.fly.dev/healthz
```

Expected response:

```json
{"status":"ok","dictionary_words":280887,"dictionaries":{"full":280887,"common":39038}}
```

Inspect logs if needed:

```bash
fly logs
```
