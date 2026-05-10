from contextlib import contextmanager, nullcontext

from core.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)
_tracer = None


def configure_tracing(app) -> None:
    global _tracer
    if not settings.otlp_endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning("OpenTelemetry dependencies are not installed; tracing disabled")
        return

    provider = TracerProvider(resource=Resource.create({"service.name": "asystqa-backend"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    _tracer = trace.get_tracer("asystqa")


@contextmanager
def trace_span(name: str, attributes: dict | None = None):
    if not _tracer:
        with nullcontext():
            yield None
        return

    with _tracer.start_as_current_span(name) as span:
        for key, value in (attributes or {}).items():
            span.set_attribute(key, value)
        yield span
