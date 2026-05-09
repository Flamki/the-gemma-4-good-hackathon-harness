from __future__ import annotations

from typing import Any


def infer_hazard(incident: str) -> str:
    text = incident.lower()
    hazard_keywords = {
        "flood": ["flood", "waterlogging", "overflow", "river"],
        "earthquake": ["earthquake", "tremor", "aftershock"],
        "fire": ["fire", "smoke", "burning"],
        "heatwave": ["heat", "heatwave", "dehydration", "hot weather"],
        "cyclone": ["cyclone", "hurricane", "typhoon", "storm surge"],
        "landslide": ["landslide", "mudslide"],
    }
    for hazard, words in hazard_keywords.items():
        if any(word in text for word in words):
            return hazard
    return "general"


def infer_severity(incident: str) -> str:
    text = incident.lower()
    high = ["trapped", "injured", "collapse", "urgent", "critical", "bleeding"]
    medium = ["stuck", "power outage", "blocked road", "no water"]
    if any(word in text for word in high):
        return "high"
    if any(word in text for word in medium):
        return "medium"
    return "low"


def get_priority_checklist(hazard: str, severity: str, constraints: str = "") -> dict[str, Any]:
    base = {
        "flood": [
            "Move to higher ground immediately.",
            "Switch off main electricity if safe.",
            "Avoid walking or driving through moving water.",
            "Keep clean drinking water in sealed containers.",
        ],
        "earthquake": [
            "Drop, cover, and hold on during shaking.",
            "Move away from damaged structures.",
            "Expect aftershocks and keep an exit route.",
            "Check gas and electrical hazards before re-entry.",
        ],
        "fire": [
            "Evacuate and stay low to avoid smoke.",
            "Close doors behind you to slow fire spread.",
            "Do not use elevators.",
            "Call emergency services from a safe location.",
        ],
        "heatwave": [
            "Hydrate immediately with clean water.",
            "Move vulnerable people to shade or cool space.",
            "Avoid outdoor activity during peak heat hours.",
            "Use wet cloth cooling for overheating symptoms.",
        ],
        "cyclone": [
            "Shelter away from windows and weak roofs.",
            "Secure loose objects and critical supplies.",
            "Track official alerts on battery-powered radio.",
            "Do not go outside during temporary calm.",
        ],
        "landslide": [
            "Move away from slopes and drainage channels.",
            "Watch for secondary slides and falling debris.",
            "Avoid crossing unstable terrain.",
            "Report blocked roads and cut utilities safely.",
        ],
        "general": [
            "Prioritize human safety over property.",
            "Check injuries and provide first aid if trained.",
            "Use verified local authority advisories.",
            "Document needs for rescue coordination.",
        ],
    }
    first = base.get(hazard, base["general"])
    if severity == "high":
        first = ["Call emergency services immediately."] + first
    if constraints:
        first.append(f"Constraint note: {constraints}")
    return {"hazard": hazard, "severity": severity, "checklist": first[:6]}


def create_sms_alert(location: str, hazard: str, urgent_actions: list[str], language: str = "English") -> str:
    action_text = "; ".join(urgent_actions[:3]) if urgent_actions else "Follow local emergency guidance."
    return (
        f"[Emergency Alert] {hazard.title()} risk near {location}. "
        f"Immediate actions: {action_text}. "
        f"Need help? Reply with people count, injuries, and exact location. "
        f"(Language preference: {language})"
    )


def format_local_resource_packet(location: str, hazard: str) -> dict[str, Any]:
    return {
        "location": location,
        "hazard": hazard,
        "resource_template": [
            "Nearest clinic/hospital",
            "Nearest evacuation shelter",
            "Safe water point",
            "Local volunteer or district hotline",
        ],
    }


def infer_escalation_level(severity: str, incident: str) -> str:
    text = incident.lower()
    if severity == "high" or any(word in text for word in ["child", "elderly", "pregnant", "disabled"]):
        return "urgent"
    if severity == "medium":
        return "priority"
    return "monitor"


def confidence_note(mode: str, source_count: int, severity: str) -> str:
    if mode == "ollama" and source_count >= 2:
        base = "Medium confidence: model response grounded with local references."
    elif mode == "ollama":
        base = "Moderate confidence: model response with limited grounding references."
    else:
        base = "Baseline confidence: deterministic fallback response used."
    if severity == "high":
        return base + " High-severity incidents should be confirmed with emergency responders."
    return base
