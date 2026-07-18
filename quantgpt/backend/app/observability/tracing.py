"""OpenTelemetry setup. Disabled unless an OTLP collector is explicitly configured."""

from fastapi import FastAPI

from app.config.settings import get_settings
from app.logging.config import get_logger


def configure_tracing(app: FastAPI) -> None:
    settings = get_settings()
    if not settings.otel_enabled:
        return
    if not settings.otel_exporter_otlp_endpoint:
        get_logger("app.tracing").warning("tracing.disabled", reason="OTLP endpoint is not configured")
        return
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": settings.otel_service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    get_logger("app.tracing").info("tracing.enabled", service=settings.otel_service_name)
