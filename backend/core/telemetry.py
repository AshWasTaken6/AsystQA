"""
Telemetry Manager - Granular Performance Monitoring for Agents

Provides distributed tracing, custom metrics, and structured logging
for all agent operations. Integrates with OpenTelemetry when available,
and falls back to local implementation.

Features:
- Span-based tracing (compatible with OpenTelemetry)
- Custom metric counters, gauges, histograms
- Structured event logging
- Agent-specific metric scopes
- Automatic error tracking
"""

import time
import uuid
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricPoint:
    """A single metric data point"""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.COUNTER


@dataclass
class SpanContext:
    """Context for a tracing span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None


@dataclass
class Span:
    """
    A trace span representing a unit of work.

    Spans can be nested to show call hierarchy.
    """
    name: str
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    parent: Optional["Span"] = None
    trace_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "OK"
    error: Optional[str] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        if exc_type:
            self.status = "ERROR"
            self.error = str(exc_val)
        return False

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute"""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span"""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })

    def duration(self) -> float:
        """Get span duration in seconds"""
        end = self.end_time or time.time()
        return end - self.start_time


class TelemetryManager:
    """
    Central telemetry manager for agents.

    Handles:
    - Distributed tracing (OpenTelemetry compatible)
    - Custom metrics
    - Event logging
    - Performance profiling

    Designed to work with or without external backends (Prometheus, Jaeger, etc.)
    """

    def __init__(
        self,
        service_name: str = "asystqa-backend",
        otlp_endpoint: Optional[str] = None,
        enable_local: bool = True,
    ):
        """
        Initialize telemetry manager.

        Args:
            service_name: Service identifier
            otlp_endpoint: Optional OTLP collector endpoint
            enable_local: Enable local metrics storage
        """
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint

        # OpenTelemetry tracer (if available)
        self._tracer = None
        if otlp_endpoint:
            self._setup_opentelemetry()

        # Local telemetry storage
        self._active_spans: Dict[str, Span] = {}
        self._agent_spans: Dict[str, List[Span]] = defaultdict(list)
        self._metrics: List[MetricPoint] = []
        self._enable_local = enable_local

        # Aggregated stats
        self._agent_executions: Dict[str, int] = defaultdict(int)
        self._agent_durations: Dict[str, float] = defaultdict(float)
        self._agent_errors: Dict[str, int] = defaultdict(int)

        logger.info(f"TelemetryManager initialized: service={service_name}")

    def _setup_opentelemetry(self) -> None:
        """Initialize OpenTelemetry if available"""
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource.create({"service.name": self.service_name})
            provider = TracerProvider(resource=resource)
            processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=self.otlp_endpoint))
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self.service_name)
            logger.info("OpenTelemetry configured")
        except ImportError:
            logger.warning("OpenTelemetry not available, using local telemetry")
        except Exception as e:
            logger.error(f"OpenTelemetry setup failed: {e}")

    @contextmanager
    def trace_span(
        self,
        agent_id: str,
        operation: str,
        attributes: Optional[Dict[str, Any]] = None,
        parent_span: Optional[Span] = None,
    ):
        """
        Create a trace span for an operation.

        Usage:
            with telemetry.trace_span("sentinel", "analyze_code") as span:
                span.set_attribute("language", "python")
                # do work
        """
        span_id = str(uuid.uuid4())[:16]
        trace_id = parent_span.trace_id if parent_span else span_id
        parent_id = parent_span.span_id if parent_span else None

        # Create span
        span = Span(
            name=f"{agent_id}.{operation}",
            span_id=span_id,
            trace_id=trace_id,
        )
        span.set_attribute("agent_id", agent_id)
        span.set_attribute("operation", operation)
        if attributes:
            span.attributes.update(attributes)

        # Track
        self._active_spans[span_id] = span
        self._agent_spans[agent_id].append(span)

        start = time.time()
        try:
            yield span
            # Success
            span.end_time = time.time()
            duration = span.duration()

            # Record metrics
            self._record_metric(f"agent.{agent_id}.{operation}.duration", duration)
            self._agent_executions[agent_id] += 1
            self._agent_durations[agent_id] += duration

        except Exception as e:
            span.end_time = time.time()
            span.status = "ERROR"
            span.error = str(e)
            self._agent_errors[agent_id] += 1
            raise
        finally:
            self._active_spans.pop(span_id, None)

    def start_session(self, agent_id: str, session_id: str) -> None:
        """Start a new agent session"""
        self._record_event(
            "session.start",
            {"agent_id": agent_id, "session_id": session_id}
        )

    def end_session(self, agent_id: str) -> None:
        """End an agent session"""
        self._record_event(
            "session.end",
            {"agent_id": agent_id}
        )

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.COUNTER,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a custom metric"""
        self._record_metric(name, value, metric_type, labels)

    def _record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.COUNTER,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Internal metric recording"""
        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
            metric_type=metric_type,
        )
        self._metrics.append(metric)

        # Could ship to Prometheus Pushgateway here

    def _record_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        level: str = "INFO",
    ) -> None:
        """Record a structured event"""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "level": level,
            **data,
        }
        logger.info(f"Telemetry event: {event_type}", extra=event)

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get statistics for a specific agent"""
        executions = self._agent_executions[agent_id]
        total_time = self._agent_durations[agent_id]
        errors = self._agent_errors[agent_id]

        return {
            "agent_id": agent_id,
            "total_executions": executions,
            "total_duration": total_time,
            "avg_duration": total_time / executions if executions > 0 else 0,
            "error_count": errors,
            "error_rate": errors / executions if executions > 0 else 0,
            "active_spans": sum(1 for s in self._active_spans.values() if s.trace_id),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics"""
        return {
            "agents": {
                aid: self.get_agent_stats(aid)
                for aid in self._agent_executions.keys()
            },
            "recent_metrics": self._metrics[-100:],  # Last 100
        }

    def reset_agent_stats(self, agent_id: Optional[str] = None) -> None:
        """Reset statistics for agent or all agents"""
        if agent_id:
            self._agent_executions[agent_id] = 0
            self._agent_durations[agent_id] = 0
            self._agent_errors[agent_id] = 0
        else:
            self._agent_executions.clear()
            self._agent_durations.clear()
            self._agent_errors.clear()
            self._metrics.clear()

    def flush(self) -> None:
        """
        Flush metrics to external backend.
        Called periodically or on shutdown.
        """
        # In real implementation, would batch and send to Prometheus, etc.
        logger.debug(f"Flushing {len(self._metrics)} metrics")
        self._metrics.clear()


# Global telemetry manager instance
_global_telemetry: Optional[TelemetryManager] = None


def get_telemetry_manager() -> TelemetryManager:
    """Get global telemetry manager"""
    global _global_telemetry
    if _global_telemetry is None:
        from core.config import settings
        _global_telemetry = TelemetryManager(
            otlp_endpoint=settings.otlp_endpoint,
        )
    return _global_telemetry
