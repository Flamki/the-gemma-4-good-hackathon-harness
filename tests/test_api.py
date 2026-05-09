from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "knowledge_records" in data


def test_plan_endpoint_returns_structured_payload() -> None:
    payload = {
        "incident": "Heavy rainfall and likely flooding near homes with elderly residents and unstable internet.",
        "location": "Ward 8 Riverside Town",
        "language": "English",
        "constraints": "Power cuts expected.",
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    for key in [
        "mode",
        "hazard",
        "severity",
        "escalation_level",
        "confidence_note",
        "summary",
        "first_15_min",
        "next_24h",
        "do_not",
        "sms_alert",
        "message_delivery_note",
        "resource_packet",
        "sources",
        "rationale",
    ]:
        assert key in data
    assert isinstance(data["first_15_min"], list)
    assert isinstance(data["resource_packet"], dict)


def test_send_sms_endpoint_simulation_mode_when_not_configured() -> None:
    payload = {"to_number": "+15551234567", "message": "Test alert message"}
    response = client.post("/api/send_sms", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["delivered"] is False
    assert "provider" in data
    assert data["error"] in {"provider_not_configured", "invalid_payload"}


def test_alert_lifecycle_create_list_ack() -> None:
    create_payload = {
        "title": "Bridge Collapse Risk",
        "message": "Do not use East Bridge. Move civilians to alternate route.",
        "severity": "critical",
        "location": "Zone 4",
        "source": "command-center",
    }
    created = client.post("/api/alerts", json=create_payload)
    assert created.status_code == 200
    c = created.json()
    assert c["title"] == create_payload["title"]
    alert_id = c["id"]

    listed = client.get("/api/alerts")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert any(x["id"] == alert_id for x in items)

    acked = client.post(f"/api/alerts/{alert_id}/ack")
    assert acked.status_code == 200
    a = acked.json()
    assert a["acknowledged"] is True
