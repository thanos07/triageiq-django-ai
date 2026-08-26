from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_engine.tools.demo_evidence import get_service_record, normalize_service_name


class ServiceMetricsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    service_name: str = Field(min_length=1, max_length=120)


def get_service_metrics(service_name: str) -> dict[str, Any]:
    service = normalize_service_name(service_name)
    record = get_service_record(service)
    return {
        "service_name": service,
        "found": record is not None,
        "window": "last_15m" if record else "",
        "values": list((record or {}).get("metrics", []))[:8],
    }
