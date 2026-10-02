from __future__ import annotations

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class APISecurityMiddleware:
    """Apply API-safe headers and cheap request guards before body parsing."""

    def __init__(self, app: ASGIApp, *, max_request_body_bytes: int) -> None:
        self.app = app
        self.max_request_body_bytes = max_request_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        headers = Headers(scope=scope)
        if path.endswith("/imports/preview"):
            rejected = self._request_rejection(headers)
            if rejected is not None:
                await rejected(scope, receive, send)
                return

        async def security_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers["X-Content-Type-Options"] = "nosniff"
                response_headers["Referrer-Policy"] = "no-referrer"
                response_headers["X-Frame-Options"] = "DENY"
                if path.startswith("/api/"):
                    response_headers["Content-Security-Policy"] = (
                        "default-src 'none'; frame-ancestors 'none'; "
                        "base-uri 'none'; form-action 'none'"
                    )
                if _is_sensitive(path):
                    response_headers["Cache-Control"] = "no-store, private"
                    response_headers["Pragma"] = "no-cache"
            await send(message)

        await self.app(scope, receive, security_send)

    def _request_rejection(self, headers: Headers) -> JSONResponse | None:
        content_length = headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > self.max_request_body_bytes
            except ValueError:
                too_large = True
            if too_large:
                return _error_response(
                    413,
                    "REQUEST_BODY_TOO_LARGE",
                    "Request body exceeds the configured API limit",
                )
        content_type = headers.get("content-type", "")
        charset = _charset(content_type)
        if charset is not None and charset not in {"utf-8", "utf8"}:
            return _error_response(
                415,
                "ENCODING_INVALID",
                "CSV preview JSON must use UTF-8 encoding",
            )
        return None


def _charset(content_type: str) -> str | None:
    for parameter in content_type.split(";")[1:]:
        name, separator, value = parameter.strip().partition("=")
        if separator and name.lower() == "charset":
            return value.strip('"').lower()
    return None


def _is_sensitive(path: str) -> bool:
    return (
        path.startswith("/api/v1/results")
        or path.endswith("/calculations")
        or path.endswith("/pii")
        or path.endswith("/export")
    )


def _error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
        headers={
            "Cache-Control": "no-store, private",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": (
                "default-src 'none'; frame-ancestors 'none'; "
                "base-uri 'none'; form-action 'none'"
            ),
        },
    )
