from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from openai import OpenAI

from ai_engine.guardrails import sanitize_payload


class ProviderError(RuntimeError):
    pass


@dataclass(slots=True)
class CompletionResult:
    data: dict[str, Any]
    model_name: str
    latency_ms: int
    retry_count: int = 0


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ProviderError("The model did not return a JSON object.")
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ProviderError("The model response must be a JSON object.")
    return value


class OpenAICompatibleProvider:
    """Provider used with Groq today and any OpenAI-compatible endpoint later."""

    def __init__(self) -> None:
        if not settings.AI_API_KEY:
            raise ProviderError("AI_API_KEY is not configured.")
        self.client = OpenAI(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
            timeout=settings.AI_TIMEOUT_SECONDS,
        )
        self.model_name = settings.AI_MODEL

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> CompletionResult:
        last_error: Exception | None = None
        models = [settings.AI_MODEL]
        if settings.AI_FALLBACK_MODEL and settings.AI_FALLBACK_MODEL != settings.AI_MODEL:
            models.append(settings.AI_FALLBACK_MODEL)

        for retry_count, model in enumerate(models):
            started = time.monotonic()
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_completion_tokens=2200,
                )
                content = response.choices[0].message.content or ""
                return CompletionResult(
                    data=sanitize_payload(_extract_json(content)),
                    model_name=model,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    retry_count=retry_count,
                )
            except Exception as exc:  # Provider errors are converted to a safe fallback by agents.
                last_error = exc

        raise ProviderError(str(last_error or "AI provider request failed."))
