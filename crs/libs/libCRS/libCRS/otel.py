import logging
from typing import Literal
import os
import json
from urllib.parse import quote
from loguru import logger
import threading
import time
import atexit

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import Status, StatusCode

from grpc import RpcError


class OpenTelemetryHandler(logging.Handler):
    ENVKEY_AIXCC_OTLP_ENDPOINT = "AIXCC_OTLP_ENDPOINT"
    ENVKEY_OTEL_EXPORTER_OTLP_HEADERS = "OTEL_EXPORTER_OTLP_HEADERS"
    ENVKEY_CRS_TASK_METADATA_JSON = "CRS_TASK_METADATA_JSON"

    OTEL_TIME_WINDOW = 60

    def __init__(
        self,
        service_name: str,
        action_category: Literal[
            "static_analysis",
            "dynamic_analysis",
            "fuzzing",
            "program_analysis",
            "building",
            "input_generation",
            "patch_generation",
            "testing",
            "scoring_submission",
        ],
        action_name: str,
        harness_name: str = "",
        otlp_endpoint: str = None,
        otlp_header: str = None,
        task_metadata_json: str = None,
    ):
        super().__init__()

        if self.ENVKEY_AIXCC_OTLP_ENDPOINT not in os.environ:
            return

        self.setLevel(logging.INFO)

        self.service_name = service_name
        self.action_category = action_category
        self.action_name = action_name
        self.harness_name = harness_name

        if task_metadata_json is None:
            task_metadata_json = os.environ.get(
                self.ENVKEY_CRS_TASK_METADATA_JSON, "/app/task_metadata.json"
            )
        if otlp_endpoint is None:
            otlp_endpoint = os.environ.get(
                self.ENVKEY_AIXCC_OTLP_ENDPOINT, "http://localhost:4317"
            )
        if otlp_header is None:
            otlp_header_env = os.environ.get(self.ENVKEY_OTEL_EXPORTER_OTLP_HEADERS, "")
            try:
                k, v = otlp_header_env.split("=")
                otlp_header = f"{k}={quote(v)}"
            except:
                otlp_header = otlp_header_env
        try:
            with open(task_metadata_json) as f:
                self.task_metadata = json.load(f)
        except:
            self.task_metadata = dict()

        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=otlp_header,
            timeout=5,
        )

        # Prevent retrying on RpcError
        # See https://github.com/open-telemetry/opentelemetry-python/blob/main/exporter/opentelemetry-exporter-otlp-proto-grpc/src/opentelemetry/exporter/otlp/proto/grpc/exporter.py#L297
        orig_Export = otlp_exporter._client.Export

        def _Export(*args, **kwargs):
            try:
                return orig_Export(*args, **kwargs)
            except RpcError as e:
                e.code = lambda: None
                raise e

        otlp_exporter._client.Export = _Export
        #

        resource = Resource.create({ResourceAttributes.SERVICE_NAME: self.service_name})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(processor)

        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer(service_name)

        self.current_span = None
        self.current_span_generated_at = None
        atexit.register(self.flush)

    def emit(self, record):
        try:
            if self.ENVKEY_AIXCC_OTLP_ENDPOINT not in os.environ:
                return

            # Skip opentelemetry module logs
            if record.name.startswith("opentelemetry"):
                return

            with threading.Lock():
                if (
                    self.current_span
                    and time.time() - self.current_span_generated_at
                    > self.OTEL_TIME_WINDOW
                ):
                    self.current_span.end()
                    self.current_span = None

                if self.current_span is None:
                    self.current_span_generated_at = time.time()
                    self.current_span = self.tracer.start_span(self.service_name)
                    self.current_span.set_attribute(
                        "crs.action.category", self.action_category
                    )
                    self.current_span.set_attribute("crs.action.name", self.action_name)
                    self.current_span.set_attribute(
                        "crs.action.harness", self.harness_name
                    )
                    for k, v in self.task_metadata.items():
                        self.current_span.set_attribute(k, v)

            attributes = dict()
            record_dict = record.__dict__
            record_dict["msg"] = record.getMessage()
            for k, v in record_dict.items():
                if v is not None:
                    attributes[str(k)] = str(v)
            self.current_span.add_event(name="log", attributes=attributes)
        except:
            logging.getLogger().critical(
                "Failed to emit log to OpenTelemetry.",
                exc_info=True,
            )

    def flush(self):
        try:
            if self.ENVKEY_AIXCC_OTLP_ENDPOINT not in os.environ:
                return

            # End the current span if it exists
            with threading.Lock():
                if self.current_span is not None:
                    self.current_span.end()
                    self.current_span = None
        except Exception:
            logging.getLogger().critical("Failed to flush OpenTelemetry handler.", exc_info=True)


def install_otel_logger(
    service_name: str = os.getenv("CRS_SERVICE_NAME", "CRS_SERVICE_NAME IS NOT SET"),
    action_category: Literal[
        "static_analysis",
        "dynamic_analysis",
        "fuzzing",
        "program_analysis",
        "building",
        "input_generation",
        "patch_generation",
        "testing",
        "scoring_submission",
    ] = os.getenv("CRS_ACTION_CATEGORY", "testing"),
    action_name: str = os.getenv("CRS_ACTION_NAME", "CRS_ACTION_NAME IS NOT SET"),
    harness_name: str = os.getenv("CRS_HARNESS_NAME", ""),
):
    try:
        if not logging.getLogger().handlers:
            logging.getLogger().addHandler(logging.StreamHandler())
        for handler in logging.getLogger().handlers:
            if isinstance(handler, OpenTelemetryHandler):
                logging.getLogger().removeHandler(handler)
        otel_handler = OpenTelemetryHandler(
            service_name=service_name,
            action_category=action_category,
            action_name=action_name,
            harness_name=harness_name,
        )
        logging.getLogger().addHandler(otel_handler)

        class LoguruIntegrate:
            def __init__(self):
                logger.add(self.emit, level="DEBUG")

            def emit(self, msg):
                record_dict = msg.record

                # Extract exception info if present
                exc_info = None
                if record_dict.get("exception"):
                    exc_info = (
                        record_dict["exception"].type,
                        record_dict["exception"].value,
                        record_dict["exception"].traceback,
                    )

                # Create extra fields dict for additional context
                extra = {
                    k: v
                    for k, v in record_dict.items()
                    if k
                    not in ("name", "level", "file", "line", "message", "exception")
                }

                # Create a LogRecord
                log_record = logging.LogRecord(
                    name=record_dict["name"],
                    level=record_dict["level"].no,
                    pathname=record_dict["file"].path,
                    lineno=record_dict["line"],
                    msg=record_dict["message"],
                    args=(),
                    exc_info=exc_info,
                    func=record_dict.get("function"),
                )

                # Add extra fields to the LogRecord
                for key, value in extra.items():
                    setattr(log_record, key, value)

                # Send to OpenTelemetry handler
                otel_handler.emit(log_record)

        LoguruIntegrate()
    except:
        logging.getLogger().critical(
            "Failed to install OpenTelemetry logger.",
            exc_info=True,
        )


if __name__ == "__main__":
    install_otel_logger()
    logger.debug("testing...", extra={"extrakey": "extravalue"})
    logger.debug("testing...", extra={"extrakey": "extravalue"})
    logger.debug("testing...", extra={"extrakey": "extravalue"})
    logger.debug("testing...", extra={"extrakey": "extravalue"})
    logger.debug("testing...", extra={"extrakey": "extravalue"})
    logger.debug("testing...", extra={"extrakey": "extravalue"})
