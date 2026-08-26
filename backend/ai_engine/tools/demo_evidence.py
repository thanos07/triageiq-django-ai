from __future__ import annotations

from typing import Any


# Local, deterministic operational evidence used only by the demo investigation tools.
# Keeping it separate from incident input prevents the tools from simply echoing the
# text the user submitted while still avoiding external observability dependencies.
_SERVICE_PROFILES: dict[str, dict[str, Any]] = {
    "orders-api": {
        "logs": ["PostgreSQL connection pool exhausted", "database rejected connection: too many clients"],
        "metrics": [("http_5xx_percent", 0.4, 21.6, "%"), ("db_active_connections", 118, 500, "connections")],
    },
    "inventory-db": {
        "logs": ["read replica WAL replay lag exceeded 500 seconds", "stale reads detected while replica remains behind primary"],
        "metrics": [("replica_replay_lag_seconds", 4, 548, "s"), ("replica_apply_rate", 1.0, 0.23, "ratio")],
    },
    "checkout-db": {
        "deployment": ("order-discount-2026.08.26", "order-discount-2026.08.20", "Order-discount transaction flow updated"),
        "logs": ["deadlock detected while updating checkout and discount rows", "transaction aborted after lock wait timeout"],
        "metrics": [("deadlocks_per_min", 0, 18, "count/min"), ("transaction_abort_percent", 0.2, 14.7, "%")],
    },
    "product-catalog": {
        "deployment": ("config-2026.08.26.1", "config-2026.08.21.3", "ConfigMap rollout"),
        "logs": ["startup failed: connection refused to config-service", "container exited with code 1; CrashLoopBackOff"],
        "metrics": [("ready_pods", 8, 0, "pods"), ("container_restarts", 0, 41, "count")],
    },
    "recommendation-engine": {
        "deployment": ("model-8.4-large", "model-8.3", "Larger recommendation model artifact released"),
        "logs": ["container terminated: OOMKilled exit code 137", "OOMKilled after loading model artifact"],
        "metrics": [("memory_working_set_gib", 2.1, 4.0, "GiB"), ("oom_kills", 0, 6, "count")],
    },
    "search-api": {
        "deployment": ("ranking-feature-2026.08.26", "ranking-feature-2026.08.19", "New ranking feature enabled"),
        "logs": ["request deadline exceeded while CPU throttling is active", "ranking request queue exceeded normal threshold"],
        "metrics": [("cpu_utilization_percent", 54, 98, "%"), ("p99_latency_ms", 620, 12300, "ms")],
    },
    "logging-platform": {
        "logs": ["disk high watermark exceeded; index switched to read-only", "log ingestion queue growing because index writes are blocked"],
        "metrics": [("disk_used_percent", 71, 94, "%"), ("ingestion_queue_depth", 120, 28400, "events")],
    },
    "coredns": {
        "logs": ["upstream DNS lookup timeout", "service lookup failed: no such host"],
        "metrics": [("dns_error_percent", 0.1, 11.8, "%"), ("cpu_throttled_percent", 2, 44, "%")],
    },
    "service-mesh": {
        "logs": ["x509 certificate has expired", "mTLS handshake failed using expired intermediate certificate"],
        "metrics": [("tls_handshake_error_percent", 0.0, 72.0, "%"), ("affected_services", 0, 8, "services")],
    },
    "identity-api": {
        "logs": ["external load balancer reports no healthy upstream auth targets", "internal application health endpoint still returns 200"],
        "metrics": [("login_failure_percent", 0.6, 99.4, "%"), ("load_balancer_healthy_targets", 6, 0, "targets")],
    },
    "api-auth-middleware": {
        "deployment": ("signing-key-rotation-42", "signing-key-rotation-41", "JWT signing-key rotation"),
        "logs": ["JWT signature verification failed for rotated key identifier", "JWKS cache contains retired key identifier"],
        "metrics": [("http_401_percent", 1.1, 63.2, "%"), ("jwt_verification_error_percent", 0.0, 61.7, "%")],
    },
    "payment-api": {
        "logs": ["payment authorization timed out after 15 seconds", "provider latency elevated; retry retained idempotency key"],
        "metrics": [("payment_timeout_percent", 0.3, 39.8, "%"), ("provider_p95_latency_ms", 410, 15100, "ms")],
    },
    "payment-webhook-consumer": {
        "deployment": ("event-source-config-17", "event-source-config-16", "Event-source mapping configuration changed"),
        "logs": ["webhook endpoint returned 504", "event source mapping is disabled; callbacks are accumulating"],
        "metrics": [("webhook_backlog", 120, 14000, "events"), ("oldest_event_age_minutes", 1, 45, "min")],
    },
    "notification-worker": {
        "deployment": ("consumer-config-50", "consumer-config-500", "Consumer concurrency reduced from 500 to 50"),
        "logs": ["notification queue backlog is increasing faster than drain rate", "configured consumer concurrency is 50"],
        "metrics": [("queue_depth", 900, 280000, "messages"), ("oldest_message_age_minutes", 2, 180, "min")],
    },
    "session-cache": {
        "logs": ["Redis connection refused; no healthy session-cache replica", "session cache miss storm is increasing database load"],
        "metrics": [("redis_connection_error_percent", 0.0, 94.0, "%"), ("database_read_qps", 1200, 8700, "qps")],
    },
    "api-gateway": {
        "deployment": ("waf-ruleset-2026.08.26", "waf-ruleset-2026.08.23", "Rate-limit rule updated"),
        "logs": ["WAF rate-limit rule blocked traffic from shared NAT address", "legitimate enterprise requests returned HTTP 429"],
        "metrics": [("http_429_percent", 0.3, 27.1, "%"), ("enterprise_accounts_affected", 0, 12, "accounts")],
    },
    "checkout-edge": {
        "deployment": ("healthcheck-path-2026.08.26", "healthcheck-path-2026.08.20", "Target-group health-check path changed"),
        "logs": ["load balancer reports no healthy upstream checkout targets", "target health checks failing after path configuration change"],
        "metrics": [("healthy_targets", 8, 0, "targets"), ("http_502_percent", 0.2, 96.4, "%")],
    },
    "profile-api": {
        "deployment": ("8.2.0", "8.1.7", "Application release 8.2.0"),
        "logs": ["request failures began immediately after release 8.2.0", "profile update returned HTTP 500 after application release"],
        "metrics": [("http_5xx_percent", 0.2, 18.0, "%"), ("p95_latency_ms", 230, 1810, "ms")],
    },
    "billing-worker": {
        "deployment": ("secret-rotation-2026.08.26", "secret-rotation-2026.08.01", "Database credential secret rotated"),
        "logs": ["startup failed: database secret missing expected credential", "database authentication failed: invalid password after secret rotation"],
        "metrics": [("worker_start_failure_percent", 0.0, 100.0, "%"), ("billing_queue_depth", 320, 5200, "jobs")],
    },
    "address-verification": {
        "logs": ["address verification vendor request timed out", "internal service health remains normal while vendor requests fail"],
        "metrics": [("vendor_timeout_percent", 0.4, 88.0, "%"), ("internal_health_percent", 100.0, 100.0, "%")],
    },
}


def normalize_service_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


def get_service_record(service_name: str) -> dict[str, Any] | None:
    service = normalize_service_name(service_name)
    profile = _SERVICE_PROFILES.get(service)
    if profile is None:
        return None

    deployment = profile.get("deployment")
    deployments = []
    if deployment:
        deployments.append({
            "version": deployment[0],
            "previous_version": deployment[1],
            "deployed_at": "2026-08-26T08:10:00Z",
            "change_summary": deployment[2],
        })

    logs = [
        {
            "timestamp": f"2026-08-26T08:{20 + index:02d}:00Z",
            "level": "ERROR" if index == 0 else "WARN",
            "message": message,
        }
        for index, message in enumerate(profile.get("logs", []))
    ]
    metrics = [
        {"name": name, "before": before, "current": current, "unit": unit}
        for name, before, current, unit in profile.get("metrics", [])
    ]
    return {"deployments": deployments, "logs": logs, "metrics": metrics}
