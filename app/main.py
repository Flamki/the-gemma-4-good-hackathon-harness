from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.disaster_tools import (
    confidence_note,
    create_sms_alert,
    format_local_resource_packet,
    get_priority_checklist,
    infer_escalation_level,
    infer_hazard,
    infer_severity,
)
from app.knowledge import load_knowledge, rank_knowledge
from app.model_client import OllamaGemmaClient


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
KNOWLEDGE_PATH = BASE_DIR / "knowledge" / "emergency_knowledge.json"
SCENARIOS_PATH = BASE_DIR / "evaluation" / "scenarios.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))

app = FastAPI(title="RescueLoop", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

knowledge_records = load_knowledge(KNOWLEDGE_PATH)
model_client = OllamaGemmaClient(
    base_url=OLLAMA_BASE_URL,
    model=OLLAMA_MODEL,
    timeout_seconds=REQUEST_TIMEOUT_SECONDS,
)


class PlanRequest(BaseModel):
    incident: str = Field(..., min_length=10, max_length=600)
    location: str = Field(..., min_length=2, max_length=120)
    language: str = Field(default="English", min_length=2, max_length=40)
    constraints: str = Field(default="", max_length=200)


class PlanResponse(BaseModel):
    mode: str
    hazard: str
    severity: str
    escalation_level: str
    confidence_note: str
    summary: str
    first_15_min: list[str]
    next_24h: list[str]
    do_not: list[str]
    sms_alert: str
    message_delivery_note: str
    resource_packet: dict[str, Any]
    sources: list[str]
    rationale: str


def _tool_runner(name: str, args: dict[str, Any]) -> Any:
    if name == "get_priority_checklist":
        return get_priority_checklist(
            hazard=args.get("hazard", "general"),
            severity=args.get("severity", "medium"),
            constraints=args.get("constraints", ""),
        )
    if name == "create_sms_alert":
        return create_sms_alert(
            location=args.get("location", "your area"),
            hazard=args.get("hazard", "general emergency"),
            urgent_actions=args.get("urgent_actions", []),
            language=args.get("language", "English"),
        )
    if name == "format_local_resource_packet":
        return format_local_resource_packet(
            location=args.get("location", "your area"),
            hazard=args.get("hazard", "general emergency"),
        )
    return {"error": f"Unknown tool: {name}"}


def _tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_priority_checklist",
                "description": "Return urgent safety checklist based on hazard and severity.",
                "parameters": {
                    "type": "object",
                    "required": ["hazard", "severity"],
                    "properties": {
                        "hazard": {"type": "string"},
                        "severity": {"type": "string"},
                        "constraints": {"type": "string"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_sms_alert",
                "description": "Create an outbound SMS alert for volunteers or neighbors.",
                "parameters": {
                    "type": "object",
                    "required": ["location", "hazard", "urgent_actions", "language"],
                    "properties": {
                        "location": {"type": "string"},
                        "hazard": {"type": "string"},
                        "urgent_actions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "language": {"type": "string"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "format_local_resource_packet",
                "description": "Return categories of local resources to gather for disaster response.",
                "parameters": {
                    "type": "object",
                    "required": ["location", "hazard"],
                    "properties": {
                        "location": {"type": "string"},
                        "hazard": {"type": "string"},
                    },
                },
            },
        },
    ]


def _fallback_plan(
    incident: str,
    location: str,
    language: str,
    constraints: str,
    hazard: str,
    severity: str,
    snippets: list[dict[str, Any]],
) -> PlanResponse:
    checklist = get_priority_checklist(hazard=hazard, severity=severity, constraints=constraints)
    first_15 = checklist["checklist"][:5]
    next_24 = [
        "Confirm everyone is accounted for and triage injuries.",
        "Track verified local advisories every 2-3 hours.",
        "Protect clean water, medicines, and backup power.",
        "Document needs and share with responders or volunteers.",
    ]
    do_not = [
        "Do not spread unverified rumors or social media forwards.",
        "Do not return to unsafe structures without clearance.",
        "Do not consume contaminated water.",
    ]
    sms = create_sms_alert(location=location, hazard=hazard, urgent_actions=first_15, language=language)
    resources = format_local_resource_packet(location=location, hazard=hazard)
    escalation = infer_escalation_level(severity=severity, incident=incident)
    sources = [f"{s.get('title', 'Unknown source')} ({s.get('source', 'n/a')})" for s in snippets]
    if not sources:
        sources = ["Internal emergency playbook (offline fallback)"]
    return PlanResponse(
        mode="fallback",
        hazard=hazard,
        severity=severity,
        escalation_level=escalation,
        confidence_note=confidence_note(mode="fallback", source_count=len(sources), severity=severity),
        summary=f"{hazard.title()} risk assessed as {severity}. Follow immediate safety actions and coordinate local help.",
        first_15_min=first_15,
        next_24h=next_24,
        do_not=do_not,
        sms_alert=sms,
        message_delivery_note=_delivery_note(constraints),
        resource_packet=resources,
        sources=sources,
        rationale="Fallback planner used deterministic checklist due to unavailable or failing local model service.",
    )


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        return {}


def _delivery_note(constraints: str) -> str:
    constraints_lower = constraints.lower()
    if "no internet" in constraints_lower or "no network" in constraints_lower:
        return (
            "Message prepared offline. Delivery still requires SMS or internet signal; "
            "send when connectivity returns."
        )
    return "Message content is generated locally; transmission depends on available SMS or internet connectivity."


def _load_scenarios() -> list[dict[str, Any]]:
    if not SCENARIOS_PATH.exists():
        return []
    try:
        with SCENARIOS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        return []
    return []


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "ollama_available": model_client.is_available(),
        "model": OLLAMA_MODEL,
        "knowledge_records": len(knowledge_records),
        "scenario_count": len(_load_scenarios()),
    }


@app.get("/api/scenarios")
def scenarios() -> dict[str, Any]:
    return {"items": _load_scenarios()}


@app.post("/api/plan", response_model=PlanResponse)
def generate_plan(request: PlanRequest) -> PlanResponse:
    hazard = infer_hazard(request.incident)
    severity = infer_severity(request.incident)
    snippets = rank_knowledge(knowledge_records, request.incident, hazard, top_k=4)

    context_chunks = []
    for i, snippet in enumerate(snippets, start=1):
        context_chunks.append(
            f"[{i}] {snippet.get('title', 'Untitled')}: {snippet.get('content', '')}"
        )
    context_text = "\n".join(context_chunks) if context_chunks else "No external snippets found."

    system_prompt = (
        "You are a disaster-response copilot built for offline-first usage. "
        "Produce practical, non-alarmist, safety-first instructions. "
        "Use tools when useful. Return strict JSON with keys: "
        "summary, first_15_min, next_24h, do_not, sms_alert, rationale, escalation_level."
    )
    user_prompt = (
        f"Incident: {request.incident}\n"
        f"Location: {request.location}\n"
        f"Language: {request.language}\n"
        f"Constraints: {request.constraints}\n"
        f"Hazard guess: {hazard}\n"
        f"Severity guess: {severity}\n"
        f"Reference snippets:\n{context_text}\n"
    )

    result = model_client.generate_with_tools(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tools=_tool_schemas(),
        tool_runner=_tool_runner,
    )

    if result.mode != "ollama" or not result.content:
        return _fallback_plan(
            incident=request.incident,
            location=request.location,
            language=request.language,
            constraints=request.constraints,
            hazard=hazard,
            severity=severity,
            snippets=snippets,
        )

    parsed = _extract_json(result.content)
    if not parsed:
        return _fallback_plan(
            incident=request.incident,
            location=request.location,
            language=request.language,
            constraints=request.constraints,
            hazard=hazard,
            severity=severity,
            snippets=snippets,
        )

    sources = [f"{s.get('title', 'Unknown source')} ({s.get('source', 'n/a')})" for s in snippets]
    if not sources:
        sources = ["No external snippets (model-only response)"]

    return PlanResponse(
        mode="ollama",
        hazard=hazard,
        severity=severity,
        escalation_level=str(parsed.get("escalation_level", infer_escalation_level(severity=severity, incident=request.incident))),
        confidence_note=confidence_note(mode="ollama", source_count=len(sources), severity=severity),
        summary=str(parsed.get("summary", ""))[:400],
        first_15_min=[str(x) for x in parsed.get("first_15_min", [])][:7],
        next_24h=[str(x) for x in parsed.get("next_24h", [])][:7],
        do_not=[str(x) for x in parsed.get("do_not", [])][:7],
        sms_alert=str(parsed.get("sms_alert", ""))[:500],
        message_delivery_note=_delivery_note(request.constraints),
        resource_packet=format_local_resource_packet(location=request.location, hazard=hazard),
        sources=sources,
        rationale=str(parsed.get("rationale", ""))[:500],
    )
