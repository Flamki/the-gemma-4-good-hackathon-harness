from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class SmsSendResult:
    delivered: bool
    provider: str
    message: str
    provider_message_id: str | None = None
    error: str | None = None


class SmsSender:
    def __init__(
        self,
        provider: str = "none",
        twilio_account_sid: str = "",
        twilio_auth_token: str = "",
        twilio_from_number: str = "",
        timeout_seconds: int = 30,
    ) -> None:
        self.provider = provider.lower().strip()
        self.twilio_account_sid = twilio_account_sid.strip()
        self.twilio_auth_token = twilio_auth_token.strip()
        self.twilio_from_number = twilio_from_number.strip()
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        if self.provider != "twilio":
            return False
        return bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number)

    def send_sms(self, to_number: str, body: str) -> SmsSendResult:
        to_number = to_number.strip()
        body = body.strip()
        if not to_number or not body:
            return SmsSendResult(
                delivered=False,
                provider=self.provider or "none",
                message="Missing recipient or message body.",
                error="invalid_payload",
            )

        if self.provider != "twilio" or not self.is_configured():
            return SmsSendResult(
                delivered=False,
                provider=self.provider or "none",
                message="SMS provider not configured; simulated mode only.",
                error="provider_not_configured",
            )

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
        payload = {"From": self.twilio_from_number, "To": to_number, "Body": body}
        try:
            response = requests.post(
                url,
                data=payload,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                timeout=self.timeout_seconds,
            )
            if 200 <= response.status_code < 300:
                data: dict[str, Any] = response.json()
                return SmsSendResult(
                    delivered=True,
                    provider="twilio",
                    message="SMS sent successfully.",
                    provider_message_id=str(data.get("sid", "")) or None,
                )
            return SmsSendResult(
                delivered=False,
                provider="twilio",
                message="Twilio rejected SMS request.",
                error=f"http_{response.status_code}",
            )
        except requests.RequestException as exc:
            return SmsSendResult(
                delivered=False,
                provider="twilio",
                message="Twilio request failed.",
                error=str(exc),
            )
