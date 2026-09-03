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


@dataclass(slots=True)
class ToolCallRequest:
    id: str
    name: str
    arguments: str


@dataclass(slots=True)
class ToolTurnResult:
    content: str
    tool_calls: list[ToolCallRequest]
    assistant_message: dict[str, Any]
    model_name: str
    latency_ms: int
    retry_count: int = 0


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ProviderError("The model did not return a JSON object.")
        try:
            value = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ProviderError("The model returned invalid JSON.") from exc
    if not isinstance(value, dict):
        raise ProviderError("The model response must be a JSON object.")
    return value


# Backwards-compatible internal alias for any existing imports.
_extract_json = extract_json_object


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

    @staticmethod
    def _models() -> list[str]:
        models = [settings.AI_MODEL]
        if settings.AI_FALLBACK_MODEL and settings.AI_FALLBACK_MODEL != settings.AI_MODEL:
            models.append(settings.AI_FALLBACK_MODEL)
        return models

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> CompletionResult:
        last_error: Exception | None = None

        for retry_count, model in enumerate(self._models()):
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
                    data=sanitize_payload(extract_json_object(content)),
                    model_name=model,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    retry_count=retry_count,
                )
            except Exception as exc:  # Provider errors are converted to a safe fallback by agents.
                last_error = exc

        raise ProviderError(str(last_error or "AI provider request failed."))

    def complete_tool_turn(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ToolTurnResult:
        """Run one chat-completions turn, optionally allowing local function calls.

        This method does not execute tools. It only returns the model's requested
        function calls and a serializable assistant message that the caller can
        append to the conversation after validating/executing those calls.
        """
        last_error: Exception | None = None

        for retry_count, model in enumerate(self._models()):
            started = time.monotonic()
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "max_completion_tokens": 1600,
                }
                if tools:
                    kwargs.update(
                        {
                            "tools": tools,
                            "tool_choice": "auto",
                            "parallel_tool_calls": False,
                        }
                    )

                response = self.client.chat.completions.create(**kwargs)
                message = response.choices[0].message
                tool_calls: list[ToolCallRequest] = []
                serialized_calls: list[dict[str, Any]] = []

                for call in message.tool_calls or []:
                    name = str(call.function.name or "")
                    arguments = str(call.function.arguments or "{}")
                    call_id = str(call.id or "")
                    tool_calls.append(
                        ToolCallRequest(
                            id=call_id,
                            name=name,
                            arguments=arguments,
                        )
                    )
                    serialized_calls.append(
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": arguments,
                            },
                        }
                    )

                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": message.content or "",
                }
                if serialized_calls:
                    assistant_message["tool_calls"] = serialized_calls

                return ToolTurnResult(
                    content=message.content or "",
                    tool_calls=tool_calls,
                    assistant_message=assistant_message,
                    model_name=model,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    retry_count=retry_count,
                )
            except Exception as exc:
                last_error = exc

        raise ProviderError(str(last_error or "AI provider tool turn failed."))
