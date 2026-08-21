"""Gateway middleware — correlation IDs, observability, size limits, rate-limit hook."""

import hashlib
import uuid

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from apps.api.gateway.errors import structured_error
from apps.api.gateway.rate_limit import NoOpRateLimiter, RateLimiter
from apps.api.tenancy import parse_tenant_id

logger = structlog.get_logger()

DEFAULT_MAX_BODY_BYTES = 1_048_576  # 1 MiB
DEFAULT_MAX_RESPONSE_BYTES = 10_485_760  # 10 MiB


def _client_key(request: Request) -> str:
    """Hash identity material so bearer tokens are never used as log/rate-limit keys."""
    raw = request.headers.get("Authorization") or (request.client.host if request.client else "unknown")
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()


async def _read_response_body(response: Response) -> bytes:
    existing = getattr(response, "body", None)
    if isinstance(existing, bytes) and existing:
        return existing
    chunks: list[bytes] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
    return b"".join(chunks)


class GatewayMiddleware(BaseHTTPMiddleware):
    """Cross-cutting gateway concerns applied before route handlers."""

    def __init__(
        self,
        app,
        *,
        rate_limiter: RateLimiter | None = None,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter or NoOpRateLimiter()
        self.max_body_bytes = max_body_bytes
        self.max_response_bytes = max_response_bytes

    def _json_error(
        self,
        *,
        status_code: int,
        message: str,
        request_id: str,
        headers: dict[str, str] | None = None,
        error: str | None = None,
    ) -> JSONResponse:
        payload = structured_error(status_code=status_code, message=message, request_id=request_id)
        if error:
            payload["error"] = error
        response_headers = {"X-Request-ID": request_id, **(headers or {})}
        return JSONResponse(status_code=status_code, content=payload, headers=response_headers)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        tenant_id = parse_tenant_id(request)
        request.state.tenant_id = tenant_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            tenant_id=tenant_id,
            method=request.method,
            path=request.url.path,
        )

        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_bytes:
            logger.warning("Request body too large", content_length=content_length, request_id=request_id)
            return self._json_error(
                status_code=413,
                message="Request body too large",
                request_id=request_id,
            )

        rate_result = await self.rate_limiter.check(request, client_key=_client_key(request))
        if not rate_result.allowed:
            retry_after = rate_result.retry_after_seconds or 60
            return self._json_error(
                status_code=429,
                message="Rate limit exceeded",
                request_id=request_id,
                headers={"Retry-After": str(int(retry_after))},
            )

        logger.info("Request started", request_id=request_id)
        response = await call_next(request)
        headers = MutableHeaders(response.headers)
        headers["X-Request-ID"] = request_id
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = "no-referrer"
        headers["Cache-Control"] = "no-store"
        headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if rate_result.limit is not None:
            headers["X-RateLimit-Limit"] = str(rate_result.limit)
        if rate_result.remaining is not None:
            headers["X-RateLimit-Remaining"] = str(rate_result.remaining)

        body = await _read_response_body(response)
        if len(body) > self.max_response_bytes:
            logger.warning("Response body too large", size=len(body), request_id=request_id)
            return self._json_error(
                status_code=500,
                message="Response body too large",
                request_id=request_id,
                error="response_too_large",
            )

        if "content-length" in headers:
            del headers["content-length"]
        logger.info("Request completed", status_code=response.status_code, request_id=request_id)
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(headers),
            media_type=response.media_type,
            background=getattr(response, "background", None),
        )
