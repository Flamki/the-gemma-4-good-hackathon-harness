from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
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
from app.message_sender import SmsSender
from app.model_client import HuggingFaceRouterClient, ModelResult, OllamaGemmaClient


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
KNOWLEDGE_PATH = BASE_DIR / "knowledge" / "emergency_knowledge.json"
SCENARIOS_PATH = BASE_DIR / "evaluation" / "scenarios.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))
INFERENCE_BACKEND = os.getenv("INFERENCE_BACKEND", "auto").lower()
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "google/gemma-2-2b-it")
HF_BASE_URL = os.getenv("HF_BASE_URL", "https://router.huggingface.co/v1")
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "none")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

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
hf_client = HuggingFaceRouterClient(
    token=HF_TOKEN,
    model=HF_MODEL,
    base_url=HF_BASE_URL,
    timeout_seconds=REQUEST_TIMEOUT_SECONDS,
)
sms_sender = SmsSender(
    provider=SMS_PROVIDER,
    twilio_account_sid=TWILIO_ACCOUNT_SID,
    twilio_auth_token=TWILIO_AUTH_TOKEN,
    twilio_from_number=TWILIO_FROM_NUMBER,
    timeout_seconds=REQUEST_TIMEOUT_SECONDS,
)
alert_store: list[dict[str, Any]] = []


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


class SmsSendRequest(BaseModel):
    to_number: str = Field(..., min_length=6, max_length=32)
    message: str = Field(..., min_length=1, max_length=1000)


class SmsSendResponse(BaseModel):
    delivered: bool
    provider: str
    message: str
    provider_message_id: str | None = None
    error: str | None = None


class AlertCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    message: str = Field(..., min_length=3, max_length=600)
    severity: str = Field(default="high", min_length=3, max_length=20)
    location: str = Field(default="", max_length=120)
    source: str = Field(default="command-center", max_length=60)


class AlertRecord(BaseModel):
    id: str
    title: str
    message: str
    severity: str
    location: str
    source: str
    created_at: str
    acknowledged: bool


class AlertListResponse(BaseModel):
    items: list[AlertRecord]


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


def _run_model(
    system_prompt: str,
    user_prompt: str,
    tools: list[dict[str, Any]],
) -> ModelResult:
    backend = INFERENCE_BACKEND

    if backend == "ollama":
        return model_client.generate_with_tools(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools,
            tool_runner=_tool_runner,
        )

    if backend == "hf_router":
        return hf_client.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)

    # auto mode: prefer local ollama, then hosted HF router, then fallback
    if model_client.is_available():
        return model_client.generate_with_tools(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools,
            tool_runner=_tool_runner,
        )
    if hf_client.is_configured():
        return hf_client.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
    return ModelResult(mode="fallback", content="", error="no_available_backend")


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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_severity(value: str) -> str:
    v = value.lower().strip()
    if v in {"critical", "high", "medium", "low"}:
        return v
    return "high"


def _prune_alert_store(max_items: int = 200) -> None:
    if len(alert_store) > max_items:
        del alert_store[: len(alert_store) - max_items]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/companion")
def companion() -> FileResponse:
    return FileResponse(STATIC_DIR / "companion.html")


@app.get("/manifest.webmanifest")
def manifest() -> FileResponse:
    return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/service-worker.js")
def service_worker() -> FileResponse:
    return FileResponse(STATIC_DIR / "service-worker.js", media_type="application/javascript")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "ollama_available": model_client.is_available(),
        "hf_router_configured": hf_client.is_configured(),
        "hf_router_available": hf_client.is_available() if hf_client.is_configured() else False,
        "inference_backend": INFERENCE_BACKEND,
        "model": OLLAMA_MODEL,
        "hf_model": HF_MODEL,
        "sms_provider": SMS_PROVIDER,
        "sms_configured": sms_sender.is_configured(),
        "active_alerts": sum(1 for x in alert_store if not x.get("acknowledged", False)),
        "knowledge_records": len(knowledge_records),
        "scenario_count": len(_load_scenarios()),
    }


@app.get("/api/scenarios")
def scenarios() -> dict[str, Any]:
    return {"items": _load_scenarios()}


@app.post("/api/send_sms", response_model=SmsSendResponse)
def send_sms(request: SmsSendRequest) -> SmsSendResponse:
    result = sms_sender.send_sms(to_number=request.to_number, body=request.message)
    return SmsSendResponse(
        delivered=result.delivered,
        provider=result.provider,
        message=result.message,
        provider_message_id=result.provider_message_id,
        error=result.error,
    )


@app.post("/api/alerts", response_model=AlertRecord)
def create_alert(request: AlertCreateRequest) -> AlertRecord:
    item = {
        "id": str(uuid.uuid4()),
        "title": request.title.strip(),
        "message": request.message.strip(),
        "severity": _normalize_severity(request.severity),
        "location": request.location.strip(),
        "source": request.source.strip() or "command-center",
        "created_at": _now_iso(),
        "acknowledged": False,
    }
    alert_store.append(item)
    _prune_alert_store()
    return AlertRecord(**item)


@app.get("/api/alerts", response_model=AlertListResponse)
def list_alerts(since_id: str | None = None, unacked_only: bool = True, limit: int = 50) -> AlertListResponse:
    items = alert_store
    if since_id:
        idx = next((i for i, x in enumerate(items) if x["id"] == since_id), -1)
        if idx >= 0:
            items = items[idx + 1 :]
    if unacked_only:
        items = [x for x in items if not x.get("acknowledged", False)]
    items = items[-max(1, min(limit, 200)) :]
    return AlertListResponse(items=[AlertRecord(**x) for x in items])


@app.post("/api/alerts/{alert_id}/ack", response_model=AlertRecord)
def acknowledge_alert(alert_id: str) -> AlertRecord:
    for item in alert_store:
        if item["id"] == alert_id:
            item["acknowledged"] = True
            return AlertRecord(**item)
    # Return a lightweight not-found record-like response to keep client flow simple.
    return AlertRecord(
        id=alert_id,
        title="Not found",
        message="Alert no longer available.",
        severity="low",
        location="",
        source="system",
        created_at=_now_iso(),
        acknowledged=True,
    )


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

    result = _run_model(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tools=_tool_schemas(),
    )

    if result.mode not in {"ollama", "hf_router"} or not result.content:
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
        mode=result.mode if result.mode in {"ollama", "hf_router"} else "fallback",
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
