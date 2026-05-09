# RescueLoop: Offline Disaster Response Copilot

RescueLoop is a local-first emergency assistant designed for low-connectivity settings.
It uses a Gemma-compatible local model endpoint (Ollama API) plus a small offline knowledge pack to generate:

- first 15-minute safety actions,
- next 24-hour coordination plan,
- "do not" mistakes to avoid,
- a structured SMS draft for volunteers.

This project is built as a fast MVP for the Gemma 4 Good Hackathon.

## Why this matters

During floods, storms, heatwaves, and earthquakes, the first minutes matter most.
Communities often have:

- unstable internet,
- fragmented information,
- language barriers.

RescueLoop focuses on practical, grounded guidance when connectivity is poor.

## Offline boundaries (important)

RescueLoop is **offline-first for planning**:

- incident analysis and response planning run locally,
- model inference can run locally (Gemma via Ollama),
- knowledge retrieval runs from local files.

Message **transmission** is separate:

- SMS/WhatsApp delivery still requires telecom or internet connectivity,
- the app drafts messages offline and supports store-and-forward behavior.

The UI includes a local **Outbox simulation**:

- queue SMS drafts while offline,
- switch connectivity state,
- simulate send when connectivity returns.

## Architecture

1. **Frontend (`static/index.html`)**
   - Simple one-page interface for incident details and plan output.
2. **Backend (`app/main.py`)**
   - FastAPI endpoint `/api/plan` for plan generation.
3. **Knowledge layer (`knowledge/emergency_knowledge.json`)**
   - Small local emergency snippets used for grounding context.
4. **Agent tools (`app/disaster_tools.py`)**
   - Checklist generation, SMS drafting, and resource packet formatting.
5. **Model adapter (`app/model_client.py`)**
   - Calls local Ollama `/api/chat` with function/tool schemas.
   - Falls back to deterministic logic when model service is unavailable.

## Gemma usage

RescueLoop is designed to run with Gemma-family models served locally.
Default model variable:

- `OLLAMA_MODEL=gemma3`

For the hackathon, set this to your Gemma 4 model tag available in your local runtime.

## Local runtime setup (Ollama)

If Ollama is installed locally:

1. Pull a Gemma model in Ollama.
2. Set env vars:

```bash
set OLLAMA_BASE_URL=http://localhost:11434
set OLLAMA_MODEL=<your_gemma_model_tag>
```

3. Start the API and verify:

```bash
uvicorn app.main:app --reload --port 8000
curl http://127.0.0.1:8000/health
```

`ollama_available: true` indicates local model mode is reachable.

## Quickstart

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optional: configure environment variables:

```bash
set OLLAMA_BASE_URL=http://localhost:11434
set OLLAMA_MODEL=gemma3
set REQUEST_TIMEOUT_SECONDS=60
```

4. Run the app:

```bash
uvicorn app.main:app --reload --port 8000
```

5. Open:

- `http://127.0.0.1:8000`

## Production deployment

### Option A: Docker (recommended)

1. Start local production container:

```bash
powershell -ExecutionPolicy Bypass -File scripts/deploy_local.ps1
```

2. Open:

- `http://127.0.0.1:8000`

3. Stop:

```bash
powershell -ExecutionPolicy Bypass -File scripts/stop_local.ps1
```

### Option B: Temporary public demo URL (for judging demo access)

After local deploy is running:

```bash
powershell -ExecutionPolicy Bypass -File scripts/start_tunnel_bg.ps1
```

This creates a temporary public URL tunnel to your local app and prints the URL.

Stop tunnel:

```bash
powershell -ExecutionPolicy Bypass -File scripts/stop_tunnel.ps1
```

### Option C: Render cloud deploy

This repo includes `render.yaml` and `Procfile`.
On Render, connect the repo and deploy as a Python web service.

Start command:

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

Health check path:

- `/health`

Important: hosted cloud instances usually do not have your local Ollama runtime. In that case, RescueLoop will run in deterministic fallback mode unless you provide a reachable model endpoint.

## Evaluation harness

Run scenario benchmark:

```bash
python evaluation/run_benchmark.py
```

This executes multiple disaster scenarios from `evaluation/scenarios.json` and writes:

- `evaluation/benchmark_results.json`

with a simple reliability/coverage summary for writeup reporting.

## Tests

```bash
python -m pytest -q
```

## API

`POST /api/plan`

Example payload:

```json
{
  "incident": "Heavy rain, river overflow likely, two elderly residents, no reliable internet.",
  "location": "Ward 8, Riverside Town",
  "language": "English",
  "constraints": "Power cuts expected; only SMS works intermittently."
}
```

## Demo strategy for judges

1. Show a realistic flood/cyclone incident input.
2. Generate the emergency plan live.
3. Highlight:
   - first 15-minute checklist,
   - structured SMS draft for volunteer coordination,
   - outbox queue behavior in no-connectivity mode,
   - fallback reliability when local model is offline.
4. Mention local-first design and multilingual support.

## Limitations and next steps

- Current knowledge pack is small; expand with district-specific verified advisories.
- Add geocoded shelters and local hotline databases.
- Add audit logs and confidence scoring for safety review workflows.
- Add post-training/evaluation pipeline using public agent traces such as AgentTrove for stronger tool-use reliability.
