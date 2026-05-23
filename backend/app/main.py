"""Minimal HTTP entrypoint for the HLL Vietnam backend bootstrap."""

from __future__ import annotations

import json
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import get_allowed_origins, get_bind_address
from .payloads import build_error_payload
from .routes import resolve_get_payload


class HealthHandler(BaseHTTPRequestHandler):
    """Serve the minimal routes required for the backend bootstrap."""

    server_version = "HLLVietnamBackend/0.1"

    def do_OPTIONS(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler interface
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_default_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler interface
        try:
            status, payload = resolve_get_payload(self.path)
        except Exception:  # noqa: BLE001 - preserve HTTP/CORS response on route failures
            self._write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_error_payload("Unexpected backend error"),
            )
            return

        if status is None:
            self._write_json(
                HTTPStatus.NOT_FOUND,
                {"status": "error", "message": "Route not found"},
            )
            return

        self._write_json(status, payload)

    def log_message(self, format: str, *args: object) -> None:
        # Keep local startup output clean unless future tasks need request logging.
        return

    def _write_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, default=_json_default).encode("utf-8")
        self.send_response(status)
        self._send_default_headers(content_length=len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_default_headers(self, content_length: int | None = None) -> None:
        origin = self.headers.get("Origin")
        if origin in get_allowed_origins():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

        self.send_header("Content-Type", "application/json; charset=utf-8")
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))


def create_server() -> ThreadingHTTPServer:
    """Build the HTTP server using the package-supported handler and bind settings."""
    host, port = get_bind_address()
    return ThreadingHTTPServer((host, port), HealthHandler)


def _json_default(value: object) -> str:
    """Serialize PostgreSQL date/time values before they can abort an HTTP response."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def run() -> None:
    """Start the local bootstrap server."""
    host, port = get_bind_address()
    server = create_server()
    print(f"HLL Vietnam backend bootstrap listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
