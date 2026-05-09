# RescueLoop 3-Minute Video Script

## 0:00 - 0:20 | Hook
"When disasters hit, the first hour saves lives. But in many places, internet fails exactly when people need guidance most."

"We built **RescueLoop**, an offline-first disaster response copilot powered by Gemma-family local intelligence."

## 0:20 - 0:45 | Problem
"During floods, cyclones, and earthquakes, families and volunteers face three barriers: fragmented information, low bandwidth, and language gaps."

"Most AI tools assume stable cloud connectivity. RescueLoop is designed for the opposite condition."

## 0:45 - 1:40 | Live Demo
1. Show the input form.
2. Enter incident:
   - heavy rain
   - river overflow risk
   - elderly residents
   - unstable internet
3. Click **Generate Response Plan**.
4. Show output sections:
   - first 15-minute actions
   - next 24-hour plan
   - do-not mistakes
   - volunteer SMS alert
   - escalation level + confidence note + resource handoff packet
5. Click **Queue In Outbox**.
6. Keep connectivity as **No** and show queued state.
7. Switch connectivity to **Yes**, click **Try Send Queued**, show sent state.
5. Call out mode badge:
   - local model mode or fallback mode.

Voice-over:
"RescueLoop returns immediate, practical guidance and a structured SMS so local volunteers can coordinate quickly, even on weak networks."

"The app drafts message content offline; delivery happens when SMS or internet signal is available."

## 1:40 - 2:20 | Technical Depth
"Architecture has five parts: web UI, FastAPI orchestration, local knowledge retrieval, deterministic disaster tools, and local model adapter."

"Gemma-compatible local inference is integrated via tool-calling. The model can call functions for checklists, SMS drafting, and resource packet formatting."

"If local inference is unavailable, RescueLoop degrades gracefully into a deterministic fallback planner rather than failing silently."

"We also include a multi-scenario benchmark harness to verify reliability beyond a single scripted demo."

## 2:20 - 2:45 | Impact
"This system can support NGOs, ward-level volunteers, and families in low-connectivity regions."

"The goal is not generic chatbot output. The goal is usable decisions in the first critical minutes."

## 2:45 - 3:00 | Close
"RescueLoop shows how local Gemma intelligence can turn limited infrastructure into actionable resilience."

"Thank you."
