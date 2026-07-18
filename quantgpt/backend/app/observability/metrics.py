"""Prometheus metrics exposed only on the private monitoring network."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

HTTP_REQUESTS = Counter(
    "quantgpt_http_requests_total", "HTTP requests processed", ["method", "path", "status_code"]
)
HTTP_DURATION = Histogram(
    "quantgpt_http_request_duration_seconds", "HTTP request latency", ["method", "path"]
)
HTTP_ERRORS = Counter("quantgpt_http_errors_total", "Unhandled HTTP errors", ["method", "path"])


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
