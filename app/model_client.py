from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

import requests


ToolRunner = Callable[[str, dict[str, Any]], Any]


@dataclass
class ModelResult:
    mode: str
    content: str
    raw: dict[str, Any] | None = None
    error: str | None = None


class OllamaGemmaClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def is_available(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=min(self.timeout_seconds, 8),
            )
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False

    def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_runner: ToolRunner,
        max_rounds: int = 4,
    ) -> ModelResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            for _ in range(max_rounds):
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "tools": tools,
                    "stream": False,
                    "format": "json",
                }
                data = self._post_chat(payload)
                message = data.get("message", {}) or {}
                messages.append(message)

                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    content = message.get("content", "")
                    return ModelResult(mode="ollama", content=content, raw=data)

                for call in tool_calls:
                    function = call.get("function", {})
                    name = function.get("name")
                    if not name:
                        continue
                    args = function.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    result = tool_runner(name, args if isinstance(args, dict) else {})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_name": name,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )

            return ModelResult(
                mode="ollama",
                content='{"summary":"Unable to finalize within tool loop.","actions":[]}',
                error="tool_loop_limit_reached",
            )
        except requests.RequestException as exc:
            return ModelResult(mode="fallback", content="", error=str(exc))


class HuggingFaceRouterClient:
    def __init__(
        self,
        token: str,
        model: str,
        base_url: str = "https://router.huggingface.co/v1",
        timeout_seconds: int = 60,
    ) -> None:
        self.token = token
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.token and self.model)

    def is_available(self) -> bool:
        if not self.is_configured():
            return False
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=min(self.timeout_seconds, 12),
            )
            return response.status_code < 500
        except requests.RequestException:
            return False

    def generate_json(self, system_prompt: str, user_prompt: str) -> ModelResult:
        if not self.is_configured():
            return ModelResult(mode="fallback", content="", error="hf_router_not_configured")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return ModelResult(mode="fallback", content="", error="hf_no_choices")
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, list):
                content = " ".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
            return ModelResult(mode="hf_router", content=str(content), raw=data)
        except requests.RequestException as exc:
            return ModelResult(mode="fallback", content="", error=str(exc))
