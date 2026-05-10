from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_DURATION: Any
SCAN_TOTAL: Any
ERRORS_TOTAL: Any
AGENT_DURATION: Any
MEMORY_FILE_SIZE: Any

REQUEST_DURATION = Histogram(
    "asystqa_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["endpoint", "status_code"],
)
SCAN_TOTAL = Counter(
    "asystqa_scan_total",
    "Completed code scans.",
    ["language", "status"],
)
ERRORS_TOTAL = Counter(
    "asystqa_errors_total",
    "Application errors.",
    ["error_type", "module"],
)
AGENT_DURATION = Histogram(
    "asystqa_pipeline_agent_duration_seconds",
    "Agent execution duration in seconds.",
    ["agent_name"],
)
MEMORY_FILE_SIZE = Gauge(
    "asystqa_memory_file_size_bytes",
    "Size of the JSON memory store.",
)


def observe_request(endpoint: str, status_code: str, duration: float) -> None:
    if REQUEST_DURATION:
        REQUEST_DURATION.labels(endpoint=endpoint, status_code=status_code).observe(duration)


def increment_scan(language: str, status: str) -> None:
    if SCAN_TOTAL:
        SCAN_TOTAL.labels(language=language, status=status).inc()


def increment_error(error_type: str, module: str) -> None:
    if ERRORS_TOTAL:
        ERRORS_TOTAL.labels(error_type=error_type, module=module).inc()


def observe_agent(agent_name: str, duration: float) -> None:
    if AGENT_DURATION:
        AGENT_DURATION.labels(agent_name=agent_name).observe(duration)


def update_memory_file_size(path: Path) -> None:
    if MEMORY_FILE_SIZE:
        MEMORY_FILE_SIZE.set(path.stat().st_size if path.exists() else 0)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


class timed_agent:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.started_at = 0.0
        self.duration = 0.0

    def __enter__(self):
        self.started_at = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.duration = time.perf_counter() - self.started_at
        observe_agent(self.agent_name, self.duration)
        return False
