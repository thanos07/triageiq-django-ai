from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from django.conf import settings
from pydantic import BaseModel, ValidationError

from ai_engine.provider import OpenAICompatibleProvider, ProviderError

T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class AgentRun(Generic[T]):
    output: T
    model_name: str
    latency_ms: int
    retry_count: int
    execution_mode: str
    error_message: str = ""


class BaseAgent(Generic[T]):
    stage = "base"
    schema: type[T]
    system_prompt = ""

    def build_prompt(self, context: dict[str, Any]) -> str:
        return json.dumps(context, indent=2, default=str)

    def deterministic(self, context: dict[str, Any]) -> T:
        raise NotImplementedError

    def postprocess(self, output: T) -> T:
        return output

    def run(self, context: dict[str, Any]) -> AgentRun[T]:
        started = time.monotonic()
        if settings.AI_MODE != "live" or not settings.AI_API_KEY:
            output = self.postprocess(self.deterministic(context))
            return AgentRun(
                output=output,
                model_name="deterministic-demo-v1",
                latency_ms=max(1, int((time.monotonic() - started) * 1000)),
                retry_count=0,
                execution_mode="mock",
            )

        try:
            result = OpenAICompatibleProvider().complete_json(
                system_prompt=self.system_prompt,
                user_prompt=self.build_prompt(context),
            )
            output = self.postprocess(self.schema.model_validate(result.data))
            return AgentRun(
                output=output,
                model_name=result.model_name,
                latency_ms=result.latency_ms,
                retry_count=result.retry_count,
                execution_mode="live",
            )
        except (ProviderError, ValidationError, ValueError) as exc:
            output = self.postprocess(self.deterministic(context))
            return AgentRun(
                output=output,
                model_name="deterministic-fallback-v1",
                latency_ms=max(1, int((time.monotonic() - started) * 1000)),
                retry_count=1,
                execution_mode="fallback",
                error_message=str(exc),
            )
