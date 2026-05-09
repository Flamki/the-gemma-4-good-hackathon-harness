from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.main import app


SCENARIOS_PATH = BASE_DIR / "evaluation" / "scenarios.json"
RESULTS_PATH = BASE_DIR / "evaluation" / "benchmark_results.json"


def load_scenarios() -> list[dict]:
    with SCENARIOS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return []
    return data


def score_result(item: dict) -> dict:
    first_len = len(item.get("first_15_min", []))
    next_len = len(item.get("next_24h", []))
    donot_len = len(item.get("do_not", []))
    has_sms = 1 if item.get("sms_alert") else 0
    has_sources = 1 if len(item.get("sources", [])) > 0 else 0
    coverage_score = min(100, (first_len * 10) + (next_len * 8) + (donot_len * 6) + (has_sms * 10) + (has_sources * 10))
    return {
        "coverage_score": coverage_score,
        "first_actions": first_len,
        "next_actions": next_len,
        "do_not_count": donot_len,
        "mode": item.get("mode", "unknown"),
        "hazard": item.get("hazard", "unknown"),
        "severity": item.get("severity", "unknown"),
        "escalation_level": item.get("escalation_level", "unknown"),
    }


def main() -> None:
    scenarios = load_scenarios()
    client = TestClient(app)
    scenario_results = []

    for scenario in scenarios:
        payload = {
            "incident": scenario["incident"],
            "location": scenario["location"],
            "language": scenario["language"],
            "constraints": scenario.get("constraints", ""),
        }
        response = client.post("/api/plan", json=payload, timeout=120)
        data = response.json() if response.status_code == 200 else {}
        metrics = score_result(data)
        scenario_results.append(
            {
                "id": scenario["id"],
                "status_code": response.status_code,
                "metrics": metrics,
                "summary": data.get("summary", "")[:180],
            }
        )

    scores = [result["metrics"]["coverage_score"] for result in scenario_results if result["status_code"] == 200]
    summary = {
        "scenario_count": len(scenarios),
        "success_count": sum(1 for r in scenario_results if r["status_code"] == 200),
        "avg_coverage_score": round(mean(scores), 2) if scores else 0,
        "mode_breakdown": {
            "ollama": sum(1 for r in scenario_results if r["metrics"]["mode"] == "ollama"),
            "fallback": sum(1 for r in scenario_results if r["metrics"]["mode"] == "fallback"),
        },
    }

    output = {"summary": summary, "results": scenario_results}
    with RESULTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2))
    print(f"Saved benchmark results to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
