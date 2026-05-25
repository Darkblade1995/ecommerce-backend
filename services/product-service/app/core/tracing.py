from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource


def setup_tracing(service_name: str) -> None:
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://jaeger.ecommerce.svc.cluster.local:4317",
        insecure=True,
    )
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)


def instrument_app(app) -> None:
    FastAPIInstrumentor.instrument_app(app)


def instrument_db(engine) -> None:
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


def get_tracer(name: str):
    return trace.get_tracer(name)