# RescueLoop: Offline Disaster Response Copilot with Gemma

## Subtitle
Local-first, multilingual emergency guidance for low-connectivity communities

## Track
Global Resilience

## 1. Problem
Disaster response often fails in the first hour because information is fragmented, connectivity is unstable, and instructions are not localized for community constraints. In many regions, people cannot depend on cloud tools during floods, cyclones, heatwaves, or earthquakes. They need immediate, practical, and trustworthy guidance that still works under poor internet conditions.

## 2. Solution
We built **RescueLoop**, an offline-first disaster response copilot powered by a Gemma-family local model endpoint. RescueLoop accepts a short incident report and returns:

1. First 15-minute priority actions
2. Next 24-hour coordination plan
3. Critical "do not" safety errors to avoid
4. A structured SMS draft template for volunteer coordination

This design focuses on fast decisions, low bandwidth communication, and practical field usefulness.

### Offline scope clarification
RescueLoop is offline-first for local planning and inference.  
Actual message transmission (SMS/WhatsApp/internet channels) still depends on network availability.  
The system therefore uses a store-and-forward pattern: draft locally now, send when connectivity returns.

## 3. Why Gemma
Gemma enables local, private, and low-latency reasoning suitable for edge use cases where cloud dependence is risky. We use a Gemma-compatible local runtime interface (Ollama chat API) and tool-calling patterns to keep output structured and operational.

Our approach leverages:

1. **Local inference** for continuity under weak internet
2. **Tool-calling** for deterministic, auditable helper functions
3. **Grounding context** from an offline emergency knowledge pack

## 4. System Architecture
RescueLoop has five components:

1. **Web UI (`static/index.html`)**
   - Collects incident, location, language preference, and constraints.
2. **API Layer (`app/main.py`)**
   - Exposes `/api/plan` endpoint and orchestrates planning.
3. **Knowledge Retrieval (`app/knowledge.py`)**
   - Ranks local emergency snippets by hazard and incident keywords.
4. **Agent Tools (`app/disaster_tools.py`)**
   - Generates checklists, SMS templates, and local resource packet formats.
5. **Model Adapter (`app/model_client.py`)**
   - Calls local model with tools; falls back to deterministic safety plan if model is unavailable.

## 5. Gemma-specific Technical Flow
For each request:

1. Infer hazard and severity from incident text.
2. Retrieve top relevant knowledge snippets.
3. Build structured prompt and tool schema.
4. Query local model through tool-enabled chat.
5. Execute requested tools and continue loop.
6. Return strict JSON response to UI.
7. If model unavailable, fallback planner generates a safe minimal plan.

This hybrid design improves reliability for real-world deployments where local model services may intermittently fail.

## 6. Real-world Utility
RescueLoop is designed for community volunteers, NGOs, and local response coordinators. It is useful when:

1. Data connectivity is unstable
2. Coordination must happen over SMS
3. Households need plain-language instructions fast

The generated SMS format supports concise reporting: people count, injury status, and exact location.

## 7. Safety and Trust
Safety guardrails include:

1. Non-alarmist response style requirement in system prompt
2. Deterministic checklist tool for baseline consistency
3. "Do not" section to prevent common harmful behaviors
4. Grounding references shown in output sources
5. Fallback mode explicitly marked to avoid false confidence

## 8. Evaluation
We include a reproducible benchmark harness (`evaluation/run_benchmark.py`) over multi-hazard scenarios (`evaluation/scenarios.json`).  
It reports:

1. Success rate across scenarios
2. Coverage score based on structured action completeness
3. Mode breakdown (local model vs deterministic fallback)
4. Hazard/severity/escalation consistency per scenario

This provides transparent verification that outputs are not one-off demo artifacts.

## 9. Current Limitations
1. Knowledge pack is intentionally small for MVP and should be expanded with verified district-level guidance.
2. Location intelligence is currently template-based and not yet geocoded.
3. We still need calibrated confidence scoring and escalation logic for high-risk medical instructions.

## 10. Future Work
1. District and language specific disaster packs with citation links.
2. Shelter and hotline lookup integration with cached geodata.
3. Multi-agent simulation mode for training community volunteers.
4. Post-training and tool-use reliability optimization using public agent datasets such as AgentTrove.

## 11. Conclusion
RescueLoop demonstrates how Gemma-powered local intelligence can improve crisis response for communities where connectivity, time, and trust are constrained. By combining local inference, tool-calling, and grounded emergency context, this project delivers practical impact in the moments that matter most.
