# Kaggle Submission Packet (Ready to Paste)

## Title
RescueLoop: Offline-First Disaster Response Copilot with Gemma 4

## Subtitle
Local-first emergency planning, store-and-forward messaging, and multilingual response support for low-connectivity communities

## Track
Global Resilience

## Live Demo URL
https://the-gemma-4-good-hackathon-harness.vercel.app

## Public Code Repository
https://github.com/Flamki/the-gemma-4-good-hackathon-harness

## Project Summary
RescueLoop is an offline-first disaster response copilot designed for the first critical minutes of floods, cyclones, heatwaves, fires, and earthquakes.  
It generates practical response plans, hazard-specific "do not" warnings, and structured volunteer SMS drafts that can be sent when connectivity returns.

The system is designed for low-connectivity environments where cloud dependence is risky and response quality needs to remain stable.

## Gemma 4 Usage
RescueLoop uses Gemma-family inference in two deployment modes:

1. Local-first mode through Ollama (for edge/community setups).
2. Hosted mode via Hugging Face Inference Providers on Vercel.

Current production demo is configured with hosted Gemma 4 route:

- `HF_MODEL=google/gemma-4-26B-A4B-it`
- Backend mode: `hf_router`

## Architecture
1. Frontend web app (`static/index.html`) for incident intake and action display.
2. FastAPI backend (`app/main.py`) for planning orchestration.
3. Emergency tools (`app/disaster_tools.py`) for deterministic checklist generation, resource packet formatting, and SMS drafting.
4. Grounding layer (`knowledge/emergency_knowledge.json`) for local emergency references.
5. Model adapter (`app/model_client.py`) with backend switching:
   - `ollama`
   - `hf_router`
   - `auto`

## Offline Scope Clarification
RescueLoop is offline-first for **planning and drafting**:

1. Incident reasoning and response planning can run locally.
2. Knowledge retrieval is local-file based.
3. Message text is generated offline.

Message delivery itself requires network infrastructure (SMS/internet).  
To address this, RescueLoop includes a **store-and-forward outbox simulation**:

1. Queue message drafts while offline.
2. Send when connectivity becomes available.

## Real-World Utility
RescueLoop targets:

1. Community volunteers and ward-level coordinators.
2. Families managing elderly or medically vulnerable members.
3. Low-bandwidth settings where short, structured instructions are critical.

## Safety and Trust
1. Non-alarmist, safety-first system behavior.
2. "Do not" section to reduce harmful actions.
3. Grounding source snippets surfaced in output.
4. Explicit delivery note distinguishing offline drafting vs network transmission.
5. Deterministic fallback path when an inference backend is unavailable.

## Evaluation and Reliability
The repo includes an evaluation harness over multi-hazard scenarios.

- Local benchmark artifact: `evaluation/benchmark_results.json`
- Live Vercel smoke benchmark artifact: `evaluation/vercel_smoke_results.json`

Live production benchmark result:

1. Scenario count: 5
2. Success count: 5
3. `hf_router` responses: 5
4. Fallback responses: 0

## Video Notes (for 3-minute demo)
1. Show a flood or cyclone input with constrained connectivity.
2. Show first-15-minute actions, next-24h actions, and do-not list.
3. Show SMS draft and outbox queue/store-and-forward behavior.
4. Mention live hosted Gemma 4 backend and local-first architecture option.

## What to Attach in Kaggle Writeup
1. YouTube video link (public, <= 3 min).
2. Public GitHub repo link.
3. Live demo URL.
4. Cover image in media gallery.
