from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error, request


DEFAULT_CONNECT_TIMEOUT_SECONDS = 0.8


class LlmClientError(Exception):
    pass


@dataclass(frozen=True)
class LlmJsonResponse:
    payload: dict[str, object]
    model: str


class LlmClient:
    def __init__(self, *, base_url: str, model: str, timeout_ms: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = max(timeout_ms, 1) / 1000

    def complete_json(self, *, prompt: str, system_prompt: str) -> LlmJsonResponse:
        endpoint = f"{self.base_url}/api/generate"
        body = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
            },
        }
        payload = json.dumps(body).encode("utf-8")
        req = request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        timeout = max(self.timeout_seconds, DEFAULT_CONNECT_TIMEOUT_SECONDS)
        try:
            with request.urlopen(req, timeout=timeout) as response:
                raw_text = response.read().decode("utf-8")
        except error.HTTPError as exc:
            raise LlmClientError(f"llm_http_{exc.code}") from exc
        except error.URLError as exc:
            raise LlmClientError("llm_connection_error") from exc
        except TimeoutError as exc:
            raise LlmClientError("llm_timeout") from exc

        try:
            envelope = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise LlmClientError("llm_invalid_envelope_json") from exc
        if not isinstance(envelope, dict):
            raise LlmClientError("llm_invalid_envelope")

        response_text = envelope.get("response")
        if not isinstance(response_text, str) or not response_text.strip():
            raise LlmClientError("llm_missing_response")

        try:
            json_payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise LlmClientError("llm_invalid_response_json") from exc
        if not isinstance(json_payload, dict):
            raise LlmClientError("llm_invalid_response_shape")

        model = envelope.get("model")
        resolved_model = model if isinstance(model, str) and model else self.model
        return LlmJsonResponse(payload=json_payload, model=resolved_model)
