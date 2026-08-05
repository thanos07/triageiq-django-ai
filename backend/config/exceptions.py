from typing import Any

from rest_framework.views import exception_handler


def _first_message(value: Any) -> str:
    if isinstance(value, dict):
        for child in value.values():
            return _first_message(child)
    if isinstance(value, (list, tuple)) and value:
        return _first_message(value[0])
    if value is not None:
        return str(value)
    return "Request validation failed."


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    original = response.data
    message = _first_message(original.get("detail")) if isinstance(original, dict) and "detail" in original else _first_message(original)
    response.data = {
        "error": {
            "message": message,
            "status": response.status_code,
            "fields": original if not (isinstance(original, dict) and set(original) == {"detail"}) else None,
        }
    }
    return response
